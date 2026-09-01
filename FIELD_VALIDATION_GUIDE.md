# FIELD_VALIDATION_GUIDE

This is how a real board should enter the loop. Nothing here invents a PASS.

1. Import manufacturing files  
   `python scripts/import_validation_case.py --case CASE-008 --gerber board.zip --pnp pnp.csv --bom bom.csv`  
   Status becomes `IMPORTED`. No reference DXF is created.

2. Parse + generate  
   `POST /api/validation/cases/CASE-008/regenerate`  
   Writes `generated/fixture.dxf`, SVG, manifest. Lifecycle `GENERATED`. Comparison remains `awaiting_reference`.

3. Engineer review  
   Mandatory reviews and DRC still block Production DXF. Structured overrides go to `overrides/*.json` with reason + engineer. Do not edit the DXF.

4. Reference  
   Only an engineer-drawn DXF in `reference/engineer_fixture.dxf` moves lifecycle to `REFERENCE_AVAILABLE`. Copying generated → reference is forbidden.

5. Validate  
   Feature scores (pins: center/diameter; openings: IoU/Hausdorff/area; outline: contour deviation). Overlay: blue generated, green reference, highlighted difference.

6. Physical feedback  
   Fill `manufacturing_feedback.json` after CNC / assembly / wave. Untested stays `tested: false`.

7. Approve  
   `APPROVED` requires a real reference DXF. Software PASS without shop trials is still **not production ready**.
