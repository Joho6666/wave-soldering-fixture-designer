"""Parse engineer-drawn fixture DXF files into Shapely geometries."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ezdxf
from shapely.geometry import (
    LineString,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.ops import polygonize, unary_union

STANDARD_LAYER_MAP: dict[str, str] = {
    "SINK_AREA": "sink_region",
    "SINK_REGION": "sink_region",
    "KEEPOUT_BOT": "keepout_regions",
    "KEEP_OUT_BOT": "keepout_regions",
    "SOLDER_WINDOW_TOP": "solder_regions",
    "SOLDER_TOP": "solder_regions",
    "POSITIONING_PINS": "locating_pins",
    "LOCATING_PINS": "locating_pins",
    "CLIPS": "clamp_holes",
    "CLAMP_HOLES": "clamp_holes",
    "FIXTURE_OUTLINE": "fixture_outline",
    "RAILS": "rails",
    "SOLDER_BARRIERS": "solder_barriers",
    "BARRIER_MOUNT_HOLES": "barrier_mount_holes",
    "SPRING_CLIPS": "spring_clips",
    "HANDHOLDS": "handholds",
    "PCB_OUTLINE": "pcb_outline",
}

CIRCLE_FEATURE_KEYS = {
    "locating_pins",
    "clamp_holes",
    "barrier_mount_holes",
    "spring_clips",
}

POLYGON_FEATURE_KEYS = {
    "sink_region",
    "keepout_regions",
    "solder_regions",
    "fixture_outline",
    "rails",
    "solder_barriers",
    "handholds",
    "pcb_outline",
}


@dataclass
class CircleFeature:
    x: float
    y: float
    diameter: float
    layer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y, "diameter": self.diameter, "layer": self.layer}


@dataclass
class ManualFixtureData:
    sink_region: list[Polygon] = field(default_factory=list)
    keepout_regions: list[Polygon] = field(default_factory=list)
    solder_regions: list[Polygon] = field(default_factory=list)
    fixture_outline: list[Polygon] = field(default_factory=list)
    rails: list[Polygon] = field(default_factory=list)
    solder_barriers: list[Polygon] = field(default_factory=list)
    handholds: list[Polygon] = field(default_factory=list)
    pcb_outline: list[Polygon] = field(default_factory=list)
    locating_pins: list[CircleFeature] = field(default_factory=list)
    clamp_holes: list[CircleFeature] = field(default_factory=list)
    barrier_mount_holes: list[CircleFeature] = field(default_factory=list)
    spring_clips: list[CircleFeature] = field(default_factory=list)
    unmapped_layers: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


class ManualFixtureDxfParser:
    """Read an engineer-drawn DXF and extract fixture geometry per layer."""

    def __init__(self, layer_mapping: dict[str, str] | None = None):
        self._custom_map = layer_mapping or {}

    def parse(self, dxf_path: str | Path) -> ManualFixtureData:
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            raise FileNotFoundError(f"DXF file not found: {dxf_path}")

        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        result = ManualFixtureData()
        layer_geometries: dict[str, list] = {}
        layer_circles: dict[str, list[CircleFeature]] = {}

        for entity in msp:
            dxf_layer = entity.dxf.layer.upper().strip()
            feature_key = self._resolve_layer(dxf_layer)

            if feature_key is None:
                if dxf_layer not in result.unmapped_layers:
                    result.unmapped_layers.append(dxf_layer)
                continue

            if entity.dxftype() == "CIRCLE":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                circle = CircleFeature(x=round(cx, 4), y=round(cy, 4), diameter=round(r * 2, 4), layer=dxf_layer)
                layer_circles.setdefault(feature_key, []).append(circle)
                continue

            geom = self._entity_to_shapely(entity)
            if geom is not None:
                layer_geometries.setdefault(feature_key, []).append(geom)

        for key in POLYGON_FEATURE_KEYS:
            raw_geoms = layer_geometries.get(key, [])
            polygons = self._lines_to_polygons(raw_geoms)
            setattr(result, key, polygons)

        for key in CIRCLE_FEATURE_KEYS:
            circles = layer_circles.get(key, [])
            setattr(result, key, circles)

        result.diagnostics.append(f"Parsed {dxf_path.name}: {sum(len(getattr(result, k)) for k in POLYGON_FEATURE_KEYS)} polygon features, "
                                  f"{sum(len(getattr(result, k)) for k in CIRCLE_FEATURE_KEYS)} circle features")
        return result

    @classmethod
    def from_case_dir(cls, case_dir: str | Path) -> ManualFixtureData:
        case_dir = Path(case_dir)
        expected_dir = case_dir / "expected"
        dxf_path = expected_dir / "manual_fixture.dxf"
        mapping_path = expected_dir / "manual_layer_mapping.json"

        layer_mapping = None
        if mapping_path.exists():
            with open(mapping_path, "r", encoding="utf-8") as f:
                layer_mapping = json.load(f)

        parser = cls(layer_mapping=layer_mapping)
        return parser.parse(dxf_path)

    def _resolve_layer(self, dxf_layer: str) -> str | None:
        if dxf_layer in self._custom_map:
            target = self._custom_map[dxf_layer].upper().strip()
            return STANDARD_LAYER_MAP.get(target, self._custom_map[dxf_layer])
        for key_upper in self._custom_map:
            if key_upper.upper().strip() == dxf_layer:
                target = self._custom_map[key_upper].upper().strip()
                return STANDARD_LAYER_MAP.get(target, self._custom_map[key_upper])
        return STANDARD_LAYER_MAP.get(dxf_layer)

    def _entity_to_shapely(self, entity) -> LineString | Polygon | None:
        etype = entity.dxftype()
        try:
            if etype == "LINE":
                s = entity.dxf.start
                e = entity.dxf.end
                return LineString([(s.x, s.y), (e.x, e.y)])

            if etype == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in entity.get_points(format="xyseb")]
                if len(pts) < 2:
                    return None
                if entity.closed and len(pts) >= 3:
                    if pts[0] != pts[-1]:
                        pts.append(pts[0])
                    return Polygon(pts)
                return LineString(pts)

            if etype == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                if len(pts) < 2:
                    return None
                if entity.is_closed and len(pts) >= 3:
                    if pts[0] != pts[-1]:
                        pts.append(pts[0])
                    return Polygon(pts)
                return LineString(pts)

            if etype == "ARC":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                if end_angle <= start_angle:
                    end_angle += 2 * math.pi
                num_segments = max(16, int((end_angle - start_angle) / (math.pi / 32)))
                angles = [start_angle + i * (end_angle - start_angle) / num_segments for i in range(num_segments + 1)]
                pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]
                return LineString(pts)

        except Exception:
            return None
        return None

    @staticmethod
    def _lines_to_polygons(geoms: list) -> list[Polygon]:
        polygons = []
        lines = []
        for g in geoms:
            if isinstance(g, Polygon) and g.is_valid and not g.is_empty:
                polygons.append(g)
            elif isinstance(g, LineString) and not g.is_empty:
                lines.append(g)

        if lines:
            try:
                merged = unary_union(lines)
                for poly in polygonize(merged):
                    if poly.is_valid and not poly.is_empty:
                        polygons.append(poly)
            except Exception:
                pass

        return polygons
