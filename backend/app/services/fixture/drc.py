"""Geometry-based design rule checks."""
from __future__ import annotations

import math
from typing import Any

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

from app.geometry.spatial import query_intersects
from app.models.geometry import FixtureGeometry


def _hole_disk(hole: dict[str, Any], default_diameter: float = 3.0) -> BaseGeometry:
    radius = float(hole.get("diameter", default_diameter)) / 2.0
    return Point(hole["x"], hole["y"]).buffer(max(radius, 1e-6))


def run_drc(fixture: FixtureGeometry) -> list[dict]:
    issues: list[dict] = []
    pcb = fixture.pcb
    params = fixture.parameters
    min_web = float(params.get("minimumMaterialWebMm", 2.0))

    issues.extend(_geometry_validity(fixture))

    if pcb.outline is not None and not pcb.outline.is_valid:
        issues.append(_issue("PCB_OUTLINE_INVALID", "PCB 外形无效", "PCB 外形存在自交或无效拓扑。", "blocking", source_ids=["pcb-outline"]))
    if fixture.sink_region.is_empty or not fixture.sink_region.is_valid:
        issues.append(_issue("SINK_REGION_INVALID", "沉板区无效", "PCB 外扩后未形成有效沉板区域。", "blocking", source_ids=["sink"]))
    if not fixture.body.contains(fixture.sink_region):
        issues.append(_issue("FIXTURE_BODY_OVERFLOW", "沉板区超出治具", "沉板区超出了治具主体外框边界。", "blocking", geometry=fixture.sink_region, source_ids=["sink"]))

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

    for b_idx, barrier in enumerate(fixture.solder_barriers):
        if barrier.intersects(fixture.sink_region):
            issues.append(
                _issue(
                    "BARRIER_SINK_COLLISION",
                    "挡锡条与沉板区干涉",
                    f"防锡桥挡锡条 #{b_idx+1} 与沉板区域重叠，可能压坏板边元件。",
                    "warning",
                    object_id=f"barrier-{b_idx+1}",
                    geometry=barrier,
                    source_ids=[f"barrier-{b_idx+1}"],
                )
            )

    for hole in fixture.solder_barrier_mount_holes:
        p = Point(hole["x"], hole["y"])
        disk = _hole_disk(hole, 3.2)
        if fixture.sink_region.intersects(disk):
            issues.append(
                _issue(
                    "BARRIER_HOLE_COLLISION",
                    "挡锡条安装孔与沉板区干涉",
                    f"挡锡条安装孔 ({hole['x']:.1f}, {hole['y']:.1f}) 落入沉板区内。",
                    "error",
                    point=p,
                    object_id=f"barrier-hole-{hole.get('id', 'unk')}",
                    source_ids=[str(hole.get("id", "barrier-hole"))],
                )
            )

    for h_idx, handhold in enumerate(fixture.handholds):
        if not fixture.body.contains(handhold):
            issues.append(
                _issue(
                    "HANDHOLD_FIXTURE_COLLISION",
                    "取手位超出治具边界",
                    f"取手位 #{h_idx+1} 掏空超出了治具外框边界。",
                    "error",
                    object_id=f"handhold-{h_idx+1}",
                    geometry=handhold,
                    source_ids=[f"handhold-{h_idx+1}"],
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
                        geometry=handhold,
                        source_ids=[f"handhold-{h_idx+1}", f"rail-{r_idx+1}"],
                    )
                )

    for clamp in fixture.clamp_holes:
        cp = Point(clamp["x"], clamp["y"])
        c_id = clamp.get("id", "clamp")
        disk = _hole_disk(clamp, 3.4)
        if not fixture.body.contains(disk):
            issues.append(
                _issue(
                    "CLAMP_FIXTURE_COLLISION",
                    "压扣孔超出治具外框",
                    f"压扣孔 {c_id} ({clamp['x']:.1f}, {clamp['y']:.1f}) 超出治具主体边界。",
                    "error",
                    point=cp,
                    object_id=f"{c_id}-body",
                    source_ids=[c_id],
                )
            )
        if fixture.sink_region.intersects(disk):
            issues.append(
                _issue(
                    "CLAMP_SINK_COLLISION",
                    "压扣孔落入沉板区",
                    f"压扣孔 {c_id} ({clamp['x']:.1f}, {clamp['y']:.1f}) 落在沉板台阶内部。",
                    "error",
                    point=cp,
                    object_id=f"{c_id}-sink",
                    source_ids=[c_id],
                )
            )
        for h_idx, handhold in enumerate(fixture.handholds):
            if handhold.intersects(disk):
                issues.append(
                    _issue(
                        "CLAMP_HANDHOLD_COLLISION",
                        "压扣与取手位干涉",
                        f"压扣孔 {c_id} ({clamp['x']:.1f}, {clamp['y']:.1f}) 与取手掏空干涉。",
                        "error",
                        point=cp,
                        object_id=f"{c_id}-handhold-{h_idx+1}",
                        source_ids=[c_id, f"handhold-{h_idx+1}"],
                    )
                )
        for r_idx, rail in enumerate(fixture.rails):
            if rail.intersects(disk):
                issues.append(
                    _issue(
                        "CLAMP_RAIL_COLLISION",
                        "压扣与轨道干涉",
                        f"压扣孔 {c_id} ({clamp['x']:.1f}, {clamp['y']:.1f}) 过于靠近或位于轨道卡槽内。",
                        "warning",
                        point=cp,
                        object_id=f"{c_id}-rail-{r_idx+1}",
                        source_ids=[c_id, f"rail-{r_idx+1}"],
                    )
                )
        for pin in fixture.locating_pins:
            p_id = pin.get("id", "pin")
            dist = math.hypot(clamp["x"] - pin["x"], clamp["y"] - pin["y"])
            clamp_pin_clearance = float(params.get("clampPinClearanceMm", 10.0))
            if dist < clamp_pin_clearance:
                issues.append(
                    _issue(
                        "CLAMP_LOCATING_PIN_COLLISION",
                        "压扣与定位销距离过近",
                        f"压扣 {c_id} 与定位销 {p_id} 间距 ({dist:.1f}mm < {clamp_pin_clearance:.1f}mm) 存在机械干涉风险。",
                        "warning",
                        current_value=dist,
                        required_value=clamp_pin_clearance,
                        unit="mm",
                        point=cp,
                        object_id=f"{c_id}-{p_id}",
                        source_ids=[c_id, p_id],
                    )
                )

    for pin in fixture.locating_pins:
        pp = Point(pin["x"], pin["y"])
        p_id = pin.get("id", "pin")
        pin_disk = _hole_disk(pin, 3.0)
        for k_idx, keepout in enumerate(fixture.keepout_regions):
            if keepout.intersects(pin_disk):
                issues.append(
                    _issue(
                        "LOCATING_PIN_KEEP_OUT_COLLISION",
                        "定位销与 BOT 避位区干涉",
                        f"定位销 {p_id} ({pin['x']:.1f}, {pin['y']:.1f}) 落在 BOT 避位区 #{k_idx+1} 内，无法有效下沉打销。",
                        "error",
                        point=pp,
                        object_id=f"{p_id}-keepout-{k_idx+1}",
                        source_ids=[p_id, f"keepout-{k_idx+1}"],
                    )
                )
        for s_idx, solder in enumerate(fixture.solder_regions):
            if solder.intersects(pin_disk):
                issues.append(
                    _issue(
                        "LOCATING_PIN_SOLDER_COLLISION",
                        "定位销与 TOP 上锡窗口干涉",
                        f"定位销 {p_id} ({pin['x']:.1f}, {pin['y']:.1f}) 位于上锡窗口 #{s_idx+1} 内，可能被锡液浸润卡死。",
                        "error",
                        point=pp,
                        object_id=f"{p_id}-solder-{s_idx+1}",
                        source_ids=[p_id, f"solder-{s_idx+1}"],
                    )
                )

    issues.extend(_solder_keepout_conflicts(fixture))

    for clip in fixture.spring_clip_holes:
        cp = Point(clip["x"], clip["y"])
        clip_id = clip.get("id", "clip")
        clip_circle = _hole_disk(clip, 4.9)
        if fixture.sink_region.intersects(clip_circle):
            issues.append(
                _issue(
                    "SPRING_CLIP_SINK_COLLISION",
                    "弹簧卡安装孔与沉板区干涉",
                    f"弹簧卡安装孔 {clip_id} ({clip['x']:.1f}, {clip['y']:.1f}) 落入沉板区内，无法有效安装前挡板。",
                    "warning",
                    point=cp,
                    object_id=f"{clip_id}-sink",
                    source_ids=[clip_id],
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
                        source_ids=[clip_id, f"keepout-{k_idx+1}"],
                    )
                )

    issues.extend(_material_web(fixture, min_web))
    issues.extend(_opening_proximity(fixture, min_web))
    issues.extend(_feature_outside_and_zero_area(fixture))
    issues.extend(_pressure_relief_drc(fixture, min_web))
    issues.extend(_panel_drc(fixture, min_web))
    issues.extend(_semantic_drc(fixture, params))
    return issues


