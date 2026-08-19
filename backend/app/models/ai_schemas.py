"""Strict, non-arbitrary AI command contracts."""
from __future__ import annotations

from typing import Annotated, Literal, List
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from app.models.schemas import FixtureParameters


class ParameterPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sinkClearanceMm: FiniteFloat | None = Field(None, gt=0, le=20)
    keepoutClearanceMm: FiniteFloat | None = Field(None, gt=0, le=20)
    solderClearanceMm: FiniteFloat | None = Field(None, gt=0, le=30)
    filletRadiusMm: FiniteFloat | None = Field(None, gt=0, le=20)
    clampHoleDiameterMm: FiniteFloat | None = Field(None, gt=0, le=30)
    clampOffsetMm: FiniteFloat | None = Field(None, gt=0, le=100)
    handholdWidthMm: FiniteFloat | None = Field(None, gt=0, le=200)
    handholdHeightMm: FiniteFloat | None = Field(None, gt=0, le=300)
    handholdOverlapMm: FiniteFloat | None = Field(None, gt=0, le=20)
    handholdCornerRadiusMm: FiniteFloat | None = Field(None, gt=0, le=50)
    fixtureMarginXmm: FiniteFloat | None = Field(None, gt=0, le=200)
    fixtureMarginYmm: FiniteFloat | None = Field(None, gt=0, le=200)
    fixtureCornerRadiusMm: FiniteFloat | None = Field(None, gt=0, le=50)
    railWidthMm: FiniteFloat | None = Field(None, gt=0, le=50)
    solderBarrierWidthMm: FiniteFloat | None = Field(None, gt=0, le=100)
    minimumMaterialWebMm: FiniteFloat | None = Field(None, gt=0, le=50)
    springClipRadiusMm: FiniteFloat | None = Field(None, gt=0, le=20)
    keepoutInnerFilletMm: FiniteFloat | None = Field(None, ge=0, le=20)
    solderMinOuterDiameterMm: FiniteFloat | None = Field(None, gt=0, le=30)
    fixtureSizeRoundStepMm: FiniteFloat | None = Field(None, gt=0, le=50)

    def values(self) -> dict:
        return self.model_dump(exclude_none=True)


class UpdateParametersCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["update_parameters"] = "update_parameters"
    parameters: ParameterPatch
    reason: str = Field(default="调整工程参数", max_length=1000)
    requiresConfirmation: bool = True


class ApplyRecipePresetCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["apply_recipe_preset"] = "apply_recipe_preset"
    presetId: Literal["automotive_high_reliability", "dense_consumer", "thick_copper_heavy", "standard"]
    presetName: str = Field(default="", max_length=100)
    parameters: ParameterPatch
    reason: str = Field(default="应用工艺配方预设", max_length=1000)
    requiresConfirmation: bool = True


class SetLocatingPinsCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["set_locating_pins"] = "set_locating_pins"
    pinDrillIds: List[str] = Field(min_length=1, max_length=10)
    reason: str = Field(default="指定定位孔方案", max_length=1000)
    requiresConfirmation: bool = True


class AddCustomRegionCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["add_custom_region"] = "add_custom_region"
    regionType: Literal["keepout", "solder"]
    x: float = Field(..., description="X 坐标 (mm)")
    y: float = Field(..., description="Y 坐标 (mm)")
    width: float = Field(..., gt=0, le=500, description="区域宽度 (mm)")
    height: float = Field(..., gt=0, le=500, description="区域高度 (mm)")
    label: str = Field(default="", max_length=100)
    reason: str = Field(default="添加自定义避位/上锡区域", max_length=1000)
    requiresConfirmation: bool = True


class AutoFixDrcCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["auto_fix_drc"] = "auto_fix_drc"
    targetIssueIds: List[str] = Field(default_factory=list)
    suggestedParameters: ParameterPatch
    reason: str = Field(default="自动修复 DRC 规则违规", max_length=1000)
    requiresConfirmation: bool = True


class RegenerateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["regenerate"] = "regenerate"
    reason: str = Field(default="重新计算治具几何", max_length=1000)
    requiresConfirmation: bool = True


class LocateIssueCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["locate_issue"] = "locate_issue"
    issueId: str = Field(min_length=1, max_length=200)
    reason: str = Field(default="在图纸中定位 DRC 问题", max_length=1000)
    requiresConfirmation: bool = False


class ExplainIssueCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["explain_issue"] = "explain_issue"
    issueId: str = Field(min_length=1, max_length=200)
    reason: str = Field(default="解释 DRC 规则违规原因", max_length=1000)
    requiresConfirmation: bool = False


class NoOpCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["no_op"] = "no_op"
    reason: str = Field(default="常规对话，无需修改 CAD 几何", max_length=1000)
    requiresConfirmation: bool = False


CADCommand = Annotated[
    UpdateParametersCommand
    | ApplyRecipePresetCommand
    | SetLocatingPinsCommand
    | AddCustomRegionCommand
    | AutoFixDrcCommand
    | RegenerateCommand
    | LocateIssueCommand
    | ExplainIssueCommand
    | NoOpCommand,
    Field(discriminator="kind"),
]


class AICommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    userMessage: str = Field(min_length=1, max_length=4000)
    conversationId: str | None = Field(None, max_length=200)
    command: CADCommand | None = None
    apply: bool = False
    requestId: str | None = Field(None, max_length=200)


class AICommandResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversationId: str | None = None
    message: str
    status: Literal["complete", "needs_confirmation", "error"]
    command: CADCommand
    applied: bool = False
    job: dict | None = None
    errors: list[str] = []
