# Seed Data

The development seed command creates fictional demonstration records only. These records are not real company data and must not be presented as live pharmaceutical records.

## Command

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.utilities.seed_database
```

The command prints table counts as JSON. Running it more than once is safe; records use stable natural identifiers and are updated in place rather than duplicated.

## Stable Demo Scenario

The core scenario centers on Amoxicillin Capsules 500 mg and batches:

- `BMX240602`
- `BMX240603`
- `BMX240604`

Batch `BMX240602` is connected to manufacturing line `ML-02`, packaging line `PL-04`, raw material lots `AMX-API-L2405` and `MCC-L2406`, shared packaging material lot `ALU-BLISTER-L2406`, equipment including `EQ-PL04-SEALER` and `EQ-PL04-CAMERA`, deviation `DEV-2026-023`, CAPA `CAPA-2026-014`, distribution records for Delhi, Mumbai, Jaipur, remaining warehouse inventory, and related historical demonstration complaints.

## Expected Counts

After seeding the initial database layer:

- Products: 5
- Batches: 3
- Suppliers: 2
- Raw material lots: 2
- Packaging material lots: 1
- Equipment records: 3
- Deviations: 1
- CAPAs: 1
- Historical complaints: 13
- Distribution records: 3
- Warehouse inventory records: 1

Historical complaint examples cover capsule discolouration, broken tablets, missing tablets, blister leakage, wrong label, foreign particles, API assay discrepancy, API moisture discrepancy, damaged container, suspected adverse event, and suspected counterfeit or tampering.
