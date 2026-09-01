# V06_IMPLEMENTATION_REPORT

日期: 2026-09-01  
版本: 0.6.0 / fixture-engine-0.6.0 / rules 1.2.0

本轮把系统从 Semantic Fixture Engine 推到 Manufacturing Validation Engine。目标不是堆功能，而是让每一次生产几何变化可追踪、可复现、可对照人工 DXF。

## Implemented

- Geometry SHA 覆盖 body、sink、keepout、solder、pins、clamps、springs、handholds、rails、barriers、barrier holes、pressure relief、tooling/fiducials、PCB outline、pocket depth、影响加工的板厚参数。排序键为 centroid + area + WKB，不依赖 Python 对象顺序。
- Golden Validator：分 feature 的 IoU / Hausdorff / centroid / area% / perimeter% / hole position / hole diameter / count / unmatched；输出 `validation_report.json` + `validation_report.md` + overlay SVG。
- CASE-001 `case.json` 状态机（awaiting_input / awaiting_reference_dxf / ready / passed / failed / review_required）。**没有伪造 reference DXF。**
- `/validation` 仪表盘：案例列表、IoU/精度摘要、PASS/WARNING/FAIL、三栏 overlay（绿=一致，琥珀=仅生成，红=仅参考）。
- Wave direction-aware opening：`directionalOpeningEnabled` 默认 False；参数全部进 ProcessProfile。
- Pressure relief channels + DRC：`PRESSURE_RELIEF_COLLISION` / `PRESSURE_RELIEF_WEB_TOO_THIN` / `PRESSURE_RELIEF_OUT_OF_FIXTURE`。
- ProcessProfile ParameterDefinition（默认值/单位/描述/min/max/editable/category）；`GET /api/process-profile`；参数面板动态读取 Wave / Pressure Relief / Panel。
- Grid PanelModel：NxM 实例、各自 Transform2D、V-cut metadata、tooling/fiducial。
- Transform2D：translate / rotate / mirror / local_to_global / global_to_local。
- DRC 增强与统一字段：code / severity / message / geometry / sourceIds / recommendedAction。
- Fixture Manifest：版本、geometry SHA、输入哈希、DXF 哈希、参数、DRC、reviews、overrides。
- 10 次生成 SHA 相同。
- STRtree 用于 keepout↔solder 和邻近窗口扫描。
- Production Gate 未弱化：mandatory review 仍须工程师逐条处理；override 仍绑定 geometrySha256。

## Partially Implemented

- Golden Dataset：框架完整，但 CASE-001 仍无 PCB ZIP、无人工 DXF，因此没有真实 IoU。
- Panelization：只有 Grid。没有完整 mouse-bite 几何、没有从 Gerber 自动识别拼板。
- Overlay：有 SVG 差集着色；没有把完整 DXF 栅格化成三栏 CAD 视图。
- 性能：现有样本太小，STRtree 收益无法在真实 large Gerber 上证明。
- DXF 仍是 2D。口袋深度只进入 SHA / DRC / manifest，不下铣刀路。

## Not Implemented

- 真实客户 Gerber 验证
- 人工 reference DXF 入库
- CNC 试加工 / 实板 / 波峰现场
- KiCad IPC API
- 2.5D CAM / 3D fixture
- 把 LLM 接入几何（明确禁止，未做）

## Tests (this machine, 2026-09-01)

- pytest: **177 passed**
- vitest: **17 passed** / 5 files
- tsc --noEmit: **0 errors**
- npm run build: **Clean** (JS 379.88 kB, CSS 33.81 kB)

## Field validation counts

| 项 | 数量 |
|---|---:|
| 真实客户 Gerber | 0 |
| 人工 Reference DXF | 0 |
| CNC 试加工 | 0 |
| 实板装配 | 0 |
| 波峰焊现场 | 0 |

**不是生产就绪，不是 CNC 就绪。**
