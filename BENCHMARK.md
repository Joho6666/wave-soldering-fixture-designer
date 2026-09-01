# BENCHMARK.md

日期: 2026-09-01  
命令: `backend/.venv/Scripts/python.exe scripts/benchmark_fixture.py`  
机器: Windows 10, 本地开发机。数字是这一次实测，不是估计。

当前仓库里没有真正的“大客户 Gerber”。所谓 small / medium / large 只是仓库里现有的三个 ZIP，几何规模接近，不能代表生产现场的大型拼板。

| 样本 | parse ms | semantic ms | fixture generation ms | DRC ms | DXF export ms | solder windows |
|---|---:|---:|---:|---:|---:|---:|
| small (`wave_fixture_outline_drill.zip`) | 44.23 | 2.77 | 26.41 | 6.82 | 107.34 | 5 |
| medium (`case_001_standard_demo`) | 9.24 | 2.24 | 29.72 | 6.93 | 97.28 | 5 |
| large (`CASE-004_x2_nonstandard_names.zip`) | 9.57 | 0.58 | 15.68 | 4.88 | 110.12 | 5 |

观察:

- 生成与 DRC 都在数十毫秒量级；DXF 写出约占全程大部分时间。
- keepout/solder DRC 已改用 STRtree 做包围盒预筛，再 `intersects`。现有样本窗口数量很少，看不出数量级差异。
- 没有对上千个开窗的真实客户板做 profiling。下一轮需要真正的 large PCB。
