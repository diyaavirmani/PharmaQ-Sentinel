# Database Schema

PharmaQ Sentinel uses MySQL 8 or newer as the application database. The initial schema is focused on durable complaint records, append-only history, and fictional connected pharmaceutical reference data.

## Draft Versus Committed Complaint

`complaint_drafts` stores the mutable working record before QMS-ledger commitment. Draft values are preliminary and may be corrected later through application services.

`complaints` stores the official committed complaint record. It copies the complaint fields needed to reconstruct the record, so it does not depend on the continued existence of the mutable draft.

## Complaint Versions

`complaint_versions` stores immutable snapshots for committed complaints. Each row has a monotonically increasing `version_number` per complaint and a SHA-256 hexadecimal checksum.

Normal repositories expose append/list behavior only for versions. They do not expose update or delete operations.

## Field Evidence

`field_evidence` preserves source evidence at field level. Evidence can point to a user message, uploaded attachment, system record, or AI inference. Old evidence is not deleted when a field is corrected.

## Append-Only Audit Events

`audit_events` records mutation history with old value, new value, timestamp, actor, tool, reason, provider/model metadata where applicable, and extra metadata. The repository exposes append and list operations only.

Audit events use `SET NULL` for optional draft or complaint references so audit rows remain available if an optional related record is removed.

## Connected Pharmaceutical Records

The seed/reference schema includes products, batches, suppliers, material lots, packaging material lots, equipment, manufacturing lines, deviations, CAPAs, distribution records, warehouse inventory, and historical complaints.

Join tables connect batches to raw material lots, packaging material lots, and equipment:

- `batch_material_lots`
- `batch_packaging_material_lots`
- `batch_equipment`

Composite primary keys and composite unique constraints prevent duplicate relationships.

## MySQL Type Decisions

- UUIDs are generated in Python and stored as `CHAR(36)`.
- JSON values use MySQL `JSON`, not JSONB.
- Large extracted text and message bodies use `LONGTEXT`.
- Normal descriptions use `TEXT`.
- Timestamps use `DATETIME(6)` for microsecond precision.
- Python generates timezone-aware UTC timestamps before persistence.
- MySQL `DATETIME` does not retain timezone-offset information; application code treats persisted/reloaded values as UTC.
- Confidence values use `DECIMAL(5,4)`.
- Quantities use `DECIMAL(14,3)`.
- Enums are Python enums stored as uppercase `VARCHAR` values, not native MySQL enums.
- Searchable identifiers use bounded `VARCHAR` columns for predictable indexing.
