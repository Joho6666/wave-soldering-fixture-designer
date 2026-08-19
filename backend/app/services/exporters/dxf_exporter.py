"""
DXF and SVG exporter with authentic CAD primitives and strict layer separation.
"""
from __future__ import annotations

import ezdxf
from shapely.geometry import Polygon, MultiPolygon
from typing import Dict, List, Any


def export_fixture_dxf(layers_data: Dict[str, Any], output_path: str) -> str:
    """
    导出治具 DXF 文件（AutoCAD R2018 格式）
    """
    doc = ezdxf.new('R2018')
    msp = doc.modelspace()
    
    # 工业标准分层定义与线色映射
    doc.layers.new('PCB_OUTLINE', dxfattribs={'color': 7})       # 白色
    doc.layers.new('SINK_AREA', dxfattribs={'color': 3})         # 绿色
    doc.layers.new('KEEPOUT_BOT', dxfattribs={'color': 1})       # 红色
    doc.layers.new('SOLDER_WINDOW_TOP', dxfattribs={'color': 2}) # 黄色
    doc.layers.new('POSITIONING_PINS', dxfattribs={'color': 5})  # 蓝色
    doc.layers.new('CLIPS', dxfattribs={'color': 6})             # 品红
    doc.layers.new('FIXTURE_OUTLINE', dxfattribs={'color': 4})   # 青色
    doc.layers.new('HANDHOLDS', dxfattribs={'color': 6})         # 紫色
    doc.layers.new('RAILS', dxfattribs={'color': 8})             # 灰色
    doc.layers.new('SOLDER_BARRIERS', dxfattribs={'color': 30})  # 橙色
    doc.layers.new('BARRIER_MOUNT_HOLES', dxfattribs={'color': 30})
    doc.layers.new('PCB_DRILL', dxfattribs={'color': 9})         # 浅灰
    doc.layers.new('SPRING_CLIPS', dxfattribs={'color': 41})     # 浅蓝
    doc.layers.new('DIMENSIONS', dxfattribs={'color': 7})        # 白色
    
    # 1. 绘制 PCB 外形
    pcb_outline = layers_data.get('pcb_outline')
    if pcb_outline:
        _draw_polygon(msp, pcb_outline, 'PCB_OUTLINE')
    
    # 2. 绘制沉板区 (含清角)
    sink_area = layers_data.get('sink_area')
    if sink_area:
        _draw_polygon(msp, sink_area, 'SINK_AREA')
    
    # 3. 绘制 BOT 避位区
    keepout_zones = layers_data.get('keepout_zones', [])
    if isinstance(keepout_zones, list):
        for zone in keepout_zones:
            _draw_polygon(msp, zone, 'KEEPOUT_BOT')
    elif keepout_zones:
        _draw_polygon(msp, keepout_zones, 'KEEPOUT_BOT')
    
    # 4. 绘制 TOP 上锡区
    solder_windows = layers_data.get('solder_windows', [])
    for window in solder_windows:
        _draw_polygon(msp, window, 'SOLDER_WINDOW_TOP')
    
    # 5. 绘制定位销（原生 CIRCLE）
    pins = layers_data.get('pins', [])
    for pin in pins:
        msp.add_circle(
            center=(pin['x'], pin['y']),
            radius=pin['diameter'] / 2,
            dxfattribs={'layer': 'POSITIONING_PINS'}
        )
    
    # 6. 绘制压扣孔（原生 CIRCLE）
    clips = layers_data.get('clips', [])
    for clip in clips:
        msp.add_circle(
            center=(clip['x'], clip['y']),
            radius=clip.get('diameter', 3.4) / 2,
            dxfattribs={'layer': 'CLIPS'}
        )
    
    # 7. 治具外框
    fixture_outline = layers_data.get('fixture_outline')
    if fixture_outline is None:
        raise ValueError("FixtureGeometry 缺少 fixture_outline")
    _draw_polygon(msp, fixture_outline, 'FIXTURE_OUTLINE')

    # 8. 取手位、轨道、挡锡条
    for handhold in layers_data.get('handholds', []):
        _draw_polygon(msp, handhold, 'HANDHOLDS')
    for rail in layers_data.get('rails', []):
        _draw_polygon(msp, rail, 'RAILS')
    for barrier in layers_data.get('solder_barriers', []):
        _draw_polygon(msp, barrier, 'SOLDER_BARRIERS')
    
    # 9. 挡锡条安装螺丝孔（原生 CIRCLE）
    for mount_hole in layers_data.get('solder_barrier_mount_holes', []):
        msp.add_circle(
            center=(mount_hole['x'], mount_hole['y']),
            radius=mount_hole.get('diameter', 3.2) / 2,
            dxfattribs={'layer': 'BARRIER_MOUNT_HOLES'}
        )

    # 10. 弹簧卡安装孔（原生 CIRCLE）
    for clip in layers_data.get('spring_clips', []):
        msp.add_circle(
            center=(clip['x'], clip['y']),
            radius=clip.get('diameter', 4.9) / 2,
            dxfattribs={'layer': 'SPRING_CLIPS'}
        )

    # 11. 尺寸标注
    _add_dimensions(doc, msp, layers_data)

    # 12. PCB 原生钻孔
    fixture_geom = layers_data.get('fixture_geometry')
    if fixture_geom and hasattr(fixture_geom, 'pcb') and fixture_geom.pcb:
        for hole in fixture_geom.pcb.holes:
            msp.add_circle(
                center=(hole.x, hole.y),
                radius=hole.diameter_mm / 2,
                dxfattribs={'layer': 'PCB_DRILL'}
            )

    doc.saveas(output_path)
    # Read-back validation
    ezdxf.readfile(output_path)
    return output_path



