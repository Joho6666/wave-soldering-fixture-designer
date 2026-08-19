import { FixtureApi } from "./fixtureApi";
import { GerberLayer, PCBAnalysis } from "../types/gerber";
import { DEFAULT_PARAMETERS, FixtureParameters, FixtureResult, ReviewItem, ProductionGateResult } from "../types/fixture";
import { Project } from "../types/project";
import { generateFixtureDxf } from "../utils/dxfGenerator";
import { AiSettingsResponse, AiSettingsUpdate, AiTestConnectionResponse } from "../types/settings";
import { AiCommandRequest, AiCommandResponse } from "../types/ai";
import { buildDemoFixture } from "../utils/demoFixtureEngine";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

class MockFixtureApiService implements FixtureApi {
  private currentProject: Project = {
    id: "DEMO-WSJ-2026",
    name: "320-WSJ-2026-Industrial-Gerber.zip",
    createdAt: new Date().toISOString(),
    status: "completed",
    progress: 100,
    currentStepDescription: "治具设计完成 (Client Standalone Engine)",
    logs: [
      { time: "10:00:00", level: "info", message: "解压 8 个 Gerber/Excellon 制造文件" },
      { time: "10:00:01", level: "info", message: "识别 PCB 外形 (180.00 × 120.00 mm), 提取 326 个钻孔" },
      { time: "10:00:02", level: "info", message: "计算沉板台阶与 R1.85mm 铣刀清角" },
      { time: "10:00:02", level: "info", message: "聚类生成 18 处 BOT 贴片避位与 12 处 TOP 上锡窗口" },
      { time: "10:00:03", level: "info", message: "自动排布左右钛合金挡锡条、4 处压扣与 2 处定位销" },
      { time: "10:00:03", level: "info", message: "生成 AutoCAD R2018 DXF 与分层 SVG 预览完成" },
    ],
  };

  private currentParameters: FixtureParameters = { ...DEFAULT_PARAMETERS };
  private manualPins: string[] = ["D1", "D2"];
  private customRegions: Array<{ regionType: "keepout" | "solder"; x: number; y: number; width: number; height: number; label?: string }> = [];

  private mockAiSettings: AiSettingsResponse = {
    aiEnabled: true,
    aiProvider: "client_demo_agent",
    aiBaseUrl: "https://api.openai.com/v1",
    aiModel: "Wave-Fixture-Copilot",
    aiApiKeyMasked: "sk-****demo",
    aiTimeoutMs: 10000,
  };

  private getEngineData() {
    return buildDemoFixture(this.currentParameters, this.manualPins, this.customRegions);
  }

  async createJob(file: File | { name: string; size: number }): Promise<Project> {
    await sleep(400);
    this.currentProject = {
      id: `JOB-${Date.now().toString().slice(-6)}`,
      name: file.name,
      createdAt: new Date().toISOString(),
      status: "completed",
      progress: 100,
      currentStepDescription: "治具设计完成 (Client Demo Engine)",
      logs: [
        { time: new Date().toLocaleTimeString(), level: "info", message: `成功解析制造归档: ${file.name}` },
        { time: new Date().toLocaleTimeString(), level: "info", message: "识别 PCB 闭合外形 180×120mm，提取钻孔 326 个" },
        { time: new Date().toLocaleTimeString(), level: "info", message: "已自动生成沉板区、避位区、透锡槽与辅件" },
      ],
    };
    return { ...this.currentProject };
  }

  async getJob(_id: string): Promise<Project> {
    await sleep(50);
    return { ...this.currentProject };
  }

  async getAnalysis(_id: string): Promise<PCBAnalysis> {
    await sleep(50);
    return this.getEngineData().analysis;
  }

  async confirmLayers(_id: string, _layers: GerberLayer[]): Promise<void> {
    await sleep(200);
  }

  async updateParameters(_id: string, params: FixtureParameters): Promise<void> {
    await sleep(100);
    this.currentParameters = { ...this.currentParameters, ...params };
  }

