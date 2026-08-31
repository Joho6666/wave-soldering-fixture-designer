"""Adapt PCB semantic objects into fixture-generation inputs."""
from __future__ import annotations

from app.models.geometry import PCBComponent, PCBGeometry, ThroughHoleComponent
from app.services.gerber.component_detector import detect_through_hole_components
from app.services.gerber.semantic_builder import build_semantic_model


def ensure_semantic(pcb: PCBGeometry) -> PCBGeometry:
    """Fill semantic fields when the caller only provided raw geometry."""
    needs_components = not pcb.components and not pcb.bot_components
    needs_tht = not pcb.through_hole_components
    if needs_components:
        build_semantic_model(pcb)
        return pcb
    if needs_tht:
        pcb.through_hole_components = detect_through_hole_components(pcb)
    return pcb


def bottom_keepout_components(pcb: PCBGeometry) -> list[PCBComponent]:
    comps = [c for c in pcb.components if c.side == "bottom"]
    if comps:
        return comps
    # Legacy detector regions, if present and not yet promoted.
    return []


def tht_components(pcb: PCBGeometry) -> list[ThroughHoleComponent]:
    return list(pcb.through_hole_components or [])
