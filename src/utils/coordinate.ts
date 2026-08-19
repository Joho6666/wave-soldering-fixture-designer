/**
 * 坐标映射工具（已废弃 - 仅供 Demo 演示使用）
 * 真实模式下请使用 SVG 元素 getScreenCTM().inverse() 直接映射到物理 mm viewBox
 * @deprecated 仅用于固定尺寸的纯前端 Demo 模式
 */

export interface CadOriginConfig {
  originX: number; // SVG 画布上对应 0,0 mm 的 X 像素
  originY: number; // SVG 画布上对应 0,0 mm 的 Y 像素
  scale: number;   // 1 mm 对应多少 SVG 像素 (如 2.0 px/mm)
}

export const DEFAULT_CAD_CONFIG: CadOriginConfig = {
  originX: 90,
  originY: 380,
  scale: 1.75
};

/**
 * 将 SVG 坐标转换为真实工程坐标 (mm)
 * @deprecated 仅用于 Demo 模式，正式流程使用 SVG viewBox 坐标系
 */
export function svgToCadMm(
  svgX: number,
  svgY: number,
  config: CadOriginConfig = DEFAULT_CAD_CONFIG
): { x: number; y: number } {
  const mmX = (svgX - config.originX) / config.scale;
  const mmY = (config.originY - svgY) / config.scale;
  return {
    x: Number(Math.max(0, mmX).toFixed(2)),
    y: Number(Math.max(0, mmY).toFixed(2))
  };
}

/**
 * 将工程坐标 (mm) 转换为 SVG 坐标
 * @deprecated 仅用于 Demo 模式，正式流程使用 SVG viewBox 坐标系
 */
export function cadMmToSvg(
  mmX: number,
  mmY: number,
  config: CadOriginConfig = DEFAULT_CAD_CONFIG
): { x: number; y: number } {
  return {
    x: config.originX + mmX * config.scale,
    y: config.originY - mmY * config.scale
  };
}
