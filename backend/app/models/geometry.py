"""Canonical in-memory geometry models used by parsing, generation and export."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from shapely.geometry.base import BaseGeometry


Side = Literal["top", "bottom", "unknown"]
ComponentType = Literal["smd", "tht", "connector", "unknown"]
PadType = Literal["smd", "pth", "npth"]
HoleKind = Literal["hole", "slot"]
PlatingKind = Literal["pth", "npth", "unknown"]
THTKind = Literal["1xn", "2xn", "dip", "terminal_block", "connector", "unknown"]
RegionType = Literal["keepout", "solder_opening", "pocket", "pressure_relief", "custom"]
SourceType = Literal[
    "pnp",
    "bom",
    "gerber_x2",
    "silkscreen_inference",
    "semantic_component",
    "gerber_fallback",
    "manual",
]


@dataclass(frozen=True)
class DrillHit:
    id: str
    x: float
    y: float
    diameter_mm: float
    plated: bool | None
    tool_id: str | None
    source_layer_id: str
    kind: HoleKind = "hole"
    slot_width_mm: float | None = None
    slot_length_mm: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "diameterMm": self.diameter_mm,
            "plated": self.plated,
            "toolId": self.tool_id,
            "sourceLayerId": self.source_layer_id,
            "kind": self.kind,
            "slotWidthMm": self.slot_width_mm,
            "slotLengthMm": self.slot_length_mm,
        }


# PCBHole is the v0.5 name for a drill feature. DrillHit remains the on-board hole list type.
PCBHole = DrillHit


@dataclass
class PCBPad:
    id: str
    component_id: str | None
    x: float
    y: float
    width_mm: float
    height_mm: float
    drill_diameter_mm: float | None
    plated: bool | None
    shape: str
    pad_type: PadType
    side: Side
    hole_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "componentId": self.component_id,
            "x": self.x,
            "y": self.y,
            "widthMm": self.width_mm,
            "heightMm": self.height_mm,
            "drillDiameterMm": self.drill_diameter_mm,
            "plated": self.plated,
            "shape": self.shape,
            "padType": self.pad_type,
            "side": self.side,
            "holeId": self.hole_id,
        }


@dataclass
class PCBComponent:
    id: str
    refdes: str | None
    footprint: str | None
    side: Side
    centroid_x: float
    centroid_y: float
    rotation: float | None
    bbox: tuple[float, float, float, float]
    courtyard: BaseGeometry | None
    body_width_mm: float | None
    body_length_mm: float | None
    body_height_mm: float | None
    component_type: ComponentType
    confidence: float
    source: SourceType
    value: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "refdes": self.refdes,
            "footprint": self.footprint,
            "side": self.side,
            "centroidX": self.centroid_x,
            "centroidY": self.centroid_y,
            "rotation": self.rotation,
            "bbox": list(self.bbox),
            "bodyWidthMm": self.body_width_mm,
            "bodyLengthMm": self.body_length_mm,
            "bodyHeightMm": self.body_height_mm,
            "componentType": self.component_type,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class ThroughHoleComponent:
    id: str
    hole_ids: tuple[str, ...]
    pad_ids: tuple[str, ...]
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    inferred_pitch: float | None
    inferred_rows: int | None
    inferred_columns: int | None
    orientation: float | None
    confidence: float
    component_type: THTKind
    refdes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "holeIds": list(self.hole_ids),
            "padIds": list(self.pad_ids),
            "centroid": list(self.centroid),
            "bbox": list(self.bbox),
            "inferredPitch": self.inferred_pitch,
            "inferredRows": self.inferred_rows,
            "inferredColumns": self.inferred_columns,
            "orientation": self.orientation,
            "confidence": round(self.confidence, 3),
            "componentType": self.component_type,
            "refdes": self.refdes,
        }


@dataclass
class FixtureRegion:
    id: str
    region_type: RegionType
    geometry: BaseGeometry
    source_type: SourceType
    source_ids: tuple[str, ...]
    confidence: float
    manual_override: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "regionType": self.region_type,
            "sourceType": self.source_type,
            "sourceIds": list(self.source_ids),
            "confidence": round(self.confidence, 3),
            "manualOverride": self.manual_override,
            "parameters": dict(self.parameters),
        }


@dataclass
class PCBGeometry:
    outline: BaseGeometry
    holes: list[DrillHit]
    layers: list[dict[str, Any]]
    source_sha256: str
    geometry_sha256: str
    spring_clip_holes: list[dict[str, Any]] = field(default_factory=list)
    top_copper: BaseGeometry | None = None
    bottom_copper: BaseGeometry | None = None
    top_soldermask: BaseGeometry | None = None
    bottom_soldermask: BaseGeometry | None = None
    top_silkscreen: BaseGeometry | None = None
    bottom_silkscreen: BaseGeometry | None = None
    diagnostics: list[str] = field(default_factory=list)
    bot_components: list[Any] = field(default_factory=list)
    through_hole_clusters: list[Any] = field(default_factory=list)
    components: list[PCBComponent] = field(default_factory=list)
    pads: list[PCBPad] = field(default_factory=list)
    through_hole_components: list[ThroughHoleComponent] = field(default_factory=list)
    semantic_conflicts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.outline.bounds

    @property
    def width(self) -> float:
        min_x, _, max_x, _ = self.bounds
        return max_x - min_x

    @property
    def height(self) -> float:
        _, min_y, _, max_y = self.bounds
        return max_y - min_y


@dataclass
class FixtureGeometry:
    pcb: PCBGeometry
    body: BaseGeometry
    sink_region: BaseGeometry
    keepout_regions: list[BaseGeometry]
    solder_regions: list[BaseGeometry]
    locating_pins: list[dict[str, Any]]
    locating_pin_candidates: list[dict[str, Any]]
    clamp_holes: list[dict[str, Any]]
    handholds: list[BaseGeometry]
    rails: list[BaseGeometry]
    solder_barriers: list[BaseGeometry]
    solder_barrier_mount_holes: list[dict[str, Any]]
    drc_issues: list[dict[str, Any]]
    review_items: list[dict[str, Any]]
    parameters: dict[str, Any]
    geometry_sha256: str
    spring_clip_holes: list[dict[str, Any]] = field(default_factory=list)
    keepout_region_meta: list[FixtureRegion] = field(default_factory=list)
    solder_region_meta: list[FixtureRegion] = field(default_factory=list)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.body.bounds

    @property
    def width(self) -> float:
        min_x, _, max_x, _ = self.bounds
        return max_x - min_x

    @property
    def height(self) -> float:
        _, min_y, _, max_y = self.bounds
        return max_y - min_y
