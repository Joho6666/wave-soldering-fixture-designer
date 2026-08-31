# 波峰焊治具自动出图系统 (Wave Soldering Fixture Designer)

基于真实 PCB 制造文件（Gerber / Excellon / PnP / BOM）的波峰焊过锡载具（Fixture）自动分析、语义规则生成与 AutoCAD DXF 出图系统。

当前版本：**0.5.0** / `fixture-engine-0.5.0` / rules `1.1.0`（单一来源：`backend/app/core/version.py`）

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)

---

## 🌟 核心功能

1. **真实制造文件全自动解析**
   - 支持 Gerber RS-274X、Gerber X2（%TF.FileFunction 元数据解析）、Excellon 钻孔，以及 ZIP 内 PnP/CPL 与 BOM CSV。
   - 自动识别 PCB 闭合外形、PTH/NPTH 钻孔、阻焊层（GTS/GBS）、丝印层（GTO/GBO）与走线铜皮，并构建 Semantic PCB Model。
   - 低置信度或缺少关键图层时提供人工确认映射界面与持久化。

2. **生产级治具几何算法引擎**
   - **沉板区与清角**：基于 PCB 外形外扩生成沉板台阶，并在内角自动生成 R1.85mm 铣刀清角（Corner Relief）。
   - **定位销算法**：基于真实 Drill/NPTH 筛选最优定位孔（边缘距、对角跨距、孔径适配），孔径规则按 `pinDiameter = holeDiameter - 0.1mm`。
   - **BOT 避位与 TOP 上锡**：优先使用 PCB 语义元件 / ThroughHoleComponent；仅在语义缺失时回退 GBO/GBS 与 PTH 邻近聚类。
   - **治具辅件**：自动排布传送轨道槽（上下两端）、防锡桥钛合金挡锡条（左右两端各 3 个 Ø3.2mm 安装孔）、防浮板压扣（4 处 Ø3.4mm 安装孔）与人体工学取手位（20×40mm）。
   - **前挡板弹簧卡**：基于 TOP 丝印层识别元器件中心点生成 R2.45mm 弹簧卡安装孔。

3. **DRC 制造规则检查与生产安全门禁 (Safety Gate)**
   - 自动校验避位壁厚、定位销干涉、压扣干涉、挡锡条碰撞与结构边界。
   - 支持工程师人工放行确认（Override）机制，记录操作人与审计日志。
   - 区分预览版 DXF（带水印）与正式生产 DXF（需通过生产安全门禁解锁）。

4. **工业 CAD 导出与 SVG 实时预览**
   - 输出符合 AutoCAD R2018 标准的分层 DXF 图纸（含标准图层线色与尺寸标注 DIMENSIONS）。
   - 提供基于 SVG 的高精度图层渲染、平移缩放（Pan/Zoom）、图层通道独立显隐控制与钻孔交互。

5. **Golden Sample 自动化比对框架**
   - 内置 `validation/` 几何对比框架，支持人工绘制 DXF 与算法自动生成 DXF 的 IoU、Hausdorff 距离、圆孔位置与多边形分割误差对比。

---

## 🛠️ 技术架构

- **前端 (Frontend)**: React 18 + TypeScript + Vite + Zustand + Tailwind CSS
- **后端 (Backend)**: Python 3.11 + FastAPI + Uvicorn + SQLite + SQLAlchemy
- **几何与 CAD 引擎**: Shapely 2.0+ + Gerbonara + Ezdxf
- **测试框架**: Pytest + Vitest（数量以 [VALIDATION_STATUS.md](VALIDATION_STATUS.md) 同一次实测为准）

---

## 🚀 快速启动

Mock 演示引擎 **仅当** `VITE_USE_MOCK_API=true` 时启用。默认（含 launcher / `dist/`）走真实 FastAPI。

### 开发（两个进程）

```bash
# 终端 1：后端
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 终端 2：前端（/api 代理到 :8000）
npm ci
npm run dev
```

打开 http://localhost:3000 ，上传 Gerber ZIP。

### 交付（单进程）

```bash
npm ci
npm run build
python launcher/launcher.py
```

打开 http://127.0.0.1:8000 。`dist/` 不进 git：clone 后必须先 `npm run build`，否则 launcher 会退出。

---

## 🧪 运行测试

数量以 [VALIDATION_STATUS.md](VALIDATION_STATUS.md) 为准，不要在其它文档另写一套。

```bash
# 后端（必须在 backend/ 目录，pytest.ini 的 pythonpath=. 相对该目录）
cd backend
python -m pytest tests

# 前端
npm test -- --run
npm run lint
npm run build
```

---

## 📄 开源许可

本项目采用 [MIT License](LICENSE) 授权许可。
