import { FixtureApi } from "./fixtureApi";
import { mockFixtureApi } from "./mockFixtureApi";
import { httpFixtureApi } from "./httpFixtureApi";

/**
 * Mock 只在显式打开时启用。
 *
 * 生产构建（launcher / dist 同源 FastAPI）必须走真实 /api。
 * 以前用「生产 + 没有非 localhost VITE_API_BASE_URL」自动切 mock，
 * 会导致本地交付包把真实 Gerber ZIP 当成前端演示板。
 */
export const isClientDemoMode = import.meta.env.VITE_USE_MOCK_API === "true";

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
