from __future__ import annotations

import os
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
from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app
from app.models import (
    ActorType,
    AuditEvent,
    Base,
    Batch,
    Complaint,
    ComplaintDraft,
    ComplaintStatus,
    Product,
    ProductType,
)
from app.models.base import utc_now
from app.models.reference import batch_material_lots
from app.repositories.audit_events import AuditEventRepository
from app.repositories.complaint_drafts import ComplaintDraftRepository
from app.repositories.complaints import ComplaintRepository
from app.services.complaint_snapshots import (
    ComplaintSnapshotService,
    checksum_snapshot,
    draft_to_canonical_dict,
)
from app.utilities.seed_database import seed_database

pytestmark = pytest.mark.mysql


EXPECTED_TABLES = {
    "audit_events",
    "batch_equipment",
    "batch_material_lots",
    "batch_packaging_material_lots",
    "batches",
    "capas",
    "complaint_attachments",
    "complaint_drafts",
    "complaint_messages",
    "complaint_versions",
    "complaints",
    "deviations",
    "distribution_records",
    "equipment",
    "field_evidence",
    "historical_complaints",
    "manufacturing_lines",
    "material_lots",
    "packaging_material_lots",
    "products",
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
    assert db_session.scalars(select(AuditEvent)).one().event_type == "DRAFT_CREATED"


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