  async regenerate(_id: string, params?: FixtureParameters, manualPins?: string[]): Promise<Project> {
    if (params) this.currentParameters = { ...this.currentParameters, ...params };
    if (manualPins) this.manualPins = manualPins;
    await sleep(300);
    return { ...this.currentProject };
  }

  async getResult(_id: string): Promise<FixtureResult> {
    await sleep(50);
    const data = this.getEngineData();
    return {
      ...data.result,
      id: this.currentProject.id,
      locatingPins: this.manualPins.length,
    };
  }

  async getPreviewSvg(_id: string): Promise<string> {
    await sleep(50);
    return this.getEngineData().svg;
  }

  async downloadDxf(_id: string): Promise<Blob> {
    await sleep(200);
    const data = this.getEngineData();
    const dxfString = generateFixtureDxf(data.result, this.currentParameters);
    return new Blob([dxfString], { type: "application/dxf;charset=utf-8" });
  }

  async downloadPreviewDxf(_id: string): Promise<Blob> {
    await sleep(200);
    const data = this.getEngineData();
    const dxfString = generateFixtureDxf(data.result, this.currentParameters);
    return new Blob([dxfString], { type: "application/dxf;charset=utf-8" });
  }

  async getReviews(_id: string): Promise<ReviewItem[]> {
    return this.getEngineData().result.reviewItems || [];
  }

  async acceptReview(_id: string, _reviewId: string): Promise<void> {
    await sleep(100);
  }

  async rejectReview(_id: string, _reviewId: string): Promise<void> {
    await sleep(100);
  }

  async modifyReview(_id: string, _reviewId: string, _modifiedData?: any): Promise<void> {
    await sleep(100);
  }

  async completeReviews(_id: string): Promise<void> {
    await sleep(100);
  }

  async overrideDrc(_id: string, _issueId: string, _operator: string, _reason: string): Promise<void> {
    await sleep(100);
  }

  async getProductionGate(_id: string): Promise<ProductionGateResult> {
    return {
      blocking_reviews: 0,
      blocking_drc_errors: 0,
      unconfirmed_layers: 0,
      missing_required_data: 0,
      geometry_validation_errors: 0,
      production_ready: true,
      blocking_reasons: [],
    };
  }

