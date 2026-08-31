# NEXT_ROUND

本轮已完成 Semantic Fixture Engine v0.5。下一轮只做真正改变制造结果的事，不要继续无限扩功能。

## 值得做

1. **Wave Direction-aware opening**  
   `ProcessProfile.waveDirection` 已入库但 opening 算法未使用。按波峰流向拉长/倒角上锡窗口。

2. **Pressure Relief**  
   口袋与上锡窗口之间的泄压槽，避免真空吸附和锡爆。

3. **Panelization**  
   拼板、V-cut、stamp hole、多板共用治具。

4. **KiCad IPC API**  
   比 PnP/丝印更高置信的 footprint / courtyard / 高度。

5. **CNC CAM**  
   2.5D 刀路、口袋深度真正下铣、刀具半径补偿。当前 DXF 仍是 2D。

6. **3D Fixture**  
   底板厚度、口袋、销柱的实体模型，给装配和干涉检查。

## 不要做

- 不要把 AI 接进核心几何
- 不要弱化 Production Gate / SHA override
- 不要伪造客户验证或黄金 DXF
- 不要宣称未经实测的「行业标准」数字
- 不要在没有工程师 DXF 的情况下把 CASE-001 标成已验证
