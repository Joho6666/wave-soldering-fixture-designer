# ENGINEERING_STATUS.md - 生产验证与元件语义识别迭代报告

## 报告日期: 2026-08-19
## 软件版本: 0.4.0 / fixture-engine-0.4.0 / rules-1.0.0

---

## 1. 后端真实测试数量
- pytest: **95/95 passed** (152 warnings, 28 test files)
- 本轮新增: 6 个测试文件 (27 个测试用例)

## 2. 前端真实测试数量
- tsc --noEmit: **0 errors**
- npm run build: **Clean** (375KB JS, 32KB CSS)
- vitest: 15 pass (3 test suites)

## 3. Production Gate 状态
- **已修复**: complete_all_reviews 不再自动接受 pending mandatory reviews (HTTP 409)
- **已修复**: 缺少关键层数据 (GBO/GBS/GTO/NPTH) 时生成 mandatory blocking review
- **已实现**: 4 种数据确认 Review 类型 (CONFIRM_NO_BOTTOM_SMD, CONFIRM_NO_TOP_THT, CONFIRM_NO_SPRING_CLIP_REQUIRED, CONFIRM_NO_NPTH_AVAILABLE)
- 前端显示语义化确认按钮

## 4. Missing Data Blocking 状态
- **已实现**: 缺 GBO/GBS -> CONFIRM_NO_BOTTOM_SMD (mandatory=True)
- **已实现**: 缺 PTH 通孔 -> CONFIRM_NO_TOP_THT (mandatory=True)
- **已实现**: 缺 GTO -> CONFIRM_NO_SPRING_CLIP_REQUIRED (mandatory=True)
- **已实现**: 无钻孔 -> CONFIRM_NO_NPTH_AVAILABLE (mandatory=True)
- 低置信度几何区域: mandatory=False (可选确认)

## 5. DRC Override SHA 状态
- **已实现**: override 必须 geometrySha256 匹配当前几何才有效
- 参数变更/重新生成后旧 override 自动过期
- DrcOverrideRecord 增加 status 字段 (active/expired/revoked)

## 6. 人工定位销校验
- **已实现**: 后端 regenerate 端点验证:
  - drill 存在于当前 PCB 钻孔列表
  - 孔径 >= 2.0mm
  - 不满足条件返回 HTTP 422

## 7. X2 / Unknown Layer 状态
- **正常**: X2 metadata 通过 gerbonara file_attrs 提取
- **正常**: 非标准文件名通过 X2 FileFunction 自动识别
- **正常**: 低置信度或缺失关键层时进入 layer_confirmation 流程

## 8. Component Semantic Layer
- **已实现**: BOT Component Detector (backend/app/services/gerber/component_detector.py)
  - 基于 GBO 底层丝印闭合多边形检测 BOT 贴片区域
  - 输出 ComponentRegion (id, centroid, bbox, area, layer_side)
  - 已集成到 process_job 管道

## 9. BOT Component Detector
- **已实现**: detect_bot_components() 从 bottom_silkscreen 提取独立闭合区域
- 最小面积阈值 1.0mm2, 需与 PCB outline 有交集
- 3 个测试通过

## 10. Through-hole Component Detector
- **已实现**: detect_through_hole_clusters() 基于 PTH 钻孔距离聚类
- 默认 eps=5mm, min_holes=2
- 使用 BFS 距离聚类 (非 sklearn DBSCAN, 避免额外依赖)
- 输出 convex hull WKT, centroid, hole IDs
- 3 个测试通过

## 11. OCR Engine
- **已实现**: backend/app/services/ocr/refdes_ocr.py
- 可选依赖 pytesseract (启动时检查, 不可用则 graceful skip)
- 配置开关: ENABLE_OCR = False (默认关闭)

## 12. OCR RefDes Accuracy
- 尚未验证 (Tesseract 未安装在当前环境)

## 13. OCR Precision / Recall
- 尚未验证

## 14. OCR Coordinate Error
- 尚未验证

## 15. Golden Sample 数量
- 框架已就绪 (validation/ 目录)
- 0 个真实人工 DXF 对比案例

## 16. Golden Sample 各项误差
- 尚未验证 (无真实人工 DXF)

## 17. API E2E 测试
- 95 个单元/集成测试覆盖核心管道
- 完整 E2E 需要真实 Gerber 文件

## 18. 当前最弱算法
- BOT 避位区: 仅基于丝印/阻焊几何, 无元件高度信息
- TOP 上锡窗口: 简单 PTH 聚类 buffer, 无布尔差集优化

## 19. 当前仍必须人工确认的场景
- 缺少 GBO/GBS/GTO/NPTH 时
- 定位销少于 2 个时
- 低置信度避位/上锡区域

## 20. 是否 100% 断网可运行
- **是**: AI Assistant 为 Optional, OCR 为 Local
- 核心管道: Gerber -> Semantic -> Fixture -> DXF 完全离线

## 21. 当前是否适合直接 CNC 生产
- **否**: 尚未通过 CNC 加工与实板装配验证
- **否**: 无真实人工 DXF 对比数据
- 适合进入工程师审核验证阶段

---

## 本轮变更摘要

### 新增文件
- ackend/app/services/gerber/component_detector.py - BOT 元件 + THT 聚类检测
- ackend/app/services/ocr/__init__.py - OCR 模块
- ackend/app/services/ocr/refdes_ocr.py - 本地 OCR RefDes 引擎
- ackend/tests/test_complete_reviews_rejects_pending.py - 3 个测试
- ackend/tests/test_drc_override_sha_expiry.py - 3 个测试
- ackend/tests/test_missing_data_blocking_review.py - 5 个测试
- ackend/tests/test_manual_pin_validation.py - 3 个测试
- ackend/tests/test_component_detector.py - 6 个测试
- ackend/tests/test_ocr_refdes.py - 7 个测试
- NEXT_ROUND_AUDIT.md - 审计文档

### 修改文件
- ackend/app/api/v1/jobs.py - Safety gate fixes (complete_all_reviews, SHA validation, pin validation)
- ackend/app/services/fixture/generator.py - 4 种 mandatory review types
- ackend/app/models/schemas.py - DrcOverrideRecord status 字段
- ackend/app/models/geometry.py - PCBGeometry 新增 bot_components, through_hole_clusters
- ackend/app/tasks/process_job.py - 集成 component detector + OCR
- ackend/app/core/config.py - ENABLE_OCR 开关
- src/components/inspection/ReviewBanner.tsx - 语义化确认按钮
- src/types/fixture.ts - DrcOverrideRecord status type
- launcher/launcher.py - 移除 --reload
- ackend/tests/test_fixture_pipeline.py - 适配新 review type
- ackend/tests/test_spring_clips.py - 适配新 review type
