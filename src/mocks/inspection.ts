import { DesignIssue } from "../types/inspection";

export const MOCK_DESIGN_ISSUES: DesignIssue[] = [
  {
    id: "issue-01",
    type: "clearance",
    title: "安全间距不足",
    description: "上锡区 #03 与 BOT 避位区间距不足",
    severity: "warning",
    currentValue: 0.62,
    requiredValue: 0.70,
    unit: "mm",
    confirmed: false,
    target: {
      layerId: "layer-drc-overlay",
      objectId: "drc-area-03",
      x: 145.0, // mm in CAD system
      y: 42.0,  // mm in CAD system
      width: 48,
      height: 36
    }
  },
  {
    id: "issue-02",
    type: "outline",
    title: "外形尺寸验证",
    description: "板框公差符合标准 (±0.10mm)",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-03",
    type: "pin_clash",
    title: "定位孔干涉检查",
    description: "4 处定位销孔未与走线/焊盘发生干涉",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-04",
    type: "solder_window",
    title: "开窗完整性",
    description: "12/12 处插件焊盘上锡窗口均已完全暴露",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-05",
    type: "rail_margin",
    title: "轨道夹持边距",
    description: "两侧传送轨道夹持边宽 5.10mm (要求 ≥5.00mm)",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-06",
    type: "flow_angle",
    title: "波峰流向角度",
    description: "主流向夹角 0°，排锡顺畅",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-07",
    type: "clamp_margin",
    title: "旋转压扣干涉",
    description: "4 处旋转压扣与高器件保持 3.2mm 安全间距",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-08",
    type: "counterbore_depth",
    title: "沉板台阶深度",
    description: "沉板台阶深度 1.60mm (PCB 厚度 1.60mm)",
    severity: "info",
    confirmed: true
  },
  {
    id: "issue-09",
    type: "solder_barrier",
    title: "防锡桥挡锡条",
    description: "密集引脚排针区域已生成 1.5mm 钛合金挡锡条",
    severity: "info",
    confirmed: true
  }
];