def _add_dimensions(doc, msp, layers_data):
    """添加工业级尺寸标注到 DIMENSIONS 图层"""
    try:
        dim_style = doc.dimstyles.new('FIXTURE_DIM')
        dim_style.dxf.dimtxt = 2.5
        dim_style.dxf.dimasz = 1.5
        dim_style.dxf.dimdec = 2
        dim_style.dxf.dimclrd = 7
        dim_style.dxf.dimclre = 7
        dim_style.dxf.dimclrt = 7
    except Exception:
        dim_style = None

    dim_attrs = {'layer': 'DIMENSIONS'}
    style_name = 'FIXTURE_DIM' if dim_style else 'Standard'

    fixture_outline = layers_data.get('fixture_outline')
    pcb_outline = layers_data.get('pcb_outline')

    if fixture_outline and not fixture_outline.is_empty:
        fx0, fy0, fx1, fy1 = fixture_outline.bounds
        offset = 8.0
        msp.add_linear_dim(
            base=(fx0, fy0 - offset),
            p1=(fx0, fy0),
            p2=(fx1, fy0),
            dimstyle=style_name,
            override=dim_attrs,
        ).render()
        msp.add_linear_dim(
            base=(fx1 + offset, fy0),
            p1=(fx1, fy0),
            p2=(fx1, fy1),
            angle=90,
            dimstyle=style_name,
            override=dim_attrs,
        ).render()

    if pcb_outline and not pcb_outline.is_empty:
        px0, py0, px1, py1 = pcb_outline.bounds
        offset = 5.0
        msp.add_linear_dim(
            base=(px0, py1 + offset),
            p1=(px0, py1),
            p2=(px1, py1),
            dimstyle=style_name,
            override=dim_attrs,
        ).render()
        msp.add_linear_dim(
            base=(px0 - offset, py0),
            p1=(px0, py0),
            p2=(px0, py1),
            angle=90,
            dimstyle=style_name,
            override=dim_attrs,
        ).render()

    pins = layers_data.get('pins', [])
    if len(pins) >= 2:
        p1 = pins[0]
        p2 = pins[-1]
        offset_y = min(p1['y'], p2['y']) - 6.0
        msp.add_linear_dim(
            base=(p1['x'], offset_y),
            p1=(p1['x'], p1['y']),
            p2=(p2['x'], p2['y']),
            dimstyle=style_name,
            override=dim_attrs,
        ).render()

