# VALIDATION_STATUS

日期：2026-09-01  
版本源：`backend/app/core/version.py`  
- SOFTWARE_VERSION **0.7.0**
- ALGORITHM_VERSION **fixture-engine-0.7.0**
- RULE_PROFILE_VERSION **1.3.0**
- package.json **0.7.0**
- FastAPI APP_VERSION **0.7.0**

以下全部为本地真实执行结果，不是估计。

## pytest

命令：`cd backend && .venv/Scripts/python.exe -m pytest tests -q`

结果：**200 passed**（198 warnings，来自 gerbonara/ezdxf 弃用提示，非失败）

## vitest

命令：`npx vitest --run --pool=threads`

结果：**19 passed** / 6 test files

## tsc

命令：`npm run lint`（`tsc --noEmit`）

结果：**0 errors**

## build

命令：`npm run build`（`tsc && vite build`）

结果：**Clean**

- `dist/index.html` 0.66 kB
- `dist/assets/index-BzGkQJJq.js` 383.19 kB (gzip 112.54 kB)
- `dist/assets/index-DpCDXjiw.css` 33.95 kB (gzip 7.10 kB)

## Golden Case

| 项 | 数量 | 状态 |
|---|---|---|
| validation/cases | 5 | 全部 `awaiting_reference`，kind=`synthetic_demo` |
| 已生成 fixture.dxf | 5 / 5 | 无工程师 DXF，未标 PASS |
| 真实客户 Gerber | 0 | 未验证 |
| 人工 DXF IoU | 0 | 未验证 |
| CNC / 装配 / 波峰现场 | 0 / 0 / 0 | 未验证 |

## 交付启动

- 开发：`npm run dev` + `uvicorn`（Vite `/api` 代理）
- 验证页：`/validation`
- 导入案例：`python scripts/import_validation_case.py --case CASE-008 --gerber board.zip`

**NOT PRODUCTION READY**
