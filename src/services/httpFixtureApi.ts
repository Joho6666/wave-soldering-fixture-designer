import { FixtureApi } from "./fixtureApi";
import { GerberLayer, PCBAnalysis } from "../types/gerber";
import { FixtureParameters, FixtureResult, ReviewItem, ProductionGateResult } from "../types/fixture";
import { Project } from "../types/project";
import { AiSettingsResponse, AiSettingsUpdate, AiTestConnectionResponse } from "../types/settings";
import { AiCommandRequest, AiCommandResponse } from "../types/ai";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

class HttpFixtureApiService implements FixtureApi {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    return response.json();
  }

  async createJob(file: File): Promise<Project> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/jobs`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getJob(id: string): Promise<Project> {
    return this.request<Project>(`/api/jobs/${id}`);
  }

  async getAnalysis(id: string): Promise<PCBAnalysis> {
    return this.request<PCBAnalysis>(`/api/jobs/${id}/analysis`);
  }

  async confirmLayers(id: string, layers: GerberLayer[]): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/layers/confirm`, {
      method: "POST",
      body: JSON.stringify({ layers }),
    });
  }

  async updateParameters(id: string, params: FixtureParameters): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/parameters`, {
      method: "PUT",
      body: JSON.stringify(params),
    });
  }

  async regenerate(id: string, params?: FixtureParameters, manualPins?: string[]): Promise<Project> {
    return this.request<Project>(`/api/jobs/${id}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ parameters: params, manualLocatingPins: manualPins }),
    });
  }

  async getResult(id: string): Promise<FixtureResult> {
    return this.request<FixtureResult>(`/api/jobs/${id}/result`);
  }

  async getPreviewSvg(id: string): Promise<string> {
    const response = await fetch(`${API_BASE_URL}/api/jobs/${id}/preview.svg`);
    if (!response.ok) {
      throw new Error(`Failed to load SVG preview: ${response.statusText}`);
    }
    return response.text();
  }

  async downloadDxf(id: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/jobs/${id}/result.dxf`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Download failed: ${response.statusText}`);
    }
    return response.blob();
  }

  async getReviews(id: string): Promise<ReviewItem[]> {
    return this.request<ReviewItem[]>(`/api/jobs/${id}/reviews`);
  }

  async acceptReview(id: string, reviewId: string): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/reviews/${reviewId}/accept`, {
      method: "POST",
    });
  }

  async rejectReview(id: string, reviewId: string): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/reviews/${reviewId}/reject`, {
      method: "POST",
    });
  }

  async modifyReview(id: string, reviewId: string, modifiedData?: Record<string, any>): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/reviews/${reviewId}/modify`, {
      method: "POST",
      body: JSON.stringify({ action: "modify", modifiedData }),
    });
  }

  async completeReviews(id: string): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/reviews/complete`, {
      method: "POST",
    });
  }

  async overrideDrc(id: string, issueId: string, operator: string, reason: string): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/drc/${issueId}/override`, {
      method: "POST",
      body: JSON.stringify({ operator, reason }),
    });
  }

  async revokeDrcOverride(id: string, issueId: string): Promise<void> {
    await this.request<void>(`/api/jobs/${id}/drc/${issueId}/override`, {
      method: "DELETE",
    });
  }

  async getProductionGate(id: string): Promise<ProductionGateResult> {
    return this.request<ProductionGateResult>(`/api/jobs/${id}/production-gate`);
  }

  async downloadPreviewDxf(id: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/jobs/${id}/preview.dxf`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Preview DXF download failed: ${response.statusText}`);
    }
    return response.blob();
  }

  async sendAiCommand(jobId: string, request: AiCommandRequest): Promise<AiCommandResponse> {
    return this.request<AiCommandResponse>(`/api/jobs/${jobId}/ai/command`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async getAiSettings(): Promise<AiSettingsResponse> {
    return this.request<AiSettingsResponse>("/api/settings/ai");
  }

  async updateAiSettings(update: AiSettingsUpdate): Promise<AiSettingsResponse> {
    return this.request<AiSettingsResponse>("/api/settings/ai", {
      method: "PUT",
      body: JSON.stringify(update),
    });
  }

  async testAiConnection(): Promise<AiTestConnectionResponse> {
    return this.request<AiTestConnectionResponse>("/api/settings/ai/test", {
      method: "POST",
    });
  }
}

export const httpFixtureApi = new HttpFixtureApiService();
