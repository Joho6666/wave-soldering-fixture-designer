import { buildDemoFixture } from "../utils/demoFixtureEngine";
import { create } from "zustand";
import { JobStatus, Project } from "../types/project";
import { GerberLayer, PCBAnalysis } from "../types/gerber";
import { DEFAULT_PARAMETERS, FixtureParameters, FixtureResult } from "../types/fixture";
import { DesignIssue } from "../types/inspection";
import { AiMessage } from "../types/ai";
import { fixtureApi } from "../services/api";
import { MOCK_ERROR_PCB_ANALYSIS } from "../mocks/gerber";

export type ViewMode = "all" | "pcb_only" | "fixture_only";

export interface UploadedFileMeta {
  name: string;
  size: number;
  fileCount: number;
  gerberCount?: number;
  drillCount?: number;
  dxfCount?: number;
}

interface BackendFixtureResult {
  fixtureWidth: number;
  fixtureHeight: number;
  featureSummary: {
    sinkRegionCount: number;
    keepoutRegionCount: number;
    solderWindowCount: number;
    locatingPinCount: number;
    clampCount: number;
    barrierMountHoleCount: number;
    springClipCount: number;
    locatingCandidateCount: number;
  };
  reviewItems?: FixtureResult["reviewItems"];
  locatingCandidates?: FixtureResult["locatingCandidates"];
  status?: "completed" | "review_required" | "failed";
  geometrySha256?: string;
  issues: Array<{
    id: string;
    code?: string;
    type?: string;
    title: string;
    description: string;
    severity: "info" | "warning" | "error" | "blocking";
    currentValue?: number;
    requiredValue?: number;
    unit?: string;
    confirmed?: boolean;
    target?: {
      layerId: string;
      objectId?: string;
      x: number;
      y: number;
      width?: number;
      height?: number;
    };
  }>;
}

const EMPTY_ANALYSIS: PCBAnalysis = {
  width: 0,
  height: 0,
  fileCount: 0,
  holeCount: 0,
  outlineClosed: false,
  outlineAreaMm2: 0,
  layers: [],
};

const EMPTY_RESULT: FixtureResult = {
  id: "",
  pcb: { width: 0, height: 0 },
  fixture: { width: 0, height: 0, thickness: 0, material: "待后端计算" },
  locatingPins: 0,
  clamps: 0,
  keepoutRegions: 0,
  solderWindows: 0,
  issues: [],
  status: "failed",
};

const DEFAULT_VISIBLE_LAYERS: Record<string, boolean> = {
  "pcb-outline": true,
  "pcb-copper": true,
  "pcb-drill": true,
  "locating-pin-candidates": true,
  "sink-region": true,
  "keepout-bot": true,
  "solder-top": true,
  "locating-pins": true,
  clamps: true,
  "fixture-outline": true,
  handholds: true,
  rails: true,
  "solder-barriers": true,
  "barrier-mount-holes": true,
  dimensions: true,
  "drc-overlay": true,
  "spring-clips": true,
  "gerber-top-copper": false,
  "gerber-bot-copper": false,
  "gerber-top-silk": false,
  "gerber-bot-silk": false,
  "gerber-top-mask": false,
  "gerber-bot-mask": false,
};

function toFixtureResult(
  job: Project,
  analysis: PCBAnalysis,
  result: BackendFixtureResult,
  previewSvg: string,
  _parameters: FixtureParameters,
): FixtureResult {
  return {
    id: job.id,
    pcb: { width: analysis.width ?? 0, height: analysis.height ?? 0 },
    fixture: {
      width: result.fixtureWidth ?? 0,
      height: result.fixtureHeight ?? 0,
      thickness: 0,
      material: "待工程确认",
    },
    locatingPins: result.featureSummary?.locatingPinCount ?? (result as any).locatingPins ?? 0,
    clamps: result.featureSummary?.clampCount ?? (result as any).clamps ?? 0,
    keepoutRegions: result.featureSummary?.keepoutRegionCount ?? (result as any).keepoutRegions ?? 0,
    solderWindows: result.featureSummary?.solderWindowCount ?? (result as any).solderWindows ?? 0,
    springClips: result.featureSummary?.springClipCount ?? (result as any).springClips ?? 0,
    issues: result.issues.map((issue) => ({
      id: issue.id,
      type: issue.type || issue.code || "DRC_ISSUE",
      title: issue.title,
      description: issue.description,
      severity: issue.severity,
      currentValue: issue.currentValue,
      requiredValue: issue.requiredValue,
      unit: issue.unit,
      confirmed: issue.confirmed,
      target: issue.target,
    })),
    reviewItems: result.reviewItems || [],
    locatingCandidates: result.locatingCandidates || [],
    previewSvg,
    geometrySha256: result.geometrySha256,
    algorithmVersion: (result as any).algorithmVersion,
    softwareVersion: (result as any).softwareVersion,
    ruleProfileVersion: (result as any).ruleProfileVersion,
    status: (result.status as any) || (job.status as any) || "completed",
  };
}

