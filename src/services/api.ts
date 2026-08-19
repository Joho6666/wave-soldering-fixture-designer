import { FixtureApi } from "./fixtureApi";
import { mockFixtureApi } from "./mockFixtureApi";
import { httpFixtureApi } from "./httpFixtureApi";

/**
 * 智能 API 派发器：
 * 1. 若显式开启 Mock 或处于无后端云端托管（如 Netlify 纯静态演示），自动使用纯前端高精度演示引擎；
 * 2. 若配置了有效 VITE_API_BASE_URL，自动走真实云端 Python FastAPI。
 */
const hasBackendUrl = Boolean(
  import.meta.env.VITE_API_BASE_URL &&
  import.meta.env.VITE_API_BASE_URL.trim() !== "" &&
  !import.meta.env.VITE_API_BASE_URL.includes("localhost")
);

const isExplicitMock = import.meta.env.VITE_USE_MOCK_API === "true";

// 在生产环境下若未提供远程后端地址，自动启用客户端全功能演示引擎
export const isClientDemoMode = isExplicitMock || (!import.meta.env.DEV && !hasBackendUrl);

export const fixtureApi: FixtureApi = isClientDemoMode ? mockFixtureApi : httpFixtureApi;

/**
 * 轮询任务直到完成
 */
export async function pollJobUntilFinished(
  jobId: string,
  interval: number = 1000,
  onProgress?: (project: any) => void
): Promise<any> {
  let aborted = false;
  const abortController = {
    abort: () => {
      aborted = true;
    },
  };

  while (!aborted) {
    const project = await fixtureApi.getJob(jobId);
    
    if (onProgress) {
      onProgress(project);
    }

    if (
      project.status === "completed" ||
      project.status === "failed" ||
      project.status === "review_required"
    ) {
      return project;
    }

    await new Promise((resolve) => setTimeout(resolve, interval));
  }

  return abortController;
}