def _geometry_validity(fixture: FixtureGeometry) -> list[dict]:
    issues: list[dict] = []
    named = [("body", fixture.body), ("sink", fixture.sink_region)]
    named.extend((f"keepout-{i+1}", g) for i, g in enumerate(fixture.keepout_regions))
    named.extend((f"solder-{i+1}", g) for i, g in enumerate(fixture.solder_regions))
    named.extend((f"handhold-{i+1}", g) for i, g in enumerate(fixture.handholds))
    named.extend((f"relief-{i+1}", g) for i, g in enumerate(getattr(fixture, "pressure_relief_channels", []) or []))
    for name, geom in named:
        if geom is None:
            continue
        if geom.is_empty:
            issues.append(
                _issue(
                    "ZERO_AREA_FEATURE",
                    "零面积特征",
                    f"{name} 几何为空或面积为零。",
                    "error",
                    object_id=name,
                    source_ids=[name],
                    recommended_action="检查输入外形或参数是否导致该特征退化。",
                )
            )
            continue
        if not geom.is_valid:
            reason = explain_validity(geom)
            code = "SELF_INTERSECTION" if "Self-intersection" in reason or "self-intersection" in reason.lower() else "INVALID_GEOMETRY"
            issues.append(
                _issue(
                    code,
                    "几何无效",
                    f"{name} 无效: {reason}",
                    "blocking",
                    object_id=name,
                    geometry=geom,
                    source_ids=[name],
                    recommended_action="修复自交或退化多边形后再出图。",
                )
            )
        elif geom.area <= 1e-9:
            issues.append(
                _issue(
                    "ZERO_AREA_FEATURE",
                    "零面积特征",
                    f"{name} 面积接近零。",
                    "error",
                    object_id=name,
                    geometry=geom,
                    source_ids=[name],
                )
            )
    return issues