export interface ProjectState {
  currentProject: Project | null;
  sourceFile: File | null;
  uploadedFileMeta: UploadedFileMeta | null;
  analysis: PCBAnalysis;
  fixtureResult: FixtureResult;
  parameters: FixtureParameters;
  manualLocatingPins: string[];
  jobStatus: JobStatus;
  jobProgress: number;
  previewSvg: string | null;
  visibleLayers: Record<string, boolean>;
  viewMode: ViewMode;
  cadTransform: { scale: number; x: number; y: number };
  hoverCoordinate: { x: number; y: number } | null;
  highlightTarget: { objectId?: string; x: number; y: number; width: number; height: number } | null;

  isParameterDrawerOpen: boolean;
  isAiDrawerOpen: boolean;
  isLayerConfirmModalOpen: boolean;
  isAiSettingsOpen: boolean;
  toast: { message: string; type: "info" | "success" | "warning" | "error" } | null;

  aiMessages: AiMessage[];
  aiIsLoading: boolean;
  aiError: string | null;
  isAiThinking: boolean;

  setCurrentProject: (project: Project | null) => void;
  setSourceFile: (file: File | null) => void;
  setUploadedFileMeta: (meta: UploadedFileMeta | null) => void;
  setJobStatus: (status: JobStatus) => void;
  setJobProgress: (progress: number) => void;
  setAnalysis: (analysis: PCBAnalysis) => void;
  setFixtureResult: (result: FixtureResult) => void;
  hydrateJob: (jobId: string) => Promise<Project>;
  
  // Review
  acceptReview: (reviewId: string) => Promise<void>;
  rejectReview: (reviewId: string) => Promise<void>;
  toggleManualPin: (drillId: string) => Promise<void>;

  // AI Assistant methods
  sendAiMessage: (prompt: string) => Promise<void>;
  applyAiCommand: (message: AiMessage) => Promise<void>;
  rejectAiCommand: (messageId: string, reason?: string) => void;
  clearAiConversation: () => void;

  updateParameters: (params: Partial<FixtureParameters>) => void;
  regenerate: () => Promise<void>;
  resetParameters: () => void;

  toggleLayer: (layerId: string) => void;
  setLayerVisibility: (layerId: string, visible: boolean) => void;
  setViewMode: (mode: ViewMode) => void;

  setCadTransform: (transform: Partial<{ scale: number; x: number; y: number }>) => void;
  resetCadView: () => void;
  setHoverCoordinate: (coord: { x: number; y: number } | null) => void;
  locateIssue: (issue: DesignIssue) => void;
  confirmIssue: (issueId: string) => void;
  overrideDrc: (issueId: string, operator?: string, reason?: string) => Promise<void>;
  revokeDrcOverride: (issueId: string) => Promise<void>;
  confirmLayers: (layers: GerberLayer[]) => Promise<void>;

  toggleParameterDrawer: (open?: boolean) => void;
  toggleAiDrawer: (open?: boolean) => void;
  toggleLayerConfirmModal: (open?: boolean) => void;
  toggleAiSettingsModal: (open?: boolean) => void;
  showToast: (message: string, type?: "info" | "success" | "warning" | "error") => void;
  hideToast: () => void;
  resetProject: () => void;

  loadNormalDemo: () => void;
  loadErrorDemo: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProject: null,
  sourceFile: null,
  uploadedFileMeta: null,
  analysis: EMPTY_ANALYSIS,
  fixtureResult: EMPTY_RESULT,
  parameters: { ...DEFAULT_PARAMETERS },
  manualLocatingPins: [],
  jobStatus: "idle",
  jobProgress: 0,
  previewSvg: null,
  visibleLayers: { ...DEFAULT_VISIBLE_LAYERS },
  viewMode: "all",
  cadTransform: { scale: 1, x: 0, y: 0 },
  hoverCoordinate: null,
  highlightTarget: null,
  isParameterDrawerOpen: false,
  isAiDrawerOpen: false,
  isLayerConfirmModalOpen: false,
  isAiSettingsOpen: false,
  toast: null,
  aiMessages: [],
  aiIsLoading: false,
  aiError: null,
  isAiThinking: false,

