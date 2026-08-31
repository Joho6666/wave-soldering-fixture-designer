# SEMANTIC_ENGINE — Gerber / PnP / BOM → Semantic PCB → Fixture

## 数据流

```
制造 ZIP
 ├─ Gerber RS-274X / X2     → 外形、丝印、阻焊、铜皮
 ├─ Excellon                → DrillHit (hole | slot, PTH/NPTH)
 ├─ PnP / CPL / centroid    → RefDes, X/Y, rotation, side, footprint
 └─ BOM CSV                 → RefDes, value, footprint, height (optional)
        ↓
build_semantic_model()
        ↓
PCBGeometry
 ├─ components: PCBComponent[]
 ├─ pads: PCBPad[]
 ├─ through_hole_components: ThroughHoleComponent[]
 ├─ bot_components / through_hole_clusters   (兼容旧检测器)
 └─ semantic_conflicts[]
        ↓
ProcessProfile.from_dict(job.parameters)
        ↓
FixtureGenerator.generate()
 ├─ sink / body / clamps / rails            (确定性，与 v0.4 同参数)
 ├─ keepout_generator                       (语义优先)
 ├─ solder_optimizer                        (THT 组件优先)
 ├─ locating_pin_optimizer                  (评分 + 最远两孔)
 └─ customRegions                           (工程师/AI 命令注入的盒子)
        ↓
run_drc() + geometrySha256
        ↓
DXF R2018 / SVG / Review / Production Gate
```

## 优先级

1. **PnP** — 位置与 RefDes，confidence ≈ 0.94
2. **BOM** — value / footprint / height。没有 Height 就保持 `body_height_mm = None`，禁止编造
3. **Gerber X2** — 已有层分类
4. **底层丝印几何** — `detect_bot_components`，confidence ≈ 0.72

同一 RefDes 的 PnP 封装与 BOM 封装明显不同 → `COMPONENT_DATA_CONFLICT`，不静默覆盖。

## Keepout / Pocket

主路径：

`PCBComponent(side=bottom)` → courtyard/bbox → `keepoutClearanceMm` → inner fillet → `FixtureRegion(pocket)`

口袋深度：

```
if height:
    pocketDepth = height + componentVerticalClearanceMm
else:
    pocketDepth = defaultPocketDepthMm
    DRC COMPONENT_HEIGHT_UNKNOWN   # warning，非 blocking

if palletThicknessMm - pocketDepth < pocketFloorThicknessMm:
    DRC POCKET_FLOOR_TOO_THIN      # blocking
```

本轮 DXF 仍是 2D。深度只挂在 `FixtureRegion.parameters` 并进入 DRC。

无 bottom 元件且无 GBO/GBS → mandatory `CONFIRM_NO_BOTTOM_SMD`。

## Solder opening

主路径按 `ThroughHoleComponent` 隔离：

| 识别 | 开口 |
|---|---|
| 单孔 | 圆，`max(dia/2+clearance, minOD/2)` |
| 1xN | 沿主轴的圆角长圆/矩形 |
| 2xN / DIP | 双排 bbox 包络，不是整板 hull |
| connector / 不规则 | 该组件自己的 convex envelope |

GBS 只做 pad 扩张 refinement。语义失败才走 greedy eps=6。无 PTH → `CONFIRM_NO_TOP_THT`。

## Locating pins

评分：slot 禁止、NPTH 优先、孔径窗、板边距、与 keepout/solder/clamp 冲突。

输出每个候选：`score` + `reasons` + `rejectionReasonsOnly`。自动选择仍是合格孔中最远两孔，避免静默改掉历史选孔。跨距不足 → `PIN_SPAN_TOO_SMALL`。

## FixtureRegion 审计

每个自动区域带：

```json
{
  "sourceType": "semantic_component",
  "sourceIds": ["J3"],
  "confidence": 0.94
}
```

或：

```json
{
  "sourceType": "gerber_fallback",
  "confidence": 0.75
}
```

写入 `result_data.regionAudit`。低置信 fallback 触发 `SEMANTIC_CONFIDENCE_LOW`。

## AI 边界

允许：解释 DRC、推荐参数、`add_custom_region`、帮助工程师理解结果。

禁止：AI 直接生成未经验证的生产几何。正式几何只来自确定性引擎。