def _solder_keepout_conflicts(fixture: FixtureGeometry) -> list[dict]:
    issues: list[dict] = []
    keepouts = list(fixture.keepout_regions or [])
    for s_idx, solder in enumerate(fixture.solder_regions):
        for k_idx, keepout in query_intersects(keepouts, solder):
            issues.append(
                _issue(
                    "SOLDER_KEEP_OUT_CONFLICT",
                    "上锡窗口与 BOT 避位区重叠冲突",
                    f"上锡窗口 #{s_idx+1} 与 BOT 避位区 #{k_idx+1} 存在几何相交，容易导致治具壁破损或漏锡。",
                    "error",
                    object_id=f"solder-{s_idx+1}-keepout-{k_idx+1}",
                    geometry=solder,
                    source_ids=[f"solder-{s_idx+1}", f"keepout-{k_idx+1}"],
                    recommended_action="缩小窗口或避位，或由工程师确认冲突可接受。",
                )
            )
    return issues


def _material_web(fixture: FixtureGeometry, min_web: float) -> list[dict]:
    issues: list[dict] = []
    solders = list(fixture.solder_regions or [])
    for i, s1 in enumerate(solders):
        try:
            s1_boundary = s1.boundary
            sink_boundary = fixture.sink_region.boundary
            dist_to_sink_edge = s1_boundary.distance(sink_boundary)
        except Exception:
            continue
        if dist_to_sink_edge < min_web:
            issues.append(
                _issue(
                    "MINIMUM_MATERIAL_WEB_TOO_SMALL",
                    "上锡窗口与沉板边缘材料壁厚过薄",
                    f"上锡窗口 #{i+1} 距离沉板台阶边缘仅 {dist_to_sink_edge:.2f}mm (要求 >= {min_web:.1f}mm)。",
                    "warning",
                    current_value=dist_to_sink_edge,
                    required_value=min_web,
                    unit="mm",
                    object_id=f"solder-{i+1}-sink-edge",
                    geometry=s1,
                    source_ids=[f"solder-{i+1}"],
                )
            )
            issues.append(
                _issue(
                    "MINIMUM_MATERIAL_WEB",
                    "最小材料壁厚不足",
                    f"上锡窗口 #{i+1} 距沉板边缘 {dist_to_sink_edge:.2f}mm < {min_web:.1f}mm。",
                    "warning",
                    current_value=dist_to_sink_edge,
                    required_value=min_web,
                    unit="mm",
                    object_id=f"web-solder-{i+1}",
                    geometry=s1,
                    source_ids=[f"solder-{i+1}"],
                )
            )

    for i, s1 in enumerate(solders):
        for j, s2 in query_intersects(solders, s1.buffer(min_web)):
            if j <= i:
                continue
            try:
                dist_between = s1.boundary.distance(s2.boundary)
            except Exception:
                continue
            if 0 < dist_between < min_web:
                issues.append(
                    _issue(
                        "MINIMUM_MATERIAL_WEB_TOO_SMALL",
                        "上锡窗口间材料壁厚过薄",
                        f"上锡窗口 #{i+1} 与窗口 #{j+1} 间壁厚仅 {dist_between:.2f}mm (要求 >= {min_web:.1f}mm)。",
                        "warning",
                        current_value=dist_between,
                        required_value=min_web,
                        unit="mm",
                        object_id=f"solder-web-{i+1}-{j+1}",
                        source_ids=[f"solder-{i+1}", f"solder-{j+1}"],
                    )
                )
    return issues