  setCurrentProject: (project) => set({ currentProject: project }),
  setSourceFile: (file) => set({ sourceFile: file }),
  setUploadedFileMeta: (meta) => set({ uploadedFileMeta: meta }),
  setJobStatus: (status) => set({ jobStatus: status }),
  setJobProgress: (progress) => set({ jobProgress: progress }),
  setAnalysis: (analysis) => set({ analysis }),
  setFixtureResult: (result) => set({ fixtureResult: result }),

  hydrateJob: async (jobId: string) => {
    const job = await fixtureApi.getJob(jobId);
    set({ currentProject: job, jobStatus: job.status, jobProgress: job.progress });

    if (job.status === "layer_confirmation") {
      try {
        const analysis = await fixtureApi.getAnalysis(jobId);
        set({ analysis, isLayerConfirmModalOpen: true });
      } catch {}
      return job;
    }

    if (job.status === "completed" || job.status === "review_required") {
      const [analysis, result, previewSvg] = await Promise.all([
        fixtureApi.getAnalysis(jobId),
        fixtureApi.getResult(jobId),
        fixtureApi.getPreviewSvg(jobId),
      ]);
      const mappedResult = toFixtureResult(job, analysis, result as any, previewSvg, get().parameters);
      set({ analysis, fixtureResult: mappedResult, previewSvg, jobStatus: job.status });
    }
    return job;
  },

  acceptReview: async (reviewId: string) => {
    const job = get().currentProject;
    if (!job) return;
    try {
      await fixtureApi.acceptReview(job.id, reviewId);
      await get().hydrateJob(job.id);
      get().showToast("审核项已接受并重新计算治具几何", "success");
    } catch (e) {
      get().showToast(`操作失败: ${(e as Error).message}`, "error");
    }
  },

  rejectReview: async (reviewId: string) => {
    const job = get().currentProject;
    if (!job) return;
    try {
      await fixtureApi.rejectReview(job.id, reviewId);
      await get().hydrateJob(job.id);
      get().showToast("审核项已拒绝并更新治具几何", "info");
    } catch (e) {
      get().showToast(`操作失败: ${(e as Error).message}`, "error");
    }
  },

  toggleManualPin: async (drillId: string) => {
    const job = get().currentProject;
    if (!job) return;
    const cleanId = drillId.replace(/^pin-cand-/, "").replace(/^pin-/, "");
    const currentPins = [...get().manualLocatingPins];
    const index = currentPins.findIndex(
      (p) => p === cleanId || p.replace(/^pin-cand-/, "").replace(/^pin-/, "") === cleanId
    );
    if (index >= 0) {
      currentPins.splice(index, 1);
    } else {
      currentPins.push(cleanId);
    }
    set({ manualLocatingPins: currentPins });
    try {
      await fixtureApi.regenerate(job.id, get().parameters, currentPins);
      await get().hydrateJob(job.id);
      get().showToast(`定位销设置已更新: ${cleanId}`, "success");
    } catch (e) {
      get().showToast(`更新定位销失败: ${(e as Error).message}`, "error");
    }
  },

  sendAiMessage: async (prompt: string) => {
    const job = get().currentProject;
    const userMsg: AiMessage = {
      id: `ai-msg-${Date.now()}`,
      role: "user",
      content: prompt,
      createdAt: new Date().toISOString(),
    };
    set({ aiMessages: [...get().aiMessages, userMsg], aiIsLoading: true, aiError: null });

    if (!job) {
      set({
        aiIsLoading: false,
        aiError: "请先上传并解析工程任务。",
      });
      return;
    }

    try {
      const response = await fixtureApi.sendAiCommand(job.id, {
        userMessage: prompt,
        conversationId: job.id,
        apply: false,
      });

      const assistantMsg: AiMessage = {
        id: `ai-msg-${Date.now() + 1}`,
        role: "assistant",
        content: response.message,
        createdAt: new Date().toISOString(),
        command: response.command,
        commandStatus: response.command?.requiresConfirmation ? "pending" : undefined,
      };

      set({
        aiMessages: [...get().aiMessages, assistantMsg],
        aiIsLoading: false,
      });
    } catch (error) {
      set({
        aiIsLoading: false,
        aiError: (error as Error).message || "AI 助手请求失败",
      });
    }
  },

