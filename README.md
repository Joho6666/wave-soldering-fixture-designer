# 波峰焊治具自动出图系统 (Wave Soldering Fixture Designer)

基于真实 PCB 制造文件（Gerber / Excellon / PnP / BOM）的波峰焊过锡载具（Fixture）自动分析、语义规则生成与 AutoCAD DXF 出图系统。

当前版本：**0.6.0** / `fixture-engine-0.6.0` / rules `1.2.0`（单一来源：`backend/app/core/version.py`）

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![React](https://img.shields.io/badge/React-18-blue.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)

**不是 CNC 就绪，不是生产就绪。** 真实客户 Gerber = 0，人工 Reference DXF = 0，CNC / 实板 / 波峰现场 = 0。

---

## 核心功能

1. **制造文件解析** — Gerber RS-274X / X2、Excellon、ZIP 内 PnP/BOM。低置信图层必须人工确认。
2. **Semantic PCB → ProcessProfile → Fixture** — 沉板、避位、上锡、定位销、压扣、轨道、挡锡条、取手。
3. **Manufacturing Validation Engine (v0.6)**
   - Geometry SHA 覆盖所有生产实体；几何变化会使 DRC override 失效。
   - 方向相关上锡窗口（默认关闭，兼容 v0.5）。
   - 大口袋泄压槽（默认关闭）。
   - Grid 拼板语义（NxM）。
   - Golden Validator + `/validation` 仪表盘。无工程师 DXF 时案例保持 awaiting，不会标成 passed。
4. **DRC + Production Gate** — blocking/error 未放行、mandatory review 未完成、图层未确认、SHA 不一致时，Production DXF 返回 409。
5. **Fixture Manifest** — 版本、输入哈希、几何 SHA、DXF 哈希、参数、DRC、审核记录。

---

## 技术架构

- Frontend: React 18 + TypeScript + Vite + Zustand + Tailwind CSS
- Backend: Python 3.11 + FastAPI + SQLite + SQLAlchemy
- Geometry / CAD: Shapely + Gerbonara + ezdxf
- Tests: Pytest + Vitest（数量以 [VALIDATION_STATUS.md](VALIDATION_STATUS.md) 同一次实测为准）

---

## 快速启动

Mock 演示引擎 **仅当** `VITE_USE_MOCK_API=true` 时启用。默认走真实 FastAPI。

```bash
# 后端
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 前端
npm ci
npm run dev
```

打开 http://localhost:3000 。验证仪表盘：http://localhost:3000/validation

交付：`npm run build` 后 `python launcher/launcher.py`。

---

## 测试

```bash
cd backend
python -m pytest tests

npm test -- --run
npm run lint
npm run build
```

---

## 开源许可

[MIT License](LICENSE)
