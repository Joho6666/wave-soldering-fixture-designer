import JSZip from "jszip";
import { GerberLayer, GerberLayerType } from "../types/gerber";

/**
 * 启发式匹配 Gerber 文件类型与置信度
 */
export function classifyGerberFilename(filename: string): { type: GerberLayerType; confidence: number } {
  const lower = filename.toLowerCase();

  // 0. DXF 文件（优先判断文件格式，不是Gerber图层类型）
  if (lower.endsWith(".dxf")) {
    return { type: "board_outline", confidence: 0.75 };
  }

  // 1. 钻孔文件
  if (
    lower.endsWith(".drl") ||
    lower.endsWith(".drd") ||
    lower.endsWith(".nc") ||
    lower.endsWith(".ncd") ||
    lower.endsWith(".xln") ||
    lower.includes("drill") ||
    (lower.endsWith(".txt") && (lower.includes("drill") || lower.includes("hole") || lower.includes("drl") || lower.includes("roundhole") || lower.includes("slothole")))
  ) {
    return { type: "drill", confidence: 0.96 };
  }

  // 2. 板框 / 外形
  if (
    lower.endsWith(".gko") ||
    lower.endsWith(".gml") ||
    lower.endsWith(".rou") ||
    lower.endsWith(".cut") ||
    lower.includes("boardoutline") ||
    lower.includes("outline") ||
    lower.includes("profile")
  ) {
    return { type: "board_outline", confidence: 0.98 };
  }

  if (lower.endsWith(".gm1")) {
    return { type: "board_outline", confidence: 0.80 };
  }

  if (
    lower.endsWith(".gm2") ||
    lower.endsWith(".gm3") ||
    lower.includes("mech")
  ) {
    return { type: "board_outline", confidence: 0.60 };
  }

  // 3. 丝印顶层
  if (
    lower.endsWith(".gto") ||
    lower.endsWith(".gsp") ||
    lower.endsWith(".legend_top") ||
    lower.includes("topsilk") ||
    lower.includes("silktop") ||
    lower.includes("pos_top") ||
    lower.endsWith(".tsl")
  ) {
    return { type: "top_silkscreen", confidence: 0.92 };
  }

  // 4. 丝印底层
  if (
    lower.endsWith(".gbo") ||
    lower.endsWith(".gsb") ||
    lower.endsWith(".legend_bot") ||
    lower.includes("botsilk") ||
    lower.includes("silkbot") ||
    lower.includes("pos_bot") ||
    lower.endsWith(".bsl")
  ) {
    return { type: "bottom_silkscreen", confidence: 0.90 };
  }

  // 5. 阻焊顶层
  if (
    lower.endsWith(".gts") ||
    lower.endsWith(".sm_top") ||
    lower.includes("topmask") ||
    lower.includes("masktop") ||
    lower.endsWith(".st")
  ) {
    return { type: "top_soldermask", confidence: 0.93 };
  }

  // 6. 阻焊底层
  if (
    lower.endsWith(".gbs") ||
    lower.endsWith(".sm_bot") ||
    lower.includes("botmask") ||
    lower.includes("maskbot") ||
    lower.endsWith(".sb")
  ) {
    return { type: "bottom_soldermask", confidence: 0.89 };
  }

  // 7. 顶层铜箔
  if (
    lower.endsWith(".gtl") ||
    lower.endsWith(".l1") ||
    lower.endsWith(".top") ||
    lower.includes("copper_top")
  ) {
    return { type: "top_copper", confidence: 0.94 };
  }

  // 8. 底层铜箔
  if (
    lower.endsWith(".gbl") ||
    lower.endsWith(".l2") ||
    lower.endsWith(".bot") ||
    lower.includes("copper_bot")
  ) {
    return { type: "bottom_copper", confidence: 0.94 };
  }

  // 未知层
  return { type: "unknown", confidence: 0.45 };
}

export interface ZipAnalysisSummary {
  fileCount: number;
  gerberCount: number;
  drillCount: number;
  dxfCount: number;
  otherCount: number;
  layers: GerberLayer[];
  totalSizeBytes: number;
}

export async function analyzeZipFile(file: File): Promise<ZipAnalysisSummary> {
  const zip = new JSZip();
  const zipContent = await zip.loadAsync(file);

  const layers: GerberLayer[] = [];
  let drillCount = 0;
  let gerberCount = 0;
  let dxfCount = 0;
  let otherCount = 0;
  let totalSizeBytes = 0;

  const entries = Object.keys(zipContent.files);

  for (const filename of entries) {
    const entry = zipContent.files[filename];
    if (entry.dir || filename.startsWith("__MACOSX/") || filename.startsWith(".")) {
      continue;
    }

    const cleanName = filename.split("/").pop() || filename;
    const lower = cleanName.toLowerCase();
    
    // 先判断文件格式（用于统计计数）
    if (lower.endsWith(".dxf")) {
      dxfCount++;
    } else if (lower.endsWith(".drl") || lower.endsWith(".xln") || lower.includes("drill")) {
      drillCount++;
    } else if (
      lower.endsWith(".gbr") || 
      lower.endsWith(".ger") ||
      lower.endsWith(".gko") || lower.endsWith(".gm1") || lower.endsWith(".gm2") ||
      lower.endsWith(".gtl") || lower.endsWith(".gbl") ||
      lower.endsWith(".gto") || lower.endsWith(".gbo") ||
      lower.endsWith(".gts") || lower.endsWith(".gbs")
    ) {
      gerberCount++;
    } else {
      otherCount++;
    }

    // 再判断Gerber图层语义
    const { type, confidence } = classifyGerberFilename(cleanName);
    const isConfirmed = confidence >= 0.9 && type !== "unknown";

    layers.push({
      id: `layer-${layers.length + 1}`,
      filename: cleanName,
      type,
      confidence,
      confirmed: isConfirmed
    });

    totalSizeBytes += 1024;
  }

  return {
    fileCount: layers.length,
    gerberCount,
    drillCount,
    dxfCount,
    otherCount,
    layers,
    totalSizeBytes
  };
}
