#!/usr/bin/env python3
"""Import a validation case. Never invents an engineer reference DXF."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validation.lifecycle import append_history, utc_now
from validation.manufacturing import default_feedback, write_feedback

CASE_RE = re.compile(r"^CASE-\d{3,}$")
CASES_ROOT = (ROOT / "validation" / "cases").resolve()


def _confine(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes {root}: {path}") from exc
    return resolved


def import_case(
    case_id: str,
    gerber: Path,
    pnp: Path | None = None,
    bom: Path | None = None,
    reference: Path | None = None,
    description: str = "",
    kind: str = "synthetic_demo",
) -> Path:
    if not CASE_RE.match(case_id):
        raise ValueError("case id must look like CASE-008")
    if kind not in {"synthetic_demo", "customer"}:
        raise ValueError("kind must be synthetic_demo or customer")
    if not gerber.is_file():
        raise FileNotFoundError(gerber)
    case_dir = _confine(CASES_ROOT / case_id, CASES_ROOT)
    for name in ("input", "reference", "generated", "report", "overrides"):
        (case_dir / name).mkdir(parents=True, exist_ok=True)
        keep = case_dir / name / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    shutil.copy2(gerber, case_dir / "input" / "gerber.zip")
    if pnp is not None:
        shutil.copy2(pnp, case_dir / "input" / "pnp.csv")
    if bom is not None:
        shutil.copy2(bom, case_dir / "input" / "bom.csv")

    has_reference = False
    if reference is not None:
        if not reference.is_file():
            raise FileNotFoundError(reference)
        shutil.copy2(reference, case_dir / "reference" / "engineer_fixture.dxf")
        has_reference = True

    history = append_history([], "IMPORTED")
    if has_reference:
        history = append_history(history, "REFERENCE_AVAILABLE")
    meta = {
        "caseId": case_id,
        "kind": kind,
        "description": description or f"Imported {case_id}",
        "pcbInput": "input/gerber.zip",
        "referenceDxf": "reference/engineer_fixture.dxf" if has_reference else None,
        "fixtureParameters": {},
        "processProfile": {},
        "expectedFeatures": {},
        "status": "awaiting_reference" if not has_reference else "ready",
        "lifecycle": "REFERENCE_AVAILABLE" if has_reference else "IMPORTED",
        "history": history,
        "hasReference": has_reference,
        "engineer": None,
        "createdAt": utc_now(),
        "notes": "Do not copy generated DXF into reference/. Do not mark passed without an engineer DXF.",
    }
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_feedback(case_dir, default_feedback(case_id))
    return case_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a validation case directory. Does not invent reference DXF.")
    parser.add_argument("--case", required=True)
    parser.add_argument("--gerber", required=True)
    parser.add_argument("--pnp")
    parser.add_argument("--bom")
    parser.add_argument("--reference", help="Optional engineer DXF. Omitted = no fake reference.")
    parser.add_argument("--description", default="")
    parser.add_argument("--kind", default="synthetic_demo", choices=["synthetic_demo", "customer"])
    args = parser.parse_args()
    case_dir = import_case(
        args.case,
        Path(args.gerber),
        Path(args.pnp) if args.pnp else None,
        Path(args.bom) if args.bom else None,
        Path(args.reference) if args.reference else None,
        args.description,
        args.kind,
    )
    print(f"created {case_dir}")
    if args.reference is None:
        print("reference: none (awaiting_reference)")


if __name__ == "__main__":
    main()
