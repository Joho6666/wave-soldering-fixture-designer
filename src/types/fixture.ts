import { DesignIssue } from "./inspection";

export interface FixtureParameters {
  sinkClearanceMm: number;
  keepoutClearanceMm: number;
  solderClearanceMm: number;
  filletRadiusMm: number;
  clampHoleDiameterMm: number;
  clampOffsetMm: number;
  handholdWidthMm: number;
  handholdHeightMm: number;
  handholdOverlapMm: number;
  handholdCornerRadiusMm: number;
  fixtureMarginXmm: number;
  fixtureMarginYmm: number;
  fixtureCornerRadiusMm: number;
  railWidthMm: number;
  solderBarrierWidthMm: number;
  minimumMaterialWebMm?: number;
  springClipRadiusMm?: number;
  keepoutInnerFilletMm?: number;
  solderMinOuterDiameterMm?: number;
  fixtureSizeRoundStepMm?: number;
}

export const DEFAULT_PARAMETERS: FixtureParameters = {
  sinkClearanceMm: 0.2,
  keepoutClearanceMm: 0.7,
  solderClearanceMm: 3.0,
  filletRadiusMm: 1.85,
  clampHoleDiameterMm: 3.4,
  clampOffsetMm: 10.0,
  handholdWidthMm: 20.0,
  handholdHeightMm: 40.0,
  handholdOverlapMm: 1.0,
  handholdCornerRadiusMm: 2.0,
  fixtureMarginXmm: 20.0,
  fixtureMarginYmm: 30.0,
  fixtureCornerRadiusMm: 5.0,
  railWidthMm: 5.0,
  solderBarrierWidthMm: 10.0,
  minimumMaterialWebMm: 2.0,
  springClipRadiusMm: 2.45,
  keepoutInnerFilletMm: 1.5,
  solderMinOuterDiameterMm: 3.0,
  fixtureSizeRoundStepMm: 5.0,
};

export interface ReviewItem {
  id: string;
  type: "bot_keepout_region" | "top_solder_region" | "locating_pin_candidate" | string;
  status: "pending" | "accepted" | "rejected" | "modified";
  title: string;
  description: string;
  mandatory?: boolean;
  confidence: number;
  geometryId?: string;
  x?: number;
  y?: number;
  data?: Record<string, any>;
}

export interface LocatingPinCandidate {
  id: string;
  drillId: string;
  x: number;
  y: number;
  diameterMm: number;
  plated: boolean | null;
  score: number;
  eligible: boolean;
  selected: boolean;
  pinDiameterMm: number;
  rejectionReasons: string[];
}

export interface ProductionGateResult {
  blocking_reviews: number;
  blocking_drc_errors: number;
  unconfirmed_layers: number;
  missing_required_data: number;
  geometry_validation_errors: number;
  production_ready: boolean;
  blocking_reasons: string[];
}

export interface DrcOverrideRecord {
  issueId: string;
  operator: string;
  reason: string;
  timestamp: string;
  originalSeverity: string;
  geometrySha256?: string;
  status?: "active" | "expired" | "revoked";
}

export interface FixtureResult {
  id: string;
  pcb: {
    width: number;
    height: number;
  };
  fixture: {
    width: number;
    height: number;
    thickness: number;
    material: string;
  };
  locatingPins: number;
  clamps: number;
  keepoutRegions: number;
  solderWindows: number;
  springClips?: number;
  previewSvg?: string;
  issues: DesignIssue[];
  reviewItems?: ReviewItem[];
  locatingCandidates?: LocatingPinCandidate[];
  geometrySha256?: string;
  productionGate?: ProductionGateResult;
  drcOverrides?: DrcOverrideRecord[];
  algorithmVersion?: string;
  softwareVersion?: string;
  ruleProfileVersion?: string;
  status: "completed" | "review_required" | "failed";
}


