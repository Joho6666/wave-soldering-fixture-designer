import { describe, it, expect } from 'vitest';
import { classifyGerberFilename } from './zipHelper';

describe('Gerber文件名分类', () => {
  it('应正确识别PCB外形层', () => {
    expect(classifyGerberFilename('PCB-BoardOutline.gko').type).toBe('board_outline');
    expect(classifyGerberFilename('outline.gm1').type).toBe('board_outline');
    expect(classifyGerberFilename('profile.gbr').type).toBe('board_outline');
  });

  it('应正确识别钻孔文件', () => {
    expect(classifyGerberFilename('drill.drl').type).toBe('drill');
    expect(classifyGerberFilename('NC-Drill.xln').type).toBe('drill');
  });

  it('应正确识别DXF文件', () => {
    const result = classifyGerberFilename('outline.dxf');
    expect(result.type).toBe('board_outline');
    expect(result.confidence).toBe(0.75);
  });

  it('应正确识别顶层铜箔', () => {
    expect(classifyGerberFilename('copper_top.gtl').type).toBe('top_copper');
    expect(classifyGerberFilename('layer1.l1').type).toBe('top_copper');
  });

  it('应正确识别底层铜箔', () => {
    expect(classifyGerberFilename('copper_bot.gbl').type).toBe('bottom_copper');
    expect(classifyGerberFilename('layer2.l2').type).toBe('bottom_copper');
  });

  it('应正确识别丝印层', () => {
    expect(classifyGerberFilename('silkscreen_top.gto').type).toBe('top_silkscreen');
    expect(classifyGerberFilename('silkscreen_bot.gbo').type).toBe('bottom_silkscreen');
  });

  it('应正确识别阻焊层', () => {
    expect(classifyGerberFilename('soldermask_top.gts').type).toBe('top_soldermask');
    expect(classifyGerberFilename('soldermask_bot.gbs').type).toBe('bottom_soldermask');
  });

  it('应处理未知文件', () => {
    const result = classifyGerberFilename('unknown.txt');
    expect(result.type).toBe('unknown');
    expect(result.confidence).toBeLessThan(0.5);
  });

  it('应大小写不敏感', () => {
    expect(classifyGerberFilename('OUTLINE.GKO').type).toBe('board_outline');
    expect(classifyGerberFilename('Drill.DRL').type).toBe('drill');
  });
});
