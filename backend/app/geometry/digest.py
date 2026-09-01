"""Deterministic geometry SHA covering every entity that changes production output."""
from __future__ import annotations

import hashlib
from typing import Any, Iterable

from shapely import make_valid, normalize, to_wkb
from shapely.geometry.base import BaseGeometry


MACHINING_PARAM_KEYS = (
    "palletThicknessMm",
    "pocketFloorThicknessMm",
    "defaultPocketDepthMm",
    "componentVerticalClearanceMm",
    "minimumMaterialWebMm",
    "solderMinOpeningWidthMm",
    "solderClearanceMm",
    "keepoutClearanceMm",
    "fixtureMarginXmm",
    "fixtureMarginYmm",
    "railWidthMm",
    "solderBarrierWidthMm",
)


def _round(value: float) -> str:
    return f"{float(value):.6f}"


def _geom_wkb(geom: BaseGeometry) -> bytes:
    valid = make_valid(geom)
    if valid.is_empty:
        return b"empty"
    return to_wkb(normalize(valid), hex=False)


def _geom_sort_key(geom: BaseGeometry) -> tuple:
    c = geom.centroid
    return (
        round(float(c.x), 6),
        round(float(c.y), 6),
        round(float(geom.area), 6),
        _geom_wkb(geom),
    )


def _update_geom(h: Any, geom: BaseGeometry | None) -> None:
    if geom is None or geom.is_empty:
        h.update(b"none")
        return
    h.update(_geom_wkb(geom))


def _update_geoms(h: Any, geoms: Iterable[BaseGeometry] | None, label: bytes) -> None:
    h.update(label)
    items = [g for g in (geoms or []) if g is not None and not g.is_empty]
    items.sort(key=_geom_sort_key)
    h.update(str(len(items)).encode("utf-8"))
    for g in items:
        h.update(_geom_wkb(g))


def _update_holes(h: Any, holes: Iterable[dict[str, Any]] | None, label: bytes) -> None:
    h.update(label)
    items = list(holes or [])
    items.sort(
        key=lambda p: (
            round(float(p.get("x", 0.0)), 6),
            round(float(p.get("y", 0.0)), 6),
            round(float(p.get("diameter", 0.0)), 6),
        )
    )
    h.update(str(len(items)).encode("utf-8"))
    for p in items:
        h.update(
            f"{_round(p.get('x', 0.0))}:{_round(p.get('y', 0.0))}:{_round(p.get('diameter', 0.0))}".encode("utf-8")
        )


def _update_pocket_depths(h: Any, metas: Iterable[Any] | None) -> None:
    h.update(b"pocket-depth")
    rows: list[tuple] = []
    for meta in metas or []:
        geom = getattr(meta, "geometry", None)
        params = getattr(meta, "parameters", None) or {}
        depth = params.get("pocketDepthMm")
        if geom is None or geom.is_empty:
            key = (0.0, 0.0, 0.0)
        else:
            key = (round(float(geom.centroid.x), 6), round(float(geom.centroid.y), 6), round(float(geom.area), 6))
        depth_s = _round(depth) if depth is not None else "none"
        rows.append((*key, depth_s))
    rows.sort()
    for row in rows:
        h.update(repr(row).encode("utf-8"))


def _update_machining_params(h: Any, params: dict[str, Any] | None) -> None:
    h.update(b"machining-params")
    data = params or {}
    for key in MACHINING_PARAM_KEYS:
        raw = data.get(key)
        if raw is None:
            h.update(f"{key}=none".encode("utf-8"))
        else:
            try:
                h.update(f"{key}={_round(raw)}".encode("utf-8"))
            except (TypeError, ValueError):
                h.update(f"{key}={raw}".encode("utf-8"))


def geometry_digest(fixture: Any) -> str:
    """SHA-256 of every entity that changes the produced fixture.

    Sorting keys are numeric (centroid, area) plus WKB — never Python object
    identity or insertion order.
    """
    h = hashlib.sha256()
    pcb = getattr(fixture, "pcb", None)
    _update_geom(h, getattr(pcb, "outline", None) if pcb is not None else None)
    _update_geom(h, getattr(fixture, "body", None))
    _update_geom(h, getattr(fixture, "sink_region", None))
    _update_geoms(h, getattr(fixture, "keepout_regions", None), b"keepout")
    _update_geoms(h, getattr(fixture, "solder_regions", None), b"solder")
    _update_geoms(h, getattr(fixture, "handholds", None), b"handhold")
    _update_geoms(h, getattr(fixture, "rails", None), b"rail")
    _update_geoms(h, getattr(fixture, "solder_barriers", None), b"barrier")
    _update_geoms(h, getattr(fixture, "pressure_relief_channels", None), b"relief")
    _update_holes(h, getattr(fixture, "locating_pins", None), b"pins")
    _update_holes(h, getattr(fixture, "clamp_holes", None), b"clamps")
    _update_holes(h, getattr(fixture, "spring_clip_holes", None), b"springs")
    _update_holes(h, getattr(fixture, "solder_barrier_mount_holes", None), b"barrier-holes")
    _update_holes(h, getattr(fixture, "tooling_holes", None), b"tooling")
    _update_holes(h, getattr(fixture, "fiducials", None), b"fiducials")
    _update_pocket_depths(h, getattr(fixture, "keepout_region_meta", None))
    _update_machining_params(h, getattr(fixture, "parameters", None))
    panel = getattr(fixture, "panel", None)
    if panel is not None:
        h.update(b"panel")
        h.update(str(len(getattr(panel, "pcb_instances", []) or [])).encode("utf-8"))
        for inst in getattr(panel, "pcb_instances", []) or []:
            h.update(
                f"{inst.x:.6f}:{inst.y:.6f}:{inst.rotation:.6f}:{int(bool(inst.mirror))}".encode("utf-8")
            )
    return h.hexdigest()
