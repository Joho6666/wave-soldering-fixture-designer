# Wave Soldering Fixture Designer

Gerber / Excellon / PnP / BOM → semantic PCB → deterministic wave-soldering fixture geometry → DXF / SVG.

Current version: **0.7.0** / `fixture-engine-0.7.0` / rules `1.3.0`  
Source of truth: `backend/app/core/version.py`

**NOT PRODUCTION READY.** Customer Gerber = 0. Engineer reference DXF = 0. CNC / assembly / wave solder = 0.

---

## What it does

Builds a pallet fixture from manufacturing files: sink pocket, BOT keepouts, THT solder openings, locating pins, clamps, rails, solder barriers, handholds. Optional (off by default): wave-direction openings, pressure relief, NxM grid panel.

v0.7 adds a field-validation pipeline: case lifecycle, feature-level comparison, CAD overlay, structured engineer overrides, manufacturing feedback, and honest metrics. It does **not** claim the algorithm is shop-floor proven.

## Supported Inputs

- Gerber RS-274X / X2 ZIP (EasyEDA / 嘉立创 / KiCad / Altium / Allegro naming attempted; nonstandard names need layer confirmation)
- Excellon drills
- Optional PnP / CPL
- Optional BOM CSV
- Chinese / GBK ZIP names
- mil or mm
- Missing PnP, BOM, GBO, GTO, or NPTH → mandatory engineer review, not invented geometry

## Pipeline

Automatic generation → Validation → Engineer review → Structured override → Regenerate → SHA / DRC / Production Gate → (future) CNC / assembly / wave feedback.

AI may explain DRC, parameters, and failures, and may translate language into a structured command. AI may not generate production geometry, bypass DRC, auto-override blocking issues, accept mandatory reviews, edit golden reference, or mark a case PASS.

## Validation Status

Numbers below are dataset facts. Test counts live in [VALIDATION_STATUS.md](VALIDATION_STATUS.md) from the same machine run.

- Software Validation: see VALIDATION_STATUS.md
- Golden Samples: 5 structurally complete synthetic cases
- Engineer Reference DXF: **0**
- CNC Trials: **0**
- Assembly Trials: **0**
- Wave Solder Trials: **0**

Details: [VALIDATION_METRICS.md](VALIDATION_METRICS.md)

## Known Limitations

- No real customer boards in this repository
- No engineer-drawn reference DXF, so no real IoU
- Directional openings and pressure relief default off
- Grid panel is metadata + instance copies, not KiKit / mouse-bite CAM
- DXF is 2D; pocket depth is recorded, not toolpathed
- Component height often missing; pocket depth falls back to defaults
- Without PnP, BOT keepout still depends on silkscreen

## Run

Mock API is **only** `VITE_USE_MOCK_API=true`. Default is real FastAPI.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

npm ci
npm run dev
```

Open http://localhost:3000 and http://localhost:3000/validation

## Test

```bash
cd backend
python -m pytest tests

npm test -- --run
npm run lint
npm run build
```

Import a case (does not invent reference DXF):

```bash
python scripts/import_validation_case.py --case CASE-008 --gerber board.zip
```

## Real-world Validation

None yet.

| Gate | Count |
|---|---:|
| Software Validation tests | see VALIDATION_STATUS.md |
| Golden Samples | 5 (synthetic_demo) |
| Engineer Reference DXF | 0 |
| CNC Trials | 0 |
| Assembly Trials | 0 |
| Wave Solder Trials | 0 |

**NOT PRODUCTION READY**

[MIT License](LICENSE)
