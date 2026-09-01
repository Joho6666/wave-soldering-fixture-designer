"""Structured engineer overrides. Never edit the final DXF file in place."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely import wkt
from shapely.geometry import Point, mapping

ALLOWED_TYPES = {
    "modify_locating_pin",
    "modify_solder_opening",
    "modify_keepout",
    "modify_clamp",
    "modify_pocket",
    "modify_pressure_relief",
}

_FEATURE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


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


def _replace_or_append_polygon(items: list, geom, feature_id: str) -> None:
    for idx, existing in enumerate(items):
        ident = None
        if hasattr(existing, "id"):
            ident = existing.id
        items[idx] = geom if ident == feature_id or idx == 0 and ident is None else existing
    if not items:
        items.append(geom)
    else:
        items[-1] = geom


def apply_overrides(fixture_data: dict[str, Any], overrides: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply structured overrides onto generated fixture dict before SHA/DRC/export."""
    from shapely import wkt as shapely_wkt

    for record in overrides:
        geom = shapely_wkt.loads(record["newGeometry"]["wkt"])
        kind = record["type"]
        feature_id = record["featureId"]
        if kind in {"modify_solder_opening"}:
            windows = list(fixture_data.get("solder_windows") or [])
            if windows:
                windows[0] = geom
            else:
                windows = [geom]
            fixture_data["solder_windows"] = windows
            fg = fixture_data.get("fixture_geometry")
            if fg is not None:
                fg.solder_regions = windows
        elif kind in {"modify_keepout", "modify_pocket"}:
            zones = list(fixture_data.get("keepout_zones") or [])
            if zones:
                zones[0] = geom
            else:
                zones = [geom]
            fixture_data["keepout_zones"] = zones
            fg = fixture_data.get("fixture_geometry")
            if fg is not None:
                fg.keepout_regions = zones
        elif kind == "modify_pressure_relief":
            channels = list(fixture_data.get("pressure_relief_channels") or [])
            if channels:
                channels[0] = geom
            else:
                channels = [geom]
            fixture_data["pressure_relief_channels"] = channels
            fg = fixture_data.get("fixture_geometry")
            if fg is not None:
                fg.pressure_relief_channels = channels
        elif kind == "modify_locating_pin":
            centroid = geom.centroid if geom.geom_type != "Point" else geom
            diameter = 3.0
            if geom.geom_type != "Point":
                minx, miny, maxx, maxy = geom.bounds
                diameter = max(maxx - minx, maxy - miny)
            pins = list(fixture_data.get("pins") or [])
            updated = False
            for pin in pins:
                if str(pin.get("id")) == feature_id:
                    pin["x"] = float(centroid.x)
                    pin["y"] = float(centroid.y)
                    pin["diameter"] = float(diameter)
                    updated = True
            if not updated:
                pins.append({"id": feature_id, "x": float(centroid.x), "y": float(centroid.y), "diameter": float(diameter)})
            fixture_data["pins"] = pins
            fg = fixture_data.get("fixture_geometry")
            if fg is not None:
                fg.locating_pins = pins
        elif kind == "modify_clamp":
            centroid = geom.centroid if geom.geom_type != "Point" else geom
            diameter = 3.4
            if geom.geom_type != "Point":
                minx, miny, maxx, maxy = geom.bounds
                diameter = max(maxx - minx, maxy - miny)
            clips = list(fixture_data.get("clips") or [])
            updated = False
            for clip in clips:
                if str(clip.get("id")) == feature_id:
                    clip["x"] = float(centroid.x)
                    clip["y"] = float(centroid.y)
                    clip["diameter"] = float(diameter)
                    updated = True
            if not updated:
                clips.append({"id": feature_id, "x": float(centroid.x), "y": float(centroid.y), "diameter": float(diameter)})
            fixture_data["clips"] = clips
            fg = fixture_data.get("fixture_geometry")
            if fg is not None:
                fg.clamp_holes = clips
        _ = Point  # keep import used for type checkers
    fg = fixture_data.get("fixture_geometry")
    if fg is not None:
        from app.geometry.digest import geometry_digest
        from app.services.fixture.drc import run_drc

        fg.drc_issues = run_drc(fg)
        fg.geometry_sha256 = geometry_digest(fg)
        fixture_data["issues"] = fg.drc_issues
        fixture_data["geometrySha256"] = fg.geometry_sha256
    return fixture_data
