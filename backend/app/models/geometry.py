"""Canonical in-memory geometry models used by parsing, generation and export."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class DrillHit:
    id: str
    x: float
    y: float
    diameter_mm: float
    plated: bool | None
    tool_id: str | None
    source_layer_id: str
    kind: Literal["hole", "slot"] = "hole"

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
