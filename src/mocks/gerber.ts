import { GerberLayer, PCBAnalysis } from "../types/gerber";

export const MOCK_NORMAL_GERBER_LAYERS: GerberLayer[] = [
  { id: "layer-1", filename: "320-WSJ.GM1", type: "board_outline", confidence: 0.82, confirmed: false },
  { id: "layer-2", filename: "320-WSJ.GTL", type: "top_copper", confidence: 0.94, confirmed: true },
  { id: "layer-3", filename: "320-WSJ.GBL", type: "bottom_copper", confidence: 0.94, confirmed: true },
  { id: "layer-4", filename: "320-WSJ.GTO", type: "top_silkscreen", confidence: 0.90, confirmed: true },
  { id: "layer-5", filename: "320-WSJ.GBO", type: "bottom_silkscreen", confidence: 0.85, confirmed: false },
  { id: "layer-6", filename: "320-WSJ.GTS", type: "top_soldermask", confidence: 0.92, confirmed: true },
  { id: "layer-7", filename: "320-WSJ.GBS", type: "bottom_soldermask", confidence: 0.88, confirmed: false },
  { id: "layer-8", filename: "320-WSJ.DRL", type: "drill", confidence: 0.98, confirmed: true },
  { id: "layer-9", filename: "320-WSJ.GKO", type: "board_outline", confidence: 0.95, confirmed: true },
  { id: "layer-10", filename: "320-WSJ.MECH2", type: "unknown", confidence: 0.50, confirmed: false },
  { id: "layer-11", filename: "320-WSJ-TOP-PASTE.GTP", type: "unknown", confidence: 0.60, confirmed: false },
  { id: "layer-12", filename: "320-WSJ-BOT-PASTE.GBP", type: "unknown", confidence: 0.60, confirmed: false },
];

export const MOCK_NORMAL_PCB_ANALYSIS: PCBAnalysis = {
  width: 180.0,
  height: 120.0,
  fileCount: 18,
  holeCount: 326,
  pthCount: 281,
  npthCount: 45,
  smdCount: 142,
  outlineClosed: true,
  outlineAreaMm2: 21600,
  layers: MOCK_NORMAL_GERBER_LAYERS
};

export const MOCK_ERROR_GERBER_LAYERS: GerberLayer[] = [
  { id: "layer-e1", filename: "DEMO_ERR.GTL", type: "top_copper", confidence: 0.92, confirmed: true },
  { id: "layer-e2", filename: "DEMO_ERR.GBL", type: "bottom_copper", confidence: 0.92, confirmed: true },
  { id: "layer-e3", filename: "DEMO_ERR.GTO", type: "top_silkscreen", confidence: 0.90, confirmed: true },
  { id: "layer-e4", filename: "DEMO_ERR.GTS", type: "top_soldermask", confidence: 0.90, confirmed: true },
  { id: "layer-e5", filename: "UNKNOWN_OUTLINE.RAW", type: "unknown", confidence: 0.35, confirmed: false },
];

export const MOCK_ERROR_PCB_ANALYSIS: PCBAnalysis = {
  width: 0,
  height: 0,
  fileCount: 5,
  holeCount: 0,
  outlineClosed: false,
  outlineAreaMm2: 0,
  layers: MOCK_ERROR_GERBER_LAYERS
};