def _opening_proximity(fixture: FixtureGeometry, min_web: float) -> list[dict]:
    issues: list[dict] = []
    body_boundary = fixture.body.boundary if fixture.body is not None else None
    for i, solder in enumerate(fixture.solder_regions or []):
        if body_boundary is not None:
            try:
                dist_edge = solder.distance(body_boundary)
            except Exception:
                dist_edge = 999.0
            if dist_edge < min_web:
                issues.append(
                    _issue(
                        "OPENING_TOO_CLOSE_TO_FIXTURE_EDGE",
                        "上锡窗口过靠近治具外缘",
                        f"上锡窗口 #{i+1} 距治具外缘 {dist_edge:.2f}mm < {min_web:.1f}mm。",
                        "error",
                        current_value=dist_edge,
                        required_value=min_web,
                        unit="mm",
                        object_id=f"solder-edge-{i+1}",
                        geometry=solder,
                        source_ids=[f"solder-{i+1}"],
                        recommended_action="增大治具余量或缩小窗口。",
                    )
                )
        for pin in fixture.locating_pins or []:
            pin_r = float(pin.get("diameter", 3.0)) / 2.0
            dist = solder.distance(Point(pin["x"], pin["y"])) - pin_r
            if dist < min_web:
                issues.append(
                    _issue(
                        "OPENING_TOO_CLOSE_TO_PIN",
                        "上锡窗口过靠近定位销",
                        f"上锡窗口 #{i+1} 距定位销 {pin.get('id', 'pin')} {dist:.2f}mm < {min_web:.1f}mm。",
                        "error",
                        current_value=dist,
                        required_value=min_web,
                        unit="mm",
                        object_id=f"solder-pin-{i+1}-{pin.get('id', 'pin')}",
                        geometry=solder,
                        source_ids=[f"solder-{i+1}", str(pin.get("id", "pin"))],
                        recommended_action="移动定位销或调整窗口。",
                    )
                )
    return issues


