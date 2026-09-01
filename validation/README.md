# Golden Sample Validation Framework

Compare auto-generated fixture DXF against engineer-drawn reference DXF for the same PCB, producing per-feature PASS / WARNING / FAIL reports.

## Directory

```
validation/
  cases/
    CASE-001/
      case.json
      input/          # gerber.zip (missing today)
      reference/      # engineer DXF (missing today)
      generated/      # auto DXF/SVG
      report/         # validation_report.json / .md / overlay.svg
```

`case.json` status: `awaiting_input` | `awaiting_reference_dxf` | `ready` | `passed` | `failed` | `review_required`.

CASE-001 is `awaiting_input`. There is **no** engineer DXF in this repository. Do not mark it passed.

## Usage

```bash
python -m validation.run_all
```

API:

- `GET /api/validation/cases`
- `GET /api/validation/cases/{id}`
- `GET /api/validation/cases/{id}/overlay`
- `POST /api/validation/cases/{id}/run` — 409 if input or reference DXF is missing

UI: `/validation`
