# 波峰焊治具自动出图系统——生产就绪报告

**日期**: 2026-08-31
**版本**: 0.5.0 / fixture-engine-0.5.0 / rules-1.1.0
**测试数量**: 见 `VALIDATION_STATUS.md`（pytest 150、vitest 16、tsc 0 errors、build clean）

---

## 核验

| # | 核验项目 | 真实状态 |
|---|---------|---------|
| 1 | 当前软件版本 | 0.5.0（`backend/app/core/version.py`） |
| 2 | 当前支持输入 | Gerber RS-274X ZIP + Excellon + 可选 PnP/CPL + 可选 BOM CSV |
| 3 | 当前支持 PCB 范围 | 标准矩形/异形单板，无拼板 |
| 4 | 当前 Gerber 解析能力 | Gerbonara 真实解析，文件名模式 + X2 元数据置信度打分 |
| 5 | Layer Confirmation 是否真正闭环 | **是** |
| 6 | BOT 避位 | 语义元件优先；GBO/GBS fallback；缺层 Review |
| 7 | TOP 上锡 | ThroughHoleComponent 优先；greedy PTH fallback |
| 8 | 定位销 | NPTH + 孔径 + 边缘距 + 冲突评分；最远两孔 fallback；支持手动指定 |
| 9 | 人工 Review | Accept/Reject/Modify API + 前端卡片 |
| 10 | DRC | 旧规则全部保留 + v0.5 语义/口袋/开窗规则 |
| 11 | Production Gate | blocking review + error/blocking DRC + 未确认图层 = 生产 DXF 409 |
| 12 | DXF | AutoCAD R2018 分层 + Preview 水印 / Production 门禁 |
| 13 | Mock | 仅 `VITE_USE_MOCK_API=true`；生产核心管道无 Mock |
| 14 | 假 Geometry | **否** — 无估算外形 |
| 15 | 离线 | 核心几何/解析/DRC/DXF **是**。UI 使用系统字体，不再请求 Google Fonts CDN |
| 16 | pytest | **150 passed** (2026-08-31) |
| 17 | npm lint | 无报错 |
| 18 | npm build | **成功** |
| 19 | Golden Cases | 1 占位 CASE-001，0 个人工 DXF |
| 20 | 真实客户验证 | 0 |
| 21 | 人工 DXF 对比 | 0 |
| 22 | CNC 试加工 | 0 |
| 23 | 实板装配 | 0 |
| 24 | 波峰焊现场 | 0 |
| 25 | 已知风险 | 无 PnP 时 BOT 避位仍依赖丝印；元件高度常缺失；拼板未支持 |
| 26 | 禁止生产 | 任何 blocking/error DRC 未 override；mandatory review 未完成；图层未确认 |
| 27 | 待工程师确认的参数 | 板材厚度、口袋底板、波峰方向、连接器开窗 |
| 28 | 下一步 | 见 `NEXT_ROUND.md` |

**结论：不是 CNC 就绪。** Semantic 架构已落地，现场验证尚未开始。
