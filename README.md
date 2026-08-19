# 波峰焊治具自动出图系统 (Wave Soldering Fixture Designer)

基于真实 PCB 制造文件（Gerber / Excellon）的波峰焊过锡载具（Fixture）自动分析、几何生成与 AutoCAD DXF 出图系统。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)

---

## 🌟 核心功能

1. **真实制造文件全自动解析**
   - 支持 Gerber RS-274X、Gerber X2（%TF.FileFunction 元数据解析）与 Excellon 钻孔文件。
   - 自动识别 PCB 闭合外形、PTH/NPTH 钻孔、阻焊层（GTS/GBS）、丝印层（GTO/GBO）与走线铜皮。
   - 低置信度或缺少关键图层时提供人工确认映射界面与持久化。

2. **生产级治具几何算法引擎**
   - **沉板区与清角**：基于 PCB 外形外扩生成沉板台阶，并在内角自动生成 R1.85mm 铣刀清角（Corner Relief）。
   - **定位销算法**：基于真实 Drill/NPTH 筛选最优定位孔（边缘距、对角跨距、孔径适配），孔径规则按 `pinDiameter = holeDiameter - 0.1mm`。
   - **BOT 避位与 TOP 上锡**：根据底层贴片元件与顶层通孔引脚群自动聚类生成避位腔体（支持 R1.5 内倒角）与波峰透锡开窗（支持一字/方框开窗）。
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
- **测试框架**: Pytest (后端 63 项测试用例) + Vitest (前端组件与生命周期测试)

---

## 🚀 快速启动

### 1. 前端启动
```bash
# 安装依赖
npm install

# 启动开发服务器 (默认端口 3000)
npm run dev
```

### 2. 后端启动
```bash
cd backend

# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动 FastAPI 服务 (默认端口 8000)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🧪 运行测试

```bash
# 后端自动化测试
pytest backend/tests

# 前端单元与组件测试
npm test

# 前端类型检查与生产构建
npm run lint
npm run build
```

---

## 📄 开源许可

本项目采用 [MIT License](LICENSE) 授权许可。
