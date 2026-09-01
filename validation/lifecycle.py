"""Production case lifecycle. Distinct from golden comparison status."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

LIFECYCLE_STATES = (
    "IMPORTED",
    "PARSED",
    "GENERATED",
    "ENGINEER_REVIEW",
    "REFERENCE_AVAILABLE",
    "VALIDATED",
    "CNC_TESTED",
    "ASSEMBLY_TESTED",
    "WAVE_TESTED",
    "APPROVED",
    "REJECTED",
)

_ORDER = {name: i for i, name in enumerate(LIFECYCLE_STATES)}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_history(status: str = "IMPORTED", time: str | None = None) -> list[dict[str, str]]:
    return [{"status": status, "time": time or utc_now()}]


def append_history(history: list[dict[str, Any]] | None, status: str, time: str | None = None) -> list[dict[str, Any]]:
    items = list(history or [])
    if items and items[-1].get("status") == status:
        return items
    if status not in LIFECYCLE_STATES:
        raise ValueError(f"unknown lifecycle status: {status}")
    items.append({"status": status, "time": time or utc_now()})
    return items


def can_advance(current: str, nxt: str) -> bool:
    if nxt == "REJECTED":
        return current in LIFECYCLE_STATES
    if nxt == "APPROVED":
        return current in {"VALIDATED", "CNC_TESTED", "ASSEMBLY_TESTED", "WAVE_TESTED"}
    if current not in _ORDER or nxt not in _ORDER:
        return False
    return _ORDER[nxt] >= _ORDER[current]


def infer_lifecycle(*, has_input: bool, has_generated: bool, has_reference: bool, has_report: bool, declared: str | None) -> str:
    if declared in LIFECYCLE_STATES:
        return declared
    if not has_input:
        return "IMPORTED"
    if has_reference and has_report:
        return "VALIDATED"
    if has_reference:
        return "REFERENCE_AVAILABLE"
    if has_generated:
        return "GENERATED"
    return "PARSED" if has_input else "IMPORTED"