  async sendAiCommand(_jobId: string, request: AiCommandRequest): Promise<AiCommandResponse> {
    await sleep(400);
    const userMsg = request.userMessage.toLowerCase();

    // 1. 如果是 apply
    if (request.apply && request.command) {
      if (request.command.kind === "apply_recipe_preset" && request.command.parameters) {
        this.currentParameters = { ...this.currentParameters, ...request.command.parameters };
      } else if (request.command.kind === "update_parameters" && request.command.parameters) {
        this.currentParameters = { ...this.currentParameters, ...request.command.parameters };
      } else if (request.command.kind === "set_locating_pins" && request.command.pinDrillIds) {
        this.manualPins = request.command.pinDrillIds;
      } else if (request.command.kind === "add_custom_region") {
        this.customRegions.push({
          regionType: request.command.regionType || "keepout",
          x: request.command.x || 50,
          y: request.command.y || 30,
          width: request.command.width || 20,
          height: request.command.height || 15,
          label: request.command.label,
        });
      } else if (request.command.kind === "auto_fix_drc" && request.command.suggestedParameters) {
        this.currentParameters = { ...this.currentParameters, ...request.command.suggestedParameters };
      }
      return {
        conversationId: request.conversationId,
        message: "AI 建设指令已由纯前端确定性几何引擎执行并刷新图纸。",
        status: "complete",
        command: request.command,
        applied: true,
        errors: [],
      };
    }

    // 2. 智能指令识别
    if (userMsg.includes("汽车") || userMsg.includes("可靠性") || userMsg.includes("auto")) {
      return {
        conversationId: request.conversationId,
        message: "已为您生成【汽车电子高可靠性标准】工艺方案：加宽避位安全间距至 1.0mm，最小材料壁厚提升至 2.5mm，压扣偏移增大至 12.0mm 以提高抗振能力。",
        status: "needs_confirmation",
        command: {
          kind: "apply_recipe_preset",
          presetId: "automotive_high_reliability",
          presetName: "汽车电子高可靠性标准",
          parameters: {
            sinkClearanceMm: 0.3,
            keepoutClearanceMm: 1.0,
            solderClearanceMm: 3.5,
            clampOffsetMm: 12.0,
            minimumMaterialWebMm: 2.5,
            solderMinOuterDiameterMm: 3.2,
          },
          reason: "应用汽车电子高可靠性工艺参数配方",
          requiresConfirmation: true,
        },
        applied: false,
        errors: [],
      };
    }

    if (userMsg.includes("定位销") || userMsg.includes("定位孔") || userMsg.includes("pin")) {
      return {
        conversationId: request.conversationId,
        message: "已为您分析 PCB 钻孔矩阵：检测到对角两处 Ø3.2mm NPTH 非金属化机械定位孔 (D1, D2)，跨距 174.5mm，符合最佳定位约束要求。",
        status: "needs_confirmation",
        command: {
          kind: "set_locating_pins",
          pinDrillIds: ["D1", "D2"],
          reason: "优选对角非金属化机械定位孔方案",
          requiresConfirmation: true,
        },
        applied: false,
        errors: [],
      };
    }

    if (userMsg.includes("修复") || userMsg.includes("壁厚") || userMsg.includes("drc") || userMsg.includes("fix")) {
      return {
        conversationId: request.conversationId,
        message: "已针对【上锡窗口与沉板边缘壁厚不足】缺陷计算优化方案：将 solderClearanceMm 微调为 2.5mm，消除过炉熔锡溢出风险，完全满足 2.0mm 最小壁厚规范。",
        status: "needs_confirmation",
        command: {
          kind: "auto_fix_drc",
          targetIssueIds: ["drc-minimum_material_web_too_small-global"],
          suggestedParameters: { solderClearanceMm: 2.5 },
          reason: "自动微调开窗间隙以满足材料壁厚规范",
          requiresConfirmation: true,
        },
        applied: false,
        errors: [],
      };
    }

    if (userMsg.includes("避位") || userMsg.includes("开槽") || userMsg.includes("custom")) {
      return {
        conversationId: request.conversationId,
        message: "已在坐标 (50.0, 30.0) 处规划 20.0×15.0mm 自定义非标避位槽，用于避让特殊高器件或排针。",
        status: "needs_confirmation",
        command: {
          kind: "add_custom_region",
          regionType: "keepout",
          x: 50.0,
          y: 30.0,
          width: 20.0,
          height: 15.0,
          label: "J1接插件避位",
          reason: "添加非标排针避位开槽",
          requiresConfirmation: true,
        },
        applied: false,
        errors: [],
      };
    }

    return {
      conversationId: request.conversationId,
      message: "您好！我是波峰焊治具 AI 助手。您可以告诉我“按汽车电子标准配置”、“选用对角定位销”、“修复壁厚不足”或“在指定位置增加避位槽”，我将为您生成结构化建设方案。",
      status: "complete",
      command: { kind: "no_op", reason: "常规问答", requiresConfirmation: false },
      applied: false,
      errors: [],
    };
  }

  async getAiSettings(): Promise<AiSettingsResponse> {
    await sleep(50);
    return { ...this.mockAiSettings };
  }

  async updateAiSettings(settings: AiSettingsUpdate): Promise<AiSettingsResponse> {
    await sleep(100);
    this.mockAiSettings = { ...this.mockAiSettings, ...settings };
    return { ...this.mockAiSettings };
  }

  async testAiConnection(): Promise<AiTestConnectionResponse> {
    await sleep(200);
    return { ok: true, message: "AI 客户端演示引擎已就绪，所有建设与审查指令均支持本地实时交互！" };
  }
}

export const mockFixtureApi = new MockFixtureApiService();
