# NEXT_ROUND

本轮已完成 Manufacturing Validation Engine v0.6。下一轮只做能改变制造可信度的事。

## 值得做

1. **放入第一块真实客户 Gerber + 工程师 DXF**  
   CASE-001 现在仍 awaiting_input。没有这两样文件，验证器无法给出真实 IoU。不要伪造。

2. **真正的 large PCB profiling**  
   当前仓库样本太小。需要上千窗口/口袋的板来验证 STRtree 是否足够。

3. **拼板第二阶段**  
   从 Gerber 识别拼板、mouse-bite 几何、V-cut 真正开槽，而不是只有 Grid metadata。

4. **2.5D CAM**  
   口袋深度真正下铣。当前 DXF 仍是 2D。

5. **CNC 试切一块治具**  
   在宣称生产就绪之前必须发生。数量现在是 0。

## 不要做

- 不要把 AI 接进核心几何
- 不要弱化 Production Gate / SHA override
- 不要伪造客户验证或黄金 DXF
- 不要把 CASE-001 标成 passed
- 不要宣称未经实测的「行业标准」
- 不要做账号系统 / SaaS / 营销页
