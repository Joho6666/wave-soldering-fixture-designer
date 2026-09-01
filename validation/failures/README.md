# Failure library

Typical software and manufacturing failure modes. Each real bug fix must add a folder here **and** a regression test.

Do not invent CNC / assembly / wave-solder accidents. Current field failures: **0**.

## Layout

```
validation/failures/<slug>/
  README.md
  input/            optional reproducing ZIP
  generated/        optional
  expected_behavior.md
  actual_behavior.md
  root_cause.md
  fix_commit.txt
  regression_test.txt   path to pytest/vitest
```

## Catalog (software modes only)

| slug | expected | actual (historical) | regression |
|---|---|---|---|
| wrong-layer-mapping | low-confidence layers stay unconfirmed | would have auto-mapped | `tests/test_layer_confirmation.py` |
| missing-npth | no NPTH → mandatory review | pin search used slots | `tests/test_slot_drill_filter.py` |
| incorrect-locating-pin | pin from NPTH scoring | slot drills as pins | `tests/test_locating_pin_selection.py` |
| oversized-keepout | keepout from BOT/PnP | invented 1 mm keepout | `tests/test_pocket_and_solder_optimizer.py` |
| undersized-solder-opening | THT window from pads | greedy PTH too small | `tests/test_solder_shape_optimization.py` |
| pcb-outline-parsing-error | closed outline required | empty outline used estimate | `tests/test_fixture_pipeline.py` |
| component-collision | DRC keepout↔solder | missed intersections | `tests/test_drc_collisions.py` |
| insufficient-pocket-floor | blocking DRC | depth ignored in SHA | `tests/test_geometry_sha_coverage.py` |
| panel-transform-error | instance frames kept | body from single board | `tests/test_v06_codex_fixes.py` |
| pressure-relief-collision | channel attached to pocket | detached centroid corridor | `tests/test_v06_codex_fixes.py` |
| cli-legacy-paths | input/ + reference/ | only source/expected | `tests/test_v06_codex_fixes.py` |