def _draw_polygon(msp, geometry, layer: str):
    """Recursively export Polygon/MultiPolygon geometry to AutoCAD LWPOLYLINE."""
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == "MultiPolygon":
        for polygon in geometry.geoms:
            _draw_polygon(msp, polygon, layer)
        return
    if geometry.geom_type != "Polygon":
        raise TypeError(f"DXF 图层 {layer} 不支持几何类型 {geometry.geom_type}")
    msp.add_lwpolyline(list(geometry.exterior.coords), close=True, dxfattribs={'layer': layer})
    for interior in geometry.interiors:
        msp.add_lwpolyline(list(interior.coords), close=True, dxfattribs={'layer': layer})


def export_fixture_svg(layers_data: Dict[str, Any], output_path: str) -> str:
    """
    导出治具 SVG 矢量图形文件（用于前端高精度图层渲染）
    """
    pcb_outline = layers_data.get('pcb_outline')
    fixture_outline = layers_data.get('fixture_outline')
    if pcb_outline is None or fixture_outline is None:
        raise ValueError("FixtureGeometry 缺少 PCB 或治具外形，禁止生成占位 SVG")
    
    minx, miny, maxx, maxy = fixture_outline.bounds
    width = maxx - minx
    height = maxy - miny
    
    padding = 20
    viewbox_width = width + 2 * padding
    viewbox_height = height + 2 * padding
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{minx-padding} {miny-padding} {viewbox_width} {viewbox_height}" '
        f'width="{viewbox_width}" height="{viewbox_height}">'
    ]
    
    # 黑色 CAD 背景
    svg_parts.append(
        f'<rect x="{minx-padding}" y="{miny-padding}" '
        f'width="{viewbox_width}" height="{viewbox_height}" '
        f'fill="#121212"/>'
    )
    
    # 1. 治具外形
    svg_parts.append('<g id="fixture-outline">')
    svg_parts.append(_polygon_to_svg_path(fixture_outline, '#448aff', 'Fixture Outline'))
    svg_parts.append('</g>')

    # 2. PCB 外形
    svg_parts.append('<g id="pcb-outline">')
    if pcb_outline:
        svg_parts.append(_polygon_to_svg_path(pcb_outline, '#00ffff', 'PCB Outline'))
    svg_parts.append('</g>')

    # 3. 沉板区 (含清角)
    sink_area = layers_data.get('sink_area')
    svg_parts.append('<g id="sink-region">')
    if sink_area:
        svg_parts.append(_polygon_to_svg_path(sink_area, '#00ff00', 'Sink Area'))
    svg_parts.append('</g>')

    # 4. BOT 避位区
    keepout_zones = layers_data.get('keepout_zones', [])
    svg_parts.append('<g id="keepout-bot">')
    if isinstance(keepout_zones, list):
        for i, zone in enumerate(keepout_zones):
            svg_parts.append(_polygon_to_svg_path(zone, '#ff5252', f'Keepout {i+1}'))
    elif keepout_zones:
        svg_parts.append(_polygon_to_svg_path(keepout_zones, '#ff5252', 'Keepout'))
    svg_parts.append('</g>')

    # 5. TOP 上锡区
    solder_windows = layers_data.get('solder_windows', [])
    svg_parts.append('<g id="solder-top">')
    for i, window in enumerate(solder_windows):
        svg_parts.append(_polygon_to_svg_path(window, '#ffd740', f'Solder Window {i+1}'))
    svg_parts.append('</g>')

    # 6. 定位销
    pins = layers_data.get('pins', [])
    svg_parts.append('<g id="locating-pins">')
    for i, pin in enumerate(pins):
        pin_id = pin.get("id", f"pin-{i+1}")
        pin_dia = pin["diameter"]
        svg_parts.append(
            f'<circle id="{pin_id}" cx="{pin["x"]}" cy="{pin["y"]}" r="{pin_dia/2}" '
            f'fill="none" stroke="#2979ff" stroke-width="0.6">'
            f'<title>Pin {i+1} Ø{pin_dia:.2f}</title></circle>'
        )
    svg_parts.append('</g>')

    # 7. PCB 原生钻孔
    fixture_geom = layers_data.get('fixture_geometry')
    svg_parts.append('<g id="pcb-drill">')
    if fixture_geom and hasattr(fixture_geom, 'pcb') and fixture_geom.pcb:
        for hole in fixture_geom.pcb.holes:
            svg_parts.append(
                f'<circle id="{hole.id}" cx="{hole.x}" cy="{hole.y}" r="{hole.diameter_mm/2}" '
                f'fill="none" stroke="#90caf9" stroke-width="0.15"><title>Drill {hole.id} Ø{hole.diameter_mm:.3f}</title></circle>'
            )
    svg_parts.append('</g>')

    # 8. 定位孔候选
    svg_parts.append('<g id="locating-pin-candidates">')
    for candidate in layers_data.get('locating_candidates', []):
        cand_id = candidate["id"]
        cand_dia = candidate["diameterMm"]
        cand_score = candidate.get("score", 0)
        svg_parts.append(
            f'<circle id="{cand_id}" cx="{candidate["x"]}" cy="{candidate["y"]}" r="{cand_dia/2 + 0.3}" '
            f'fill="none" stroke="#ff9800" stroke-width="0.25" stroke-dasharray="0.8 0.4"><title>Candidate {cand_dia:.3f} mm (Score: {cand_score})</title></circle>'
        )
    svg_parts.append('</g>')

    # 9. 压扣孔
    svg_parts.append('<g id="clamps">')
    for clip in layers_data.get('clips', []):
        clip_id = clip["id"]
        clip_dia = clip.get("diameter", 3.4)
        svg_parts.append(f'<circle id="{clip_id}" cx="{clip["x"]}" cy="{clip["y"]}" r="{clip_dia/2}" fill="none" stroke="#e040fb" stroke-width="0.4"/>')
    svg_parts.append('</g>')

    # 10. 挡锡条安装孔
    svg_parts.append('<g id="barrier-mount-holes">')
    for mount_hole in layers_data.get('solder_barrier_mount_holes', []):
        hole_id = mount_hole["id"]
        hole_dia = mount_hole.get("diameter", 3.2)
        svg_parts.append(f'<circle id="{hole_id}" cx="{mount_hole["x"]}" cy="{mount_hole["y"]}" r="{hole_dia/2}" fill="none" stroke="#ffab40" stroke-width="0.3"/>')
    svg_parts.append('</g>')

    # 11. 弹簧卡安装孔
    svg_parts.append('<g id="spring-clips">')
    for i, clip in enumerate(layers_data.get('spring_clips', [])):
        clip_id = clip.get('id', f'spring-clip-{i+1}')
        clip_dia = clip.get('diameter', 4.9)
        clip_x = clip["x"]
        clip_y = clip["y"]
        svg_parts.append(
            f'<circle id="{clip_id}" cx="{clip["x"]}" cy="{clip["y"]}" r="{clip_dia/2}" '
            f'fill="none" stroke="#00bcd4" stroke-width="0.5">'
            f'<title>Spring Clip {i+1} Ø{clip_dia:.2f}</title></circle>'
        )
    svg_parts.append('</g>')

    # 12. Gerber 源层预览
    fixture_geom = layers_data.get('fixture_geometry')
    if fixture_geom and hasattr(fixture_geom, 'pcb') and fixture_geom.pcb:
        pcb = fixture_geom.pcb
        gerber_layers = [
            ('gerber-top-copper', pcb.top_copper, '#ff5722', 'Top Copper'),
            ('gerber-bot-copper', pcb.bottom_copper, '#4caf50', 'Bot Copper'),
            ('gerber-top-silk', pcb.top_silkscreen, '#ffffff', 'Top Silk'),
            ('gerber-bot-silk', pcb.bottom_silkscreen, '#ffeb3b', 'Bot Silk'),
            ('gerber-top-mask', pcb.top_soldermask, '#9c27b0', 'Top Mask'),
            ('gerber-bot-mask', pcb.bottom_soldermask, '#009688', 'Bot Mask'),
        ]
        for layer_id, geom, color, label in gerber_layers:
            svg_parts.append(f'<g id="{layer_id}" style="display:none">')
            if geom and not geom.is_empty:
                try:
                    svg_parts.append(_polygon_to_svg_path(geom, color, label))
                except (TypeError, Exception):
                    pass
            svg_parts.append('</g>')

    # 13. 取手位、轨道、挡锡条
    for group_id, color, geometries in [
        ('handholds', '#ab47bc', layers_data.get('handholds', [])),
        ('rails', '#78909c', layers_data.get('rails', [])),
        ('solder-barriers', '#ff6e40', layers_data.get('solder_barriers', [])),
    ]:
        svg_parts.append(f'<g id="{group_id}">')
        for index, geometry in enumerate(geometries):
            svg_parts.append(_polygon_to_svg_path(geometry, color, f'{group_id}-{index + 1}'))
        svg_parts.append('</g>')

    svg_parts.append('</svg>')
    
    svg_content = '\n'.join(svg_parts)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    return output_path


