"""Structured engineer overrides. Never edit the final DXF file in place."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely import wkt
from shapely.geometry import mapping

ALLOWED_TYPES = {
    "modify_locating_pin",
    "modify_solder_opening",
    "modify_keepout",
    "modify_clamp",
    "modify_pocket",
    "modify_pressure_relief",
}

POLYGON_TYPES = {
    "modify_solder_opening",
    "modify_keepout",
    "modify_pocket",
    "modify_pressure_relief",
}

_FEATURE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_INDEX_RE = re.compile(r"(\d+)$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_override(payload: dict[str, Any]) -> dict[str, Any]:
    kind = payload.get("type")
    if kind not in ALLOWED_TYPES:
        raise ValueError(f"unsupported override type: {kind}")
    feature_id = str(payload.get("featureId") or "").strip()
    if not _FEATURE_ID_RE.match(feature_id):
        raise ValueError("featureId is required and must be a simple identifier")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 8:
        raise ValueError("reason is required (min 8 characters)")
    engineer = str(payload.get("engineer") or "").strip()
    if not engineer:
        raise ValueError("engineer is required")
    geometry = payload.get("newGeometry")
    if not isinstance(geometry, dict) or not geometry.get("wkt"):
        raise ValueError("newGeometry.wkt is required")
    try:
        geom = wkt.loads(str(geometry["wkt"]))
    except Exception as exc:
        raise ValueError(f"invalid WKT: {exc}") from exc
    if geom.is_empty:
        raise ValueError("newGeometry is empty")
    if kind in POLYGON_TYPES and geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"{kind} requires Polygon WKT, not {geom.geom_type}")
    record = {
        "type": kind,
        "featureId": feature_id,
        "sourceIds": list(payload.get("sourceIds") or []),
        "oldGeometrySha": payload.get("oldGeometrySha"),
        "newGeometry": {"wkt": geom.wkt, "geojson": mapping(geom)},
        "reason": reason,
        "engineer": engineer,
        "timestamp": payload.get("timestamp") or utc_now(),
    }
    return record


def override_dir(case_dir: Path) -> Path:
    path = case_dir / "overrides"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_overrides(case_dir: Path) -> list[dict[str, Any]]:
    folder = case_dir / "overrides"
    if not folder.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return items


def save_override(case_dir: Path, record: dict[str, Any]) -> Path:
    folder = override_dir(case_dir)
    stamp = record["timestamp"].replace(":", "").replace("-", "")
    filename = f"{stamp}_{record['type']}_{record['featureId']}.json"
    path = folder / filename
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _index_from_feature_id(feature_id: str, count: int) -> int | None:
    match = _INDEX_RE.search(feature_id.replace("SO-", "").replace("so-", ""))
    if not match:
        return None
    idx = int(match.group(1))
    if idx == 0:
        return 0 if count > 0 else None
    idx -= 1
    if 0 <= idx < count:
        return idx
    return None


def _replace_polygon(geoms: list, metas: list, feature_id: str, geom) -> None:
    for i, meta in enumerate(metas or []):
        ident = getattr(meta, "id", None)
        if ident == feature_id:
            geoms[i] = geom
            meta.geometry = geom
            return
    idx = _index_from_feature_id(feature_id, len(geoms))
    if idx is None:
        raise ValueError(f"featureId {feature_id} did not match a generated feature")
    geoms[idx] = geom
    if idx < len(metas):
        metas[idx].geometry = geom


def _replace_hole(items: list[dict[str, Any]], feature_id: str, centroid, diameter: float) -> list[dict[str, Any]]:
    updated = False
    for item in items:
        if str(item.get("id")) == feature_id:
            item["x"] = float(centroid.x)
            item["y"] = float(centroid.y)
            item["diameter"] = float(diameter)
            updated = True
    if not updated:
        raise ValueError(f"featureId {feature_id} did not match a generated hole")
    return items


def apply_overrides(fixture_data: dict[str, Any], overrides: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply structured overrides onto generated fixture dict before SHA/DRC/export."""
    from shapely import wkt as shapely_wkt

    fg = fixture_data.get("fixture_geometry")
    for record in overrides:
        geom = shapely_wkt.loads(record["newGeometry"]["wkt"])
        kind = record["type"]
        feature_id = record["featureId"]
        if kind == "modify_solder_opening":
            windows = list(fixture_data.get("solder_windows") or [])
            metas = list(getattr(fg, "solder_region_meta", None) or []) if fg is not None else []
            if not windows:
                raise ValueError("no solder openings to override")
            _replace_polygon(windows, metas, feature_id, geom)
            fixture_data["solder_windows"] = windows
            if fg is not None:
                fg.solder_regions = windows
                fg.solder_region_meta = metas
        elif kind in {"modify_keepout", "modify_pocket"}:
            zones = list(fixture_data.get("keepout_zones") or [])
            metas = list(getattr(fg, "keepout_region_meta", None) or []) if fg is not None else []
            if not zones:
                raise ValueError("no keepout/pocket regions to override")
            _replace_polygon(zones, metas, feature_id, geom)
            fixture_data["keepout_zones"] = zones
            if fg is not None:
                fg.keepout_regions = zones
                fg.keepout_region_meta = metas
        elif kind == "modify_pressure_relief":
            channels = list(fixture_data.get("pressure_relief_channels") or [])
            metas = list(getattr(fg, "pressure_relief_meta", None) or []) if fg is not None else []
            if not channels:
                raise ValueError("no pressure-relief channels to override")
            _replace_polygon(channels, metas, feature_id, geom)
            fixture_data["pressure_relief_channels"] = channels
            if fg is not None:
                fg.pressure_relief_channels = channels
                fg.pressure_relief_meta = metas
        elif kind == "modify_locating_pin":
            centroid = geom.centroid if geom.geom_type != "Point" else geom
            diameter = 3.0
            if geom.geom_type != "Point":
                minx, miny, maxx, maxy = geom.bounds
                diameter = max(maxx - minx, maxy - miny)
            pins = list(fixture_data.get("pins") or [])
            fixture_data["pins"] = _replace_hole(pins, feature_id, centroid, diameter)
            if fg is not None:
                fg.locating_pins = fixture_data["pins"]
        elif kind == "modify_clamp":
            centroid = geom.centroid if geom.geom_type != "Point" else geom
            diameter = 3.4
            if geom.geom_type != "Point":
                minx, miny, maxx, maxy = geom.bounds
                diameter = max(maxx - minx, maxy - miny)
            clips = list(fixture_data.get("clips") or [])
            fixture_data["clips"] = _replace_hole(clips, feature_id, centroid, diameter)
            if fg is not None:
                fg.clamp_holes = fixture_data["clips"]
    if fg is not None:
        from app.geometry.digest import geometry_digest
        from app.services.fixture.drc import run_drc

        fg.drc_issues = run_drc(fg)
        fg.geometry_sha256 = geometry_digest(fg)
        fixture_data["issues"] = fg.drc_issues
        fixture_data["geometrySha256"] = fg.geometry_sha256
    return fixture_data
