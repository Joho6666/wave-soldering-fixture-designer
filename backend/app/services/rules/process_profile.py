"""ProcessProfile — single source of manufacturing numeric defaults.

Values match the v0.4 / v0.5 FixtureParameters defaults so existing jobs keep
the same 2D geometry unless an engineer overrides them. New fields are software
defaults, not claimed industry standards. Directional opening and pressure
relief are off by default for v0.5 compatibility.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Literal


WaveDirection = Literal["+X", "-X", "+Y", "-Y"]


@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    default: Any
    unit: str
    description: str
    category: str
    min: float | None = None
    max: float | None = None
    editable: bool = True
    value_type: str = "number"
    choices: tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "default": self.default,
            "unit": self.unit,
            "description": self.description,
            "category": self.category,
            "min": self.min,
            "max": self.max,
            "editable": self.editable,
            "type": self.value_type,
            "choices": list(self.choices) if self.choices else None,
        }


PARAMETER_DEFINITIONS: tuple[ParameterDefinition, ...] = (
    ParameterDefinition("palletThicknessMm", 10.0, "mm", "治具板材厚度", "Fixture", 4.0, 30.0),
    ParameterDefinition("fixtureMarginXmm", 20.0, "mm", "治具相对沉板区 X 向余量", "Fixture", 5.0, 80.0),
    ParameterDefinition("fixtureMarginYmm", 30.0, "mm", "治具相对沉板区 Y 向余量", "Fixture", 5.0, 80.0),
    ParameterDefinition("fixtureCornerRadiusMm", 5.0, "mm", "治具外框圆角", "Fixture", 0.0, 20.0),
    ParameterDefinition("minimumMaterialWebMm", 2.0, "mm", "最小材料壁厚", "Fixture", 0.5, 8.0),
    ParameterDefinition("fixtureSizeRoundStepMm", 5.0, "mm", "治具外形取整步长", "Fixture", 1.0, 10.0),
    ParameterDefinition("sinkClearanceMm", 0.2, "mm", "沉板台阶间隙", "Pocket", 0.05, 2.0),
    ParameterDefinition("filletRadiusMm", 1.85, "mm", "沉板内角铣刀清角半径", "Pocket", 0.5, 5.0),
    ParameterDefinition("railWidthMm", 5.0, "mm", "传送轨道卡槽宽度", "Fixture", 2.0, 15.0),
    ParameterDefinition("solderBarrierWidthMm", 10.0, "mm", "挡锡条宽度", "Fixture", 4.0, 30.0),
    ParameterDefinition("barrierMountHoleDiameterMm", 3.2, "mm", "挡锡条安装孔径", "Fixture", 2.0, 6.0),
    ParameterDefinition("clampHoleDiameterMm", 3.4, "mm", "压扣安装孔径", "Clamp", 2.0, 6.0),
    ParameterDefinition("clampOffsetMm", 10.0, "mm", "压扣相对沉板边偏移", "Clamp", 2.0, 30.0),
    ParameterDefinition("clampPinClearanceMm", 10.0, "mm", "压扣与定位销最小间距", "Clamp", 2.0, 30.0),
    ParameterDefinition("handholdWidthMm", 20.0, "mm", "取手位宽度", "Fixture", 10.0, 40.0),
    ParameterDefinition("handholdHeightMm", 40.0, "mm", "取手位高度", "Fixture", 15.0, 80.0),
    ParameterDefinition("handholdOverlapMm", 1.0, "mm", "取手位与沉板重叠", "Fixture", 0.0, 5.0),
    ParameterDefinition("handholdCornerRadiusMm", 2.0, "mm", "取手位圆角", "Fixture", 0.0, 10.0),
    ParameterDefinition("springClipRadiusMm", 2.45, "mm", "弹簧卡安装孔半径", "Clamp", 1.0, 5.0),
    ParameterDefinition("keepoutClearanceMm", 0.7, "mm", "BOT 避位外扩间隙", "Keepout", 0.2, 5.0),
    ParameterDefinition("keepoutInnerFilletMm", 1.5, "mm", "避位区内倒角", "Keepout", 0.0, 5.0),
    ParameterDefinition("componentVerticalClearanceMm", 0.5, "mm", "元件高度之上的口袋余量", "Pocket", 0.0, 5.0),
    ParameterDefinition("pocketFloorThicknessMm", 2.0, "mm", "口袋铣削后最小底板厚度", "Pocket", 0.5, 8.0),
    ParameterDefinition("defaultPocketDepthMm", 2.0, "mm", "无元件高度时的默认口袋深度", "Pocket", 0.2, 15.0),
    ParameterDefinition("solderClearanceMm", 3.0, "mm", "上锡窗口相对焊盘/孔径间隙", "Solder", 0.5, 8.0),
    ParameterDefinition("solderMinOuterDiameterMm", 3.0, "mm", "上锡窗口最小外径", "Solder", 1.0, 10.0),
    ParameterDefinition("solderMinOpeningWidthMm", 1.5, "mm", "上锡窗口最小宽度", "Solder", 0.5, 8.0),
    ParameterDefinition("solderOpeningMergeDistanceMm", 2.0, "mm", "邻近上锡窗口合并距离", "Solder", 0.0, 10.0),
    ParameterDefinition(
        "directionalOpeningEnabled",
        False,
        "",
        "按波峰流向拉长/倒角上锡窗口（默认关闭以兼容 v0.5）",
        "Wave",
        value_type="boolean",
    ),
    ParameterDefinition("solderLeadingExtensionMm", 0.8, "mm", "上锡窗口迎锡边额外延伸", "Wave", 0.0, 8.0),
    ParameterDefinition("solderTrailingExtensionMm", 1.5, "mm", "上锡窗口出锡边额外延伸", "Wave", 0.0, 8.0),
    ParameterDefinition("solderSideClearanceMm", 0.0, "mm", "上锡窗口垂直于流向的额外侧向间隙", "Wave", 0.0, 5.0),
    ParameterDefinition("solderEntryChamferMm", 0.0, "mm", "迎锡边倒角尺寸", "Wave", 0.0, 5.0),
    ParameterDefinition("solderExitChamferMm", 0.0, "mm", "出锡边倒角尺寸", "Wave", 0.0, 5.0),
    ParameterDefinition("minPinHoleDiameterMm", 2.0, "mm", "定位孔候选最小孔径", "Pins", 1.0, 6.0),
    ParameterDefinition("maxPinHoleDiameterMm", 4.5, "mm", "定位孔候选最大孔径", "Pins", 2.0, 10.0),
    ParameterDefinition("preferredPinDiameterMinMm", 2.5, "mm", "优先孔径下限", "Pins", 1.0, 6.0),
    ParameterDefinition("preferredPinDiameterMaxMm", 4.5, "mm", "优先孔径上限", "Pins", 2.0, 10.0),
    ParameterDefinition("preferredNPTH", True, "", "优先选择 NPTH 作为定位孔", "Pins", value_type="boolean"),
    ParameterDefinition("minPinSeparationMm", 15.0, "mm", "定位销最小跨距", "Pins", 5.0, 80.0),
    ParameterDefinition("pinEdgeBonusMm", 15.0, "mm", "靠近板边的评分距离", "Pins", 0.0, 40.0),
    ParameterDefinition("pinDiameterOffsetMm", 0.1, "mm", "定位销直径 = 孔径 − 该偏移", "Pins", 0.0, 0.5),
    ParameterDefinition("pinDiameterMinMm", 1.5, "mm", "定位销最小直径", "Pins", 0.8, 5.0),
    ParameterDefinition("pinDiameterMaxMm", 4.0, "mm", "定位销最大直径", "Pins", 1.5, 8.0),
    ParameterDefinition(
        "waveDirection",
        "+X",
        "",
        "波峰流向（软件坐标，非宣称行业标准）",
        "Wave",
        value_type="enum",
        choices=("+X", "-X", "+Y", "-Y"),
    ),
    ParameterDefinition(
        "conveyorDirection",
        "+X",
        "",
        "传送方向（记录用；开窗算法使用 waveDirection）",
        "Wave",
        value_type="enum",
        choices=("+X", "-X", "+Y", "-Y"),
    ),
    ParameterDefinition(
        "pressureReliefEnabled",
        False,
        "",
        "为封闭大口袋生成排气泄压槽（默认关闭）",
        "Pressure Relief",
        value_type="boolean",
    ),
    ParameterDefinition("pressureReliefMinPocketAreaMm2", 400.0, "mm²", "触发泄压槽的口袋最小面积", "Pressure Relief", 50.0, 5000.0),
    ParameterDefinition("pressureReliefChannelWidthMm", 2.0, "mm", "泄压槽宽度", "Pressure Relief", 0.5, 8.0),
    ParameterDefinition("pressureReliefEdgeClearanceMm", 3.0, "mm", "泄压槽出口相对治具外缘的保留距离", "Pressure Relief", 0.5, 15.0),
    ParameterDefinition("panelEnabled", False, "", "启用网格拼板（默认关闭）", "Panel", value_type="boolean"),
    ParameterDefinition("panelRows", 1.0, "", "拼板行数", "Panel", 1.0, 10.0),
    ParameterDefinition("panelCols", 1.0, "", "拼板列数", "Panel", 1.0, 10.0),
    ParameterDefinition("panelBoardSpacingMm", 2.0, "mm", "拼板 PCB 间距", "Panel", 0.0, 20.0),
    ParameterDefinition("panelOuterMarginMm", 5.0, "mm", "拼板工艺边宽度", "Panel", 0.0, 30.0),
    ParameterDefinition("panelToolingHoleDiameterMm", 3.0, "mm", "拼板 tooling 孔径", "Panel", 1.0, 6.0),
    ParameterDefinition("panelFiducialDiameterMm", 1.0, "mm", "拼板基准点直径", "Panel", 0.5, 3.0),
    ParameterDefinition("camReservedToolDiameterMm", 1.85, "mm", "CAM 预留刀具直径（本轮不生成刀路）", "CAM Reserved", 0.5, 6.0, editable=False),
)

_DEFINITIONS_BY_NAME = {d.name: d for d in PARAMETER_DEFINITIONS}


@dataclass(frozen=True)
class ProcessProfile:
    palletThicknessMm: float = 10.0
    fixtureMarginXmm: float = 20.0
    fixtureMarginYmm: float = 30.0
    fixtureCornerRadiusMm: float = 5.0
    minimumMaterialWebMm: float = 2.0
    fixtureSizeRoundStepMm: float = 5.0
    sinkClearanceMm: float = 0.2
    filletRadiusMm: float = 1.85
    railWidthMm: float = 5.0
    solderBarrierWidthMm: float = 10.0
    barrierMountHoleDiameterMm: float = 3.2
    clampHoleDiameterMm: float = 3.4
    clampOffsetMm: float = 10.0
    clampPinClearanceMm: float = 10.0
    handholdWidthMm: float = 20.0
    handholdHeightMm: float = 40.0
    handholdOverlapMm: float = 1.0
    handholdCornerRadiusMm: float = 2.0
    springClipRadiusMm: float = 2.45
    keepoutClearanceMm: float = 0.7
    keepoutInnerFilletMm: float = 1.5
    componentVerticalClearanceMm: float = 0.5
    pocketFloorThicknessMm: float = 2.0
    defaultPocketDepthMm: float = 2.0
    solderClearanceMm: float = 3.0
    solderMinOuterDiameterMm: float = 3.0
    solderMinOpeningWidthMm: float = 1.5
    solderOpeningMergeDistanceMm: float = 2.0
    directionalOpeningEnabled: bool = False
    solderLeadingExtensionMm: float = 0.8
    solderTrailingExtensionMm: float = 1.5
    solderSideClearanceMm: float = 0.0
    solderEntryChamferMm: float = 0.0
    solderExitChamferMm: float = 0.0
    minPinHoleDiameterMm: float = 2.0
    maxPinHoleDiameterMm: float = 4.5
    preferredPinDiameterMinMm: float = 2.5
    preferredPinDiameterMaxMm: float = 4.5
    preferredNPTH: bool = True
    minPinSeparationMm: float = 15.0
    pinEdgeBonusMm: float = 15.0
    pinDiameterOffsetMm: float = 0.1
    pinDiameterMinMm: float = 1.5
    pinDiameterMaxMm: float = 4.0
    waveDirection: WaveDirection = "+X"
    conveyorDirection: WaveDirection = "+X"
    pressureReliefEnabled: bool = False
    pressureReliefMinPocketAreaMm2: float = 400.0
    pressureReliefChannelWidthMm: float = 2.0
    pressureReliefEdgeClearanceMm: float = 3.0
    panelEnabled: bool = False
    panelRows: float = 1.0
    panelCols: float = 1.0
    panelBoardSpacingMm: float = 2.0
    panelOuterMarginMm: float = 5.0
    panelToolingHoleDiameterMm: float = 3.0
    panelFiducialDiameterMm: float = 1.0
    camReservedToolDiameterMm: float = 1.85

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def definitions(cls) -> list[dict[str, Any]]:
        return [d.to_dict() for d in PARAMETER_DEFINITIONS]

    @classmethod
    def from_dict(cls, supplied: dict[str, Any] | None) -> ProcessProfile:
        if not supplied:
            return cls()
        kwargs: dict[str, Any] = {}
        bool_fields = {
            "preferredNPTH",
            "directionalOpeningEnabled",
            "pressureReliefEnabled",
            "panelEnabled",
        }
        enum_fields = {"waveDirection", "conveyorDirection"}
        for f in fields(cls):
            if f.name not in supplied:
                continue
            raw = supplied[f.name]
            if f.name in bool_fields:
                if isinstance(raw, str):
                    kwargs[f.name] = raw.strip().lower() in {"1", "true", "yes", "on"}
                else:
                    kwargs[f.name] = bool(raw)
            elif f.name in enum_fields:
                value = str(raw)
                if value in {"+X", "-X", "+Y", "-Y"}:
                    kwargs[f.name] = value
            else:
                try:
                    kwargs[f.name] = float(raw)
                except (TypeError, ValueError):
                    continue
        return cls(**kwargs)


def parameter_catalog() -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in PARAMETER_DEFINITIONS:
        grouped.setdefault(item.category, []).append(item.to_dict())
    return {
        "categories": [
            "Fixture",
            "Pocket",
            "Keepout",
            "Solder",
            "Pins",
            "Clamp",
            "Wave",
            "Pressure Relief",
            "Panel",
            "CAM Reserved",
        ],
        "parameters": [d.to_dict() for d in PARAMETER_DEFINITIONS],
        "grouped": grouped,
        "defaults": ProcessProfile().to_dict(),
    }