def _feature_outside_and_zero_area(fixture: FixtureGeometry) -> list[dict]:
    issues: list[dict] = []
    body = fixture.body
    for i, geom in enumerate(list(fixture.keepout_regions) + list(fixture.solder_regions) + list(getattr(fixture, "pressure_relief_channels", []) or [])):
        if geom is None or geom.is_empty:
            continue
        if not body.contains(geom.centroid) and not body.intersects(geom):
            issues.append(
                _issue(
                    "FEATURE_OUTSIDE_FIXTURE",
                    "特征位于治具外",
                    f"特征 #{i+1} 完全位于治具外框之外。",
                    "blocking",
                    object_id=f"outside-{i+1}",
                    geometry=geom,
                    source_ids=[f"feature-{i+1}"],
                )
            )
    return issues


def _pressure_relief_drc(fixture: FixtureGeometry, min_web: float) -> list[dict]:
    issues: list[dict] = []
    channels = list(getattr(fixture, "pressure_relief_channels", []) or [])
    if not channels:
        return issues
    obstacles: list[tuple[str, BaseGeometry]] = []
    if fixture.pcb.outline is not None:
        obstacles.append(("pcb", fixture.pcb.outline))
    for i, s in enumerate(fixture.solder_regions or []):
        obstacles.append((f"solder-{i+1}", s))
    for pin in fixture.locating_pins or []:
        obstacles.append((str(pin.get("id", "pin")), Point(pin["x"], pin["y"]).buffer(float(pin.get("diameter", 3.0)) / 2.0)))
    for clamp in fixture.clamp_holes or []:
        obstacles.append((str(clamp.get("id", "clamp")), Point(clamp["x"], clamp["y"]).buffer(float(clamp.get("diameter", 3.4)) / 2.0)))

    for c_idx, ch in enumerate(channels):
        if not fixture.body.contains(ch.centroid) and not fixture.body.intersects(ch):
            issues.append(
                _issue(
                    "PRESSURE_RELIEF_OUT_OF_FIXTURE",
                    "泄压槽超出治具",
                    f"泄压槽 #{c_idx+1} 未落在治具主体内。",
                    "error",
                    object_id=f"relief-{c_idx+1}",
                    geometry=ch,
                    source_ids=[f"relief-{c_idx+1}"],
                    recommended_action="缩短通道或增大治具余量。",
                )
            )
        for name, obs in obstacles:
            if ch.intersects(obs):
                issues.append(
                    _issue(
                        "PRESSURE_RELIEF_COLLISION",
                        "泄压槽与关键结构干涉",
                        f"泄压槽 #{c_idx+1} 与 {name} 相交。",
                        "error",
                        object_id=f"relief-{c_idx+1}-{name}",
                        geometry=ch,
                        source_ids=[f"relief-{c_idx+1}", name],
                        recommended_action="改道路径，避开 PCB 有效区、定位销、压扣与上锡窗口。",
                    )
                )
        try:
            dist_edge = ch.distance(fixture.body.boundary)
        except Exception:
            dist_edge = 999.0
        if 0 < dist_edge < min_web and fixture.body.contains(ch):
            issues.append(
                _issue(
                    "PRESSURE_RELIEF_WEB_TOO_THIN",
                    "泄压槽附近壁厚过薄",
                    f"泄压槽 #{c_idx+1} 距治具边界 {dist_edge:.2f}mm < {min_web:.1f}mm。",
                    "warning",
                    current_value=dist_edge,
                    required_value=min_web,
                    unit="mm",
                    object_id=f"relief-web-{c_idx+1}",
                    geometry=ch,
                    source_ids=[f"relief-{c_idx+1}"],
                )
            )
    return issues


