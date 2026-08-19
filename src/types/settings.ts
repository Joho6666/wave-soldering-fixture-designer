/**
 * AI 服务商与 API 设置类型定义
 */

export type AiProviderType = "openai_compatible";

export interface AiSettingsResponse {
  aiEnabled: boolean;
  aiProvider: string;
  aiBaseUrl: string;
  aiModel: string;
  aiApiKeyMasked: string;
  aiTimeoutMs: number;
}

export interface AiSettingsUpdate {
  aiEnabled: boolean;
  aiProvider?: string;
  aiBaseUrl?: string;
  aiModel?: string;
  aiApiKey?: string;
  aiTimeoutMs?: number;
}

export interface AiTestConnectionResponse {
  ok: boolean;
  message: string;
}
