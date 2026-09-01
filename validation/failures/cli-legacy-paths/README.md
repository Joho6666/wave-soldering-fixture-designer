# cli-legacy-paths

- input: any case under `validation/cases/*/input/*.zip`
- generated: n/a
- expected behavior: CLI discovers Gerber ZIP in `input/` and engineer DXF in `reference/`
- actual behavior: v0.6 CLI only looked at `source/` + `expected/manual_fixture.dxf`, so new cases were skipped
- root cause: leftover v0.5 directory contract
- fix commit: v0.6 Codex follow-up on `feat/v0.6-manufacturing-validation-engine`
- regression test: `backend/tests/test_v06_codex_fixes.py::test_run_all_looks_in_input_and_reference_not_only_source`
