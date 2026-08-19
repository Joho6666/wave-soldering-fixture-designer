import { FixtureApi } from "./fixtureApi";
import { GerberLayer, PCBAnalysis } from "../types/gerber";
import { DEFAULT_PARAMETERS, FixtureParameters, FixtureResult, ProductionGateResult } from "../types/fixture";
import { Project } from "../types/project";
import { MOCK_NORMAL_PCB_ANALYSIS, MOCK_ERROR_PCB_ANALYSIS } from "../mocks/gerber";
import { MOCK_FIXTURE_RESULT } from "../mocks/fixture";
import { generateFixtureDxf } from "../utils/dxfGenerator";
import { AiSettingsResponse, AiSettingsUpdate, AiTestConnectionResponse } from "../types/settings";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

class MockFixtureApiService implements FixtureApi {

  async getPreviewSvg(_id: string): Promise<string> {
    return "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><rect width=\"100\" height=\"100\" fill=\"#111\"/></svg>";
  }
  async getReviews(_id: string): Promise<any[]> {
    return [];
  }
  async acceptReview(_id: string, _reviewId: string): Promise<void> {}
  async rejectReview(_id: string, _reviewId: string): Promise<void> {}
  async modifyReview(_id: string, _reviewId: string, _modifiedData?: any): Promise<void> {}
  async completeReviews(_id: string): Promise<void> {}

  private currentProject: Project = {
    id: "320-WSJ-2024",
    name: "320-WSJ-2024-Gerber.zip",
    createdAt: new Date().toISOString(),
    status: "idle",
    progress: 0,
    logs: []
  };

  private currentAnalysis: PCBAnalysis = { ...MOCK_NORMAL_PCB_ANALYSIS };
  private currentParameters: FixtureParameters = { ...DEFAULT_PARAMETERS };
  private currentResult: FixtureResult = JSON.parse(JSON.stringify(MOCK_FIXTURE_RESULT));
  private mockAiSettings: AiSettingsResponse = {
    aiEnabled: false,
    aiProvider: "openai_compatible",
    aiBaseUrl: "https://api.openai.com/v1",
    aiModel: "gpt-4o-mini",
    aiApiKeyMasked: "sk-****demo",
    aiTimeoutMs: 10000,
  };

  async createJob(file: File | { name: string; size: number }): Promise<Project> {
    await sleep(400);

    const isErrorDemo = file.name.toLowerCase().includes("err") || file.name.toLowerCase().includes("fail");

    this.currentProject = {
      id: isErrorDemo ? "ERR-OUTLINE-MISSING" : `JOB-${Date.now().toString().slice(-6)}`,
      name: file.name,
      createdAt: new Date().toISOString(),
      status: "uploading",
      progress: 10,
      logs: [
        { time: new Date().toLocaleTimeString(), level: "info", message: `文件已上传: ${file.name}` }
      ]
    };

    if (isErrorDemo) {
      this.currentAnalysis = { ...MOCK_ERROR_PCB_ANALYSIS };
    } else {
      this.currentAnalysis = { ...MOCK_NORMAL_PCB_ANALYSIS };
    }

    return { ...this.currentProject };
  }

  async getJob(_id: string): Promise<Project> {
    await sleep(100);
    return { ...this.currentProject };
  }

  async getAnalysis(_id: string): Promise<PCBAnalysis> {
    await sleep(200);
    return { ...this.currentAnalysis };
  }

  async confirmLayers(_id: string, layers: GerberLayer[]): Promise<void> {
    await sleep(300);
    this.currentAnalysis.layers = layers.map((l) => ({ ...l, confirmed: true }));
    const hasOutline = layers.some((l) => l.type === "board_outline");
    if (hasOutline && this.currentAnalysis.width === 0) {
      this.currentAnalysis.width = 180.0;
      this.currentAnalysis.height = 120.0;
      this.currentAnalysis.holeCount = 326;
      this.currentAnalysis.outlineClosed = true;
    }
  }

  async updateParameters(_id: string, params: FixtureParameters): Promise<void> {
    await sleep(200);
    this.currentParameters = { ...params };
  }

  async regenerate(_id: string, params?: FixtureParameters): Promise<Project> {
    if (params) {
      this.currentParameters = { ...params };
    }
    await sleep(400);
    this.currentProject.status = "generating";
    this.currentProject.progress = 20;
    return { ...this.currentProject };
  }

  async getResult(_id: string): Promise<FixtureResult> {
    await sleep(200);
    return JSON.parse(JSON.stringify(this.currentResult));
  }

  async getPreview(_id: string): Promise<string> {
    await sleep(100);
    return "<svg></svg>";
  }

  async downloadDxf(_id: string): Promise<Blob> {
    await sleep(500);
    const dxfString = generateFixtureDxf(this.currentResult, this.currentParameters);
    return new Blob([dxfString], { type: "application/dxf;charset=utf-8" });
  }

  async sendAiCommand(_jobId: string, _request: import("../types/ai").AiCommandRequest): Promise<import("../types/ai").AiCommandResponse> {
    return {
      message: "开发 Mock 未配置 AI Provider。",
      status: "error",
      command: { kind: "no_op", reason: "Mock AI disabled", requiresConfirmation: false },
      applied: false,
      errors: ["请在后端配置 AI Provider。"],
    };
  }

  async getAiSettings(): Promise<AiSettingsResponse> {
    await sleep(100);
    return { ...this.mockAiSettings };
  }

  async updateAiSettings(settings: AiSettingsUpdate): Promise<AiSettingsResponse> {
    await sleep(200);
    this.mockAiSettings = {
      ...this.mockAiSettings,
      aiEnabled: settings.aiEnabled,
      aiProvider: settings.aiProvider ?? this.mockAiSettings.aiProvider,
      aiBaseUrl: settings.aiBaseUrl ?? this.mockAiSettings.aiBaseUrl,
      aiModel: settings.aiModel ?? this.mockAiSettings.aiModel,
      aiTimeoutMs: settings.aiTimeoutMs ?? this.mockAiSettings.aiTimeoutMs,
      aiApiKeyMasked: settings.aiApiKey && settings.aiApiKey.trim() ? "sk-****" + settings.aiApiKey.slice(-4) : this.mockAiSettings.aiApiKeyMasked,
    };
    return { ...this.mockAiSettings };
  }

  async testAiConnection(): Promise<AiTestConnectionResponse> {
    await sleep(300);
    return {
      ok: true,
      message: `Mock 连接测试成功！模型 [${this.mockAiSettings.aiModel}] 响应正常。`,
    };
  }

  async overrideDrc(_id: string, _issueId: string, _operator: string, _reason: string): Promise<void> {}

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

  async downloadPreviewDxf(_id: string): Promise<Blob> {
    return new Blob(["mock-preview-dxf"], { type: "application/dxf" });
  }
}

export const mockFixtureApi = new MockFixtureApiService();

