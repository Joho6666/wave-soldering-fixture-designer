"""Grid panel construction. Each PCB instance keeps its own Transform2D."""
from __future__ import annotations

from typing import Any

from shapely.geometry import LineString, box
from shapely.ops import unary_union

from app.models.geometry import PCBGeometry
from app.models.panel import PCBInstance, PanelModel, VCut


def build_grid_panel(pcb: PCBGeometry, params: dict[str, Any]) -> PanelModel | None:
    if not params.get("panelEnabled"):
        return None
    rows = max(1, int(round(float(params.get("panelRows", 1)))))
    cols = max(1, int(round(float(params.get("panelCols", 1)))))
    if rows == 1 and cols == 1:
        return None

    spacing = float(params.get("panelBoardSpacingMm", 2.0))
    outer = float(params.get("panelOuterMarginMm", 5.0))
    tooling_d = float(params.get("panelToolingHoleDiameterMm", 3.0))
    fid_d = float(params.get("panelFiducialDiameterMm", 1.0))

    minx, miny, maxx, maxy = pcb.outline.bounds
    board_w = maxx - minx
    board_h = maxy - miny
    pitch_x = board_w + spacing
    pitch_y = board_h + spacing

    instances: list[PCBInstance] = []
    for r in range(rows):
        for c in range(cols):
            dx = c * pitch_x
            dy = r * pitch_y
            instances.append(
                PCBInstance(
                    id=f"pcb-{r+1}-{c+1}",
                    source_pcb=pcb,
                    x=dx,
                    y=dy,
                    rotation=0.0,
                    mirror=False,
                )
            )

    outlines = [inst.global_outline() for inst in instances]
    content = unary_union(outlines)
    cminx, cminy, cmaxx, cmaxy = content.bounds
    panel_outline = box(cminx - outer, cminy - outer, cmaxx + outer, cmaxy + outer)

    v_cuts: list[VCut] = []
    for c in range(1, cols):
        x = minx + c * pitch_x - spacing / 2.0
        v_cuts.append(VCut(id=f"vcut-v-{c}", x1=x, y1=cminy, x2=x, y2=cmaxy, kind="vcut"))
    for r in range(1, rows):
        y = miny + r * pitch_y - spacing / 2.0
        v_cuts.append(VCut(id=f"vcut-h-{r}", x1=cminx, y1=y, x2=cmaxx, y2=y, kind="vcut"))

    pminx, pminy, pmaxx, pmaxy = panel_outline.bounds
    inset = max(outer * 0.5, tooling_d)
    tooling = [
        {"id": "tooling-sw", "x": pminx + inset, "y": pminy + inset, "diameter": tooling_d},
        {"id": "tooling-se", "x": pmaxx - inset, "y": pminy + inset, "diameter": tooling_d},
        {"id": "tooling-nw", "x": pminx + inset, "y": pmaxy - inset, "diameter": tooling_d},
        {"id": "tooling-ne", "x": pmaxx - inset, "y": pmaxy - inset, "diameter": tooling_d},
    ]
    fiducials = [
        {"id": "fid-sw", "x": pminx + inset * 1.8, "y": pminy + inset * 1.8, "diameter": fid_d},
        {"id": "fid-ne", "x": pmaxx - inset * 1.8, "y": pmaxy - inset * 1.8, "diameter": fid_d},
        {"id": "fid-se", "x": pmaxx - inset * 1.8, "y": pminy + inset * 1.8, "diameter": fid_d},
    ]

    return PanelModel(
        outline=panel_outline,
        pcb_instances=instances,
        v_cuts=v_cuts,
        breakaway_tabs=[],
        tooling_holes=tooling,
        fiducials=fiducials,
        rows=rows,
        cols=cols,
        board_spacing_mm=spacing,
    )


def vcut_lines(panel: PanelModel) -> list[LineString]:
    return [LineString([(v.x1, v.y1), (v.x2, v.y2)]) for v in panel.v_cuts]