def _panel_drc(fixture: FixtureGeometry, min_web: float) -> list[dict]:
    issues: list[dict] = []
    panel = getattr(fixture, "panel", None)
    if panel is None:
        return issues
    outlines = []
    for inst in panel.pcb_instances:
        try:
            outlines.append((inst.id, inst.global_outline()))
        except Exception:
            continue
    for i, (id_a, g_a) in enumerate(outlines):
        for id_b, g_b in outlines[i + 1 :]:
            if g_a.buffer(-1e-6).intersects(g_b.buffer(-1e-6)):
                issues.append(
                    _issue(
                        "PANEL_INSTANCE_COLLISION",
                        "拼板实例重叠",
                        f"PCB 实例 {id_a} 与 {id_b} 外形相交。",
                        "blocking",
                        object_id=f"panel-{id_a}-{id_b}",
                        geometry=g_a,
                        source_ids=[id_a, id_b],
                        recommended_action="增大拼板间距。",
                    )
                )
    for hole in list(getattr(fixture, "tooling_holes", []) or []):
        p = Point(hole["x"], hole["y"])
        disk = _hole_disk(hole, 3.0)
        hid = str(hole.get("id", "tooling"))
        if not fixture.body.contains(disk):
            issues.append(
                _issue(
                    "TOOLING_HOLE_COLLISION",
                    "Tooling 孔超出治具",
                    f"{hid} 不在治具范围内。",
                    "error",
                    point=p,
                    object_id=hid,
                    source_ids=[hid],
                )
            )
        for id_a, g_a in outlines:
            clearance = g_a.distance(disk) if not g_a.intersects(disk) else 0.0
            if g_a.intersects(disk) or clearance < min_web:
                issues.append(
                    _issue(
                        "TOOLING_HOLE_COLLISION",
                        "Tooling 孔与拼板 PCB 干涉",
                        f"{hid} 过靠近实例 {id_a}。",
                        "error",
                        point=p,
                        object_id=f"{hid}-{id_a}",
                        source_ids=[hid, id_a],
                    )
                )
        for pin in fixture.locating_pins or []:
            pin_disk = _hole_disk(pin, 3.0)
            if disk.distance(pin_disk) < min_web or disk.intersects(pin_disk):
                issues.append(
                    _issue(
                        "TOOLING_HOLE_COLLISION",
                        "Tooling 孔与定位销过近",
                        f"{hid} 与定位销 {pin.get('id')} 间距不足。",
                        "warning",
                        point=p,
                        object_id=f"{hid}-pin",
                        source_ids=[hid, str(pin.get("id", "pin"))],
                    )
                )
    return issues


