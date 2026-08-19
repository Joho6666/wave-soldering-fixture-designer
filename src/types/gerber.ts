export type GerberLayerType =
  | "board_outline"
  | "top_silkscreen"
  | "bottom_silkscreen"
  | "top_soldermask"
  | "bottom_soldermask"
  | "drill"
  | "top_copper"
  | "bottom_copper"
  | "unknown";

export interface GerberLayer {
  id: string;
  filename: string;
  type: GerberLayerType;
  confidence: number;
  reason?: string;
  confirmed: boolean;
  sizeBytes?: number;
}

export interface DrillHit {
  id: string;
  x: number;
  y: number;
  diameterMm: number;
  plated: boolean | null;
  toolId?: string | null;
  sourceLayerId: string;
  kind: "hole" | "slot";
}

export interface PCBAnalysis {
  width: number;
  height: number;
  fileCount: number;
  holeCount: number;
  pthCount?: number;
  npthCount?: number;
  smdCount?: number;
  outlineClosed: boolean;
  outlineAreaMm2: number;
  layers: GerberLayer[];
  holes?: DrillHit[];
  diagnostics?: string[];
  sourceSha256?: string;
  geometrySha256?: string;
}

export const LAYER_TYPE_NAMES: Record<GerberLayerType, string> = {
  board_outline: "PCB 外形层",
  top_silkscreen: "TOP 丝印",
  bottom_silkscreen: "BOT 丝印",
  top_soldermask: "TOP 阻焊",
  bottom_soldermask: "BOT 阻焊",
  drill: "钻孔层",
  top_copper: "TOP 铜层",
  bottom_copper: "BOT 铜层",
  unknown: "未识别"
};
