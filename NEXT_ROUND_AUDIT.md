# NEXT_ROUND_AUDIT.md — 生产验证与元件语义识别迭代审计

## 审计日期: 2026-08-19

## 1. 真实测试基线

| 项目 | 结果 |
|------|------|
| pytest | 68/68 passed (146 warnings) |
| tsc --noEmit | 0 errors |
| npm run build | Clean (dist/ 375KB JS + 32KB CSS) |
| vitest | 待验证 |

## 2. mandatory=False 审计 (7 处)

所有生成的 review items（除定位销无孔/定位销不足外）均为 mandatory=False，
意味着即使关键层数据缺失，系统也不会阻止生产 DXF 输出。

| 文件 | 行号 | Review ID | 问题 |
|------|------|-----------|------|
| generator.py | 414 | review-bot-keepout-missing-layer | 缺 GBO/GBS 时不阻塞 |
| generator.py | 447 | review-bot-keepout-N | 低置信度避位不阻塞 |
| generator.py | 470 | review-top-solder-no-pth | 缺 PTH 不阻塞 |
| generator.py | 528 | review-top-solder-N | 低置信度上锡窗口不阻塞 |
| generator.py | 552 | review-spring-clip-no-gto | 缺 GTO 不阻塞 |
| generator.py | 572 | review-spring-clip-no-regions | 无有效丝印不阻塞 |
| generator.py | 600 | review-spring-clip-none-found | 未找到弹簧卡位不阻塞 |

## 3. complete_all_reviews 自动接受 bug

jobs.py:209 中 complete_all_reviews 将所有 pending review 自动转为 accepted。
这违反了生产安全原则：mandatory 审核项必须由工程师逐个确认。

## 4. DRC Override 不校验 Geometry SHA

_compute_production_gate() 中 override 判断仅检查 issueId 存在性，
未比对 override.geometrySha256 == current geometrySha256。

## 5. 缺少数据确认 Review 类型

不存在: CONFIRM_NO_BOTTOM_SMD, CONFIRM_NO_TOP_THT,
CONFIRM_NO_SPRING_CLIP_REQUIRED, CONFIRM_NO_NPTH_AVAILABLE

## 6. 定位销人工选择无后端校验

manual_pins 直接被 generator 使用，无孔径/镀层/存在性验证。

## 7. 缺失能力

| 能力 | 状态 |
|------|------|
| OCR RefDes | 不存在 |
| BOT Component Detector | 不存在 |
| Through-hole Clustering | 不存在 |
| DRC Override status | 不存在 |

## 8. Launcher 使用 --reload

launcher/launcher.py 在正式模式下仍使用 --reload 参数。

## 9. 修复计划

以上问题将在本轮迭代中逐一修复，按 P0-P2 优先级实施。
