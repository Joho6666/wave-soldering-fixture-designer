import { GerberLayer, PCBAnalysis } from "../types/gerber";
import { FixtureParameters, FixtureResult, ReviewItem, ProductionGateResult } from "../types/fixture";
import { Project } from "../types/project";
import { AiSettingsResponse, AiSettingsUpdate, AiTestConnectionResponse } from "../types/settings";
import { AiCommandRequest, AiCommandResponse } from "../types/ai";

/**
 * 治具设计 API 接口定义
 */
export interface FixtureApi {
  createJob(file: File): Promise<Project>;
  getJob(id: string): Promise<Project>;
  getAnalysis(id: string): Promise<PCBAnalysis>;
  confirmLayers(id: string, layers: GerberLayer[]): Promise<void>;
  updateParameters(id: string, params: FixtureParameters): Promise<void>;
  regenerate(id: string, params?: FixtureParameters, manualPins?: string[]): Promise<Project>;
  getResult(id: string): Promise<FixtureResult>;
  getPreviewSvg(id: string): Promise<string>;
  downloadDxf(id: string): Promise<Blob>;
  
  // Review 审核 API
  getReviews(id: string): Promise<ReviewItem[]>;
  acceptReview(id: string, reviewId: string): Promise<void>;
  rejectReview(id: string, reviewId: string): Promise<void>;
  modifyReview(id: string, reviewId: string, modifiedData?: Record<string, any>): Promise<void>;
  completeReviews(id: string): Promise<void>;

  // DRC Override & Production Gate
  overrideDrc(id: string, issueId: string, operator: string, reason: string): Promise<void>;
  revokeDrcOverride(id: string, issueId: string): Promise<void>;
  getProductionGate(id: string): Promise<ProductionGateResult>;
  downloadPreviewDxf(id: string): Promise<Blob>;

  // AI 智能诊断
  sendAiCommand(jobId: string, request: AiCommandRequest): Promise<AiCommandResponse>;
  getAiSettings(): Promise<AiSettingsResponse>;
  updateAiSettings(update: AiSettingsUpdate): Promise<AiSettingsResponse>;
  testAiConnection(): Promise<AiTestConnectionResponse>;
}
