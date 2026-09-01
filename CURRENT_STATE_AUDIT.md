# CURRENT_STATE_AUDIT — Wave Soldering Fixture Designer

审计日期: 2026-09-01  
审计对象: `Joho6666/wave-soldering-fixture-designer` @ `4d0c0e7` (v0.5.0 Semantic Fixture Engine)  
原则: 以真实代码、测试与目录为准，不以文档口号为准。

---

## 1. 已实现能力

- Gerber RS-274X / X2 + Excellon 解析（Gerbonara），ZIP 安全解包。
- 可选 PnP/CPL、BOM CSV 解析；高度缺失保持 `None`，不编造。
- Semantic PCB Model：`PCBComponent` / `ThroughHoleComponent` / `FixtureRegion`，冲突写入 `semantic_conflicts`。
- 治具生成编排：沉板+清角、外框、取手、轨道、挡锡条及安装孔、压扣、弹簧卡。
- Keepout：语义 BOT 元件优先，GBO∪GBS fallback。
- Solder opening：THT 组件优先，greedy PTH fallback；GBS refinement。
- 定位销评分 + 最远两孔自动选择；支持人工指定。
- DRC 基础规则 + 语义规则（口袋底板、开窗过窄、跨距、数据冲突等）。
- Review 状态机：Accept/Reject/Modify；`complete_all_reviews` **不会**自动接受 pending mandatory（HTTP 409）。
- Production Gate：mandatory review + error/blocking DRC + 图层确认；override 必须 `geometrySha256` 匹配。
- Preview DXF 水印 vs Production DXF 409 锁定。
- DXF R2018 分层 + SVG 预览。
- 版本单一来源：`backend/app/core/version.py`（0.5.0 / fixture-engine-0.5.0 / rules 1.1.0）。
- CI workflow 文件存在。

## 2. 部分实现能力

- **Geometry SHA**：覆盖 body / sink / pins / clamps / springs / keepouts / solders。排序后 digest，重排稳定。
  - **未覆盖**：handholds、rails、solder_barriers、barrier mount holes、PCB outline、pocket depth、custom region 的非 keepout/solder 语义、以及会改变加工结果的参数。
  - 因此改变取手/轨道/挡锡条/口袋深度时，旧 DRC override **不会**自动失效。
- **Golden Dataset**：`validation/` 有 comparator 与 `run_all.py`；CASE-001 状态 `awaiting_manual_dxf`，无人工 DXF，无 IoU。目录仍是 `source/expected/`，不是本轮要求的 `input/reference/generated/report/case.json`。没有分 feature 的 PASS/WARNING/FAIL，没有 `validation_report.json`。
- **ProcessProfile**：制造数字已集中进 dataclass，但无 unit/min/max/editable/category 元数据；前端 `ParameterDrawer` 硬编码字段。
- **waveDirection / conveyorDirection**：已入库，**opening 算法未使用**。
- **DRC**：有壁厚、干涉、口袋底板；缺少本轮点名的 opening-to-edge/pin、pressure relief、panel、tooling、INVALID_GEOMETRY / SELF_INTERSECTION / ZERO_AREA_FEATURE。issue 结构缺 `geometry` / `sourceIds` / `recommendedAction` / `message` 字段（有 description）。
- **坐标系**：后端各模块各自做 bounds/offset；前端 `src/utils/coordinate.ts` 标明已废弃 Demo 工具。无统一 `Transform2D`。
- **拼板**：完全没有 PanelModel。
- **可观察性**：result_data 有版本与 SHA，无 `fixture_manifest.json`，无 DXF output hash，无 validation status。
- **性能**：solder merge 与 DRC 窗口对窗口为 O(n²)；无 STRtree。无 BENCHMARK.md。
- **ENGINEERING_AUDIT.md / NEXT_ROUND_AUDIT.md**：内容停留在 v0.4 问题清单，其中多项已被 v0.5 修复，文档过期。

## 3. 未实现能力

- Wave direction-aware solder opening profile。
- Pressure relief channels 及对应 DRC。
- Grid panel / V-cut / mouse bite / tooling / fiducial 语义。
- 统一 Transform2D（translate/rotate/mirror/local↔global）。
- Validation Dashboard（`/validation`）与 difference overlay。
- ParameterDefinition 动态前端。
- Fixture Manifest。
- 制造级几何 SHA 闭环（全实体）。
- CNC 2.5D / 3D fixture（明确超出本轮，DXF 仍为 2D）。

