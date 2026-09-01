# VALIDATION_STATUS

日期：2026-09-01  
版本源：`backend/app/core/version.py`  
- SOFTWARE_VERSION **0.6.0**
- ALGORITHM_VERSION **fixture-engine-0.6.0**
- RULE_PROFILE_VERSION **1.2.0**
- package.json **0.6.0**
- FastAPI APP_VERSION **0.6.0**

以下全部为本地真实执行结果，不是估计。

## pytest

命令：

```
cd backend
.venv/Scripts/python.exe -m pytest tests -q
```

结果：**177 passed**（144 warnings，来自 gerbonara/ezdxf 弃用提示，非失败）

## vitest

命令：`npx vitest --run --pool=threads`

结果：**17 passed** / 5 test files

## tsc

命令：`npm run lint`（`tsc --noEmit`）

结果：**0 errors**

## build

命令：`npm run build`（`tsc && vite build`）

结果：**Clean**

- `dist/index.html` 0.66 kB
- `dist/assets/index-Buqn1KFt.js` 379.88 kB (gzip 111.21 kB)
- `dist/assets/index-KgxDYFYW.css` 33.81 kB (gzip 7.05 kB)

## Golden Case

| 项 | 数量 | 状态 |
|---|---|---|
| validation/cases | 1 (CASE-001) | `awaiting_input`，无 PCB ZIP，无人工 DXF，无 IoU |
| production_samples | 1 (`case_001_standard_demo`) | 尺寸回归通过；上锡窗口 5 |
| 真实客户 Gerber | 0 | 未验证 |
| 人工 DXF IoU | 0 | 未验证 |
| CNC / 装配 / 波峰现场 | 0 | 未验证 |

## 交付启动

- 开发：`npm run dev` + `uvicorn`（Vite `/api` 代理）
- 验证页：`/validation`
- 交付：`npm run build` + `python launcher/launcher.py`
