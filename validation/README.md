# Golden Sample Validation Framework

## Purpose
Compare auto-generated fixture DXF against engineer-drawn reference DXF for the same PCB Gerber, producing quantitative geometry accuracy reports.

## Directory Structure
```
validation/
  manual_dxf_parser.py      # Parse engineer-drawn DXF into Shapely geometries
  geometry_comparator.py     # Compute IoU, Hausdorff, center/diameter errors
  run_all.py                 # CLI: scan cases/, generate, compare, report
  cases/
    CASE-NNN/
      source/                # gerber.zip (input)
      expected/              # manual_fixture.dxf + expected.json + manual_layer_mapping.json
      generated/             # auto-generated fixture.dxf + preview.svg (output)
      report/                # comparison.json + comparison.md (output)
```

## Usage
```bash
cd backend
python -m validation.run_all
```

## Adding a New Case
1. Create `validation/cases/CASE-NNN/source/` and place `gerber.zip` inside.
2. Place the engineer-drawn DXF in `expected/manual_fixture.dxf`.
3. Optionally add `expected/manual_layer_mapping.json` if DXF layer names are non-standard.
4. Optionally add `expected/expected.json` with dimensional metadata.
5. Run `python -m validation.run_all` to auto-generate and compare.

## Layer Mapping
The parser maps DXF layers to standard fixture layers:
- `SINK_AREA` / `SINK_REGION` → sink region
- `KEEPOUT_BOT` / `KEEP_OUT_BOT` → BOT keepout regions
- `SOLDER_WINDOW_TOP` / `SOLDER_TOP` → TOP solder windows
- `POSITIONING_PINS` / `LOCATING_PINS` → locating pins (circles)
- `CLIPS` / `CLAMP_HOLES` → clamp holes (circles)
- `FIXTURE_OUTLINE` → fixture body outline
- `RAILS` → rail regions
- `SOLDER_BARRIERS` → solder barrier regions

Non-standard names can be remapped via `manual_layer_mapping.json`:
```json
{
  "MyCustomSinkLayer": "SINK_AREA",
  "OuterFrame": "FIXTURE_OUTLINE"
}
```
