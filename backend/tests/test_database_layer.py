from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.agents.complaint.constants import ComplaintAssistantIntent
from app.agents.complaint.graph import (
    ComplaintAgentRuntime,
    build_complaint_graph,
    route_from_intent,
    run_complaint_assistant,
)
from app.agents.complaint.schemas import (
    ComplaintEditOperation,
    ComplaintEditResult,
    ComplaintExtractionResult,
    ComplaintFieldExtraction,
    ProvisionalRiskAssessment,
)
from app.agents.quality_war_room.agents.compliance_auditor import run_compliance_auditor
from app.agents.quality_war_room.context_builder import build_quality_war_room_context
from app.agents.quality_war_room.graph import run_quality_war_room
from app.agents.quality_war_room.schemas import SpecialistOutput
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import PharmaQSentinelError
from app.main import create_app
from app.models import (
    ActorType,
    AgentRun,
    AuditEvent,
    Base,
    Batch,
    BatchImpactRun,
    Complaint,
    ComplaintAttachment,
    ComplaintDraft,
    ComplaintStatus,
    DuplicateAnalysisRun,
    EvidenceType,
    ExtractionStatus,
    FieldEvidence,
    InvestigationPlaybookRun,
    InvestigationReviewAction,
    MessageRole,
    Priority,
    Product,
    ProductType,
    QualityWarRoomEvent,
    QualityWarRoomRun,
    RiskAssessmentVersion,
    Severity,
)
from app.models.base import utc_now
from app.models.reference import batch_material_lots
from app.repositories.attachments import ComplaintAttachmentRepository
from app.repositories.audit_events import AuditEventRepository
from app.repositories.batch_impact import BatchImpactRunRepository
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.complaint_versions import ComplaintVersionRepository
from app.repositories.complaints import ComplaintRepository
from app.repositories.evidence import FieldEvidenceRepository
from app.repositories.messages import ComplaintMessageRepository
from app.schemas.complaints import SaveComplaintRequest
from app.services.batch_impact import build_batch_impact_analysis
from app.services.batch_impact.language_rules import assert_safe_batch_impact_language
from app.services.complaint_intelligence import run_duplicate_analysis
from app.services.complaint_save import save_complaint
from app.services.complaint_snapshots import (
    ComplaintSnapshotService,
    checksum_snapshot,
    draft_to_canonical_dict,
)
from app.services.documents.docx_parser import DocxDocumentParser
from app.services.documents.email_parser import EmailDocumentParser
from app.services.documents.pdf_parser import PdfDocumentParser
from app.services.documents.security import detect_mime, validate_extension
from app.services.documents.text_parser import TextDocumentParser
from app.services.investigation.playbook_engine import (
    create_investigation_playbook,
    record_review_action,
)
from app.services.investigation.schemas import InvestigationReviewActionRequest
from app.services.llm import LLMUsage, StructuredLLMResult
from app.services.quality import assess_pharma_risk
from app.services.quality.completeness import evaluate_completeness
from app.services.quality.defect_taxonomy import classify_defects
from app.services.quality.safety_router import route_safety
from app.services.quality.safety_rules import evaluate_safety_rules
from app.services.quality.schemas import PharmaRiskAssessment, SafetyReviewRoute
from app.services.reports import (
    build_complaint_brief,
    render_complaint_brief_html,
    render_complaint_brief_pdf,
)
from app.utilities.seed_database import seed_database

pytestmark = pytest.mark.mysql


EXPECTED_TABLES = {
    "agent_runs",
    "audit_events",
    "batch_equipment",
    "batch_impact_runs",
    "batch_material_lots",
    "batch_packaging_material_lots",
    "batches",
    "capas",
    "complaint_attachments",
    "complaint_drafts",
    "complaint_messages",
    "complaint_number_sequences",
    "complaint_versions",
    "complaints",
    "deviations",
    "distribution_records",
    "duplicate_analysis_runs",
    "equipment",
    "field_evidence",
    "historical_complaints",
    "investigation_playbook_runs",
    "investigation_review_actions",
    "manufacturing_lines",
    "material_lots",
    "packaging_material_lots",
    "products",
    "quality_war_room_events",
    "quality_war_room_runs",
    "risk_assessment_versions",
    "suppliers",
    "warehouse_inventory",
}


@pytest.fixture(scope="session")
def test_database_url() -> str:
    settings = get_settings()
    url = make_url(settings.test_database_url.get_secret_value())
    if url.drivername != "mysql+pymysql":
        pytest.fail("TEST_DATABASE_URL must use mysql+pymysql")
    if not url.database or not url.database.endswith("_test"):
        pytest.fail("Refusing destructive test setup: test database name must end in _test")
    print(f"Using MySQL test database: {url.database}")
    return url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    backend_dir = Path(__file__).resolve().parents[1]
    return Config(str(backend_dir / "alembic.ini"))


@pytest.fixture(scope="session")
def mysql_engine(test_database_url: str, alembic_config: Config) -> Engine:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            version = connection.exec_driver_sql("SELECT VERSION()").scalar_one()
            print(f"MySQL server version: {version}")
    except OperationalError as exc:
        pytest.skip(f"Safe MySQL test database is unavailable: {exc}")

    Base.metadata.drop_all(engine)
    command.stamp(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(mysql_engine: Engine) -> Session:
    connection = mysql_engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def seed_demo_data(db: Session) -> dict[str, int]:
    counts = seed_database(db)
    db.flush()
    return counts


def test_alembic_upgrade_on_empty_mysql_test_database(
    mysql_engine: Engine,
    alembic_config: Config,
) -> None:
    Base.metadata.drop_all(mysql_engine)
    command.stamp(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    inspector = inspect(mysql_engine)
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))

    command.downgrade(alembic_config, "base")
    remaining_tables = set(inspect(mysql_engine).get_table_names())
    assert EXPECTED_TABLES.isdisjoint(remaining_tables)
    command.upgrade(alembic_config, "head")


def test_table_creation(mysql_engine: Engine) -> None:
    inspector = inspect(mysql_engine)
    assert len(EXPECTED_TABLES.intersection(inspector.get_table_names())) == len(EXPECTED_TABLES)


def test_uuid_generation(db_session: Session) -> None:
    product = Product(
        product_code="TEST-PROD-UUID",
        product_name="Demo UUID Product",
        product_type=ProductType.FDF.value,
        is_demo=True,
        record_source="MANUAL_DEMO_SEED",
    )
    db_session.add(product)
    db_session.flush()
    assert len(product.id) == 36
    assert product.id.count("-") == 4


