"""Geometry-based design rule checks."""
from __future__ import annotations

import math
from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points

from app.models.geometry import FixtureGeometry


def run_drc(fixture: FixtureGeometry) -> list[dict]:
    issues: list[dict] = []
    pcb = fixture.pcb
    params = fixture.parameters

    # 1. 基础外形与沉板检查
    if not pcb.outline.is_valid:
        issues.append(_issue("PCB_OUTLINE_INVALID", "PCB 外形无效", "PCB 外形存在自交或无效拓扑。", "blocking"))
    if fixture.sink_region.is_empty or not fixture.sink_region.is_valid:
        issues.append(_issue("SINK_REGION_INVALID", "沉板区无效", "PCB 外扩后未形成有效沉板区域。", "blocking"))
    if not fixture.body.contains(fixture.sink_region):
        issues.append(_issue("FIXTURE_BODY_OVERFLOW", "沉板区超出治具", "沉板区超出了治具主体外框边界。", "blocking"))

    # 2. 定位孔与定位销检查
    if len(fixture.locating_pins) < 2:
        issues.append(
            _issue(
                "LOCATING_PINS_INSUFFICIENT",
                "定位销数量不足",
                f"当前仅配置 {len(fixture.locating_pins)} 个定位销，推荐至少 2 个以保证 PCB 约束定位。",
                "warning",
                current_value=float(len(fixture.locating_pins)),
                required_value=2.0,
                unit="个",
            )
        )

    # 3. 压扣检查
    if len(fixture.clamp_holes) < 2:
        issues.append(
            _issue(
                "CLAMPS_INSUFFICIENT",
                "压扣数量不足",
                f"当前仅配置 {len(fixture.clamp_holes)} 个压扣孔，推荐至少 2 个防止浮板。",
                "warning",
                current_value=float(len(fixture.clamp_holes)),
                required_value=2.0,
                unit="个",
            )
        )

    # 4. 挡锡条冲突检查 (BARRIER_SINK_COLLISION, BARRIER_HOLE_COLLISION)
    for b_idx, barrier in enumerate(fixture.solder_barriers):
        if barrier.intersects(fixture.sink_region):
            issues.append(
                _issue(
                    "BARRIER_SINK_COLLISION",
                    "挡锡条与沉板区干涉",
                    f"防锡桥挡锡条 #{b_idx+1} 与沉板区域重叠，可能压坏板边元件。",
                    "warning",
                    object_id=f"barrier-{b_idx+1}",
                )
            )

    for hole in fixture.solder_barrier_mount_holes:
        p = Point(hole["x"], hole["y"])
        if fixture.sink_region.contains(p):
            issues.append(
                _issue(
                    "BARRIER_HOLE_COLLISION",
                    "挡锡条安装孔与沉板区干涉",
                    f"挡锡条安装孔 ({hole['x']:.1f}, {hole['y']:.1f}) 落入沉板区内。",
                    "error",
                    point=p,
                    object_id=f"barrier-hole-{hole.get('id', 'unk')}",
                )
            )

    # 5. 取手位冲突检查 (HANDHOLD_FIXTURE_COLLISION, HANDHOLD_RAIL_COLLISION)
    for h_idx, handhold in enumerate(fixture.handholds):
        if not fixture.body.contains(handhold):
            issues.append(
                _issue(
                    "HANDHOLD_FIXTURE_COLLISION",
                    "取手位超出治具边界",
                    f"取手位 #{h_idx+1} 掏空超出了治具外框边界。",
                    "error",
                    object_id=f"handhold-{h_idx+1}",
                )
            )
        for r_idx, rail in enumerate(fixture.rails):
            if handhold.intersects(rail):
                issues.append(
                    _issue(
                        "HANDHOLD_RAIL_COLLISION",
                        "取手位与传送轨道干涉",
                        f"取手位 #{h_idx+1} 与传送轨道 #{r_idx+1} 重叠，影响链条夹持。",
                        "error",
                        object_id=f"handhold-{h_idx+1}-rail-{r_idx+1}",
                    )
                )

    # 6. 压扣碰撞冲突 (CLAMP_HANDHOLD_COLLISION, CLAMP_RAIL_COLLISION, CLAMP_LOCATING_PIN_COLLISION)
    for clamp in fixture.clamp_holes:
        cp = Point(clamp["x"], clamp["y"])
        c_id = clamp.get("id", "clamp")
        for h_idx, handhold in enumerate(fixture.handholds):
            if handhold.contains(cp):
                issues.append(
                    _issue(
                        "CLAMP_HANDHOLD_COLLISION",
                        "压扣与取手位干涉",
                        f"压扣孔 {c_id} ({clamp['x']:.1f}, {clamp['y']:.1f}) 与取手掏空干涉。",
                        "error",
                        point=cp,
                        object_id=f"{c_id}-handhold-{h_idx+1}",
                    )
                )
        for r_idx, rail in enumerate(fixture.rails):
            if rail.contains(cp):
                issues.append(
                    _issue(
                        "CLAMP_RAIL_COLLISION",
                        "压扣与轨道干涉",
                        f"压扣孔 {c_id} ({clamp['x']:.1f}, {clamp['y']:.1f}) 过于靠近或位于轨道卡槽内。",
                        "warning",
                        point=cp,
                        object_id=f"{c_id}-rail-{r_idx+1}",
                    )
                )
        for pin in fixture.locating_pins:
            p_id = pin.get("id", "pin")
            dist = math.hypot(clamp["x"] - pin["x"], clamp["y"] - pin["y"])
            if dist < 10.0:
                issues.append(
                    _issue(
                        "CLAMP_LOCATING_PIN_COLLISION",
                        "压扣与定位销距离过近",
                        f"压扣 {c_id} 与定位销 {p_id} 间距 ({dist:.1f}mm < 10mm) 存在机械干涉风险。",
                        "warning",
                        current_value=dist,
                        required_value=10.0,
                        unit="mm",
                        point=cp,
                        object_id=f"{c_id}-{p_id}",
                    )
                )

    # 7. 定位销与避位/上锡区冲突 (LOCATING_PIN_KEEP_OUT_COLLISION, LOCATING_PIN_SOLDER_COLLISION)
    for pin in fixture.locating_pins:
        pp = Point(pin["x"], pin["y"])
        p_id = pin.get("id", "pin")
        for k_idx, keepout in enumerate(fixture.keepout_regions):
            if keepout.contains(pp):
                issues.append(
                    _issue(
                        "LOCATING_PIN_KEEP_OUT_COLLISION",
                        "定位销与 BOT 避位区干涉",
                        f"定位销 {p_id} ({pin['x']:.1f}, {pin['y']:.1f}) 落在 BOT 避位区 #{k_idx+1} 内，无法有效下沉打销。",
                        "error",
                        point=pp,
                        object_id=f"{p_id}-keepout-{k_idx+1}",
                    )
                )
        for s_idx, solder in enumerate(fixture.solder_regions):
            if solder.contains(pp):
                issues.append(
                    _issue(
                        "LOCATING_PIN_SOLDER_COLLISION",
                        "定位销与 TOP 上锡窗口干涉",
                        f"定位销 {p_id} ({pin['x']:.1f}, {pin['y']:.1f}) 位于上锡窗口 #{s_idx+1} 内，可能被锡液浸润卡死。",
                        "error",
                        point=pp,
                        object_id=f"{p_id}-solder-{s_idx+1}",
                    )
                )

    # 8. 上锡区与避位区冲突 (SOLDER_KEEP_OUT_CONFLICT)
    for s_idx, solder in enumerate(fixture.solder_regions):
        for k_idx, keepout in enumerate(fixture.keepout_regions):
            if solder.intersects(keepout):
                issues.append(
                    _issue(
                        "SOLDER_KEEP_OUT_CONFLICT",
                        "上锡窗口与 BOT 避位区重叠冲突",
                        f"上锡窗口 #{s_idx+1} 与 BOT 避位区 #{k_idx+1} 存在几何相交，容易导致治具壁破损或漏锡。",
                        "error",
                        object_id=f"solder-{s_idx+1}-keepout-{k_idx+1}",
                    )
                )

    # 9. 弹簧卡安装孔冲突检查 (SPRING_CLIP_SINK_COLLISION, SPRING_CLIP_KEEPOUT_COLLISION)
    for clip in fixture.spring_clip_holes:
        cp = Point(clip["x"], clip["y"])
        clip_id = clip.get("id", "clip")
        clip_circle = cp.buffer(clip["diameter"] / 2)
        if fixture.sink_region.contains(cp):
            issues.append(
                _issue(
                    "SPRING_CLIP_SINK_COLLISION",
                    "弹簧卡安装孔与沉板区干涉",
                    f"弹簧卡安装孔 {clip_id} ({clip['x']:.1f}, {clip['y']:.1f}) 落入沉板区内，无法有效安装前挡板。",
                    "warning",
                    point=cp,
                    object_id=f"{clip_id}-sink",
                )
            )
        for k_idx, keepout in enumerate(fixture.keepout_regions):
            if clip_circle.intersects(keepout):
                issues.append(
                    _issue(
                        "SPRING_CLIP_KEEPOUT_COLLISION",
                        "弹簧卡安装孔与 BOT 避位区干涉",
                        f"弹簧卡安装孔 {clip_id} ({clip['x']:.1f}, {clip['y']:.1f}) 与 BOT 避位区 #{k_idx+1} 重叠。",
                        "warning",
                        point=cp,
                        object_id=f"{clip_id}-keepout-{k_idx+1}",
                    )
                )

    # 10. 最小材料壁厚检查 (MINIMUM_MATERIAL_WEB_TOO_SMALL)
    min_web = params.get("minimumMaterialWebMm", 2.0)
    # 检查上锡窗口与沉板边缘之间
    for i, s1 in enumerate(fixture.solder_regions):
        try:
            s1_boundary = s1.boundary if not hasattr(s1, 'exterior') or s1.geom_type == 'MultiPolygon' else s1.exterior
            sink_boundary = fixture.sink_region.boundary if fixture.sink_region.geom_type == 'MultiPolygon' else fixture.sink_region.exterior
            dist_to_sink_edge = s1_boundary.distance(sink_boundary)
        except Exception:
            continue
        if dist_to_sink_edge < min_web:
            issues.append(
                _issue(
                    "MINIMUM_MATERIAL_WEB_TOO_SMALL",
                    "上锡窗口与沉板边缘材料壁厚过薄",
                    f"上锡窗口 #{i+1} 距离沉板台阶边缘仅 {dist_to_sink_edge:.2f}mm (标准要求 >= {min_web:.1f}mm)。",
                    "warning",
                    current_value=dist_to_sink_edge,
                    required_value=min_web,
                    unit="mm",
                    object_id=f"solder-{i+1}-sink-edge",
                )
            )

    # 检查相邻上锡窗口之间的材料壁厚
    num_solder = len(fixture.solder_regions)
    for i in range(num_solder):
        s1 = fixture.solder_regions[i]
        s1_b = s1.boundary if not hasattr(s1, 'exterior') or s1.geom_type == 'MultiPolygon' else s1.exterior
        for j in range(i + 1, num_solder):
            s2 = fixture.solder_regions[j]
            s2_b = s2.boundary if not hasattr(s2, 'exterior') or s2.geom_type == 'MultiPolygon' else s2.exterior
            try:
                dist_between = s1_b.distance(s2_b)
            except Exception:
                continue
            if 0 < dist_between < min_web:
                issues.append(
                    _issue(
                        "MINIMUM_MATERIAL_WEB_TOO_SMALL",
                        "上锡窗口间材料壁厚过薄",
                        f"上锡窗口 #{i+1} 与窗口 #{j+1} 间壁厚仅 {dist_between:.2f}mm (标准要求 >= {min_web:.1f}mm)。",
                        "warning",
                        current_value=dist_between,
                        required_value=min_web,
                        unit="mm",
                        object_id=f"solder-web-{i+1}-{j+1}",
                    )
                )

    return issues


def _issue(
    code: str,
    title: str,
    description: str,
    severity: str,
    current_value: float | None = None,
    required_value: float | None = None,
    unit: str | None = None,
    point: Point | None = None,
    layer_id: str = "drc",
    object_id: str | None = None,
) -> dict:
    target = None
    if point is not None:
        target = {"layerId": layer_id, "objectId": object_id or code.lower(), "x": point.x, "y": point.y}
    return {
        "id": f"drc-{code.lower()}-{object_id or 'global'}",
        "code": code,
        "type": code,
        "title": title,
        "description": description,
        "severity": severity,
        "currentValue": current_value,
        "requiredValue": required_value,
        "unit": unit,
        "target": target,
        "confirmed": False,
    }
