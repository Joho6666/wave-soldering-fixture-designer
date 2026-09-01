# V06_ENGINEERING_AUDIT

日期: 2026-09-01  
对照: CURRENT_STATE_AUDIT.md（改代码前）与本轮 diff。

## Geometry SHA

旧 `_geometry_digest` 只哈希 body / sink / pins / clamps / springs / keepouts / solders。  
现已覆盖所有会改变加工结果的实体。取手、轨道、挡锡条、口袋深度变化会使 SHA 变化，从而使旧 DRC override 失效。

风险残留：centroid 重合且面积相同的两个不同多边形理论上可能需要 WKB 才能区分；当前排序键包含 WKB。

## Golden validation

Comparator 原有 IoU/Hausdorff，但没有分 feature 判定、没有 case.json 状态、没有 overlay、没有工程师 DXF。  
现已补齐验证器与报告。CASE-001 仍 `awaiting_input`。禁止把空案例标成 passed。

## Wave / Relief / Panel

- 方向开窗默认关闭，v0.5 几何路径保持。
- 泄压槽默认关闭；开启后避开 PCB / pin / clamp / solder，并进入 DRC。
- Grid panel 复制每块板的 keepout/solder/pin 并保留 instance 坐标系；治具外框按拼板包络生成。不是 KiKit 级拼板。

## Gate

`complete_all_reviews` 仍拒绝 pending mandatory。  
Production DXF 仍要求：无 pending mandatory、无未 override 的 error/blocking DRC、图层已确认、override SHA 匹配。  
未自动 accept。

## 文档诚实性

ENGINEERING_AUDIT.md / NEXT_ROUND_AUDIT.md 仍描述 v0.4 过期问题，本轮未把它们改写成“已全部修复”的假报告。以 V06_ENGINEERING_AUDIT.md 和 CURRENT_STATE_AUDIT.md 为准。
