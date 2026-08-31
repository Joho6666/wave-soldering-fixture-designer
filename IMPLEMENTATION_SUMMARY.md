# IMPLEMENTATION_SUMMARY — v0.5 Semantic Fixture Engine

本轮把系统从「Gerber 几何猜测 → 治具」升级为「PCB Semantic Model → ProcessProfile → Fixture Geometry」。UI 没有大改，AI 仍然只发命令，不生成生产几何。

## 修改了哪些模块

### 版本
- 新增 `backend/app/core/version.py` 作为唯一版本源
- `SOFTWARE_VERSION = 0.5.0`
- `ALGORITHM_VERSION = fixture-engine-0.5.0`
- `RULE_PROFILE_VERSION = 1.1.0`
- `package.json`、`Settings.APP_VERSION`、`process_job` 结果字段全部引用该源

### 语义模型
- `backend/app/models/geometry.py`：新增 `PCBComponent` / `PCBPad` / `ThroughHoleComponent` / `FixtureRegion`
- `DrillHit` 增加可选 `slot_width_mm` / `slot_length_mm`，原有位置参数构造保持兼容
- `PCBGeometry` 增加 `components` / `pads` / `through_hole_components` / `semantic_conflicts`
- 旧字段 `bot_components` / `through_hole_clusters` 保留

### 规则
- `backend/app/services/rules/process_profile.py`：`ProcessProfile`
- 旧 `FixtureParameters` 默认值保持不变；新增口袋深度、最小开窗宽、定位销范围、波峰方向等可选字段
- `FixtureGenerator._parameters()` 不再维护第三份默认数字

### 解析
- `backend/app/services/pnp/parser.py`：CSV/TXT PnP，模糊列名，mm/mil，Top/Bottom
- `backend/app/services/bom/parser.py`：CSV BOM；缺高度保持 `None`，不编造
- `GerberParser.parse_zip` 跳过 PnP/BOM 成员以免误当 Gerber/Excellon，并把解析结果交给语义层

### 语义构建
- `component_detector.py`：保留旧 BOT / cluster API；新增 `detect_through_hole_components`（含单孔 PTH）和 1xN / 2xN / DIP 启发式
- `semantic_builder.py`：PnP > BOM > 丝印推断；冲突写入 `semantic_conflicts`

### 治具生成（拆分）
- `generator.py` 只编排
- `fixture_body_generator.py`：沉板 / 外框 / 取手 / 轨道挡锡
- `mounting_generator.py`：压扣 / 弹簧卡
- `keepout_generator.py`：语义元件优先，GBO∪GBS fallback
- `solder_optimizer.py`：`ThroughHoleComponent` 优先，greedy PTH fallback
- `locating_pin_optimizer.py`：结构化 reasons；最远两孔仍是自动选择 fallback
- `semantic_adapter.py`：测试路径补齐语义字段

### DRC
- 保留全部旧规则
- 新增：`COMPONENT_HEIGHT_UNKNOWN`、`POCKET_FLOOR_TOO_THIN`、`SOLDER_OPENING_TOO_NARROW`、`SOLDER_OPENING_KEEPOUT_CONFLICT`、`PIN_SPAN_TOO_SMALL`、`SEMANTIC_CONFIDENCE_LOW`、`COMPONENT_DATA_CONFLICT`
- Production gate / SHA override / mandatory review 未弱化

### 流水线
- `process_job.py` 在生成前调用 `build_semantic_model`
- 结果增加 `regionAudit`（sourceType / sourceIds / confidence）

### 测试 / CI / Golden
- 新增 PnP、BOM、语义 THT、口袋深度、上锡/定位销优化器测试
- `.github/workflows/ci.yml`：pytest + lint + vitest + build
- `validation/cases/CASE-001/expected/expected.json` 扩展 manifest 字段；仍 `awaiting_manual_dxf`

## 为什么修改

v0.4 已经计算 `bot_components` 和 `through_hole_clusters`，但 `FixtureGenerator` 完全不读它们。Keepout 继续 GBO∪GBS union，Solder 继续独立 greedy cluster。语义层是死代码。

本轮让正式生产几何来自确定性语义 + 规则引擎；原始几何推断只在语义缺失时 fallback。

## 新架构

```
Gerber / Excellon / PnP / BOM
        ↓
 PCB Semantic Model 2.0
        ↓
 ProcessProfile
        ↓
 Keepout / SolderOpening / LocatingPin / Body
        ↓
 DRC 2.0 + Review + SHA digest
        ↓
 现有 DXF R2018 / SVG
```

## 老逻辑哪些成为 fallback

| 功能 | 主路径 | Fallback |
|---|---|---|
| BOT 避位 | `PCBComponent(side=bottom)` courtyard + clearance | GBO ∪ GBS union + fillet（`sourceType=gerber_fallback`） |
| TOP 上锡 | `ThroughHoleComponent` 按 1xN / 2xN / DIP / connector 生成开口 | greedy PTH eps=6 + convex hull |
| 定位销自动选择 | 评分（NPTH / 孔径 / 边缘 / 冲突） | 合格孔中最远两孔（历史行为） |
| 元件位置 | PnP | 丝印多边形推断 |
| 元件高度 | BOM Height | `None` + 默认口袋深度 + `COMPONENT_HEIGHT_UNKNOWN` |

## 有意改变的几何计数

`production_samples/case_001_standard_demo`：

- 旧：greedy PTH 聚类 → **6** 个上锡窗口
- 新：5 个 `ThroughHoleComponent` 隔离开窗 → **5** 个上锡窗口
- `expected.json` 已按真实结果更新，不是为了让测试变绿而伪造

## 未改

- DXF 层名、SVG group id、`geometrySha256` 排序算法
- Production DXF 409 gate、mandatory review、DRC override SHA
- AI 不直接生成生产几何
- 前端布局
