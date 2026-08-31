# ENGINEERING_STATUS.md - Semantic Fixture Engine v0.5

## 报告日期: 2026-08-31
## 软件版本: 0.5.0 / fixture-engine-0.5.0 / rules-1.1.0
## 版本源: backend/app/core/version.py

测试数量以 `VALIDATION_STATUS.md` 同一次执行为准，不要在其它文档另写一套数字。

---

## 1. 后端真实测试数量
- pytest: **150 passed**（以 VALIDATION_STATUS.md 为准）
- 本轮新增: PnP、BOM、语义 THT、口袋深度、上锡/定位销优化器、ProcessProfile

## 2. 前端真实测试数量
- tsc --noEmit: **0 errors**
- npm run build: **Clean** (377.22KB JS, 32.13KB CSS)
- vitest: **16 pass**（以 VALIDATION_STATUS.md 为准）

## 3. Production Gate 状态
- complete_all_reviews 不再自动接受 pending mandatory reviews (HTTP 409)
- 缺少关键层数据时生成 mandatory blocking review
- 4 种数据确认 Review 类型保持不变

## 4. Missing Data Blocking 状态
- 缺 GBO/GBS -> CONFIRM_NO_BOTTOM_SMD (mandatory=True)
- 缺 PTH 通孔 -> CONFIRM_NO_TOP_THT (mandatory=True)
- 缺 GTO -> CONFIRM_NO_SPRING_CLIP_REQUIRED (mandatory=True)
- 无钻孔 -> CONFIRM_NO_NPTH_AVAILABLE (mandatory=True)
- 低置信度几何区域: mandatory=False

## 5. DRC Override SHA 状态
- override 必须 geometrySha256 匹配当前几何才有效
- 参数变更/重新生成后旧 override 自动过期

## 6. Component Semantic Layer
- **真正驱动 FixtureGenerator**
- Keepout：PCBComponent(bottom) 优先，GBO∪GBS fallback
- Solder：ThroughHoleComponent 优先，greedy PTH fallback
- 每个自动区域带 sourceType / sourceIds / confidence

## 7. PnP / BOM
- ZIP 内 CSV/TXT PnP：mm/mil、Top/Bottom、中文与非标准列名
- BOM CSV：Height 写入 body_height_mm；缺失则为 None，不编造

## 8. Pocket Depth
- height + verticalClearance；无高度用 defaultPocketDepthMm
- palletThickness - pocketDepth < floor → POCKET_FLOOR_TOO_THIN (blocking)
- 本轮 DXF 仍为 2D

## 9. Golden Sample 数量
- 框架已就绪 (validation/ 目录)
- 0 个真实人工 DXF 对比案例
- CASE-001 仍 awaiting_manual_dxf
- production sample 上锡窗口期望 6 → 5（语义 THT 隔离，真实结果）

## 10. 当前是否适合直接 CNC 生产
- **否**：无真实客户 Gerber、无人工 DXF IoU、无 CNC/装配/波峰现场验证
- 适合进入工程师审核验证阶段

## 11. 是否 100% 断网可运行
- 核心管道（Gerber 解析、语义、治具、DRC、DXF/SVG）**是**，不依赖网络。
- UI 不再请求 Google Fonts / Material Symbols CDN，改用系统字体。本地未安装 Material Symbols 时图标会退化。
- AI 助手仍为 optional，需要外网。