## 4. Mock / 占位实现

- 前端 `VITE_USE_MOCK_API=true` 才走 mock；默认真实 FastAPI。
- `src/utils/demoFixtureEngine.ts`：Demo 按钮用的客户端演示引擎，不进入生产 DXF 管道。
- CASE-001：占位 expected.json，**不是**黄金样本。
- OCR：`ENABLE_OCR` 可选，失败跳过；非制造核心。
- AI：解释/命令，不生成生产几何。

## 5. 技术债务

- `NEXT_ROUND_AUDIT.md` 仍声称 complete_all_reviews 自动 accept、override 不校验 SHA — **与当前代码不符**。
- `ENGINEERING_AUDIT.md` 仍把 Layer Confirm / Review / 挡锡安装孔标成 Partial — **与当前代码不符**。
- Geometry digest 用 centroid 排序；本轮将改为 centroid + area + WKB 的确定性键，避免重心重合时不稳定。
- `FixtureParameters` Pydantic 模型与 `ProcessProfile` 字段不完全同步。
- 无 react-router；App 按 jobStatus 切页，没有 `/validation`。
- DXF 仍 2D，口袋深度只挂在 region parameters 上。

## 6. 安全风险

- 上传 ZIP 有路径穿越与大小限制（已实现）。
- Production DXF 有门禁（已实现）。
- Geometry SHA 覆盖不全 → **DRC override / 生产批准可在取手、轨道、挡锡条、口袋深度变化后仍保持 active**。这是本轮 P0。
- 禁止自动 accept mandatory review（当前代码已遵守，必须保持）。

## 7. 制造风险

- 无真实客户 Gerber：**0**
- 人工 Reference DXF：**0**
- CNC 试加工：**0**
- 实板装配：**0**
- 波峰焊现场：**0**
- 无 PnP 时 BOT 避位仍依赖丝印。
- 元件高度常缺失，口袋深度用默认值。
- 波峰方向不影响开窗，流向工艺未进入几何。
- 大口袋无泄压槽。
- 无拼板。
- **不是 CNC / 生产就绪。**

## 8. 本轮准备修改的模块

| 模块 | 变更 |
|---|---|
| `backend/app/core/version.py` | 升至 0.6.0 / fixture-engine-0.6.0 / rules 1.2.0 |
| `backend/app/services/fixture/generator.py` | 完整 SHA；接入泄压、拼板、manifest |
| `backend/app/services/fixture/geometry_digest.py` | **新增**确定性几何摘要 |
| `backend/app/services/fixture/drc.py` | 新规则 + STRtree + 完整 issue 字段 |
| `backend/app/services/fixture/solder_optimizer.py` | 方向相关 opening（默认关闭） |
| `backend/app/services/fixture/pressure_relief.py` | **新增** |
| `backend/app/services/fixture/manifest.py` | **新增** |
| `backend/app/services/rules/process_profile.py` | 参数分类 + ParameterDefinition |
| `backend/app/geometry/transform.py` | **新增** Transform2D |
| `backend/app/models/panel.py` + `services/panel/` | **新增** Grid Panel |
| `backend/app/models/geometry.py` | pressure_relief / panel 字段 |
| `backend/app/models/schemas.py` | 新参数、extra=allow |
| `backend/app/tasks/process_job.py` | 写 manifest + DXF hash |
| `backend/app/api/v1/validation.py` | **新增** Golden cases API |
| `backend/app/api/v1/process_profile.py` | **新增** 参数定义 API |
| `backend/app/services/exporters/dxf_exporter.py` | PRESSURE_RELIEF 层 |
| `validation/` | case.json 体系 + Golden Validator + 报告 |
| `src/pages/ValidationPage.tsx` 等 | `/validation` 仪表盘与 overlay |
| `src/components/parameters/ParameterDrawer.tsx` | 动态读取参数定义 |
| 测试 | SHA / wave / relief / validator / panel / transform / DRC / manifest / 可复现 |
| 文档 | README / ENGINEERING_STATUS / VALIDATION_STATUS / PRODUCTION_READINESS / V06_* / BENCHMARK / NEXT_ROUND |

明确不做：把 LLM 接入几何、弱化 Gate、伪造黄金 DXF、宣称行业标准、账号/SaaS/营销页。