  applyAiCommand: async (message: AiMessage) => {
    const job = get().currentProject;
    const command = message.command;
    if (!job || !command) return;

    try {
      await fixtureApi.sendAiCommand(job.id, {
        userMessage: command.reason || "apply",
        conversationId: job.id,
        command,
        apply: true,
      });

      set({
        aiMessages: get().aiMessages.map((m) =>
          m.id === message.id ? { ...m, commandStatus: "applied" } : m
        ),
      });

      await get().hydrateJob(job.id);

      if (command.kind === "locate_issue" && command.issueId) {
        const issue = get().fixtureResult.issues.find((i) => i.id === command.issueId);
        if (issue) {
          get().locateIssue(issue);
        }
      }

      get().showToast(`AI 建设指令已执行并完成出图`, "success");
    } catch (error) {
      set({
        aiMessages: get().aiMessages.map((m) =>
          m.id === message.id ? { ...m, commandStatus: "failed" } : m
        ),
      });
      get().showToast(`应用 AI 命令失败: ${(error as Error).message}`, "error");
    }
  },

  rejectAiCommand: (messageId: string, _reason?: string) => {
    set({
      aiMessages: get().aiMessages.map((m) =>
        m.id === messageId ? { ...m, commandStatus: "rejected" } : m
      ),
    });
    get().showToast("已忽略 AI 建议", "info");
  },

  clearAiConversation: () => {
    set({ aiMessages: [] });
  },

  updateParameters: (params) => {
    set({ parameters: { ...get().parameters, ...params } });
  },

  regenerate: async () => {
    const job = get().currentProject;
    if (!job) {
      get().showToast("当前没有打开的工程任务", "warning");
      return;
    }
    try {
      await fixtureApi.updateParameters(job.id, get().parameters);
      const nextJob = await fixtureApi.regenerate(job.id, get().parameters, get().manualLocatingPins);
      set({ currentProject: nextJob, jobStatus: nextJob.status, previewSvg: null });
      await get().hydrateJob(nextJob.id);
    } catch (error) {
      get().showToast(`重新生成失败: ${(error as Error).message}`, "error");
      throw error;
    }
  },

  resetParameters: () => {
    set({ parameters: { ...DEFAULT_PARAMETERS } });
    get().showToast("已恢复默认工程参数", "info");
  },

  toggleLayer: (layerId) => set({
    visibleLayers: { ...get().visibleLayers, [layerId]: !get().visibleLayers[layerId] },
  }),

  setLayerVisibility: (layerId, visible) => set({
    visibleLayers: { ...get().visibleLayers, [layerId]: visible },
  }),

  setViewMode: (mode) => {
    const layers = { ...get().visibleLayers };
    const pcb = ["pcb-outline", "pcb-copper", "pcb-drill", "locating-pin-candidates"];
    const fixture = ["sink-region", "keepout-bot", "solder-top", "locating-pins", "clamps", "fixture-outline", "handholds", "rails", "solder-barriers", "barrier-mount-holes", "spring-clips", "dimensions", "drc-overlay"];
    if (mode === "pcb_only") {
      [...pcb, ...fixture].forEach((layer) => { layers[layer] = pcb.includes(layer); });
    } else if (mode === "fixture_only") {
      [...pcb, ...fixture].forEach((layer) => { layers[layer] = fixture.includes(layer) || layer === "pcb-outline"; });
    } else {
      Object.keys(DEFAULT_VISIBLE_LAYERS).forEach((layer) => { layers[layer] = DEFAULT_VISIBLE_LAYERS[layer]; });
    }
    set({ viewMode: mode, visibleLayers: layers });
  },

  setCadTransform: (transform) => set({ cadTransform: { ...get().cadTransform, ...transform } }),
  resetCadView: () => set({ cadTransform: { scale: 1, x: 0, y: 0 } }),
  setHoverCoordinate: (hoverCoordinate) => set({ hoverCoordinate }),

  locateIssue: (issue) => {
    if (!issue.target) {
      get().showToast(`该项无几何定位信息: ${issue.title}`, "info");
      return;
    }
    const layers = { ...get().visibleLayers, [issue.target.layerId]: true, "drc-overlay": true };
    set({
      visibleLayers: layers,
      cadTransform: { scale: 1.6, x: 0, y: 0 },
      highlightTarget: {
        objectId: issue.target.objectId,
        x: issue.target.x,
        y: issue.target.y,
        width: issue.target.width || 5,
        height: issue.target.height || 5,
      },
    });
    get().showToast(`已在图纸中定位: ${issue.title}`, "warning");
    window.setTimeout(() => set({ highlightTarget: null }), 2500);
  },

  confirmIssue: (issueId) => set({
    fixtureResult: {
      ...get().fixtureResult,
      issues: get().fixtureResult.issues.map((issue) => issue.id === issueId ? { ...issue, confirmed: true } : issue),
    },
  }),

