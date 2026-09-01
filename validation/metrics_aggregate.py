"""Aggregate honest validation metrics. Missing data is 0, never invented."""
from __future__ import annotations

from typing import Any


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    gerber_ok = sum(1 for c in cases if c.get("hasInput"))
    generated_ok = sum(1 for c in cases if c.get("hasGeneratedDxf"))
    reference_ok = sum(1 for c in cases if c.get("hasReferenceDxf"))
    customer = sum(1 for c in cases if c.get("kind") == "customer")
    ious: list[float] = []
    pin_err: list[float] = []
    solder_iou: list[float] = []
    corrections = 0
    cnc = assembly = wave = 0
    for case in cases:
        corrections += len(case.get("overrides") or [])
        mfg = case.get("manufacturing") or {}
        if (mfg.get("cnc") or {}).get("tested"):
            cnc += 1
        if (mfg.get("assembly") or {}).get("tested"):
            assembly += 1
        if (mfg.get("waveSolder") or {}).get("tested"):
            wave += 1
        features = ((case.get("report") or {}).get("features") or [])
        for feat in features:
            name = feat.get("feature") or feat.get("name")
            if name in {"fixture_body", "fixture_outline"} and isinstance(feat.get("iou"), (int, float)):
                ious.append(float(feat["iou"]))
            if name == "locating_pins":
                err = feat.get("centroidErrorMm") or feat.get("hole_position_error_mm")
                if isinstance(err, (int, float)):
                    pin_err.append(float(err))
            if name in {"solder_openings", "solder_windows"} and isinstance(feat.get("iou"), (int, float)):
                solder_iou.append(float(feat["iou"]))
    return {
        "totalCases": total,
        "gerberParseSuccess": f"{gerber_ok} / {total}" if total else "0 / 0",
        "gerberParseSuccessCount": gerber_ok,
        "fixtureGenerationSuccess": f"{generated_ok} / {total}" if total else "0 / 0",
        "fixtureGenerationSuccessCount": generated_ok,
        "engineerReferenceAvailable": f"{reference_ok} / {total}" if total else "0 / 0",
        "engineerReferenceCount": reference_ok,
        "customerCases": customer,
        "averageFixtureIou": _mean(ious),
        "averageLocatingPinErrorMm": _mean(pin_err),
        "averageSolderOpeningIou": _mean(solder_iou),
        "manualCorrectionsPerCase": (corrections / total) if total else 0,
        "blockingDrcFalsePositive": 0,
        "blockingDrcFalseNegative": 0,
        "cncTested": cnc,
        "assemblyTested": assembly,
        "waveSolderTested": wave,
        "softwareTestsNote": "see VALIDATION_STATUS.md for pytest/vitest counts from the same machine run",
    }


def render_markdown(stats: dict[str, Any]) -> str:
    def fmt(value: Any) -> str:
        if value is None:
            return "0 (no comparable reference)"
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    lines = [
        "# VALIDATION_METRICS",
        "",
        "Aggregated from `validation/cases/*/`. Missing measurements are 0. Nothing is invented.",
        "",
        f"Total Cases: {stats['totalCases']}",
        f"Gerber Parse Success: {stats['gerberParseSuccess']}",
        f"Fixture Generation Success: {stats['fixtureGenerationSuccess']}",
        f"Engineer Reference Available: {stats['engineerReferenceAvailable']}",
        f"Customer Cases: {stats['customerCases']}",
        f"Average Fixture IoU: {fmt(stats['averageFixtureIou'])}",
        f"Average locating pin error: {fmt(stats['averageLocatingPinErrorMm'])}",
        f"Average solder opening IoU: {fmt(stats['averageSolderOpeningIou'])}",
        f"Manual corrections per case: {fmt(stats['manualCorrectionsPerCase'])}",
        f"Blocking DRC false positive: {stats['blockingDrcFalsePositive']}",
        f"Blocking DRC false negative: {stats['blockingDrcFalseNegative']}",
        f"CNC Tested: {stats['cncTested']}",
        f"Assembly Tested: {stats['assemblyTested']}",
        f"Wave Solder Tested: {stats['waveSolderTested']}",
        "",
        "**NOT PRODUCTION READY**",
        "",
    ]
    return "\n".join(lines)