def test_product_to_batch_relationship(db_session: Session) -> None:
    seed_demo_data(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    assert batch.product.product_name == "Amoxicillin Capsules 500 mg"


def test_batch_to_material_relationship(db_session: Session) -> None:
    seed_demo_data(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    assert {lot.lot_number for lot in batch.material_lots} >= {"AMX-API-L2405", "MCC-L2406"}


def test_batch_to_packaging_lot_relationship(db_session: Session) -> None:
    seed_demo_data(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    assert {lot.lot_number for lot in batch.packaging_material_lots} == {"ALU-BLISTER-L2406"}


def test_batch_to_equipment_relationship(db_session: Session) -> None:
    seed_demo_data(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    equipment_codes = {record.equipment_code for record in batch.equipment_records}
    assert {"EQ-PL04-SEALER", "EQ-PL04-CAMERA"}.issubset(equipment_codes)


def test_deviation_to_capa_relationship(db_session: Session) -> None:
    seed_demo_data(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    deviation = next(item for item in batch.deviations if item.deviation_number == "DEV-2026-023")
    assert [capa.capa_number for capa in deviation.capas] == ["CAPA-2026-014"]


def test_complaint_draft_creation(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-db-test",
        product_type=ProductType.FDF.value,
        quantity_affected=Decimal("1.000"),
        risk_confidence=Decimal("0.7500"),
    )
    assert draft.status == ComplaintStatus.DRAFT.value
    assert draft.quantity_affected == Decimal("1.000")


def create_draft_and_complaint(db: Session) -> tuple[ComplaintDraft, Complaint]:
    draft = ComplaintDraftRepository(db).create(
        thread_id="thread-version-test",
        product_name="Amoxicillin Capsules 500 mg",
        batch_lot_number="BMX240602",
        quantity_affected=Decimal("12.000"),
        risk_confidence=Decimal("0.8123"),
    )
    complaint = ComplaintRepository(db).create(
        complaint_number="PQ-2026-0001",
        committed_by="database-test",
        committed_at=utc_now(),
        committed_from_draft_id=draft.id,
        product_name=draft.product_name,
        batch_lot_number=draft.batch_lot_number,
    )
    return draft, complaint


def seed_saveable_draft(
    db: Session,
    *,
    thread_id: str = "thread-saveable",
    missing_fields: dict[str, object] | None = None,
    adverse_event_signal: bool | None = None,
) -> ComplaintDraft:
    draft = ComplaintDraftRepository(db).create(
        thread_id=thread_id,
        complaint_source="Email",
        customer_name="Apollo Pharmacy",
        product_type=ProductType.FDF.value,
        product_name="Amoxicillin Capsules 500 mg",
        product_strength_grade="500 mg",
        batch_lot_number="BMX240602",
        quantity_affected=Decimal("12.000"),
        quantity_unit="capsules",
        complaint_type="Capsule discolouration",
        complaint_date=date(2026, 7, 30),
        detailed_description="Customer reported discoloured capsules from batch BMX240602.",
        adverse_event_signal=adverse_event_signal,
        suggested_severity=Severity.MAJOR.value,
        suggested_priority=Priority.HIGH.value,
        safety_route="PRODUCT_QUALITY",
        risk_rationale="Initial AI-suggested assessment requires QA review.",
        risk_confidence=Decimal("0.8200"),
        missing_fields=missing_fields,
    )
    db.add(
        RiskAssessmentVersion(
            draft_id=draft.id,
            version_number=1,
            severity=Severity.MAJOR.value,
            priority=Priority.HIGH.value,
            risk_rationale="Initial AI-suggested assessment requires QA review.",
            confidence=Decimal("0.8200"),
            safety_route="PRODUCT_QUALITY",
            provider_name="openai",
            requested_model="test-model",
            actual_model="test-model",
        )
    )
    db.flush()
    return draft


def save_request(
    *,
    idempotency_key: str = "save-key-0001",
    acknowledged: bool = True,
    reviewed_by: str = "Demo QA User",
    review_meaning: str = "I reviewed the complaint information and AI-suggested assessment.",
) -> dict[str, object]:
    return {
        "reviewed_by": reviewed_by,
        "review_meaning": review_meaning,
        "missing_information_acknowledged": acknowledged,
        "change_reason": "Initial complaint registration",
        "idempotency_key": idempotency_key,
    }


def test_complaint_version_snapshot_generation(db_session: Session) -> None:
    draft, complaint = create_draft_and_complaint(db_session)
    version = ComplaintSnapshotService(db_session).create_version_from_draft(
        draft_id=draft.id,
        complaint_id=complaint.id,
        created_by="database-test",
        change_reason="Initial deterministic database-layer test snapshot",
    )
    assert version.version_number == 1
    assert version.snapshot["batch_lot_number"] == "BMX240602"
    assert len(version.checksum) == 64


def test_stable_snapshot_checksum(db_session: Session) -> None:
    draft, _complaint = create_draft_and_complaint(db_session)
    first = draft_to_canonical_dict(draft)
    second = draft_to_canonical_dict(draft)
    assert checksum_snapshot(first) == checksum_snapshot(second)


def test_unique_complaint_number_constraint(db_session: Session) -> None:
    create_draft_and_complaint(db_session)
    with pytest.raises(IntegrityError):
        ComplaintRepository(db_session).create(
            complaint_number="PQ-2026-0001",
            committed_by="database-test",
            committed_at=utc_now(),
        )


def test_save_complaint_creates_ledger_record_version_and_audit(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session)
    client = TestClient(make_app_with_session(db_session), raise_server_exceptions=False)

    response = client.post(f"/api/v1/complaint-drafts/{draft.id}/save", json=save_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["complaint_number"].startswith("PQC-")
    assert payload["status"] == ComplaintStatus.COMMITTED.value
    assert payload["product_name"] == "Amoxicillin Capsules 500 mg"
    assert payload["review_meaning"] == "I reviewed the complaint information and AI-suggested assessment."
    db_session.refresh(draft)
    assert draft.status == ComplaintStatus.COMMITTED.value
    complaint = db_session.get(Complaint, payload["id"])
    assert complaint is not None
    versions = ComplaintVersionRepository(db_session).list_for_complaint(complaint.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert len(versions[0].checksum) == 64
    assert versions[0].snapshot["risk_assessment_reference"]["id"] == complaint.latest_risk_assessment_id
    events = db_session.scalars(select(AuditEvent).where(AuditEvent.complaint_id == complaint.id)).all()
    assert [event.event_type for event in events] == ["SAVE_COMPLAINT"]


def test_save_complaint_rejects_missing_required_data(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-save-missing")
    draft.detailed_description = None
    client = TestClient(make_app_with_session(db_session))

    response = client.post(f"/api/v1/complaint-drafts/{draft.id}/save", json=save_request())

    assert response.status_code == 422
    assert "meaningful complaint description" in response.json()["detail"]


def test_save_complaint_rejects_missing_reviewer(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-save-reviewer")
    client = TestClient(make_app_with_session(db_session))
    body = save_request()
    body["reviewed_by"] = ""

    response = client.post(f"/api/v1/complaint-drafts/{draft.id}/save", json=body)

    assert response.status_code == 422


def test_save_complaint_missing_information_acknowledgement(db_session: Session) -> None:
    draft = seed_saveable_draft(
        db_session,
        thread_id="thread-save-missing-info",
        missing_fields={"customer_contact": ["Not provided"]},
    )
    client = TestClient(make_app_with_session(db_session))

    blocked = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/save",
        json=save_request(idempotency_key="save-key-missing-blocked", acknowledged=False),
    )
    assert blocked.status_code == 409

    draft = seed_saveable_draft(
        db_session,
        thread_id="thread-save-missing-info-ack",
        missing_fields={"customer_contact": ["Not provided"]},
    )
    saved = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/save",
        json=save_request(idempotency_key="save-key-missing-ack", acknowledged=True),
    )
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["missing_information_acknowledged"] is True
    assert payload["unresolved_missing_information"] == {"customer_contact": ["Not provided"]}


def test_save_complaint_critical_conflict_blocks_save(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-save-conflict")
    FieldEvidenceRepository(db_session).add(
        draft_id=draft.id,
        field_name="batch_lot_number",
        field_value={"value": "BMX240602"},
        evidence_type=EvidenceType.USER_TEXT,
        is_active=True,
    )
    FieldEvidenceRepository(db_session).add(
        draft_id=draft.id,
        field_name="batch_lot_number",
        field_value={"value": "BMX240601"},
        evidence_type=EvidenceType.PDF,
        is_active=True,
    )
    client = TestClient(make_app_with_session(db_session), raise_server_exceptions=False)

    response = client.post(f"/api/v1/complaint-drafts/{draft.id}/save", json=save_request())

    assert response.status_code == 409
    assert "critical evidence conflict" in response.json()["detail"]


def test_save_complaint_uses_sequence_numbers_without_counting(db_session: Session) -> None:
    first = seed_saveable_draft(db_session, thread_id="thread-save-seq-1")
    second = seed_saveable_draft(db_session, thread_id="thread-save-seq-2")
    client = TestClient(make_app_with_session(db_session))

    first_response = client.post(
        f"/api/v1/complaint-drafts/{first.id}/save",
        json=save_request(idempotency_key="save-key-seq-1"),
    )
    second_response = client.post(
        f"/api/v1/complaint-drafts/{second.id}/save",
        json=save_request(idempotency_key="save-key-seq-2"),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_sequence = int(first_response.json()["complaint_number"].split("-")[-1])
    second_sequence = int(second_response.json()["complaint_number"].split("-")[-1])
    assert second_sequence == first_sequence + 1


def test_save_complaint_idempotency_returns_same_result(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-save-idempotency")
    client = TestClient(make_app_with_session(db_session), raise_server_exceptions=False)
    body = save_request(idempotency_key="save-key-idempotent")

    first = client.post(f"/api/v1/complaint-drafts/{draft.id}/save", json=body)
    second = client.post(f"/api/v1/complaint-drafts/{draft.id}/save", json=body)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    complaint_id = first.json()["id"]
    assert len(ComplaintVersionRepository(db_session).list_for_complaint(complaint_id)) == 1
    events = db_session.scalars(select(AuditEvent).where(AuditEvent.complaint_id == complaint_id)).all()
    assert len(events) == 1


def test_save_complaint_duplicate_save_prevented(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-save-duplicate")
    client = TestClient(make_app_with_session(db_session))

    first = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/save",
        json=save_request(idempotency_key="save-key-dup-1"),
    )
    second = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/save",
        json=save_request(idempotency_key="save-key-dup-2"),
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert "already been saved" in second.json()["detail"]


def test_save_complaint_rolls_back_when_audit_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-save-rollback")
    original_append = AuditEventRepository.append

    def broken_append(self: AuditEventRepository, **kwargs: object):
        if kwargs.get("event_type") == "SAVE_COMPLAINT":
            raise RuntimeError("audit write failed")
        return original_append(self, **kwargs)

    monkeypatch.setattr(AuditEventRepository, "append", broken_append)
    client = TestClient(make_app_with_session(db_session), raise_server_exceptions=False)

    response = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/save",
        json=save_request(idempotency_key="save-key-rollback"),
    )

    assert response.status_code == 500
    db_session.expire_all()
    assert (
        ComplaintRepository(db_session).get_by_save_idempotency_key("save-key-rollback")
        is None
    )
    reloaded_draft = db_session.get(ComplaintDraft, draft.id)
    assert reloaded_draft is None or reloaded_draft.status == ComplaintStatus.DRAFT.value


def test_ledger_endpoints_search_filters_versions_and_timeline(db_session: Session) -> None:
    draft = seed_saveable_draft(db_session, thread_id="thread-ledger")
    client = TestClient(make_app_with_session(db_session))
    saved = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/save",
        json=save_request(idempotency_key="save-key-ledger"),
    )
    complaint_id = saved.json()["id"]

    list_response = client.get("/api/v1/complaints", params={"product_name": "Amoxicillin", "limit": 10})
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == complaint_id

    filtered = client.get("/api/v1/complaints", params={"batch_number": "BMX240602", "severity": "MAJOR"})
    assert filtered.status_code == 200
    assert filtered.json()["items"][0]["complaint_number"].startswith("PQC-")

    detail = client.get(f"/api/v1/complaints/{complaint_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == complaint_id

    versions = client.get(f"/api/v1/complaints/{complaint_id}/versions")
    assert versions.status_code == 200
    assert versions.json()[0]["snapshot"]["complaint"]["complaint_number"].startswith("PQC-")

    timeline = client.get(f"/api/v1/complaints/{complaint_id}/timeline")
    assert timeline.status_code == 200
    assert "SAVE_COMPLAINT" in {item["event_type"] for item in timeline.json()["items"]}


def seed_saved_complaint_with_report_context(db_session: Session) -> Complaint:
    draft = seed_saveable_draft(db_session, thread_id="thread-report")
    attachment = ComplaintAttachment(
        draft_id=draft.id,
        original_filename="amoxicillin-demo-complaint.pdf",
        stored_filename="safe-upload-name.pdf",
        mime_type="application/pdf",
        file_size=2048,
        sha256_checksum="a" * 64,
        storage_path="C:/private/uploads/safe-upload-name.pdf",
        extracted_text=(
            "Apollo Pharmacy reported discoloured capsules. Hinglish note: "
            "capsule ka colour badal gaya."
        ),
        extraction_status=ExtractionStatus.COMPLETE.value,
        extraction_stage="COMPLETE",
        extraction_progress=100,
    )
    db_session.add(attachment)
    db_session.flush()
    db_session.add_all(
        [
            FieldEvidence(
                draft_id=draft.id,
                field_name="batch_lot_number",
                field_value={"value": "BMX240602"},
                evidence_type=EvidenceType.USER_CORRECTION.value,
                source_excerpt="Sorry, the batch is BMX240602.",
                confidence=Decimal("1.0000"),
                extraction_method="EDIT_COMPLAINT",
                is_explicit=True,
                is_active=True,
            ),
            FieldEvidence(
                draft_id=draft.id,
                field_name="detailed_description",
                field_value={"value": draft.detailed_description},
                evidence_type=EvidenceType.USER_TEXT.value,
                source_excerpt="Hinglish: capsule ka colour badal gaya.",
                confidence=Decimal("0.9000"),
                extraction_method="LOG_COMPLAINT",
                is_explicit=True,
                is_active=True,
            ),
        ]
    )
    db_session.flush()
    complaint = save_complaint(
        db_session,
        draft_id=draft.id,
        request=SaveComplaintRequest.model_validate(
            save_request(idempotency_key="report-save-key"),
        ),
    )
    db_session.add(
        FieldEvidence(
            draft_id=draft.id,
            field_name="batch_lot_number",
            field_value={"value": "AMX240602"},
            evidence_type=EvidenceType.PDF.value,
            source_attachment_id=attachment.id,
            page_number=1,
            source_excerpt="PDF said AMX240602 <script>alert('x')</script> खराब",
            confidence=Decimal("0.7100"),
            extraction_method="EXTRACT_DOCUMENT",
            is_explicit=True,
            is_active=False,
        )
    )
    db_session.flush()
    return complaint


def test_inspection_brief_complete_json_html_pdf_and_security(db_session: Session) -> None:
    complaint = seed_saved_complaint_with_report_context(db_session)

    brief = build_complaint_brief(db_session, complaint_id=complaint.id)
    html = render_complaint_brief_html(brief)
    pdf = render_complaint_brief_pdf(brief)

    section_titles = {section.title for section in brief.sections}
    assert "Complaint Snapshot Checksum" in section_titles
    assert "Complete Audit Timeline" in section_titles
    assert "Provider, Model And Prompt Versions" in section_titles
    assert len(brief.snapshot_checksum) == 64
    assert brief.source_documents[0].original_filename == "amoxicillin-demo-complaint.pdf"
    assert "storage_path" not in brief.model_dump_json()
    assert "C:/private/uploads" not in brief.model_dump_json()
    assert "&lt;script&gt;" in html
    assert "<script>alert" not in html
    assert "chain of thought" not in brief.model_dump_json().lower()
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_inspection_brief_endpoint_formats_and_unsupported_format(db_session: Session) -> None:
    complaint = seed_saved_complaint_with_report_context(db_session)
    client = TestClient(make_app_with_session(db_session))

    json_response = client.get(f"/api/v1/complaints/{complaint.id}/inspection-brief?format=json")
    html_response = client.get(f"/api/v1/complaints/{complaint.id}/inspection-brief?format=html")
    pdf_response = client.get(f"/api/v1/complaints/{complaint.id}/inspection-brief?format=pdf")
    unsupported_response = client.get(f"/api/v1/complaints/{complaint.id}/inspection-brief?format=docx")

    assert json_response.status_code == 200
    assert json_response.json()["snapshot_checksum"]
    assert html_response.status_code == 200
    assert "text/html" in html_response.headers["content-type"]
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
    assert unsupported_response.status_code == 422


def test_inspection_brief_requires_saved_version(db_session: Session) -> None:
    draft, complaint = create_draft_and_complaint(db_session)
    assert draft.id

    with pytest.raises(PharmaQSentinelError) as error:
        build_complaint_brief(db_session, complaint_id=complaint.id)

    assert error.value.status_code == 409


def test_unique_batch_number_constraint(db_session: Session) -> None:
    seed_demo_data(db_session)
    product = db_session.scalars(select(Product).where(Product.product_code == "AMOX-CAP-500")).one()
    duplicate = Batch(
        batch_number="BMX240602",
        product_id=product.id,
        status="RELEASED_DEMO",
        is_demo=True,
        record_source="MANUAL_DEMO_SEED",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_duplicate_join_relationship_prevention(db_session: Session) -> None:
    seed_demo_data(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    material_lot = batch.material_lots[0]
    with pytest.raises(IntegrityError):
        db_session.execute(
            batch_material_lots.insert().values(
                batch_id=batch.id,
                material_lot_id=material_lot.id,
            )
        )
        db_session.flush()


def test_audit_event_append(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-audit-test")
    event = AuditEventRepository(db_session).append(
        draft_id=draft.id,
        event_type="DRAFT_CREATED",
        actor_type=ActorType.SYSTEM,
        tool_name="database-test",
        reason="Testing append-only audit repository",
        old_value=None,
        new_value={"status": ComplaintStatus.DRAFT.value},
    )
    assert event.id
    persisted_event = db_session.scalars(
        select(AuditEvent).where(AuditEvent.draft_id == draft.id)
    ).one()
    assert persisted_event.event_type == "DRAFT_CREATED"


def test_audit_repository_has_no_update_operation(db_session: Session) -> None:
    repository = AuditEventRepository(db_session)
    assert not hasattr(repository, "update")
    assert not hasattr(repository, "delete")


def test_seed_command_success(db_session: Session) -> None:
    counts = seed_demo_data(db_session)
    assert counts["products"] == 5
    assert counts["batches"] == 3
    assert counts["historical_complaints"] == 13


def test_seed_idempotency(db_session: Session) -> None:
    first = seed_demo_data(db_session)
    second = seed_demo_data(db_session)
    assert second == first


def test_reference_product_endpoint(db_session: Session) -> None:
    seed_demo_data(db_session)
    app = create_app()

    def override_db() -> object:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    response = TestClient(app).get("/api/v1/reference/products")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_batch_reference_endpoint(db_session: Session) -> None:
    seed_demo_data(db_session)
    app = create_app()

    def override_db() -> object:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    response = TestClient(app).get("/api/v1/reference/batches/BMX240602")
    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_number"] == "BMX240602"
    assert payload["packaging_line"]["line_code"] == "PL-04"
    assert payload["distribution_summary"]["total_quantity_distributed"] == "49500.000"


def test_historical_complaint_filtering(db_session: Session) -> None:
    seed_demo_data(db_session)
    app = create_app()

    def override_db() -> object:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    response = TestClient(app).get(
        "/api/v1/reference/historical-complaints",
        params={"batch_number": "BMX240602", "complaint_type": "blister leakage"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["complaint_number"] == "HC-DEMO-2026-006"


def test_seed_status_counts_endpoint(db_session: Session) -> None:
    seed_demo_data(db_session)
    app = create_app()

    def override_db() -> object:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    response = TestClient(app).get("/api/v1/reference/seed-status")
    assert response.status_code == 200
    assert response.json()["historical_complaints"] == 13


def test_utc_timestamp_handling(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-utc-test")
    assert draft.created_at.tzinfo is not None
    snapshot = draft_to_canonical_dict(draft)
    assert snapshot["created_at"].endswith("Z")


def test_json_serialisation(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-json-test",
        missing_fields={"customer_contact": ["email", "phone"]},
    )
    db_session.flush()
    db_session.expire(draft)
    reloaded = db_session.get(ComplaintDraft, draft.id)
    assert reloaded is not None
    assert reloaded.missing_fields == {"customer_contact": ["email", "phone"]}


def test_decimal_serialisation(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-decimal-test",
        quantity_affected=Decimal("1.200"),
        risk_confidence=Decimal("0.5000"),
    )
    snapshot = draft_to_canonical_dict(draft)
    assert snapshot["quantity_affected"] == "1.200"
    assert snapshot["risk_confidence"] == "0.5000"


def test_foreign_key_restriction_behaviour(db_session: Session) -> None:
    seed_demo_data(db_session)
    product = db_session.scalars(select(Product).where(Product.product_code == "AMOX-CAP-500")).one()
    db_session.delete(product)
    with pytest.raises(IntegrityError):
        db_session.flush()


def make_app_with_session(db_session: Session):
    app = create_app()

    def override_db() -> object:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return app


def configure_document_test_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UPLOAD_DIRECTORY", str(tmp_path / "uploads"))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
    monkeypatch.setenv("OPENAI_MODEL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()


def complaint_document_text() -> bytes:
    return (
        b"Apollo Pharmacy reported 12 discoloured Amoxicillin Capsules 500 mg from batch BMX240602. "
        b"Manufacturing date March 2026 and expiry date February 2028. Sample is available."
    )


def test_pdf_text_extraction_and_page_evidence(tmp_path: Path) -> None:
    import fitz

    path = tmp_path / "complaint.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Apollo Pharmacy reported discoloured capsules from batch BMX240602.")
    document.save(path)
    document.close()

    parsed = PdfDocumentParser().parse(path)

    assert "BMX240602" in parsed.text
    assert parsed.segments[0].page_number == 1


def test_image_only_pdf_returns_warning(tmp_path: Path) -> None:
    import fitz

    path = tmp_path / "image-only.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()

    parsed = PdfDocumentParser().parse(path)

    assert parsed.text == ""
    assert parsed.warnings == ["PDF appears to be image-only; OCR is not enabled in this phase."]


def test_malformed_pdf_raises_safe_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-broken")

    with pytest.raises(PharmaQSentinelError, match="Malformed PDF"):
        PdfDocumentParser().parse(path)


def test_docx_text_extraction(tmp_path: Path) -> None:
    from docx import Document

    path = tmp_path / "complaint.docx"
    document = Document()
    document.add_paragraph("API assay complaint for batch BMX240602.")
    document.save(path)

    parsed = DocxDocumentParser().parse(path)

    assert parsed.document_type == "DOCX"
    assert parsed.segments[0].paragraph_index == 1
    assert "API assay complaint" in parsed.text


def test_txt_text_extraction(tmp_path: Path) -> None:
    path = tmp_path / "complaint.txt"
    path.write_text("Packaging leakage complaint for batch BMX240602.", encoding="utf-8")

    parsed = TextDocumentParser().parse(path)

    assert parsed.document_type == "TXT"
    assert parsed.segments[0].paragraph_index == 1


def test_eml_text_extraction(tmp_path: Path) -> None:
    path = tmp_path / "complaint.eml"
    path.write_text(
        "Subject: Complaint\nFrom: customer@example.test\nTo: qa@example.test\n\n"
        "Apollo Pharmacy reported blister leakage from batch BMX240602.",
        encoding="utf-8",
    )

    parsed = EmailDocumentParser().parse(path)

    assert parsed.document_type == "EML"
    assert "Subject: Complaint" in parsed.text
    assert "blister leakage" in parsed.text


def test_upload_rejects_extension_mime_mismatch() -> None:
    with pytest.raises(PharmaQSentinelError, match="extension does not match"):
        detect_mime(b"not a pdf", "complaint.pdf")


def test_upload_rejects_executable_extension() -> None:
    with pytest.raises(PharmaQSentinelError, match="Executable"):
        validate_extension("complaint.exe")


def test_attachment_upload_extracts_document_patch_evidence_and_audit(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_document_test_environment(monkeypatch, tmp_path)
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-upload")
    app = make_app_with_session(db_session)

    response = TestClient(app).post(
        f"/api/v1/complaint-drafts/{draft.id}/attachments",
        files={"file": ("complaint.txt", complaint_document_text(), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["current_stage"] == "COMPLETE"
    assert "batch_lot_number" in payload["changed_fields"]
    db_session.refresh(draft)
    assert draft.batch_lot_number == "BMX240602"
    assert draft.product_name == "Amoxicillin Capsules"
    attachment = db_session.get(ComplaintAttachment, payload["attachment_id"])
    assert attachment is not None
    assert Path(attachment.storage_path).exists()
    assert attachment.extracted_text is not None and "Apollo Pharmacy" in attachment.extracted_text
    evidence = db_session.scalars(
        select(FieldEvidence).where(
            FieldEvidence.draft_id == draft.id,
            FieldEvidence.field_name == "batch_lot_number",
        )
    ).first()
    assert evidence is not None
    assert evidence.source_attachment_id == attachment.id
    audit_types = {
        event.event_type
        for event in db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft.id)).all()
    }
    assert {"DOCUMENT_UPLOADED", "DOCUMENT_TEXT_EXTRACTED", "DOCUMENT_EXTRACTION_FIELD_CHANGED"}.issubset(
        audit_types
    )


def test_attachment_status_endpoint_and_duplicate_same_draft(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_document_test_environment(monkeypatch, tmp_path)
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-duplicate")
    app = make_app_with_session(db_session)
    client = TestClient(app)

    first = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/attachments",
        files={"file": ("complaint.txt", complaint_document_text(), "text/plain")},
    )
    second = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/attachments",
        files={"file": ("complaint.txt", complaint_document_text(), "text/plain")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["attachment_id"] == first.json()["attachment_id"]
    status = client.get(
        f"/api/v1/complaint-drafts/{draft.id}/attachments/{first.json()['attachment_id']}/status"
    )
    assert status.status_code == 200
    assert status.json()["status"] == "COMPLETE"


def test_same_hash_different_draft_is_isolated(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_document_test_environment(monkeypatch, tmp_path)
    first_draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-hash-one")
    second_draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-hash-two")
    client = TestClient(make_app_with_session(db_session))

    first = client.post(
        f"/api/v1/complaint-drafts/{first_draft.id}/attachments",
        files={"file": ("complaint.txt", complaint_document_text(), "text/plain")},
    )
    second = client.post(
        f"/api/v1/complaint-drafts/{second_draft.id}/attachments",
        files={"file": ("complaint.txt", complaint_document_text(), "text/plain")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is False
    assert second.json()["attachment_id"] != first.json()["attachment_id"]


def test_upload_rejects_oversized_file(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_document_test_environment(monkeypatch, tmp_path)
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-oversized")

    response = TestClient(make_app_with_session(db_session)).post(
        f"/api/v1/complaint-drafts/{draft.id}/attachments",
        files={"file": ("too-large.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
    )

    assert response.status_code == 422


def test_upload_sanitizes_path_traversal_filename(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_document_test_environment(monkeypatch, tmp_path)
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-path")

    response = TestClient(make_app_with_session(db_session)).post(
        f"/api/v1/complaint-drafts/{draft.id}/attachments",
        files={"file": ("../complaint.txt", complaint_document_text(), "text/plain")},
    )

    assert response.status_code == 200
    attachment = ComplaintAttachmentRepository(db_session).get(response.json()["attachment_id"])
    assert attachment is not None
    assert attachment.original_filename == "complaint.txt"


def test_malformed_pdf_upload_records_failed_status(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configure_document_test_environment(monkeypatch, tmp_path)
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-document-malformed")

    response = TestClient(make_app_with_session(db_session)).post(
        f"/api/v1/complaint-drafts/{draft.id}/attachments",
        files={"file": ("broken.pdf", b"%PDF-broken", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    attachment = ComplaintAttachmentRepository(db_session).get(response.json()["attachment_id"])
    assert attachment is not None
    assert attachment.extraction_error == "Malformed PDF could not be parsed"


def test_complaint_draft_create_endpoint(db_session: Session) -> None:
    app = make_app_with_session(db_session)
    response = TestClient(app).post(
        "/api/v1/complaint-drafts",
        json={"created_by": "Demo User"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["created_by"] == "Demo User"
    assert payload["status"] == ComplaintStatus.DRAFT.value
    assert payload["thread_id"].startswith("thread-")

    event = db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == payload["id"])).one()
    assert event.event_type == "DRAFT_CREATED"


def test_complaint_draft_retrieve_endpoint(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-api-retrieve",
        product_name="Amoxicillin Capsules 500 mg",
    )
    app = make_app_with_session(db_session)

    response = TestClient(app).get(f"/api/v1/complaint-drafts/{draft.id}")

    assert response.status_code == 200
    assert response.json()["product_name"] == "Amoxicillin Capsules 500 mg"
    event_types = [
        event.event_type
        for event in db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft.id)).all()
    ]
    assert "DRAFT_RESTORED" in event_types


def test_complaint_draft_reset_endpoint(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-api-reset",
        product_name="Amoxicillin Capsules 500 mg",
        batch_lot_number="BMX240602",
    )
    app = make_app_with_session(db_session)

    response = TestClient(app).post(f"/api/v1/complaint-drafts/{draft.id}/reset")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == draft.id
    assert payload["thread_id"] == "thread-api-reset"
    assert payload["product_name"] is None
    assert payload["batch_lot_number"] is None


def test_complaint_draft_reset_preserves_id_and_thread_id(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-api-reset-preserve",
        complaint_type="Capsule discolouration",
    )
    app = make_app_with_session(db_session)

    response = TestClient(app).post(f"/api/v1/complaint-drafts/{draft.id}/reset")

    assert response.status_code == 200
    assert response.json()["id"] == draft.id
    assert response.json()["thread_id"] == draft.thread_id


def test_complaint_draft_reset_creates_audit_event(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-api-reset-audit",
        product_name="Amoxicillin Capsules 500 mg",
    )
    app = make_app_with_session(db_session)

    response = TestClient(app).post(f"/api/v1/complaint-drafts/{draft.id}/reset")

    assert response.status_code == 200
    event = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.draft_id == draft.id,
            AuditEvent.event_type == "DRAFT_RESET",
        )
    ).one()
    assert event.old_value["product_name"] == "Amoxicillin Capsules 500 mg"
    assert event.new_value["product_name"] is None


def test_complaint_draft_reset_rolls_back_when_audit_fails(
    mysql_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with Session(mysql_engine) as setup_session:
        draft = ComplaintDraftRepository(setup_session).create(
            thread_id="thread-api-reset-rollback",
            product_name="Amoxicillin Capsules 500 mg",
        )
        setup_session.commit()
        draft_id = draft.id

    def fail_append(self: AuditEventRepository, **_kwargs: object) -> AuditEvent:
        raise RuntimeError("audit persistence failed")

    monkeypatch.setattr(AuditEventRepository, "append", fail_append)
    app = create_app()

    def override_db() -> object:
        with Session(mysql_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    response = TestClient(app, raise_server_exceptions=False).post(
        f"/api/v1/complaint-drafts/{draft_id}/reset"
    )

    assert response.status_code == 500
    with Session(mysql_engine) as verify_session:
        reloaded = verify_session.get(ComplaintDraft, draft_id)
        assert reloaded is not None
        assert reloaded.product_name == "Amoxicillin Capsules 500 mg"


def test_development_patch_endpoint_works_when_enabled(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEVELOPMENT_PATCH_ENDPOINT", "true")
    get_settings.cache_clear()
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-api-dev-patch")
    app = make_app_with_session(db_session)

    response = TestClient(app).patch(
        f"/api/v1/complaint-drafts/{draft.id}/development-patch",
        json={
            "patch": {
                "product_name": "Amoxicillin Capsules 500 mg",
                "quantity_affected": "12.000",
                "quantity_unit": "packs",
            },
            "actor_identifier": "Demo User",
            "reason": "Populate frontend Redux test fields",
            "source": "frontend-redux-test",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_name"] == "Amoxicillin Capsules 500 mg"
    assert payload["quantity_affected"] == "12.000"
    events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.draft_id == draft.id,
            AuditEvent.event_type == "DEVELOPMENT_PATCH_APPLIED",
        )
    ).all()
    assert {event.field_name for event in events} == {
        "product_name",
        "quantity_affected",
        "quantity_unit",
    }


def test_development_patch_endpoint_rejected_when_disabled(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEVELOPMENT_PATCH_ENDPOINT", "false")
    get_settings.cache_clear()
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-api-dev-patch-disabled")
    app = make_app_with_session(db_session)

    response = TestClient(app).patch(
        f"/api/v1/complaint-drafts/{draft.id}/development-patch",
        json={"patch": {"product_name": "Amoxicillin Capsules 500 mg"}},
    )

    assert response.status_code == 404


def test_development_patch_unknown_fields_are_rejected(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEVELOPMENT_PATCH_ENDPOINT", "true")
    get_settings.cache_clear()
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-api-dev-patch-unknown")
    app = make_app_with_session(db_session)

    response = TestClient(app).patch(
        f"/api/v1/complaint-drafts/{draft.id}/development-patch",
        json={"patch": {"unknown_field": "not allowed"}},
    )

    assert response.status_code == 422


def test_development_patch_invalid_quantity_is_rejected(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENABLE_DEVELOPMENT_PATCH_ENDPOINT", "true")
    get_settings.cache_clear()
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-api-dev-patch-quantity")
    app = make_app_with_session(db_session)

    response = TestClient(app).patch(
        f"/api/v1/complaint-drafts/{draft.id}/development-patch",
        json={"patch": {"quantity_affected": "-1.000"}},
    )

    assert response.status_code == 422


def test_missing_complaint_draft_returns_404(db_session: Session) -> None:
    app = make_app_with_session(db_session)

    response = TestClient(app).get("/api/v1/complaint-drafts/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


class FailingIntentGateway:
    def generate_structured(self, **_kwargs: object) -> object:
        from app.services.llm import LLMConfigurationError

        raise LLMConfigurationError("OpenAI model is not configured")

    def generate_text(self, **_kwargs: object) -> object:
        raise NotImplementedError


class MockLogComplaintGateway:
    def __init__(self, *, risk_severity: Severity = Severity.MAJOR) -> None:
        self.risk_severity = risk_severity

    def generate_structured(self, **kwargs: object) -> object:
        schema = kwargs["response_schema"]
        if schema is ComplaintExtractionResult:
            parsed_output = ComplaintExtractionResult(
                extracted_fields={
                    "complaint_source": ComplaintFieldExtraction(
                        value="Pharmacy",
                        normalised="Pharmacy",
                        explicitly_stated=True,
                        confidence=0.9,
                        source_excerpt="Apollo Pharmacy reported",
                    ),
                    "customer_name": ComplaintFieldExtraction(
                        value="Apollo Pharmacy",
                        normalised="Apollo Pharmacy",
                        explicitly_stated=True,
                        confidence=0.96,
                        source_excerpt="Apollo Pharmacy reported",
                    ),
                    "product_type": ComplaintFieldExtraction(
                        value="FDF",
                        normalised="FDF",
                        explicitly_stated=True,
                        confidence=0.82,
                        source_excerpt="Amoxicillin Capsules 500 mg",
                    ),
                    "product_name": ComplaintFieldExtraction(
                        value="Amoxicillin Capsules",
                        normalised="Amoxicillin Capsules",
                        explicitly_stated=True,
                        confidence=0.92,
                        source_excerpt="Amoxicillin Capsules 500 mg",
                    ),
                    "product_strength_grade": ComplaintFieldExtraction(
                        value="500 mg",
                        normalised="500 mg",
                        explicitly_stated=True,
                        confidence=0.92,
                        source_excerpt="500 mg",
                    ),
                    "batch_lot_number": ComplaintFieldExtraction(
                        value="AMX240602",
                        normalised="AMX240602",
                        explicitly_stated=True,
                        confidence=0.96,
                        source_excerpt="batch AMX240602",
                    ),
                    "manufacturing_date": ComplaintFieldExtraction(
                        value="March 2026",
                        normalised="March 2026",
                        explicitly_stated=True,
                        confidence=0.88,
                        source_excerpt="manufacturing date is March 2026",
                    ),
                    "expiry_retest_date": ComplaintFieldExtraction(
                        value="February 2028",
                        normalised="February 2028",
                        explicitly_stated=True,
                        confidence=0.88,
                        source_excerpt="expiry date is February 2028",
                    ),
                    "quantity_affected": ComplaintFieldExtraction(
                        value="12",
                        normalised="12",
                        explicitly_stated=True,
                        confidence=0.93,
                        source_excerpt="12 discoloured",
                    ),
                    "quantity_unit": ComplaintFieldExtraction(
                        value="capsules",
                        normalised="capsules",
                        explicitly_stated=True,
                        confidence=0.9,
                        source_excerpt="12 discoloured Amoxicillin Capsules",
                    ),
                    "complaint_type": ComplaintFieldExtraction(
                        value="Product appearance",
                        normalised="Product appearance",
                        explicitly_stated=True,
                        confidence=0.85,
                        source_excerpt="discoloured",
                    ),
                    "detailed_description": ComplaintFieldExtraction(
                        value="Discoloured capsules",
                        normalised="Discoloured capsules",
                        explicitly_stated=True,
                        confidence=0.86,
                        source_excerpt="12 discoloured Amoxicillin Capsules",
                    ),
                    "unsupported_root_cause": ComplaintFieldExtraction(
                        value="seal temperature",
                        normalised="seal temperature",
                        explicitly_stated=False,
                        confidence=0.2,
                        source_excerpt="",
                    ),
                },
                complaint_classification="Product appearance",
                detected_language="en",
                product_type=ProductType.FDF,
                possible_quality_defect=True,
                possible_adverse_event=False,
                possible_counterfeit=False,
                missing_fields=[
                    "customer contact",
                    "complaint date",
                    "sample availability",
                    "patient consumption status",
                ],
                warnings=[],
                concise_summary="Apollo Pharmacy reported discoloured capsules.",
            )
            prompt_version = "complaint-log-extraction-v1"
        elif schema is ComplaintEditResult:
            parsed_output = ComplaintEditResult(
                operations=[
                    ComplaintEditOperation(
                        field_name="batch_lot_number",
                        operation="SET",
                        new_value="BMX240602",
                        explicitly_requested=True,
                        source_excerpt="batch number is BMX240602",
                        confidence=0.92,
                        reason="User corrected the batch number.",
                    )
                ],
                no_op_fields=[],
                ambiguous_requests=[],
                clarification_required=False,
                clarification_question=None,
                warnings=[],
                concise_summary="Batch number correction.",
            )
            prompt_version = "complaint-edit-operation-v1"
        else:
            parsed_output = ProvisionalRiskAssessment(
                suggested_severity=self.risk_severity,
                suggested_priority=Priority.NORMAL if self.risk_severity == Severity.MINOR else Priority.HIGH,
                patient_harm_level=None,
                risk_rationale="Visible discolouration is a provisional quality concern requiring QA review.",
                potential_hazard="Potential product quality defect.",
                recommended_next_action="Request sample availability and quarantine any retained stock pending QA review.",
                confidence=0.78,
                supporting_fields=["product_name", "batch_lot_number", "complaint_type"],
                limitations=["No sample status or patient consumption details were provided."],
                requires_qa_confirmation=True,
            )
            prompt_version = "complaint-provisional-risk-v1"

        return StructuredLLMResult(
            provider="openai",
            requested_model="mock-model",
            actual_model="mock-model",
            response_id="mock-response",
            prompt_version=prompt_version,
            usage=LLMUsage(),
            latency_ms=1,
            retry_count=0,
            created_at=utc_now(),
            parsed_output=parsed_output,
            warnings=[],
        )

    def generate_text(self, **_kwargs: object) -> object:
        raise NotImplementedError


class DowngradingRiskGateway:
    def generate_structured(self, **kwargs: object) -> object:
        schema = kwargs["response_schema"]
        assert schema is PharmaRiskAssessment
        parsed_output = PharmaRiskAssessment(
            suggested_severity=Severity.MINOR,
            suggested_priority=Priority.NORMAL,
            patient_harm_level=None,
            quality_defect_possible=True,
            adverse_event_possible=False,
            counterfeit_possible=False,
            distribution_issue_possible=False,
            rationale="The contextual model suggested a lower draft severity.",
            potential_hazards=["Potential quality impact."],
            supporting_evidence=["wrong strength wording"],
            contradicting_evidence=[],
            recommended_actions=["QA should review the complaint."],
            missing_information=[],
            confidence=0.77,
            limitations=["Draft contextual assessment."],
            requires_qa_confirmation=True,
        )
        return StructuredLLMResult(
            provider="openai",
            requested_model="mock-risk-model",
            actual_model="mock-risk-model",
            response_id="mock-risk-response",
            prompt_version="pharma-risk-assessment-v1",
            usage=LLMUsage(),
            latency_ms=1,
            retry_count=0,
            created_at=utc_now(),
            parsed_output=parsed_output,
            warnings=[],
        )

    def generate_text(self, **_kwargs: object) -> object:
        raise NotImplementedError


class ContradictoryRiskGateway(DowngradingRiskGateway):
    def generate_structured(self, **kwargs: object) -> object:
        result = super().generate_structured(**kwargs)
        result.parsed_output = result.parsed_output.model_copy(
            update={
                "suggested_severity": Severity.MAJOR,
                "suggested_priority": Priority.HIGH,
                "contradicting_evidence": ["Reporter says outer carton was damaged but inner blister remained intact."],
            }
        )
        return result


def quality_fixture(description: str, **overrides: object) -> dict[str, object | None]:
    return {
        "complaint_source": "Customer email",
        "customer_name": "Demo Customer",
        "customer_contact": "demo@example.test",
        "country_market": "India",
        "product_type": "FDF",
        "product_name": "Amoxicillin Capsules",
        "product_strength_grade": "500 mg",
        "dosage_form": "Capsule",
        "batch_lot_number": "BMX240602",
        "quantity_affected": Decimal("1.000"),
        "quantity_unit": "pack",
        "complaint_type": description[:120],
        "complaint_date": "2026-07-31",
        "detailed_description": description,
        "defect_observed_date": "2026-07-30",
        "sample_available": True,
        "patient_consumed_product": False,
        "adverse_event_signal": False,
        "counterfeit_signal": False,
        "storage_conditions": "Ambient storage reported.",
        **overrides,
    }


@pytest.mark.parametrize(
    ("description", "expected_severity", "expected_route"),
    [
        ("Cosmetic outer carton scuff without product exposure.", Severity.MINOR, SafetyReviewRoute.QUALITY_ASSURANCE),
        ("Customer reported discoloured capsules that may indicate degradation.", Severity.MAJOR, SafetyReviewRoute.QUALITY_ASSURANCE),
        ("Wrong strength printed on the label; 250 mg supplied instead of 500 mg.", Severity.CRITICAL, SafetyReviewRoute.REGULATORY_AFFAIRS_REVIEW),
        ("A glass particle was found inside the bottle.", Severity.CRITICAL, SafetyReviewRoute.REGULATORY_AFFAIRS_REVIEW),
        ("Sterile vial leakage with possible sterile failure.", Severity.CRITICAL, SafetyReviewRoute.REGULATORY_AFFAIRS_REVIEW),
        ("Patient swelling and rash after using the product.", Severity.UNDETERMINED, SafetyReviewRoute.PHARMACOVIGILANCE),
        ("Complaint plus adverse-event signal: blister leakage and patient rash.", Severity.MAJOR, SafetyReviewRoute.PHARMACOVIGILANCE),
        ("Suspected counterfeit packaging and tampering seal difference.", Severity.CRITICAL, SafetyReviewRoute.ANTI_COUNTERFEIT_REVIEW),
        ("API assay discrepancy found during customer testing.", Severity.MAJOR, SafetyReviewRoute.QUALITY_ASSURANCE),
        ("API moisture discrepancy with high moisture result.", Severity.MAJOR, SafetyReviewRoute.QUALITY_ASSURANCE),
        ("Service complaint about delayed certificate email response.", Severity.MINOR, SafetyReviewRoute.CUSTOMER_SERVICE),
        ("Insufficient information was provided.", Severity.UNDETERMINED, SafetyReviewRoute.UNDETERMINED),
        ("Multiple related batches reported with repeated related complaints.", Severity.MAJOR, SafetyReviewRoute.QUALITY_ASSURANCE),
    ],
)
def test_quality_fixture_risk_rules_and_routes(
    description: str,
    expected_severity: Severity,
    expected_route: SafetyReviewRoute,
) -> None:
    complaint = quality_fixture(description)
    if expected_route == SafetyReviewRoute.UNDETERMINED:
        complaint = {"detailed_description": description}
    classification = classify_defects(complaint)
    deterministic = evaluate_safety_rules(complaint, classification)
    routing = route_safety(complaint, classification, deterministic.severity_floor)

    assert deterministic.severity_floor == expected_severity
    assert expected_route in routing.routes
    assert "REPORTABLE" not in " ".join(routing.route_reasons.values()).upper()


def test_completeness_calculation_and_targeted_questions() -> None:
    result = evaluate_completeness(
        {
            "detailed_description": "Discoloured capsules observed.",
            "product_name": "Amoxicillin Capsules",
            "complaint_source": "Pharmacy",
        }
    )

    assert result.can_begin_triage is True
    assert "batch or lot" in result.missing_critical_fields
    assert len(result.targeted_follow_up_questions) <= 3
    assert result.targeted_follow_up_questions[0] != "Please provide more information."


def test_contextual_assessment_cannot_downgrade_deterministic_critical_floor() -> None:
    complaint = quality_fixture("Wrong strength printed on product label.")

    result = assess_pharma_risk(
        complaint=complaint,
        latest_user_message="Wrong strength printed on product label.",
        changed_fields=["detailed_description"],
        request_id="req-risk-downgrade",
        draft_id="draft-risk-downgrade",
        thread_id="thread-risk-downgrade",
        llm_gateway=DowngradingRiskGateway(),
    )

    assert result.deterministic.severity_floor == Severity.CRITICAL
    assert result.assessment.suggested_severity == Severity.CRITICAL
    assert any("deterministic safety floor" in warning.lower() for warning in result.warnings)


def test_contradictory_evidence_preserved_in_contextual_assessment() -> None:
    complaint = quality_fixture("Outer carton damage reported, inner blister intact.")

    result = assess_pharma_risk(
        complaint=complaint,
        latest_user_message="Outer carton damage reported, inner blister intact.",
        changed_fields=["detailed_description"],
        request_id="req-risk-contradiction",
        draft_id="draft-risk-contradiction",
        thread_id="thread-risk-contradiction",
        llm_gateway=ContradictoryRiskGateway(),
    )

    assert result.assessment.contradicting_evidence == [
        "Reporter says outer carton was damaged but inner blister remained intact."
    ]


def seeded_edit_draft(db_session: Session, **overrides: object) -> ComplaintDraft:
    fields = {
        "thread_id": "thread-edit-draft",
        "product_name": "Amoxicillin Capsules",
        "product_strength_grade": "500 mg",
        "batch_lot_number": "AMX240602",
        "quantity_affected": Decimal("12.000"),
        "quantity_unit": "capsules",
        "manufacturing_date_text": "March 2026",
        "expiry_retest_date_text": "February 2028",
        "customer_name": "Apollo Pharmacy",
        "complaint_type": "Product appearance",
        "detailed_description": "Discoloured capsules",
        "suggested_severity": Severity.MAJOR.value,
        "suggested_priority": Priority.HIGH.value,
        "risk_rationale": "Visible discolouration is a provisional quality concern requiring QA review.",
        "potential_hazard": "Potential product quality defect.",
        "suggested_next_action": "Request sample availability and quarantine any retained stock pending QA review.",
        "risk_confidence": Decimal("0.7800"),
        **overrides,
    }
    return ComplaintDraftRepository(db_session).create(**fields)


def draft_field_snapshot(draft: ComplaintDraft) -> dict[str, object]:
    return {
        "product_name": draft.product_name,
        "product_strength_grade": draft.product_strength_grade,
        "batch_lot_number": draft.batch_lot_number,
        "quantity_affected": draft.quantity_affected,
        "quantity_unit": draft.quantity_unit,
        "manufacturing_date_text": draft.manufacturing_date_text,
        "expiry_retest_date_text": draft.expiry_retest_date_text,
        "customer_name": draft.customer_name,
        "customer_contact": draft.customer_contact,
        "storage_conditions": draft.storage_conditions,
        "complaint_type": draft.complaint_type,
        "detailed_description": draft.detailed_description,
        "suggested_severity": draft.suggested_severity,
        "suggested_priority": draft.suggested_priority,
        "risk_rationale": draft.risk_rationale,
        "potential_hazard": draft.potential_hazard,
        "suggested_next_action": draft.suggested_next_action,
        "risk_confidence": draft.risk_confidence,
    }


def assert_unrelated_fields_preserved(
    before: dict[str, object],
    draft: ComplaintDraft,
    changed_fields: set[str],
) -> None:
    after = draft_field_snapshot(draft)
    for field_name, old_value in before.items():
        if field_name not in changed_fields:
            assert after[field_name] == old_value, field_name


def test_complaint_graph_compiles(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-graph-compile")
    agent_run = AgentRun(
        draft_id=draft.id,
        request_id="req-graph-compile",
        intent=ComplaintAssistantIntent.UNKNOWN.value,
        status="STARTED",
        started_at=utc_now(),
    )
    runtime = ComplaintAgentRuntime(db=db_session, agent_run=agent_run, llm_gateway=FailingIntentGateway())

    graph = build_complaint_graph(runtime)

    assert graph is not None


def test_every_conditional_route_resolves() -> None:
    expected_routes = {
        ComplaintAssistantIntent.LOG_COMPLAINT: "tool_patch_flow",
        ComplaintAssistantIntent.EDIT_COMPLAINT: "tool_patch_flow",
        ComplaintAssistantIntent.EXTRACT_DOCUMENT: "tool_patch_flow",
        ComplaintAssistantIntent.ASK_QUESTION: "question",
        ComplaintAssistantIntent.REQUEST_SUMMARY: "tool_response_flow",
        ComplaintAssistantIntent.RUN_BATCH_IMPACT: "tool_response_flow",
        ComplaintAssistantIntent.RUN_QUALITY_WAR_ROOM: "tool_response_flow",
        ComplaintAssistantIntent.SAVE_COMPLAINT: "tool_response_flow",
        ComplaintAssistantIntent.UNKNOWN: "unknown",
    }
    for intent, route in expected_routes.items():
        assert route_from_intent({"intent": intent.value}) == route


def test_agent_state_is_isolated_by_draft_id(db_session: Session) -> None:
    first = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-isolated-1")
    second = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-isolated-2")

    run_complaint_assistant(
        db=db_session,
        draft_id=first.id,
        request_id="req-agent-isolated-1",
        latest_user_message="What is the current batch number?",
        llm_gateway=FailingIntentGateway(),
    )
    run_complaint_assistant(
        db=db_session,
        draft_id=second.id,
        request_id="req-agent-isolated-2",
        latest_user_message="What severity is currently displayed?",
        llm_gateway=FailingIntentGateway(),
    )

    first_messages = ComplaintMessageRepository(db_session).list_for_draft(first.id)
    second_messages = ComplaintMessageRepository(db_session).list_for_draft(second.id)
    assert len(first_messages) == 2
    assert len(second_messages) == 2
    assert "batch" in first_messages[-1].message_text.lower()
    assert "severity" in second_messages[-1].message_text.lower()


def test_agent_messages_persist_in_mysql(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-messages")

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-messages",
        latest_user_message="What information is missing?",
        llm_gateway=FailingIntentGateway(),
    )

    messages = ComplaintMessageRepository(db_session).list_for_draft(draft.id)
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER.value
    assert messages[1].role == MessageRole.ASSISTANT.value
    assert state["intent"] == ComplaintAssistantIntent.ASK_QUESTION.value


def test_question_intent_does_not_mutate_complaint_fields(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-agent-question-readonly",
        batch_lot_number="BMX240602",
        suggested_severity=Severity.UNDETERMINED.value,
    )

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-question",
        latest_user_message="What is the current batch number?",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert draft.batch_lot_number == "BMX240602"
    assert draft.suggested_severity == Severity.UNDETERMINED.value
    assert db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft.id)).all() == []


def test_summary_intent_does_not_mutate_complaint_fields(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-agent-summary-readonly",
        product_name="Amoxicillin Capsules 500 mg",
        batch_lot_number="BMX240602",
    )

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-summary",
        latest_user_message="Summarize what has already been entered.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert draft.product_name == "Amoxicillin Capsules 500 mg"
    assert state["changed_fields"] == []
    assert db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft.id)).all() == []


def test_tool_stubs_return_explicit_unimplemented_responses(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-stub")

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-stub",
        latest_user_message="Run batch impact analysis for this complaint.",
        llm_gateway=FailingIntentGateway(),
    )

    assert state["intent"] == ComplaintAssistantIntent.RUN_BATCH_IMPACT.value
    assert state["tool_implemented"] is False
    assert state["proposed_patch"] is None
    assert state["changed_fields"] == []
    assert "not implemented in this phase" in state["assistant_response"]


def test_log_complaint_populates_fields_with_evidence_audit_and_risk(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-log-complaint")

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-log-complaint",
        latest_user_message=(
            "Apollo Pharmacy reported 12 discoloured Amoxicillin Capsules 500 mg "
            "from batch AMX240602. The manufacturing date is March 2026 and "
            "the expiry date is February 2028."
        ),
        llm_gateway=MockLogComplaintGateway(),
    )

    db_session.refresh(draft)
    assert state["intent"] == ComplaintAssistantIntent.LOG_COMPLAINT.value
    assert state["tool_implemented"] is True
    assert draft.complaint_source == "Pharmacy"
    assert draft.customer_name == "Apollo Pharmacy"
    assert draft.product_type == ProductType.FDF.value
    assert draft.product_name == "Amoxicillin Capsules"
    assert draft.product_strength_grade == "500 mg"
    assert draft.batch_lot_number == "AMX240602"
    assert draft.manufacturing_date is None
    assert draft.manufacturing_date_text == "March 2026"
    assert draft.expiry_retest_date is None
    assert draft.expiry_retest_date_text == "February 2028"
    assert draft.quantity_affected == Decimal("12.000")
    assert draft.quantity_unit == "capsules"
    assert draft.complaint_type == "Product appearance"
    assert draft.detailed_description == "Discoloured capsules"
    assert draft.suggested_severity == Severity.MAJOR.value
    assert draft.suggested_priority == Priority.HIGH.value
    assert "Requires" not in draft.risk_rationale
    assert "requires qa confirmation" in state["assistant_response"].lower()
    assert any("unsupported_root_cause" in warning for warning in state["warnings"])

    evidence = db_session.scalars(select(FieldEvidence).where(FieldEvidence.draft_id == draft.id)).all()
    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft.id)).all()
    risk_versions = db_session.scalars(
        select(RiskAssessmentVersion).where(RiskAssessmentVersion.draft_id == draft.id)
    ).all()
    assert {item.field_name for item in evidence}.issuperset({"product_name", "batch_lot_number"})
    assert all(item.source_message_id is not None for item in evidence)
    assert {event.field_name for event in audit_events}.issuperset(
        {"product_name", "batch_lot_number", "suggested_severity", "suggested_priority"}
    )
    assert all(event.actor_type == ActorType.AI_AGENT.value for event in audit_events)
    assert len(risk_versions) == 1
    risk_metadata = risk_versions[0].supporting_evidence or {}
    assert risk_metadata["rule_version"] == "safety-rules-v1"
    assert risk_metadata["prompt_version"] == "pharma-risk-assessment-v1"
    assert risk_metadata["deterministic_severity_floor"] == Severity.MAJOR.value
    assert risk_metadata["final_suggested_result"]["routes"] == ["QUALITY_ASSURANCE"]
    assert set(risk_metadata["evidence_ids"])


def test_log_complaint_does_not_overwrite_conflicting_batch(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-log-conflict",
        batch_lot_number="BMX240602",
    )

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-log-conflict",
        latest_user_message="Apollo Pharmacy reported 12 discoloured capsules from batch AMX240602.",
        llm_gateway=MockLogComplaintGateway(),
    )

    db_session.refresh(draft)
    assert draft.batch_lot_number == "BMX240602"
    assert "batch_lot_number" in state["conflict_fields"]
    assert any("conflicts with current draft" in warning for warning in state["warnings"])


def test_log_complaint_enforces_deterministic_severity_floor(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-log-risk-floor")

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-log-risk-floor",
        latest_user_message="Apollo Pharmacy reported 12 discoloured capsules from batch AMX240602.",
        llm_gateway=MockLogComplaintGateway(risk_severity=Severity.MINOR),
    )

    db_session.refresh(draft)
    assert draft.suggested_severity == Severity.MAJOR.value
    assert draft.suggested_priority == Priority.HIGH.value


def test_edit_complaint_corrects_batch_and_quantity_preserving_unrelated_fields(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)
    before = draft_field_snapshot(draft)

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-batch-qty",
        latest_user_message="Sorry, the batch number is BMX240602 and the affected quantity is 48 capsules.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert state["intent"] == ComplaintAssistantIntent.EDIT_COMPLAINT.value
    assert draft.batch_lot_number == "BMX240602"
    assert draft.quantity_affected == Decimal("48.000")
    assert draft.quantity_unit == "capsules"
    assert_unrelated_fields_preserved(before, draft, {"batch_lot_number", "quantity_affected"})
    assert "All other complaint information was preserved" in state["assistant_response"]


def test_edit_complaint_adds_one_empty_field_preserving_others(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session, customer_contact=None)
    before = draft_field_snapshot(draft)

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-add-contact",
        latest_user_message="Customer contact is qa.apollo@example.test",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert draft.customer_contact == "qa.apollo@example.test"
    assert_unrelated_fields_preserved(before, draft, {"customer_contact"})


def test_edit_complaint_explicit_deletion_preserves_other_fields(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session, storage_conditions="Stored at room temperature")
    before = draft_field_snapshot(draft)

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-clear-storage",
        latest_user_message="The storage conditions were not provided. Remove the current storage value.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert draft.storage_conditions is None
    assert_unrelated_fields_preserved(before, draft, {"storage_conditions"})


def test_edit_complaint_ambiguous_quantity_correction_does_not_mutate(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)
    before = draft_field_snapshot(draft)

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-ambiguous-number",
        latest_user_message="Change the number to 48.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert state["clarification_required"] is True
    assert "quantity affected to 48" in state["assistant_response"]
    assert draft_field_snapshot(draft) == before
    assert db_session.scalars(select(AuditEvent).where(AuditEvent.draft_id == draft.id)).all() == []


def test_edit_complaint_no_op_preserves_fields(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)
    before = draft_field_snapshot(draft)

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-no-op",
        latest_user_message="Sorry, the batch number is AMX240602.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert state["no_op_fields"] == ["batch_lot_number"]
    assert "No change was required" in state["assistant_response"]
    assert draft_field_snapshot(draft) == before


def test_edit_complaint_invalid_negative_quantity_is_rejected(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)
    before = draft_field_snapshot(draft)

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-negative-quantity",
        latest_user_message="Sorry, the affected quantity is -4 capsules.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert any("quantity_affected cannot be negative" in error for error in state["errors"])
    assert draft_field_snapshot(draft) == before


def test_edit_complaint_impossible_date_is_rejected(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)
    before = draft_field_snapshot(draft)

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-impossible-date",
        latest_user_message="Sorry, the complaint date is 2026-02-31.",
        llm_gateway=FailingIntentGateway(),
    )

    db_session.refresh(draft)
    assert any("invalid or partial complaint_date" in warning for warning in state["warnings"])
    assert draft_field_snapshot(draft) == before


def test_edit_committed_draft_rejected(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session, status=ComplaintStatus.COMMITTED.value)

    with pytest.raises(PharmaQSentinelError):
        run_complaint_assistant(
            db=db_session,
            draft_id=draft.id,
            request_id="req-edit-locked",
            latest_user_message="Sorry, the batch number is BMX240602.",
            llm_gateway=FailingIntentGateway(),
        )


def test_edit_preserves_previous_evidence_and_adds_active_correction_evidence(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)
    old_message = ComplaintMessageRepository(db_session).add(
        draft_id=draft.id,
        role=MessageRole.USER,
        message_text="Original complaint",
    )
    from app.repositories.evidence import FieldEvidenceRepository

    previous = FieldEvidenceRepository(db_session).add(
        draft_id=draft.id,
        field_name="batch_lot_number",
        field_value={"value": "AMX240602"},
        evidence_type=EvidenceType.USER_TEXT,
        source_message_id=old_message.id,
        is_active=True,
    )

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-evidence",
        latest_user_message="Sorry, the batch number is BMX240602.",
        llm_gateway=FailingIntentGateway(),
    )

    evidence = db_session.scalars(
        select(FieldEvidence).where(
            FieldEvidence.draft_id == draft.id,
            FieldEvidence.field_name == "batch_lot_number",
        )
    ).all()
    db_session.refresh(previous)
    assert previous in evidence
    assert previous.is_active is False
    assert any(item.evidence_type == EvidenceType.USER_CORRECTION.value and item.is_active for item in evidence)


def test_edit_creates_audit_per_changed_field(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-audit",
        latest_user_message="Sorry, the batch number is BMX240602 and the affected quantity is 48 capsules.",
        llm_gateway=FailingIntentGateway(),
    )

    events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.draft_id == draft.id,
            AuditEvent.event_type == "EDIT_COMPLAINT_FIELD_CHANGED",
        )
    ).all()
    assert {event.field_name for event in events}.issuperset({"batch_lot_number", "quantity_affected"})
    assert all(event.reason == "User correction through AI Complaint Intake Assistant" for event in events)


def test_edit_rolls_back_when_audit_insertion_fails(
    mysql_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with Session(mysql_engine) as setup_session:
        draft = seeded_edit_draft(setup_session, thread_id="thread-edit-rollback")
        draft_id = draft.id
        setup_session.commit()

    def fail_append(self: AuditEventRepository, **_kwargs: object) -> AuditEvent:
        raise RuntimeError("audit persistence failed")

    monkeypatch.setattr(AuditEventRepository, "append", fail_append)
    app = create_app()

    def override_db() -> object:
        with Session(mysql_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    response = TestClient(app, raise_server_exceptions=False).post(
        f"/api/v1/complaint-drafts/{draft_id}/messages",
        json={"message": "Sorry, the batch number is BMX240602.", "attachment_id": None},
    )

    assert response.status_code == 500
    with Session(mysql_engine) as verify_session:
        reloaded = verify_session.get(ComplaintDraft, draft_id)
        assert reloaded is not None
        assert reloaded.batch_lot_number == "AMX240602"


def test_edit_recalculates_risk_when_relevant_field_changes(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-risk",
        latest_user_message="Sorry, the batch number is BMX240602.",
        llm_gateway=MockLogComplaintGateway(risk_severity=Severity.CRITICAL),
    )

    db_session.refresh(draft)
    versions = db_session.scalars(
        select(RiskAssessmentVersion).where(RiskAssessmentVersion.draft_id == draft.id)
    ).all()
    assert draft.suggested_severity == Severity.CRITICAL.value
    assert len(versions) == 1


def test_edit_does_not_create_risk_version_for_irrelevant_change(db_session: Session) -> None:
    draft = seeded_edit_draft(db_session)

    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-edit-no-risk",
        latest_user_message="Customer contact is qa.apollo@example.test",
        llm_gateway=FailingIntentGateway(),
    )

    versions = db_session.scalars(
        select(RiskAssessmentVersion).where(RiskAssessmentVersion.draft_id == draft.id)
    ).all()
    assert versions == []


def test_unknown_intent_produces_safe_clarification(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-unknown")

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-unknown",
        latest_user_message="hello",
        llm_gateway=FailingIntentGateway(),
    )

    assert state["intent"] == ComplaintAssistantIntent.UNKNOWN.value
    assert state["clarification_required"] is True
    assert "Please tell me" in state["assistant_response"]


def test_failed_openai_intent_classification_falls_back_safely(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-openai-fallback")

    state = run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-openai-fallback",
        latest_user_message="hello",
        llm_gateway=FailingIntentGateway(),
    )

    assert state["intent"] == ComplaintAssistantIntent.UNKNOWN.value
    assert any("AI intent classification was unavailable" in warning for warning in state["warnings"])


def test_graph_failure_records_agent_run_failure(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-failure")

    class BrokenGraph:
        def invoke(self, _state: object) -> object:
            raise RuntimeError("graph failed")

    monkeypatch.setattr("app.agents.complaint.graph.build_complaint_graph", lambda _runtime: BrokenGraph())

    with pytest.raises(RuntimeError):
        run_complaint_assistant(
            db=db_session,
            draft_id=draft.id,
            request_id="req-agent-failure",
            latest_user_message="hello",
            llm_gateway=FailingIntentGateway(),
        )

    run = db_session.scalars(select(AgentRun).where(AgentRun.draft_id == draft.id)).one()
    assert run.status == "FAILED"
    assert run.errors_json == {"errors": ["RuntimeError"]}


def test_message_api_response_has_no_hidden_reasoning(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-api")
    app = make_app_with_session(db_session)

    response = TestClient(app).post(
        f"/api/v1/complaint-drafts/{draft.id}/messages",
        json={"message": "What information is missing?", "attachment_id": None},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == ComplaintAssistantIntent.ASK_QUESTION.value
    assert "reason" not in payload
    assert "state" not in payload
    assert "prompt" not in payload


def test_message_list_endpoint_returns_chronological_messages(db_session: Session) -> None:
    draft = ComplaintDraftRepository(db_session).create(thread_id="thread-agent-list")
    run_complaint_assistant(
        db=db_session,
        draft_id=draft.id,
        request_id="req-agent-list",
        latest_user_message="What severity is currently displayed?",
        llm_gateway=FailingIntentGateway(),
    )
    app = make_app_with_session(db_session)

    response = TestClient(app).get(f"/api/v1/complaint-drafts/{draft.id}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert [message["role"] for message in payload["messages"]] == [
        MessageRole.USER.value,
        MessageRole.ASSISTANT.value,
    ]


def seed_evidence_lock_fixture(db_session: Session) -> ComplaintDraft:
    draft = ComplaintDraftRepository(db_session).create(
        thread_id="thread-evidence-lock",
        product_name="Amoxicillin Capsules 500 mg",
        batch_lot_number="BMX240602",
        quantity_affected=Decimal("12.000"),
    )
    user_message = ComplaintMessageRepository(db_session).add(
        draft_id=draft.id,
        role=MessageRole.USER,
        message_text="Apollo Pharmacy reported batch BMX240601 in the initial email.",
        created_at=utc_now(),
    )
    assistant_message = ComplaintMessageRepository(db_session).add(
        draft_id=draft.id,
        role=MessageRole.ASSISTANT,
        message_text="I populated the draft from source evidence.",
        created_at=utc_now(),
    )
    attachment = ComplaintAttachmentRepository(db_session).add(
        draft_id=draft.id,
        original_filename="complaint.pdf",
        stored_filename="safe-complaint.pdf",
        mime_type="application/pdf",
        file_size=2048,
        sha256_checksum="a" * 64,
        storage_path="C:/private/uploads/safe-complaint.pdf",
        extraction_status=ExtractionStatus.COMPLETE,
    )
    evidence_repository = FieldEvidenceRepository(db_session)
    evidence_repository.add(
        draft_id=draft.id,
        field_name="product_name",
        field_value={"value": "Amoxicillin Capsules 500 mg", "provider": "openai", "actual_model": "mock-model"},
        evidence_type=EvidenceType.USER_TEXT,
        source_message_id=user_message.id,
        source_excerpt="Apollo Pharmacy reported Amoxicillin Capsules 500 mg",
        confidence=Decimal("0.9100"),
        extraction_method="LOG_COMPLAINT",
        is_explicit=True,
        is_active=True,
    )
    evidence_repository.add(
        draft_id=draft.id,
        field_name="quantity_affected",
        field_value={"value": "12.000", "raw": "12", "normalised": "12.000"},
        evidence_type=EvidenceType.PDF,
        source_attachment_id=attachment.id,
        source_message_id=assistant_message.id,
        source_excerpt="12 affected packs",
        confidence=Decimal("0.8800"),
        extraction_method="DOCUMENT_EXTRACTION",
        page_number=2,
        paragraph_index=4,
        is_explicit=True,
        is_active=True,
    )
    evidence_repository.add(
        draft_id=draft.id,
        field_name="batch_lot_number",
        field_value={"value": "BMX240601"},
        evidence_type=EvidenceType.USER_TEXT,
        source_message_id=user_message.id,
        source_excerpt="batch BMX240601",
        confidence=Decimal("0.7200"),
        extraction_method="LOG_COMPLAINT",
        is_explicit=True,
        is_active=False,
    )
    evidence_repository.add(
        draft_id=draft.id,
        field_name="batch_lot_number",
        field_value={"value": "BMX240602"},
        evidence_type=EvidenceType.USER_CORRECTION,
        source_message_id=user_message.id,
        source_excerpt="Correct batch is BMX240602",
        confidence=Decimal("0.9700"),
        extraction_method="EDIT_COMPLAINT",
        is_explicit=True,
        is_active=True,
    )
    AuditEventRepository(db_session).append(
        draft_id=draft.id,
        event_type="EDIT_COMPLAINT_FIELD_CHANGED",
        actor_type=ActorType.AI_AGENT,
        actor_identifier="Complaint Intake Assistant",
        tool_name="EDIT_COMPLAINT",
        field_name="batch_lot_number",
        old_value={"value": "BMX240601"},
        new_value={"value": "BMX240602"},
        reason="User correction through AI Complaint Intake Assistant",
        provider_name="openai",
        actual_model="mock-model",
    )
    db_session.add(
        RiskAssessmentVersion(
            draft_id=draft.id,
            version_number=1,
            severity=Severity.MAJOR.value,
            priority=Priority.HIGH.value,
            safety_route="PRODUCT_QUALITY",
            risk_rationale="Draft risk version for evidence replay.",
            confidence=Decimal("0.6200"),
            supporting_evidence={"evidence_ids": []},
        )
    )
    db_session.flush()
    return draft


def test_evidence_endpoints_include_sources_conflicts_and_no_storage_paths(db_session: Session) -> None:
    draft = seed_evidence_lock_fixture(db_session)
    client = TestClient(make_app_with_session(db_session))

    response = client.get(f"/api/v1/complaint-drafts/{draft.id}/evidence")

    assert response.status_code == 200
    payload = response.json()
    assert {item["field_name"] for item in payload["items"]}.issuperset(
        {"product_name", "quantity_affected", "batch_lot_number"}
    )
    assert payload["critical_conflicts_block_save"] is True
    assert payload["conflicts"][0]["field_name"] == "batch_lot_number"
    assert "storage_path" not in str(payload)

    detail_response = client.get(f"/api/v1/complaint-drafts/{draft.id}/evidence/batch_lot_number")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["current_value"] == "BMX240602"
    assert detail["current_active_evidence"]["evidence_status"] == "USER_CORRECTION"
    assert len(detail["evidence_history"]) == 2
    assert any(item["evidence_status"] == "SUPERSEDED" for item in detail["evidence_history"])


def test_evidence_filters_document_source_and_normalised_status(db_session: Session) -> None:
    draft = seed_evidence_lock_fixture(db_session)
    client = TestClient(make_app_with_session(db_session))

    response = client.get(f"/api/v1/complaint-drafts/{draft.id}/evidence", params={"evidence_type": "PDF"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["source_attachment"]["original_filename"] == "complaint.pdf"
    assert items[0]["page_number"] == 2
    assert items[0]["evidence_status"] == "NORMALISED_SOURCE"
    assert items[0]["is_inferred"] is False
    assert "storage_path" not in str(items[0])


def test_timeline_orders_events_filters_and_excludes_hidden_reasoning(db_session: Session) -> None:
    draft = seed_evidence_lock_fixture(db_session)
    client = TestClient(make_app_with_session(db_session))

    response = client.get(f"/api/v1/complaint-drafts/{draft.id}/timeline")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["timestamp"] for item in items] == sorted(item["timestamp"] for item in items)
    event_types = {item["event_type"] for item in items}
    assert "USER_MESSAGE" in event_types
    assert "ASSISTANT_RESPONSE" in event_types
    assert "EDIT_COMPLAINT_FIELD_CHANGED" in event_types
    assert "CONFLICT_DETECTED" in event_types
    assert "chain-of-thought" not in str(items).lower()

    filtered = client.get(
        f"/api/v1/complaint-drafts/{draft.id}/timeline",
        params={"field_name": "batch_lot_number"},
    )
    assert filtered.status_code == 200
    assert all(
        not item["affected_fields"] or "batch_lot_number" in item["affected_fields"]
        for item in filtered.json()["items"]
    )


def test_audit_and_complaint_version_repositories_are_append_only() -> None:
    assert not hasattr(AuditEventRepository, "update")
    assert not hasattr(AuditEventRepository, "delete")
    assert not hasattr(ComplaintVersionRepository, "update")
    assert not hasattr(ComplaintVersionRepository, "delete")


def test_canonical_checksum_for_audit_export_batch_is_reproducible(db_session: Session) -> None:
    draft = seed_evidence_lock_fixture(db_session)
    first = draft_to_canonical_dict(draft)
    second = draft_to_canonical_dict(draft)

    assert checksum_snapshot(first) == checksum_snapshot(second)


def seed_batch_impact_draft(db_session: Session, *, batch_number: str | None = "BMX240602") -> ComplaintDraft:
    seed_demo_data(db_session)
    return ComplaintDraftRepository(db_session).create(
        thread_id=f"thread-batch-impact-{batch_number or 'missing'}",
        product_name="Amoxicillin Capsules 500 mg",
        batch_lot_number=batch_number,
        complaint_type="Capsule discolouration",
        detailed_description="Customer reported capsule discolouration in demo batch.",
        created_by="Demo User",
    )


def test_batch_impact_expected_bmx240602_graph(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)

    result = build_batch_impact_analysis(db_session, draft_id=draft.id, created_by="Demo User")

    labels = {node.label for node in result.nodes}
    edge_types = {edge.type for edge in result.edges}
    signal_names = {signal.name for signal in result.signals}
    assert {
        "Amoxicillin Capsules 500 mg",
        "BMX240602",
        "BMX240603",
        "BMX240604",
        "PL-04",
        "DEV-2026-023",
        "CAPA-2026-014",
        "ALU-BLISTER-L2406",
        "Delhi",
        "Mumbai",
        "Jaipur",
        "Central Demo Warehouse",
    }.issubset(labels)
    assert {
        "COMPLAINT_INVOLVES",
        "BATCH_SHARES_PACKAGING_WITH",
        "BATCH_HAS_DEVIATION",
        "DEVIATION_LINKED_TO_CAPA",
        "BATCH_DISTRIBUTED_TO",
        "BATCH_STORED_AT",
    }.issubset(edge_types)
    assert "Repeated similar complaint pattern" in signal_names
    assert result.impact_summary.primary_batch == "BMX240602"
    assert result.impact_summary.related_batches == ["BMX240603", "BMX240604"]
    assert result.impact_summary.similar_complaint_count >= 3
    assert result.impact_summary.remaining_inventory == "51000.000"


def test_batch_impact_has_no_duplicate_nodes_or_edges(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    result = build_batch_impact_analysis(db_session, draft_id=draft.id)

    assert len({node.id for node in result.nodes}) == len(result.nodes)
    assert len({edge.id for edge in result.edges}) == len(result.edges)


def test_batch_impact_evidence_ids_are_present_and_unrelated_records_excluded(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    result = build_batch_impact_analysis(db_session, draft_id=draft.id)
    payload_text = result.model_dump_json()

    assert all(node.evidence_record_id for node in result.nodes)
    assert all(edge.source_record_ids for edge in result.edges)
    assert "Paracetamol Tablets 500 mg" not in payload_text
    assert "wrong label" not in payload_text


def test_batch_impact_missing_and_unknown_batch_handled(db_session: Session) -> None:
    missing = seed_batch_impact_draft(db_session, batch_number=None)
    unknown = seed_batch_impact_draft(db_session, batch_number="UNKNOWN-BATCH")

    with pytest.raises(PharmaQSentinelError) as missing_error:
        build_batch_impact_analysis(db_session, draft_id=missing.id)
    assert missing_error.value.status_code == 409

    with pytest.raises(PharmaQSentinelError) as unknown_error:
        build_batch_impact_analysis(db_session, draft_id=unknown.id)
    assert unknown_error.value.status_code == 404


def test_batch_impact_language_rejects_prohibited_causal_copy() -> None:
    with pytest.raises(ValueError):
        assert_safe_batch_impact_language("The packaging-line deviation caused the complaint.")

    assert_safe_batch_impact_language("A packaging-line deviation may be relevant and should be investigated.")


def test_batch_impact_persists_append_only_run_history(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    first = build_batch_impact_analysis(db_session, draft_id=draft.id)
    second = build_batch_impact_analysis(db_session, draft_id=draft.id)

    runs = db_session.scalars(select(BatchImpactRun).where(BatchImpactRun.draft_id == draft.id)).all()
    assert {run.id for run in runs} == {first.run_id, second.run_id}
    assert len(runs) == 2
    assert all(run.status == "COMPLETE" for run in runs)
    assert not hasattr(BatchImpactRunRepository, "update")
    assert not hasattr(BatchImpactRunRepository, "delete")


def test_batch_impact_endpoint_returns_typed_response(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    client = TestClient(make_app_with_session(db_session))

    response = client.post(f"/api/v1/complaint-drafts/{draft.id}/batch-impact", json={"created_by": "Demo User"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"]
    assert payload["impact_summary"]["primary_batch"] == "BMX240602"
    assert any(node["label"] == "DEV-2026-023" for node in payload["nodes"])


def test_containment_simulation_does_not_modify_database_and_explains_scope(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    batch = db_session.scalars(select(Batch).where(Batch.batch_number == "BMX240602")).one()
    before_status = batch.status
    before_inventory = [
        (record.id, record.quantity_available, record.quantity_on_hold)
        for record in batch.warehouse_inventory
    ]
    client = TestClient(make_app_with_session(db_session))

    response = client.post(
        f"/api/v1/complaint-drafts/{draft.id}/batch-impact/simulate",
        json={
            "include_primary_batch": True,
            "include_shared_packaging_lot": True,
            "include_shared_material_lot": False,
            "include_shared_equipment": False,
            "equipment_date_window_days": 7,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["simulation_only"] is True
    included = {batch_scope["batch_number"]: batch_scope for batch_scope in payload["batches_included"]}
    assert set(included) == {"BMX240602", "BMX240603", "BMX240604"}
    assert "Primary complaint batch selected." in included["BMX240602"]["inclusion_reasons"]
    assert any("Shares packaging material lot" in reason for reason in included["BMX240603"]["inclusion_reasons"])
    db_session.refresh(batch)
    assert batch.status == before_status
    assert [
        (record.id, record.quantity_available, record.quantity_on_hold)
        for record in batch.warehouse_inventory
    ] == before_inventory


def test_quality_war_room_context_scopes_specialist_data(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    draft.customer_contact = "private@example.test"
    draft.patient_consumed_product = True
    db_session.add(
        FieldEvidence(
            draft_id=draft.id,
            field_name="detailed_description",
            field_value={"value": draft.detailed_description},
            evidence_type=EvidenceType.USER_TEXT.value,
            confidence=Decimal("0.9000"),
            is_explicit=True,
            is_active=True,
        )
    )
    db_session.flush()

    context = build_quality_war_room_context(db_session, draft.id)

    assert "customer_contact" not in context["specialist_contexts"]["packaging"]["complaint"]
    assert "adverse_event_signal" not in context["specialist_contexts"]["packaging"]["complaint"]
    assert "batch_impact_summary" not in context["specialist_contexts"]["pv"]


def test_quality_war_room_run_persists_events_and_no_chain_of_thought(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    run_id = run_quality_war_room(db_session, draft_id=draft.id)

    run = db_session.get(QualityWarRoomRun, run_id)
    events = db_session.scalars(select(QualityWarRoomEvent).where(QualityWarRoomEvent.run_id == run_id)).all()
    payload_text = str(run.specialist_outputs_json) + str(run.auditor_output_json) + str(run.consensus_json)

    assert run is not None
    assert run.status == "COMPLETE"
    assert run.iteration_count <= 2
    assert {event.event_type for event in events} >= {"war_room_started", "context_prepared", "consensus_completed"}
    assert "prompt" not in payload_text.lower()
    assert "chain" not in payload_text.lower()


def test_quality_war_room_auditor_rejects_final_causation_language() -> None:
    output = SpecialistOutput(
        agent_name="Manufacturing Investigator",
        concise_findings=["The deviation caused by seal temperature is confirmed root cause."],
        hypotheses=["confirmed root cause"],
        confidence="LOW",
    )

    auditor = run_compliance_auditor({"manufacturing": output})

    assert auditor.rejected_claims
    assert auditor.specialist_revision_requests["manufacturing"]


def test_duplicate_analysis_detects_seeded_recurrence_and_persists(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)

    result = run_duplicate_analysis(db_session, draft_id=draft.id, created_by="Demo User")

    assert result.candidates
    assert result.candidates[0].classification in {
        "LIKELY_EXACT_DUPLICATE",
        "POSSIBLE_DUPLICATE",
        "RECURRENCE_SIGNAL",
        "RELATED_QUALITY_SIGNAL",
    }
    assert result.recurrence_signals
    assert db_session.scalars(select(DuplicateAnalysisRun).where(DuplicateAnalysisRun.draft_id == draft.id)).one()


def test_investigation_playbook_uses_hypothesis_language_and_persists_review_action(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)

    result = create_investigation_playbook(db_session, draft_id=draft.id, created_by="Demo User")
    action = record_review_action(
        db_session,
        draft_id=draft.id,
        request=InvestigationReviewActionRequest(
            action_type="DISMISS_SUGGESTION",
            target_type="PLAYBOOK_STEP",
            target_id=result.root_cause_hypotheses[0].id,
            run_id=result.run_id,
            reason="Reviewer needs more source evidence.",
        ),
    )
    payload_text = result.model_dump_json().lower()

    assert result.category == "discolouration"
    assert "confirmed root cause" not in payload_text
    assert set(result.CAPA_considerations) == {
        "containment",
        "correction",
        "corrective_action",
        "preventive_action",
        "effectiveness_check",
    }
    assert db_session.scalars(select(InvestigationPlaybookRun).where(InvestigationPlaybookRun.draft_id == draft.id)).one()
    assert db_session.get(InvestigationReviewAction, action.id)


def test_quality_war_room_and_investigation_endpoints(db_session: Session) -> None:
    draft = seed_batch_impact_draft(db_session)
    client = TestClient(make_app_with_session(db_session))

    war_room_response = client.post(f"/api/v1/complaint-drafts/{draft.id}/quality-war-room/runs", json={"created_by": "Demo User"})
    duplicate_response = client.post(f"/api/v1/complaint-drafts/{draft.id}/duplicate-analysis", json={"created_by": "Demo User"})
    playbook_response = client.post(f"/api/v1/complaint-drafts/{draft.id}/investigation-playbook", json={"created_by": "Demo User"})

    assert war_room_response.status_code == 201
    run_id = war_room_response.json()["run_id"]
    stream = client.get(f"/api/v1/complaint-drafts/{draft.id}/quality-war-room/runs/{run_id}/stream")
    assert stream.status_code == 200
    assert "event: war_room_started" in stream.text
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["candidates"]
    assert playbook_response.status_code == 200
    assert playbook_response.json()["CAPA_considerations"]["containment"]