def _polygon_to_svg_path(geometry, color: str, title: str = '') -> str:
    """Convert Polygon/MultiPolygon including cutouts to SVG paths."""
    if geometry is None or geometry.is_empty:
        return ''
    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    if any(polygon.geom_type != "Polygon" for polygon in polygons):
        raise TypeError(f"SVG 不支持几何类型 {geometry.geom_type}")
    parts = []
    for polygon in polygons:
        rings = [polygon.exterior, *polygon.interiors]
        for ring in rings:
            coords = list(ring.coords)
            parts.append(f"M {coords[0][0]},{coords[0][1]} " + " ".join(f"L {x},{y}" for x, y in coords[1:]) + " Z")
    return (
        f'<path d="{" ".join(parts)}" fill="none" fill-rule="evenodd" '
        f'stroke="{color}" stroke-width="0.5" opacity="0.85"><title>{title}</title></path>'
    )


def add_preview_watermark(source_path: str, output_path: str) -> str:
    """Copy a DXF and add a NOT_FOR_PRODUCTION watermark layer."""
    import shutil
    shutil.copy2(source_path, output_path)
    doc = ezdxf.readfile(output_path)
    msp = doc.modelspace()
    if 'NOT_FOR_PRODUCTION' not in doc.layers:
        doc.layers.new('NOT_FOR_PRODUCTION', dxfattribs={'color': 1})
    all_bounds = [e.dxf.insert if hasattr(e.dxf, 'insert') else None for e in msp]
    try:
        bbox = msp.query('*').first.dxf
    except Exception:
        pass
    min_x, min_y, max_x, max_y = 0, 0, 300, 200
    for entity in msp:
        try:
            eb = entity.dxf
            if hasattr(eb, 'start'):
                min_x = min(min_x, eb.start.x)
                min_y = min(min_y, eb.start.y)
                max_x = max(max_x, eb.start.x)
                max_y = max(max_y, eb.start.y)
        except Exception:
            continue
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    msp.add_text(
        "NOT FOR PRODUCTION",
        height=10.0,
        dxfattribs={
            'layer': 'NOT_FOR_PRODUCTION',
            'insert': (cx - 50, cy),
            'color': 1,
        },
    )
    msp.add_text(
        "PREVIEW ONLY",
        height=8.0,
        dxfattribs={
            'layer': 'NOT_FOR_PRODUCTION',
            'insert': (cx - 35, cy - 15),
            'color': 1,
        },
    )
    doc.saveas(output_path)
    return output_path