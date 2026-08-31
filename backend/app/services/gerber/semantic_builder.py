"""Build PCB Semantic Model 2.0 from Gerber geometry, PnP and BOM.

Priority: PnP (position/refdes) > BOM (value/footprint/height) > silk inference.
Height is never invented. Conflicts are recorded, not silently overwritten.
"""
from __future__ import annotations

import math

from shapely.geometry import Point, box
from shapely.geometry.base import BaseGeometry

from app.models.geometry import (
    PCBComponent,
    PCBGeometry,
    PCBPad,
    ThroughHoleComponent,
)
from app.services.bom.parser import BomRow, explode_by_refdes
from app.services.gerber.component_detector import (
    detect_bot_components,
    detect_through_hole_clusters,
    detect_through_hole_components,
)
from app.services.pnp.parser import PnPPlacement

PNP_SILK_MATCH_MM = 4.0
PNP_THT_MATCH_MM = 6.0


def build_semantic_model(
    pcb: PCBGeometry,
    pnp_placements: list[PnPPlacement] | None = None,
    bom_rows: list[BomRow] | None = None,
) -> PCBGeometry:
    """Populate components / pads / through-hole components on `pcb` in place."""
    pcb.bot_components = detect_bot_components(pcb)
    pcb.through_hole_clusters = detect_through_hole_clusters(pcb)

    silk_components = _components_from_silk(pcb)
    pnp_components = _components_from_pnp(pnp_placements or [])
    merged, conflicts = _merge_pnp_and_silk(silk_components, pnp_components)
    _apply_bom(merged, bom_rows or [], conflicts)

    tht = detect_through_hole_components(pcb)
    _attach_refdes_to_tht(tht, merged)
    pads = _pads_from_tht(pcb, tht)

    pcb.components = merged
    pcb.pads = pads
    pcb.through_hole_components = tht
    pcb.semantic_conflicts = conflicts
    return pcb


def _components_from_silk(pcb: PCBGeometry) -> list[PCBComponent]:
    components: list[PCBComponent] = []
    for region in pcb.bot_components:
        poly = _courtyard_from_bbox(region.bbox)
        w = region.bbox[2] - region.bbox[0]
        l = region.bbox[3] - region.bbox[1]
        components.append(
            PCBComponent(
                id=region.id,
                refdes=None,
                footprint=None,
                side="bottom",
                centroid_x=region.centroid_x,
                centroid_y=region.centroid_y,
                rotation=None,
                bbox=region.bbox,
                courtyard=poly,
                body_width_mm=round(w, 3),
                body_length_mm=round(l, 3),
                body_height_mm=None,
                component_type="smd",
                confidence=0.72,
                source="silkscreen_inference",
            )
        )
    return components


def _components_from_pnp(placements: list[PnPPlacement]) -> list[PCBComponent]:
    components: list[PCBComponent] = []
    for idx, p in enumerate(placements):
        side = p.side if p.side in {"top", "bottom"} else "unknown"
        bbox = (p.x_mm, p.y_mm, p.x_mm, p.y_mm)
        components.append(
            PCBComponent(
                id=f"pnp-{p.refdes or idx + 1}",
                refdes=p.refdes,
                footprint=p.footprint,
                side=side,  # type: ignore[arg-type]
                centroid_x=p.x_mm,
                centroid_y=p.y_mm,
                rotation=p.rotation,
                bbox=bbox,
                courtyard=None,
                body_width_mm=None,
                body_length_mm=None,
                body_height_mm=None,
                component_type="unknown",
                confidence=0.94,
                source="pnp",
                value=p.value,
            )
        )
    return components


def _merge_pnp_and_silk(
    silk: list[PCBComponent],
    pnp: list[PCBComponent],
) -> tuple[list[PCBComponent], list[dict]]:
    if not pnp:
        return list(silk), []
    if not silk:
        return list(pnp), []

    used_silk: set[int] = set()
    merged: list[PCBComponent] = []
    conflicts: list[dict] = []

    for pnp_comp in pnp:
        best_i = None
        best_d = PNP_SILK_MATCH_MM
        if pnp_comp.side in {"bottom", "unknown"}:
            for i, s in enumerate(silk):
                if i in used_silk:
                    continue
                d = math.hypot(pnp_comp.centroid_x - s.centroid_x, pnp_comp.centroid_y - s.centroid_y)
                if d < best_d:
                    best_d = d
                    best_i = i
        if best_i is not None:
            s = silk[best_i]
            used_silk.add(best_i)
            if best_d > 1.5 and pnp_comp.side == "bottom":
                conflicts.append(
                    {
                        "code": "COMPONENT_DATA_CONFLICT",
                        "refdes": pnp_comp.refdes,
                        "reason": f"PnP 与底层丝印质心偏差 {best_d:.2f}mm",
                        "pnpId": pnp_comp.id,
                        "silkId": s.id,
                    }
                )
            merged.append(
                PCBComponent(
                    id=pnp_comp.id,
                    refdes=pnp_comp.refdes,
                    footprint=pnp_comp.footprint,
                    side="bottom" if pnp_comp.side == "unknown" else pnp_comp.side,
                    centroid_x=pnp_comp.centroid_x,
                    centroid_y=pnp_comp.centroid_y,
                    rotation=pnp_comp.rotation,
                    bbox=s.bbox,
                    courtyard=s.courtyard,
                    body_width_mm=s.body_width_mm,
                    body_length_mm=s.body_length_mm,
                    body_height_mm=None,
                    component_type="smd" if pnp_comp.side in {"bottom", "unknown"} else pnp_comp.component_type,
                    confidence=min(0.96, pnp_comp.confidence),
                    source="pnp",
                    value=pnp_comp.value,
                )
            )
        else:
            merged.append(pnp_comp)

    for i, s in enumerate(silk):
        if i not in used_silk:
            merged.append(s)
    return merged, conflicts


