"""
Pydantic 数据模型（API 请求/响应）
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """任务状态枚举"""
    IDLE = "idle"
    FILE_SELECTED = "file_selected"
    UPLOADING = "uploading"
    PARSING = "parsing"
    LAYER_CONFIRMATION = "layer_confirmation"
    GENERATING = "generating"
    REVIEW_REQUIRED = "review_required"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(str, Enum):
    """统一前后端错误码"""
    MISSING_OUTLINE_LAYER = "MISSING_OUTLINE_LAYER"
    MISSING_DRILL_LAYER = "MISSING_DRILL_LAYER"
    UNKNOWN_CRITICAL_LAYER = "UNKNOWN_CRITICAL_LAYER"
    INVALID_GERBER = "INVALID_GERBER"
    INVALID_EXCELLON = "INVALID_EXCELLON"
    INVALID_OUTLINE = "INVALID_OUTLINE"
    ZIP_INVALID = "ZIP_INVALID"
    ZIP_EMPTY = "ZIP_EMPTY"
    GEOMETRY_ERROR = "GEOMETRY_ERROR"
    DXF_EXPORT_ERROR = "DXF_EXPORT_ERROR"
    JOB_TIMEOUT = "JOB_TIMEOUT"


class DiagnosticLog(BaseModel):
    """诊断日志"""
    time: str
    level: str  # info, warning, error
    message: str


class FixtureError(BaseModel):
    """错误信息"""
    code: str
    title: str
    message: str
    details: Optional[List[str]] = None
    recoverable: bool = True


class GerberLayerType(str, Enum):
    """Gerber 图层类型"""
    BOARD_OUTLINE = "board_outline"
    TOP_COPPER = "top_copper"
    BOTTOM_COPPER = "bottom_copper"
    TOP_SOLDERMASK = "top_soldermask"
    BOTTOM_SOLDERMASK = "bottom_soldermask"
    TOP_SILKSCREEN = "top_silkscreen"
    BOTTOM_SILKSCREEN = "bottom_silkscreen"
    DRILL = "drill"
    UNKNOWN = "unknown"


class GerberLayer(BaseModel):
    """Gerber 图层"""
    id: str
    filename: str
    type: GerberLayerType
    confidence: float
    reason: Optional[str] = None
    confirmed: bool = False


class PCBAnalysis(BaseModel):
    """PCB 分析结果"""
    width: float
    height: float
    fileCount: int
    holeCount: int
    pthCount: int = 0
    npthCount: int = 0
    outlineClosed: bool
    outlineAreaMm2: float
    layers: List[GerberLayer]
    holes: List[Dict[str, Any]] = []
    diagnostics: List[str] = []
    sourceSha256: Optional[str] = None
    geometrySha256: Optional[str] = None


class FixtureParameters(BaseModel):
    """前后端统一的治具参数 DTO（单位均为 mm）。"""
    sinkClearanceMm: float = 0.2
    keepoutClearanceMm: float = 0.7
    solderClearanceMm: float = 3.0
    filletRadiusMm: float = 1.85
    clampHoleDiameterMm: float = 3.4
    clampOffsetMm: float = 10.0
    handholdWidthMm: float = 20.0
    handholdHeightMm: float = 40.0
    handholdOverlapMm: float = 1.0
    handholdCornerRadiusMm: float = 2.0
    fixtureMarginXmm: float = 20.0
    fixtureMarginYmm: float = 30.0
    fixtureCornerRadiusMm: float = 5.0
    railWidthMm: float = 5.0
    solderBarrierWidthMm: float = 10.0
    minimumMaterialWebMm: float = 2.0
    springClipRadiusMm: float = 2.45
    keepoutInnerFilletMm: float = 1.5
    solderMinOuterDiameterMm: float = 3.0
    fixtureSizeRoundStepMm: float = 5.0


class DesignIssue(BaseModel):
    """设计问题"""
    id: str
    code: str
    title: str
    description: str
    severity: str  # info, warning, error, blocking
    currentValue: Optional[float] = None
    requiredValue: Optional[float] = None
    unit: Optional[str] = None
    target: Optional[Dict[str, Any]] = None
    confirmed: bool = False
    overridden: bool = False


class DrcOverrideRequest(BaseModel):
    operator: str
    reason: str


class DrcOverrideRecord(BaseModel):
    issueId: str
    operator: str
    reason: str
    timestamp: str
    originalSeverity: str
    geometrySha256: Optional[str] = None
    status: str = "active"


class ProductionGateResult(BaseModel):
    blocking_reviews: int = 0
    blocking_drc_errors: int = 0
    unconfirmed_layers: int = 0
    missing_required_data: int = 0
    geometry_validation_errors: int = 0
    production_ready: bool = False
    blocking_reasons: List[str] = []


class ReviewItem(BaseModel):
    """人工审核项"""
    id: str
    type: str  # locating_pin_candidate, bot_keepout_region, top_solder_region, etc.
    status: str = "pending"  # pending, accepted, rejected, modified
    title: str
    description: str
    confidence: float
    geometryId: Optional[str] = None
    mandatory: bool = True
    x: Optional[float] = None
    y: Optional[float] = None
    data: Optional[Dict[str, Any]] = None


class ReviewActionRequest(BaseModel):
    """审核操作请求"""
    action: str = "accept"  # accept, reject, modify
    modifiedData: Optional[Dict[str, Any]] = None


class LocatingPinCandidate(BaseModel):
    """定位孔候选"""
    id: str
    drillId: str
    x: float
    y: float
    diameterMm: float
    plated: Optional[bool] = None
    score: float
    eligible: bool
    selected: bool
    pinDiameterMm: float
    rejectionReasons: List[str] = []


class FixtureResult(BaseModel):
    """治具生成结果"""
    fixtureWidth: float
    fixtureHeight: float
    featureSummary: Dict[str, int]
    issues: List[DesignIssue]
    reviewItems: List[ReviewItem] = []
    locatingCandidates: List[LocatingPinCandidate] = []
    manualLocatingPins: Optional[List[str]] = None
    status: str = "completed"
    geometrySha256: Optional[str] = None
    productionGate: Optional[ProductionGateResult] = None
    drcOverrides: List[DrcOverrideRecord] = []
    algorithmVersion: Optional[str] = None
    softwareVersion: Optional[str] = None
    ruleProfileVersion: Optional[str] = None
    generatedAt: str


class JobResponse(BaseModel):
    """Job 响应"""
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    status: JobStatus
    progress: int
    createdAt: str
    currentStepDescription: Optional[str] = None
    error: Optional[FixtureError] = None
    logs: List[DiagnosticLog] = []


class JobCreate(BaseModel):
    """创建 Job 请求"""
    pass


class LayersConfirmRequest(BaseModel):
    """图层确认请求"""
    layers: List[GerberLayer]


class RegenerateRequest(BaseModel):
    """重新生成请求"""
    parameters: Optional[FixtureParameters] = None
    manualLocatingPins: Optional[List[str]] = None
    acceptedReviews: Optional[List[str]] = None
    rejectedReviews: Optional[List[str]] = None


