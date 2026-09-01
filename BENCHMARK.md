# BENCHMARK.md

日期: 2026-09-01  
命令: `python scripts/benchmark_fixture.py`

仓库里没有真正的大客户 Gerber。`small` / `medium` / `large_zip_not_large_geometry` 是现有 ZIP，几何规模接近，**不能**代表生产现场。`large_synthetic` 和 `large_panel_synthetic` 用 PTH/拼板实例数定义规模，并标明 `synthetic_scale`。

要得到可引用的毫秒数，请在目标机器上重跑脚本并把输出贴到这里。本文件不编造一次未保存的数字。

规模定义：

- Small PCB: 现有 outline+drill demo
- Medium PCB: 同一 demo（文件不同路径，几何同类）
- Large PCB: 合成高 PTH 数，不是文件变大
- Large Panel: 3×3 grid of a small board

**NOT PRODUCTION READY**
