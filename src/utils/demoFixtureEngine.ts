import { FixtureParameters, FixtureResult } from "../types/fixture";
import { PCBAnalysis } from "../types/gerber";
import { MOCK_DESIGN_ISSUES } from "../mocks/inspection";

export interface DemoGeometryData {
  svg: string;
  result: FixtureResult;
  analysis: PCBAnalysis;
}

/**
 * 纯前端高精度波峰焊治具几何生成引擎（用于无后端/静态托管演示）
 */
export function buildDemoFixture(
  parameters: FixtureParameters,
  manualPins: string[] = ["D1", "D2"],
  customRegions: Array<{ regionType: "keepout" | "solder"; x: number; y: number; width: number; height: number; label?: string }> = []
): DemoGeometryData {
  const pw = 180.0;
  const ph = 120.0;
  const sinkClr = parameters.sinkClearanceMm ?? 0.2;
  const step = parameters.fixtureSizeRoundStepMm ?? 5.0;
  const marginX = parameters.fixtureMarginXmm ?? 20.0;
  const marginY = parameters.fixtureMarginYmm ?? 30.0;
  const cornerR = parameters.fixtureCornerRadiusMm ?? 5.0;
  const filletR = parameters.filletRadiusMm ?? 1.85;
  const clampOffset = parameters.clampOffsetMm ?? 10.0;
  const clampDia = parameters.clampHoleDiameterMm ?? 3.4;
  const railW = parameters.railWidthMm ?? 5.0;
  const barrierW = parameters.solderBarrierWidthMm ?? 10.0;
  const springR = parameters.springClipRadiusMm ?? 2.45;
  const keepoutClr = parameters.keepoutClearanceMm ?? 0.7;
  const solderClr = parameters.solderClearanceMm ?? 3.0;

  // 沉板区尺寸
  const sw = pw + 2 * sinkClr;
  const sh = ph + 2 * sinkClr;

  // 治具外形尺寸（按 step 取整）
  const rawFw = sw + 2 * marginX;
  const rawFh = sh + 2 * marginY;
  const fw = Math.ceil(rawFw / step) * step;
  const fh = Math.ceil(rawFh / step) * step;

  // 居中偏移量
  const ox = (fw - pw) / 2;
  const oy = (fh - ph) / 2;
  const sox = (fw - sw) / 2;
  const soy = (fh - sh) / 2;

  // 钻孔与定位孔数据
  const candidateDrills = [
    { id: "D1", drillId: "D1", x: ox + 8, y: oy + 8, diameterMm: 3.2, plated: false, score: 9.5, selected: manualPins.includes("D1") || manualPins.includes("pin-cand-D1") },
    { id: "D2", drillId: "D2", x: ox + pw - 8, y: oy + ph - 8, diameterMm: 3.2, plated: false, score: 9.5, selected: manualPins.includes("D2") || manualPins.includes("pin-cand-D2") },
    { id: "D3", drillId: "D3", x: ox + 8, y: oy + ph - 8, diameterMm: 3.0, plated: true, score: 7.0, selected: manualPins.includes("D3") || manualPins.includes("pin-cand-D3") },
    { id: "D4", drillId: "D4", x: ox + pw - 8, y: oy + 8, diameterMm: 3.0, plated: true, score: 7.0, selected: manualPins.includes("D4") || manualPins.includes("pin-cand-D4") },
    { id: "D5", drillId: "D5", x: ox + pw / 2, y: oy + 10, diameterMm: 2.0, plated: true, score: 5.0, selected: false },
    { id: "D6", drillId: "D6", x: ox + pw / 2, y: oy + ph - 10, diameterMm: 2.0, plated: true, score: 5.0, selected: false },
  ];

  const activePins = candidateDrills.filter((d) => d.selected);
  if (activePins.length === 0) {
    candidateDrills[0].selected = true;
    candidateDrills[1].selected = true;
  }

  // 压扣孔位 (4处)
  const clamps = [
    { id: "clamp-1", x: sox - clampOffset, y: soy - clampOffset, diameter: clampDia },
    { id: "clamp-2", x: sox + sw + clampOffset, y: soy - clampOffset, diameter: clampDia },
    { id: "clamp-3", x: sox - clampOffset, y: soy + sh + clampOffset, diameter: clampDia },
    { id: "clamp-4", x: sox + sw + clampOffset, y: soy + sh + clampOffset, diameter: clampDia },
  ];

  // 挡锡条安装螺丝孔 (左右各3孔)
  const barrierHoles = [
    { id: "barrier-l1", x: barrierW / 2, y: fh * 0.2, diameter: 3.2 },
    { id: "barrier-l2", x: barrierW / 2, y: fh * 0.5, diameter: 3.2 },
    { id: "barrier-l3", x: barrierW / 2, y: fh * 0.8, diameter: 3.2 },
    { id: "barrier-r1", x: fw - barrierW / 2, y: fh * 0.2, diameter: 3.2 },
    { id: "barrier-r2", x: fw - barrierW / 2, y: fh * 0.5, diameter: 3.2 },
    { id: "barrier-r3", x: fw - barrierW / 2, y: fh * 0.8, diameter: 3.2 },
  ];

  // 弹簧卡孔
  const springClips = [
    { id: "spring-1", x: ox + 25, y: oy + 20, diameter: springR * 2 },
    { id: "spring-2", x: ox + pw - 25, y: oy + 20, diameter: springR * 2 },
    { id: "spring-3", x: ox + 25, y: oy + ph - 20, diameter: springR * 2 },
    { id: "spring-4", x: ox + pw - 25, y: oy + ph - 20, diameter: springR * 2 },
  ];

  // TOP 上锡开窗
  const solderWindows = [
    { id: "solder-1", x: ox + 35, y: oy + 25, w: 40 + solderClr, h: 12 + solderClr },
    { id: "solder-2", x: ox + 105, y: oy + 25, w: 50 + solderClr, h: 15 + solderClr },
    { id: "solder-3", x: ox + 40, y: oy + 75, w: 60 + solderClr, h: 14 + solderClr },
    { id: "solder-4", x: ox + 120, y: oy + 75, w: 35 + solderClr, h: 20 + solderClr },
  ];

  // BOT 避位区
  const keepouts = [
    { id: "keepout-1", x: ox + 15, y: oy + 45, w: 25 + keepoutClr * 2, h: 20 + keepoutClr * 2 },
    { id: "keepout-2", x: ox + 50, y: oy + 45, w: 30 + keepoutClr * 2, h: 18 + keepoutClr * 2 },
    { id: "keepout-3", x: ox + 90, y: oy + 45, w: 40 + keepoutClr * 2, h: 22 + keepoutClr * 2 },
    { id: "keepout-4", x: ox + 140, y: oy + 45, w: 25 + keepoutClr * 2, h: 20 + keepoutClr * 2 },
    { id: "keepout-5", x: ox + 20, y: oy + 95, w: 35 + keepoutClr * 2, h: 15 + keepoutClr * 2 },
    { id: "keepout-6", x: ox + 70, y: oy + 98, w: 28 + keepoutClr * 2, h: 14 + keepoutClr * 2 },
    { id: "keepout-7", x: ox + 110, y: oy + 100, w: 45 + keepoutClr * 2, h: 12 + keepoutClr * 2 },
    { id: "keepout-8", x: ox + 145, y: oy + 10, w: 22 + keepoutClr * 2, h: 10 + keepoutClr * 2 },
  ];

  // 注入自定义开窗/避位区
  customRegions.forEach((cr, idx) => {
    if (cr.regionType === "keepout") {
      keepouts.push({ id: `custom-keepout-${idx + 1}`, x: cr.x, y: cr.y, w: cr.width, h: cr.height });
    } else {
      solderWindows.push({ id: `custom-solder-${idx + 1}`, x: cr.x, y: cr.y, w: cr.width, h: cr.height });
    }
  });

  // SVG 构建
  const pad = 25;
  const vbx = -pad;
  const vby = -pad;
  const vbw = fw + 2 * pad;
  const vbh = fh + 2 * pad;

  const svgParts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vbx} ${vby} ${vbw} ${vbh}" width="${vbw}" height="${vbh}">`,
    `<defs>`,
    `  <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="#1f2937" stroke-width="0.3"/></pattern>`,
    `</defs>`,
    `<rect x="${vbx}" y="${vby}" width="${vbw}" height="${vbh}" fill="#0f172a"/>`,
    `<rect x="0" y="0" width="${fw}" height="${fh}" fill="url(#grid)"/>`,
  ];

  // 1. FIXTURE_OUTLINE
  svgParts.push(`<g id="fixture-outline"><rect x="0" y="0" width="${fw}" height="${fh}" rx="${cornerR}" ry="${cornerR}" fill="none" stroke="#1e90ff" stroke-width="1.0" opacity="0.95"/></g>`);

  // 2. PCB_OUTLINE
  svgParts.push(`<g id="pcb-outline"><rect x="${ox}" y="${oy}" width="${pw}" height="${ph}" fill="none" stroke="#2e8b57" stroke-width="0.8" stroke-dasharray="4 2"/></g>`);

  // 3. SINK_REGION (含 R1.85 清角)
  svgParts.push(`<g id="sink-region"><rect x="${sox}" y="${soy}" width="${sw}" height="${sh}" rx="${filletR}" ry="${filletR}" fill="rgba(147, 112, 219, 0.08)" stroke="#9370db" stroke-width="0.8"/></g>`);

  // 4. RAILS (上下 5mm 导轨)
  svgParts.push(`<g id="rails">`);
  svgParts.push(`<rect x="0" y="0" width="${fw}" height="${railW}" fill="rgba(120, 144, 156, 0.2)" stroke="#78909c" stroke-width="0.5"/>`);
  svgParts.push(`<rect x="0" y="${fh - railW}" width="${fw}" height="${railW}" fill="rgba(120, 144, 156, 0.2)" stroke="#78909c" stroke-width="0.5"/>`);
  svgParts.push(`</g>`);

  // 5. SOLDER_BARRIERS (左右 10mm 挡锡条)
  svgParts.push(`<g id="solder-barriers">`);
  svgParts.push(`<rect x="0" y="${railW}" width="${barrierW}" height="${fh - 2 * railW}" fill="rgba(255, 110, 64, 0.15)" stroke="#ff6e40" stroke-width="0.6"/>`);
  svgParts.push(`<rect x="${fw - barrierW}" y="${railW}" width="${barrierW}" height="${fh - 2 * railW}" fill="rgba(255, 110, 64, 0.15)" stroke="#ff6e40" stroke-width="0.6"/>`);
  svgParts.push(`</g>`);

  // 6. BARRIER_MOUNT_HOLES
  svgParts.push(`<g id="barrier-mount-holes">`);
  barrierHoles.forEach((h) => {
    svgParts.push(`<circle id="${h.id}" cx="${h.x}" cy="${h.y}" r="${h.diameter / 2}" fill="none" stroke="#ffab40" stroke-width="0.5"/>`);
  });
  svgParts.push(`</g>`);

  // 7. HANDHOLDS (左右取手位 20x40mm)
  svgParts.push(`<g id="handholds">`);
  svgParts.push(`<rect x="${-1}" y="${fh / 2 - 20}" width="20" height="40" rx="3" fill="rgba(171, 71, 188, 0.2)" stroke="#ab47bc" stroke-width="0.7"/>`);
  svgParts.push(`<rect x="${fw - 19}" y="${fh / 2 - 20}" width="20" height="40" rx="3" fill="rgba(171, 71, 188, 0.2)" stroke="#ab47bc" stroke-width="0.7"/>`);
  svgParts.push(`</g>`);

  // 8. CLAMPS (压扣孔)
  svgParts.push(`<g id="clamps">`);
  clamps.forEach((c) => {
    svgParts.push(`<circle id="${c.id}" cx="${c.x}" cy="${c.y}" r="${c.diameter / 2}" fill="none" stroke="#a9a9a9" stroke-width="0.6"/>`);
    svgParts.push(`<circle cx="${c.x}" cy="${c.y}" r="${c.diameter / 2 + 3.0}" fill="none" stroke="#a9a9a9" stroke-width="0.4" stroke-dasharray="2 2"/>`);
  });
  svgParts.push(`</g>`);

  // 9. LOCATING PINS & CANDIDATES
  svgParts.push(`<g id="locating-pin-candidates">`);
  candidateDrills.forEach((c) => {
    svgParts.push(`<circle id="pin-cand-${c.drillId}" cx="${c.x}" cy="${c.y}" r="${c.diameterMm / 2}" fill="none" stroke="#ff9800" stroke-width="0.5" stroke-dasharray="2 1"><title>Drill ${c.drillId} Ø${c.diameterMm}mm</title></circle>`);
  });
  svgParts.push(`</g>`);

  svgParts.push(`<g id="locating-pins">`);
  candidateDrills.filter((c) => c.selected).forEach((c) => {
    const pinR = (c.diameterMm - 0.1) / 2;
    svgParts.push(`<circle id="pin-${c.drillId}" cx="${c.x}" cy="${c.y}" r="${pinR}" fill="rgba(0, 255, 255, 0.3)" stroke="#00ffff" stroke-width="0.8"><title>Locating Pin ${c.drillId} Ø${(pinR * 2).toFixed(2)}mm</title></circle>`);
  });
  svgParts.push(`</g>`);

  // 10. SPRING_CLIPS (前挡板弹簧卡孔)
  svgParts.push(`<g id="spring-clips">`);
  springClips.forEach((sc) => {
    svgParts.push(`<circle id="${sc.id}" cx="${sc.x}" cy="${sc.y}" r="${sc.diameter / 2}" fill="none" stroke="#00bcd4" stroke-width="0.6"/>`);
  });
  svgParts.push(`</g>`);

  // 11. TOP_SOLDER_WINDOW
  svgParts.push(`<g id="solder-top">`);
  solderWindows.forEach((swin) => {
    svgParts.push(`<rect id="${swin.id}" x="${swin.x}" y="${swin.y}" width="${swin.w}" height="${swin.h}" rx="2" fill="rgba(255, 140, 0, 0.2)" stroke="#ff8c00" stroke-width="0.7"/>`);
  });
  svgParts.push(`</g>`);

  // 12. BOT_KEEPOUT
  svgParts.push(`<g id="keepout-bot">`);
  keepouts.forEach((k) => {
    svgParts.push(`<rect id="${k.id}" x="${k.x}" y="${k.y}" width="${k.w}" height="${k.h}" rx="1.5" fill="rgba(50, 205, 50, 0.15)" stroke="#32cd32" stroke-width="0.6"/>`);
  });
  svgParts.push(`</g>`);

  // 13. PCB DRILL HOLES (326 真实孔阵列分布模拟)
  svgParts.push(`<g id="pcb-drill">`);
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 20; c++) {
      const hx = ox + 15 + c * 8;
      const hy = oy + 12 + r * 13;
      if (hx < ox + pw - 10 && hy < oy + ph - 10) {
        svgParts.push(`<circle cx="${hx}" cy="${hy}" r="0.45" fill="#48cae4" opacity="0.6"/>`);
      }
    }
  }
  svgParts.push(`</g>`);

  // 14. DIMENSIONS (尺寸标注)
  svgParts.push(`<g id="dimensions">`);
  // 总长标注
  svgParts.push(`<line x1="0" y1="${fh + 12}" x2="${fw}" y2="${fh + 12}" stroke="#849396" stroke-width="0.5"/>`);
  svgParts.push(`<line x1="0" y1="${fh + 5}" x2="0" y2="${fh + 15}" stroke="#849396" stroke-width="0.5"/>`);
  svgParts.push(`<line x1="${fw}" y1="${fh + 5}" x2="${fw}" y2="${fh + 15}" stroke="#849396" stroke-width="0.5"/>`);
  svgParts.push(`<text x="${fw / 2}" y="${fh + 10}" fill="#849396" font-size="6" font-family="monospace" text-anchor="middle">${fw.toFixed(1)} mm</text>`);

  // 总宽标注
  svgParts.push(`<line x1="${fw + 12}" y1="0" x2="${fw + 12}" y2="${fh}" stroke="#849396" stroke-width="0.5"/>`);
  svgParts.push(`<line x1="${fw + 5}" y1="0" x2="${fw + 15}" y2="0" stroke="#849396" stroke-width="0.5"/>`);
  svgParts.push(`<line x1="${fw + 5}" y1="${fh}" x2="${fw + 15}" y2="${fh}" stroke="#849396" stroke-width="0.5"/>`);
  svgParts.push(`<text x="${fw + 10}" y="${fh / 2}" fill="#849396" font-size="6" font-family="monospace" text-anchor="middle" transform="rotate(90 ${fw + 10} ${fh / 2})">${fh.toFixed(1)} mm</text>`);
  svgParts.push(`</g>`);

  svgParts.push(`</svg>`);

  const svg = svgParts.join("\n");

  const result: FixtureResult = {
    id: "DEMO-WSJ-2026",
    pcb: { width: pw, height: ph },
    fixture: { width: fw, height: fh, thickness: 6.0, material: "合成石 (Durostone / FR4)" },
    locatingPins: activePins.length,
    clamps: clamps.length,
    keepoutRegions: keepouts.length,
    solderWindows: solderWindows.length,
    springClips: springClips.length,
    previewSvg: svg,
    issues: MOCK_DESIGN_ISSUES,
    reviewItems: [
      { id: "review-top-solder-1", type: "top_solder_region", status: "accepted", title: "TOP J1 主排针透锡槽确认", description: "预留 3.0mm 透锡间距", confidence: 0.95, mandatory: false },
      { id: "review-bot-keepout-1", type: "bot_keepout_region", status: "pending", title: "BOT U2 芯片避位区确认", description: "检测到底层 SOP-8 贴片，已预留 0.7mm 安全间距", confidence: 0.82, mandatory: true },
      { id: "review-spring-clip-1", type: "front_panel_clip", status: "accepted", title: "前挡板定位弹簧卡孔", description: "R2.45mm 紧固孔位", confidence: 0.98, mandatory: false },
    ],
    locatingCandidates: candidateDrills.map((c) => ({
      id: `pin-cand-${c.drillId}`,
      drillId: c.drillId,
      x: c.x,
      y: c.y,
      diameterMm: c.diameterMm,
      plated: c.plated,
      score: c.score,
      eligible: true,
      selected: c.selected,
      pinDiameterMm: c.diameterMm - 0.1,
      rejectionReasons: [],
    })),
    productionGate: {
      blocking_reviews: 1,
      blocking_drc_errors: 1,
      unconfirmed_layers: 0,
      missing_required_data: 0,
      geometry_validation_errors: 0,
      production_ready: false,
      blocking_reasons: ["1 个强制审核项待确认", "1 个 DRC blocking 待解决/放行"],
    },
    algorithmVersion: "fixture-engine-0.4.0 (Client Demo)",
    softwareVersion: "0.4.0",
    ruleProfileVersion: "1.0.0",
    status: "review_required",
  };

  const analysis: PCBAnalysis = {
    width: pw,
    height: ph,
    fileCount: 8,
    holeCount: 326,
    outlineClosed: true,
    outlineAreaMm2: pw * ph,
    layers: [
      { id: "layer-1", filename: "gerber_top_copper.gtl", type: "top_copper", confidence: 0.98, confirmed: true },
      { id: "layer-2", filename: "gerber_bot_copper.gbl", type: "bottom_copper", confidence: 0.98, confirmed: true },
      { id: "layer-3", filename: "gerber_top_soldermask.gts", type: "top_soldermask", confidence: 0.98, confirmed: true },
      { id: "layer-4", filename: "gerber_bot_soldermask.gbs", type: "bottom_soldermask", confidence: 0.98, confirmed: true },
      { id: "layer-5", filename: "gerber_top_silkscreen.gto", type: "top_silkscreen", confidence: 0.98, confirmed: true },
      { id: "layer-6", filename: "gerber_bot_silkscreen.gbo", type: "bottom_silkscreen", confidence: 0.98, confirmed: true },
      { id: "layer-7", filename: "gerber_board_outline.gko", type: "board_outline", confidence: 0.99, confirmed: true },
      { id: "layer-8", filename: "drill_holes.drl", type: "drill", confidence: 1.0, confirmed: true },
    ],
  };

  return { svg, result, analysis };
}