def _semantic_drc(fixture: FixtureGeometry, params: dict) -> list[dict]:
    issues: list[dict] = []
    pallet = float(params.get("palletThicknessMm", 10.0))
    floor_min = float(params.get("pocketFloorThicknessMm", 2.0))
    min_opening = float(params.get("solderMinOpeningWidthMm", 1.5))
    min_span = float(params.get("minPinSeparationMm", 15.0))

    keepout_meta = list(getattr(fixture, "keepout_region_meta", []) or [])
    solder_meta = list(getattr(fixture, "solder_region_meta", []) or [])

    for meta in keepout_meta:
        depth = None
        height = None
        if meta.parameters:
            depth = meta.parameters.get("pocketDepthMm")
            height = meta.parameters.get("componentHeightMm")
        if height is None:
            issues.append(
                _issue(
                    "COMPONENT_HEIGHT_UNKNOWN",
                    "元件高度未知",
                    f"避位区域 {meta.id} 缺少元件高度，已使用默认口袋深度，置信度下降。",
                    "warning",
                    object_id=meta.id,
                    source_ids=list(meta.source_ids or ()),
                )
            )
        if depth is not None and pallet - float(depth) < floor_min:
            remaining = pallet - float(depth)
            issues.append(
                _issue(
                    "POCKET_FLOOR_TOO_THIN",
                    "口袋铣削后底板过薄",
                    f"避位 {meta.id} 口袋深度 {float(depth):.2f}mm 后剩余底板 {remaining:.2f}mm，低于 {floor_min:.2f}mm。",
                    "blocking",
                    current_value=remaining,
                    required_value=floor_min,
                    unit="mm",
                    object_id=meta.id,
                    geometry=meta.geometry,
                    source_ids=list(meta.source_ids or ()),
                    recommended_action="减小口袋深度、增大板厚或确认元件高度。",
                )
            )
        if meta.confidence < 0.70 and meta.source_type == "gerber_fallback":
            issues.append(
                _issue(
                    "SEMANTIC_CONFIDENCE_LOW",
                    "关键区域来自低置信度几何回退",
                    f"区域 {meta.id} 来源 {meta.source_type}，置信度 {meta.confidence:.2f}。",
                    "warning",
                    current_value=meta.confidence,
                    required_value=0.70,
                    object_id=meta.id,
                    source_ids=list(meta.source_ids or ()),
                )
            )

    for meta in solder_meta:
        geom = meta.geometry
        if geom is None or geom.is_empty:
            continue
        minx, miny, maxx, maxy = geom.bounds
        width = min(maxx - minx, maxy - miny)
        if width + 1e-9 < min_opening:
            issues.append(
                _issue(
                    "SOLDER_OPENING_TOO_NARROW",
                    "上锡窗口宽度低于工艺限制",
                    f"窗口 {meta.id} 最小外接宽度 {width:.2f}mm，低于 {min_opening:.2f}mm。",
                    "error",
                    current_value=width,
                    required_value=min_opening,
                    unit="mm",
                    object_id=meta.id,
                    geometry=geom,
                    source_ids=list(meta.source_ids or ()),
                )
            )
        if meta.confidence < 0.70 and meta.source_type == "gerber_fallback":
            issues.append(
                _issue(
                    "SEMANTIC_CONFIDENCE_LOW",
                    "关键区域来自低置信度几何回退",
                    f"上锡窗口 {meta.id} 来源 {meta.source_type}，置信度 {meta.confidence:.2f}。",
                    "warning",
                    current_value=meta.confidence,
                    required_value=0.70,
                    object_id=meta.id,
                    source_ids=list(meta.source_ids or ()),
                )
            )

    pins = fixture.locating_pins or []
    if len(pins) >= 2:
        span = 0.0
        for i in range(len(pins)):
            for j in range(i + 1, len(pins)):
                d = math.hypot(pins[i]["x"] - pins[j]["x"], pins[i]["y"] - pins[j]["y"])
                span = max(span, d)
        if span < min_span:
            issues.append(
                _issue(
                    "PIN_SPAN_TOO_SMALL",
                    "定位孔跨距不足",
                    f"已选定位销最大跨距 {span:.2f}mm，低于 {min_span:.2f}mm。",
                    "warning",
                    current_value=span,
                    required_value=min_span,
                    unit="mm",
                    object_id="locating-pins",
                    source_ids=["locating-pins"],
                )
            )

    pcb = fixture.pcb
    for conflict in getattr(pcb, "semantic_conflicts", []) or []:
        issues.append(
            _issue(
                "COMPONENT_DATA_CONFLICT",
                "元件数据源冲突",
                conflict.get("reason", "PnP / Gerber / BOM 数据明显冲突"),
                "error",
                object_id=str(conflict.get("refdes") or conflict.get("pnpId") or "semantic"),
                source_ids=[str(conflict.get("refdes") or "semantic")],
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
    geometry: BaseGeometry | None = None,
    source_ids: list[str] | None = None,
    recommended_action: str | None = None,
) -> dict:
    target = None
    if point is not None:
        target = {"layerId": layer_id, "objectId": object_id or code.lower(), "x": point.x, "y": point.y}
    geom_payload = None
    if geometry is not None and not geometry.is_empty:
        minx, miny, maxx, maxy = geometry.bounds
        geom_payload = {"bounds": [minx, miny, maxx, maxy], "area": geometry.area}
    return {
        "id": f"drc-{code.lower()}-{object_id or 'global'}",
        "code": code,
        "type": code,
        "title": title,
        "description": description,
        "message": description,
        "severity": severity,
        "currentValue": current_value,
        "requiredValue": required_value,
        "unit": unit,
        "target": target,
        "geometry": geom_payload,
        "sourceIds": source_ids or [],
        "recommendedAction": recommended_action,
        "confirmed": False,
    }
