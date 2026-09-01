"""Panel semantic model. A panel is not a single flattened polygon."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from shapely.geometry.base import BaseGeometry

from app.geometry.transform import Transform2D
from app.models.geometry import PCBGeometry


BreakawayKind = Literal["vcut", "mouse_bite", "stamp_hole"]


@dataclass
class PCBInstance:
    id: str
    source_pcb: PCBGeometry
    x: float
    y: float
    rotation: float = 0.0
    mirror: bool = False

    @property
    def transform(self) -> Transform2D:
        return Transform2D(tx=self.x, ty=self.y, rotation_deg=self.rotation, mirror_x=self.mirror)

    def global_outline(self) -> BaseGeometry:
        return self.transform.apply(self.source_pcb.outline)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "rotation": self.rotation,
            "mirror": self.mirror,
        }


@dataclass
class VCut:
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    kind: BreakawayKind = "vcut"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "kind": self.kind}


@dataclass
class BreakawayTab:
    id: str
    x: float
    y: float
    width_mm: float
    kind: BreakawayKind = "mouse_bite"
    hole_diameter_mm: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "widthMm": self.width_mm,
            "kind": self.kind,
            "holeDiameterMm": self.hole_diameter_mm,
        }


@dataclass
class PanelModel:
    outline: BaseGeometry
    pcb_instances: list[PCBInstance]
    v_cuts: list[VCut] = field(default_factory=list)
    breakaway_tabs: list[BreakawayTab] = field(default_factory=list)
    tooling_holes: list[dict[str, Any]] = field(default_factory=list)
    fiducials: list[dict[str, Any]] = field(default_factory=list)
    rows: int = 1
    cols: int = 1
    board_spacing_mm: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        minx, miny, maxx, maxy = self.outline.bounds
        return {
            "rows": self.rows,
            "cols": self.cols,
            "boardSpacingMm": self.board_spacing_mm,
            "instanceCount": len(self.pcb_instances),
            "instances": [i.to_dict() for i in self.pcb_instances],
            "vCuts": [v.to_dict() for v in self.v_cuts],
            "breakawayTabs": [t.to_dict() for t in self.breakaway_tabs],
            "toolingHoles": self.tooling_holes,
            "fiducials": self.fiducials,
            "bounds": [minx, miny, maxx, maxy],
        }
