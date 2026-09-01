# Golden Sample Validation Framework

Compare auto-generated fixture DXF against engineer-drawn reference DXF for the same PCB.

There is **no** engineer DXF in this repository. Cases stay `awaiting_reference`. Do not mark passed. Do not copy `generated/` into `reference/`.

## Directory

```
validation/cases/CASE-00N/
  case.json
  input/gerber.zip
  reference/          # empty until an engineer provides DXF
  generated/fixture.dxf
  overrides/
  report/
  manufacturing_feedback.json
```

Lifecycle: IMPORTED → PARSED → GENERATED → ENGINEER_REVIEW → REFERENCE_AVAILABLE → VALIDATED → CNC_TESTED → ASSEMBLY_TESTED → WAVE_TESTED → APPROVED | REJECTED

## Usage

```bash
python -m validation.run_all
python scripts/import_validation_case.py --case CASE-008 --gerber board.zip
python scripts/aggregate_validation_metrics.py
```

API: `/api/validation/cases`, `/overlay`, `/regenerate`, `/overrides`, `/lifecycle`, `/manufacturing`

UI: `/validation`