  overrideDrc: async (issueId: string, operator = "工程师", reason = "人工核对无干涉，确认放行") => {
    const job = get().currentProject;
    if (!job) {
      get().confirmIssue(issueId);
      return;
    }
    try {
      await fixtureApi.overrideDrc(job.id, issueId, operator, reason);
      set({
        fixtureResult: {
          ...get().fixtureResult,
          issues: get().fixtureResult.issues.map((issue) =>
            issue.id === issueId ? { ...issue, confirmed: true } : issue
          ),
        },
      });
      await get().hydrateJob(job.id);
      get().showToast(`DRC 问题已放行确认: ${issueId}`, "success");
    } catch (error) {
      get().confirmIssue(issueId);
      get().showToast(`已本地标记确认: ${issueId}`, "info");
    }
  },

  revokeDrcOverride: async (issueId: string) => {
    const job = get().currentProject;
    if (!job) {
      set({
        fixtureResult: {
          ...get().fixtureResult,
          issues: get().fixtureResult.issues.map((issue) =>
            issue.id === issueId ? { ...issue, confirmed: false } : issue
          ),
        },
      });
      return;
    }
    try {
      await fixtureApi.revokeDrcOverride(job.id, issueId);
      set({
        fixtureResult: {
          ...get().fixtureResult,
          issues: get().fixtureResult.issues.map((issue) =>
            issue.id === issueId ? { ...issue, confirmed: false } : issue
          ),
        },
      });
      await get().hydrateJob(job.id);
      get().showToast(`DRC 放行已撤销: ${issueId}`, "info");
    } catch (error) {
      get().showToast(`撤销失败: ${(error as Error).message}`, "error");
    }
  },

  confirmLayers: async (layers) => {
    const job = get().currentProject;
    if (!job) return;
    await fixtureApi.confirmLayers(job.id, layers);
    set({ analysis: { ...get().analysis, layers: layers.map((layer) => ({ ...layer, confirmed: true })) }, isLayerConfirmModalOpen: false });
    await get().hydrateJob(job.id);
    get().showToast("Gerber 图层映射已提交，后端重新出图中", "success");
  },

  toggleParameterDrawer: (open) => set({ isParameterDrawerOpen: open ?? !get().isParameterDrawerOpen, isAiDrawerOpen: false }),
  toggleAiDrawer: (open) => set({ isAiDrawerOpen: open ?? !get().isAiDrawerOpen, isParameterDrawerOpen: false }),
  toggleLayerConfirmModal: (open) => set({ isLayerConfirmModalOpen: open ?? !get().isLayerConfirmModalOpen }),
  toggleAiSettingsModal: (open) => set({ isAiSettingsOpen: open ?? !get().isAiSettingsOpen }),

  showToast: (message, type = "info") => {
    set({ toast: { message, type } });
    window.setTimeout(() => { if (get().toast?.message === message) set({ toast: null }); }, 3000);
  },
  hideToast: () => set({ toast: null }),

  resetProject: () => set({
    currentProject: null,
    sourceFile: null,
    uploadedFileMeta: null,
    analysis: EMPTY_ANALYSIS,
    fixtureResult: EMPTY_RESULT,
    parameters: { ...DEFAULT_PARAMETERS },
    manualLocatingPins: [],
    jobStatus: "idle",
    previewSvg: null,
    visibleLayers: { ...DEFAULT_VISIBLE_LAYERS },
    viewMode: "all",
    cadTransform: { scale: 1, x: 0, y: 0 },
    highlightTarget: null,
    isParameterDrawerOpen: false,
    isAiDrawerOpen: false,
    isLayerConfirmModalOpen: false,
    isAiSettingsOpen: false,
  }),

  loadNormalDemo: () => {
    const { svg, result, analysis } = buildDemoFixture(get().parameters || DEFAULT_PARAMETERS, ["D1", "D2"]);
    set({
      currentProject: {
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
      },
      analysis,
      fixtureResult: result,
      previewSvg: svg,
      jobStatus: "completed",
      visibleLayers: { ...DEFAULT_VISIBLE_LAYERS },
    });
    get().showToast("已成功载入工业级波峰焊治具演示案例！", "success");
  },

  loadErrorDemo: () => {
    set({
      currentProject: { id: "ERR-OUTLINE-MISSING", name: "ERR-DEMO-NO-OUTLINE.zip", createdAt: new Date().toISOString(), status: "failed", progress: 30, errorCode: "MISSING_OUTLINE_LAYER", errorMessage: "未检测到有效 PCB 外形层", logs: [] },
      analysis: { ...MOCK_ERROR_PCB_ANALYSIS },
      jobStatus: "failed",
    });
    get().showToast("已载入异常图层演示", "error");
  },
}));