def _apply_bom(components: list[PCBComponent], bom_rows: list[BomRow], conflicts: list[dict]) -> None:
    by_ref = explode_by_refdes(bom_rows)
    if not by_ref:
        return
    for i, comp in enumerate(components):
        if not comp.refdes:
            continue
        row = by_ref.get(comp.refdes.upper())
        if row is None:
            continue
        height = row.height_mm
        footprint = row.footprint or comp.footprint
        if (
            comp.footprint
            and row.footprint
            and _norm_fp(comp.footprint) != _norm_fp(row.footprint)
        ):
            conflicts.append(
                {
                    "code": "COMPONENT_DATA_CONFLICT",
                    "refdes": comp.refdes,
                    "reason": f"PnP 封装 {comp.footprint} 与 BOM 封装 {row.footprint} 不一致",
                    "pnpId": comp.id,
                }
            )
        components[i] = PCBComponent(
            id=comp.id,
            refdes=comp.refdes,
            footprint=footprint,
            side=comp.side,
            centroid_x=comp.centroid_x,
            centroid_y=comp.centroid_y,
            rotation=comp.rotation,
            bbox=comp.bbox,
            courtyard=comp.courtyard,
            body_width_mm=comp.body_width_mm,
            body_length_mm=comp.body_length_mm,
            body_height_mm=height,
            component_type=comp.component_type,
            confidence=min(0.98, comp.confidence + (0.02 if height else 0.0)),
            source=comp.source,
            value=row.value or comp.value,
            description=row.description,
        )


def _attach_refdes_to_tht(tht: list[ThroughHoleComponent], components: list[PCBComponent]) -> None:
    unused = [c for c in components if c.refdes]
    for i, cluster in enumerate(tht):
        best = None
        best_d = PNP_THT_MATCH_MM
        for c in unused:
            d = math.hypot(cluster.centroid[0] - c.centroid_x, cluster.centroid[1] - c.centroid_y)
            if d < best_d:
                best_d = d
                best = c
        if best is None:
            continue
        unused = [c for c in unused if c is not best]
        tht[i] = ThroughHoleComponent(
            id=cluster.id,
            hole_ids=cluster.hole_ids,
            pad_ids=cluster.pad_ids,
            centroid=cluster.centroid,
            bbox=cluster.bbox,
            inferred_pitch=cluster.inferred_pitch,
            inferred_rows=cluster.inferred_rows,
            inferred_columns=cluster.inferred_columns,
            orientation=cluster.orientation,
            confidence=max(cluster.confidence, 0.9),
            component_type=cluster.component_type,
            refdes=best.refdes,
        )
        if best.component_type == "unknown":
            idx = components.index(best)
            components[idx] = PCBComponent(
                id=best.id,
                refdes=best.refdes,
                footprint=best.footprint,
                side=best.side,
                centroid_x=best.centroid_x,
                centroid_y=best.centroid_y,
                rotation=best.rotation,
                bbox=best.bbox,
                courtyard=best.courtyard,
                body_width_mm=best.body_width_mm,
                body_length_mm=best.body_length_mm,
                body_height_mm=best.body_height_mm,
                component_type="tht",
                confidence=best.confidence,
                source=best.source,
                value=best.value,
                description=best.description,
            )


def _pads_from_tht(pcb: PCBGeometry, tht: list[ThroughHoleComponent]) -> list[PCBPad]:
    by_id = {h.id: h for h in pcb.holes}
    pads: list[PCBPad] = []
    for cluster in tht:
        for hole_id in cluster.hole_ids:
            hole = by_id.get(hole_id)
            if hole is None:
                continue
            dia = hole.diameter_mm
            pad_type = "pth" if hole.plated is not False else "npth"
            pads.append(
                PCBPad(
                    id=f"pad-{hole.id}",
                    component_id=cluster.id,
                    x=hole.x,
                    y=hole.y,
                    width_mm=dia,
                    height_mm=dia,
                    drill_diameter_mm=dia,
                    plated=hole.plated,
                    shape="circle",
                    pad_type=pad_type,  # type: ignore[arg-type]
                    side="unknown",
                    hole_id=hole.id,
                )
            )
    return pads


def _courtyard_from_bbox(bbox: tuple[float, float, float, float]) -> BaseGeometry:
    min_x, min_y, max_x, max_y = bbox
    if max_x - min_x < 1e-6 or max_y - min_y < 1e-6:
        return Point(min_x, min_y).buffer(0.5)
    return box(min_x, min_y, max_x, max_y)


def _norm_fp(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())
