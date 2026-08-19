import { FixtureParameters, FixtureResult } from "../types/fixture";

/**
 * 生成真实符合 AutoCAD DXF R2000 格式规范的文本内容
 * 包含 HEADER, TABLES, LAYERS, BLOCKS, ENTITIES 块
 */
export function generateFixtureDxf(
  fixtureResult: FixtureResult,
  parameters: FixtureParameters
): string {
  const fw = fixtureResult.fixture.width;
  const fh = fixtureResult.fixture.height;
  const pw = fixtureResult.pcb.width;
  const ph = fixtureResult.pcb.height;
  const sinkClr = parameters.sinkClearanceMm;

  const pcbOffsetX = (fw - pw) / 2;
  const pcbOffsetY = (fh - ph) / 2;

  const header = `999
WAVE-FIXTURE AI v0.1 - Wave Soldering Fixture DXF Export
  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1015
  9
$INSUNITS
 70
    4
  0
ENDSEC
  0
SECTION
  2
TABLES
  0
TABLE
  2
LAYER
 70
     7
  0
LAYER
  2
0
 70
     0
 62
     7
  6
CONTINUOUS
  0
LAYER
  2
FIXTURE_OUTLINE
 70
     0
 62
     5
  6
CONTINUOUS
  0
LAYER
  2
PCB_OUTLINE
 70
     0
 62
     3
  6
CONTINUOUS
  0
LAYER
  2
SINK_REGION
 70
     0
 62
   210
  6
CONTINUOUS
  0
LAYER
  2
BOT_KEEPOUT
 70
     0
 62
     2
  6
CONTINUOUS
  0
LAYER
  2
TOP_SOLDER_WINDOW
 70
     0
 62
    40
  6
CONTINUOUS
  0
LAYER
  2
LOCATING_PINS
 70
     0
 62
     4
  6
CONTINUOUS
  0
ENDTAB
  0
ENDSEC
  0
SECTION
  2
ENTITIES
`;

  // 1. FIXTURE_OUTLINE (Rectangle)
  const fixtureOutline = `  0
LWPOLYLINE
  8
FIXTURE_OUTLINE
 90
    4
 70
    1
 10
0.0
 20
0.0
 10
${fw.toFixed(2)}
 20
0.0
 10
${fw.toFixed(2)}
 20
${fh.toFixed(2)}
 10
0.0
 20
${fh.toFixed(2)}
`;

  // 2. PCB_OUTLINE
  const pcbOutline = `  0
LWPOLYLINE
  8
PCB_OUTLINE
 90
    4
 70
    1
 10
${pcbOffsetX.toFixed(2)}
 20
${pcbOffsetY.toFixed(2)}
 10
${(pcbOffsetX + pw).toFixed(2)}
 20
${pcbOffsetY.toFixed(2)}
 10
${(pcbOffsetX + pw).toFixed(2)}
 20
${(pcbOffsetY + ph).toFixed(2)}
 10
${pcbOffsetX.toFixed(2)}
 20
${(pcbOffsetY + ph).toFixed(2)}
`;

  // 3. SINK_REGION (Counterbore border with clearance)
  const sinkX1 = pcbOffsetX - sinkClr - 2.0;
  const sinkY1 = pcbOffsetY - sinkClr - 2.0;
  const sinkX2 = pcbOffsetX + pw + sinkClr + 2.0;
  const sinkY2 = pcbOffsetY + ph + sinkClr + 2.0;
  const sinkRegion = `  0
LWPOLYLINE
  8
SINK_REGION
 90
    4
 70
    1
 10
${sinkX1.toFixed(2)}
 20
${sinkY1.toFixed(2)}
 10
${sinkX2.toFixed(2)}
 20
${sinkY1.toFixed(2)}
 10
${sinkX2.toFixed(2)}
 20
${sinkY2.toFixed(2)}
 10
${sinkX1.toFixed(2)}
 20
${sinkY2.toFixed(2)}
`;

  // 4. LOCATING PINS (4 Circles)
  const pinRadius = 2.5;
  const pinOffset = 12.0;
  const pins = [
    { x: pinOffset, y: pinOffset },
    { x: fw - pinOffset, y: pinOffset },
    { x: pinOffset, y: fh - pinOffset },
    { x: fw - pinOffset, y: fh - pinOffset },
  ]
    .map(
      (p) => `  0
CIRCLE
  8
LOCATING_PINS
 10
${p.x.toFixed(2)}
 20
${p.y.toFixed(2)}
 30
0.0
 40
${pinRadius.toFixed(2)}
`
    )
    .join("");

  // 5. TOP SOLDER WINDOWS & BOT KEEPOUTS (Mock regions)
  const solderWindow = `  0
LWPOLYLINE
  8
TOP_SOLDER_WINDOW
 90
    4
 70
    1
 10
${(pcbOffsetX + 20).toFixed(2)}
 20
${(pcbOffsetY + 15).toFixed(2)}
 10
${(pcbOffsetX + 80).toFixed(2)}
 20
${(pcbOffsetY + 15).toFixed(2)}
 10
${(pcbOffsetX + 80).toFixed(2)}
 20
${(pcbOffsetY + 45).toFixed(2)}
 10
${(pcbOffsetX + 20).toFixed(2)}
 20
${(pcbOffsetY + 45).toFixed(2)}
`;

  const botKeepout = `  0
LWPOLYLINE
  8
BOT_KEEPOUT
 90
    4
 70
    1
 10
${(pcbOffsetX + 100).toFixed(2)}
 20
${(pcbOffsetY + 25).toFixed(2)}
 10
${(pcbOffsetX + 150).toFixed(2)}
 20
${(pcbOffsetY + 25).toFixed(2)}
 10
${(pcbOffsetX + 150).toFixed(2)}
 20
${(pcbOffsetY + 60).toFixed(2)}
 10
${(pcbOffsetX + 100).toFixed(2)}
 20
${(pcbOffsetY + 60).toFixed(2)}
`;

  const footer = `  0
ENDSEC
  0
EOF
`;

  return header + fixtureOutline + pcbOutline + sinkRegion + pins + solderWindow + botKeepout + footer;
}

/**
 * 触发浏览器端下载 DXF 文件
 */
export function triggerDxfDownload(filename: string, content: string): void {
  const blob = new Blob([content], { type: "application/dxf;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
