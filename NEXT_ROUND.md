# NEXT_ROUND

v0.7 Field Validation 软件骨架已落地。下一轮只做能改变制造可信度的事。

## 最值得做的 5 件事

1. **放入第一块真实客户 Gerber + 工程师 DXF**  
   现在 5 个 case 都是 synthetic_demo，IoU 全是“无对照”。不要伪造。

2. **CNC 试切一块治具**  
   `manufacturing_feedback.json` 的 cnc.tested 现在是 false。数量必须从 0 变成 1 才有资格谈生产。

3. **实板装配**  
   销孔、沉板、避位是否装得上，只能装一次才知道。现在 0。

4. **用真 large 板替换合成 benchmark**  
   当前 large 是内存合成 PTH 数，不是客户拼板。

5. **从 Gerber 识别拼板 / 2.5D 下铣**  
   Grid metadata 不够现场用；口袋深度仍不下刀路。

## 不要做

- 不要把 AI 接进核心几何
- 不要弱化 Production Gate
- 不要伪造客户验证或黄金 DXF
- 不要把 CASE 标成 PASS
- 不要宣称 Production Ready
