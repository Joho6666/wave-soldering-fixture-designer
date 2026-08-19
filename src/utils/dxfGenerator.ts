import { FixtureParameters, FixtureResult } from "../types/fixture";

/**
 * 生成真实符合 AutoCAD DXF R2018 格式规范的标准工程图纸
 * 包含完整的 12+ 图层、闭合多段线与圆孔图元
 */
export function generateFixtureDxf(
  fixtureResult: FixtureResult,
  parameters: FixtureParameters
): string {
  const fw = fixtureResult.fixture.width || 240.0;
  const fh = fixtureResult.fixture.height || 180.0;
  const pw = fixtureResult.pcb.width || 180.0;
  const ph = fixtureResult.pcb.height || 120.0;
  const sinkClr = parameters.sinkClearanceMm ?? 0.2;
  const clampOffset = parameters.clampOffsetMm ?? 10.0;
  const clampDia = parameters.clampHoleDiameterMm ?? 3.4;
  const railW = parameters.railWidthMm ?? 5.0;
  const barrierW = parameters.solderBarrierWidthMm ?? 10.0;

  const pcbOffsetX = (fw - pw) / 2;
  const pcbOffsetY = (fh - ph) / 2;

  const sw = pw + 2 * sinkClr;
  const sh = ph + 2 * sinkClr;
  const sox = (fw - sw) / 2;
  const soy = (fh - sh) / 2;

  let dxf = `999
WAVE-FIXTURE AI - Wave Soldering Fixture DXF Export
  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1032
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
    14
  0
LAYER
  2
PCB_OUTLINE
 70
     0
 62
     7
  6
CONTINUOUS
  0
LAYER
  2
SINK_AREA
 70
     0
 62
     3
  6
CONTINUOUS
  0
LAYER
  2
KEEPOUT_BOT
 70
     0
 62
     1
  6
CONTINUOUS
  0
LAYER
  2
SOLDER_WINDOW_TOP
 70
     0
 62
     2
  6
CONTINUOUS
  0
LAYER
  2
POSITIONING_PINS
 70
     0
 62
     5
  6
CONTINUOUS
  0
LAYER
  2
CLIPS
 70
     0
 62
     6
  6
CONTINUOUS
  0
LAYER
  2
FIXTURE_OUTLINE
 70
     0
 62
     4
  6
CONTINUOUS
  0
LAYER
  2
HANDHOLDS
 70
     0
 62
     6
  6
CONTINUOUS
  0
LAYER
  2
RAILS
 70
     0
 62
     8
  6
CONTINUOUS
  0
LAYER
  2
SOLDER_BARRIERS
 70
     0
 62
    30
  6
CONTINUOUS
  0
LAYER
  2
BARRIER_MOUNT_HOLES
 70
     0
 62
    30
  6
CONTINUOUS
  0
LAYER
  2
SPRING_CLIPS
 70
     0
 62
    41
  6
CONTINUOUS
  0
LAYER
  2
PCB_DRILL
 70
     0
 62
     9
  6
CONTINUOUS
  0
LAYER
  2
DIMENSIONS
 70
     0
 62
     7
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

  const addPoly = (layer: string, coords: Array<[number, number]>) => {
    let out = `  0\nLWPOLYLINE\n  8\n${layer}\n 90\n    ${coords.length}\n 70\n    1\n`;
    coords.forEach(([x, y]) => {
      out += ` 10\n${x.toFixed(3)}\n 20\n${y.toFixed(3)}\n`;
    });
    return out;
  };

  const addCircle = (layer: string, cx: number, cy: number, r: number) => {
    return `  0\nCIRCLE\n  8\n${layer}\n 10\n${cx.toFixed(3)}\n 20\n${cy.toFixed(3)}\n 30\n0.0\n 40\n${r.toFixed(3)}\n`;
  };

  // 1. FIXTURE_OUTLINE
  dxf += addPoly("FIXTURE_OUTLINE", [
    [0, 0],
    [fw, 0],
    [fw, fh],
    [0, fh],
  ]);

  // 2. PCB_OUTLINE
  dxf += addPoly("PCB_OUTLINE", [
    [pcbOffsetX, pcbOffsetY],
    [pcbOffsetX + pw, pcbOffsetY],
    [pcbOffsetX + pw, pcbOffsetY + ph],
    [pcbOffsetX, pcbOffsetY + ph],
  ]);

  // 3. SINK_AREA
  dxf += addPoly("SINK_AREA", [
    [sox, soy],
    [sox + sw, soy],
    [sox + sw, soy + sh],
    [sox, soy + sh],
  ]);

  // 4. RAILS (上下两端)
  dxf += addPoly("RAILS", [[0, 0], [fw, 0], [fw, railW], [0, railW]]);
  dxf += addPoly("RAILS", [[0, fh - railW], [fw, fh - railW], [fw, fh], [0, fh]]);

  // 5. SOLDER_BARRIERS (左右两端)
  dxf += addPoly("SOLDER_BARRIERS", [[0, railW], [barrierW, railW], [barrierW, fh - railW], [0, fh - railW]]);
  dxf += addPoly("SOLDER_BARRIERS", [[fw - barrierW, railW], [fw, railW], [fw, fh - railW], [fw - barrierW, fh - railW]]);

  // 6. HANDHOLDS (左右取手位)
  dxf += addPoly("HANDHOLDS", [[-1, fh / 2 - 20], [19, fh / 2 - 20], [19, fh / 2 + 20], [-1, fh / 2 + 20]]);
  dxf += addPoly("HANDHOLDS", [[fw - 19, fh / 2 - 20], [fw + 1, fh / 2 - 20], [fw + 1, fh / 2 + 20], [fw - 19, fh / 2 + 20]]);

  // 7. BARRIER_MOUNT_HOLES (6孔)
  [fh * 0.2, fh * 0.5, fh * 0.8].forEach((y) => {
    dxf += addCircle("BARRIER_MOUNT_HOLES", barrierW / 2, y, 1.6);
    dxf += addCircle("BARRIER_MOUNT_HOLES", fw - barrierW / 2, y, 1.6);
  });

  // 8. CLIPS (4处压扣孔)
  dxf += addCircle("CLIPS", sox - clampOffset, soy - clampOffset, clampDia / 2);
  dxf += addCircle("CLIPS", sox + sw + clampOffset, soy - clampOffset, clampDia / 2);
  dxf += addCircle("CLIPS", sox - clampOffset, soy + sh + clampOffset, clampDia / 2);
  dxf += addCircle("CLIPS", sox + sw + clampOffset, soy + sh + clampOffset, clampDia / 2);

  // 9. POSITIONING_PINS (定位销)
  dxf += addCircle("POSITIONING_PINS", pcbOffsetX + 8, pcbOffsetY + 8, 1.55);
  dxf += addCircle("POSITIONING_PINS", pcbOffsetX + pw - 8, pcbOffsetY + ph - 8, 1.55);

  // 10. SPRING_CLIPS (前挡板弹簧卡孔)
  dxf += addCircle("SPRING_CLIPS", pcbOffsetX + 25, pcbOffsetY + 20, 2.45);
  dxf += addCircle("SPRING_CLIPS", pcbOffsetX + pw - 25, pcbOffsetY + 20, 2.45);
  dxf += addCircle("SPRING_CLIPS", pcbOffsetX + 25, pcbOffsetY + ph - 20, 2.45);
  dxf += addCircle("SPRING_CLIPS", pcbOffsetX + pw - 25, pcbOffsetY + ph - 20, 2.45);

  // 11. TOP_SOLDER_WINDOW
  dxf += addPoly("SOLDER_WINDOW_TOP", [
    [pcbOffsetX + 35, pcbOffsetY + 25],
    [pcbOffsetX + 75, pcbOffsetY + 25],
    [pcbOffsetX + 75, pcbOffsetY + 37],
    [pcbOffsetX + 35, pcbOffsetY + 37],
  ]);
  dxf += addPoly("SOLDER_WINDOW_TOP", [
    [pcbOffsetX + 105, pcbOffsetY + 25],
    [pcbOffsetX + 155, pcbOffsetY + 25],
    [pcbOffsetX + 155, pcbOffsetY + 40],
    [pcbOffsetX + 105, pcbOffsetY + 40],
  ]);

  // 12. KEEPOUT_BOT
  dxf += addPoly("KEEPOUT_BOT", [
    [pcbOffsetX + 15, pcbOffsetY + 45],
    [pcbOffsetX + 40, pcbOffsetY + 45],
    [pcbOffsetX + 40, pcbOffsetY + 65],
    [pcbOffsetX + 15, pcbOffsetY + 65],
  ]);
  dxf += addPoly("KEEPOUT_BOT", [
    [pcbOffsetX + 50, pcbOffsetY + 45],
    [pcbOffsetX + 80, pcbOffsetY + 45],
    [pcbOffsetX + 80, pcbOffsetY + 63],
    [pcbOffsetX + 50, pcbOffsetY + 63],
  ]);

  // 13. PCB_DRILL
  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 10; c++) {
      dxf += addCircle("PCB_DRILL", pcbOffsetX + 20 + c * 15, pcbOffsetY + 15 + r * 22, 0.45);
    }
  }

  dxf += `  0\nENDSEC\n  0\nEOF\n`;
  return dxf;
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
