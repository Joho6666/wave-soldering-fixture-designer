# VALIDATION_STATUS

日期：2026-08-31  
版本源：`backend/app/core/version.py`  
- SOFTWARE_VERSION **0.5.0**
- ALGORITHM_VERSION **fixture-engine-0.5.0**
- RULE_PROFILE_VERSION **1.1.0**
- package.json / package-lock.json **0.5.0**
- FastAPI APP_VERSION **0.5.0**

以下全部为本地真实执行结果，不是估计。

## pytest

命令：

```
cd backend
.venv/Scripts/python.exe -m pytest tests -q
```

结果：**150 passed**（144 warnings，来自 gerbonara/ezdxf 弃用提示，非失败）

## vitest

命令：`npx vitest --run --pool=threads`（`vitest.config.ts` 已固定 `pool: threads`，避免 Windows fork 超时）

结果：**16 passed** / 4 test files

## tsc

命令：`npm run lint`（`tsc --noEmit`）

结果：**0 errors**

## build

命令：`npm run build`（`tsc && vite build`）

结果：**Clean**

- `dist/index.html` 0.65 kB（已去掉 Google Fonts CDN）
- `dist/assets/index-CaoZ8U5D.js` 370.50 kB (gzip 109.09 kB)
- `dist/assets/index-NJVYMueg.css` 32.23 kB (gzip 6.76 kB)

## Golden Case

| 项 | 数量 | 状态 |
|---|---|---|
| validation/cases | 1 (CASE-001) | `awaiting_manual_dxf`，无人工 DXF，无 IoU |
| production_samples | 1 (`case_001_standard_demo`) | 尺寸回归通过；上锡窗口期望 5 |
| 真实客户 Gerber | 0 | 未验证 |
| 人工 DXF IoU | 0 | 未验证 |
| CNC / 装配 / 波峰现场 | 0 | 未验证 |

## CI

`.github/workflows/ci.yml` 已在仓库中。GitHub Actions 要在 **commit + push** 之后才会跑。

## 交付启动

- 开发：`npm run dev` + `uvicorn`（Vite `/api` 代理）
- 交付：`npm run build` + `python launcher/launcher.py`
- `dist/` 不进 git：clone 后必须先 build
- `VITE_USE_MOCK_API` 未设为 `true` 时，生产 `dist/` 走真实后端
