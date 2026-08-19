import { FixtureApi } from "./fixtureApi";
import { mockFixtureApi } from "./mockFixtureApi";
import { httpFixtureApi } from "./httpFixtureApi";

/** 正式流程默认使用真实 HTTP API；Mock 必须在开发环境显式启用。 */
export const fixtureApi: FixtureApi =
  import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_API === "true"
    ? mockFixtureApi
    : httpFixtureApi;

/**
 * 轮询任务直到完成
 * 
 * @param jobId 任务ID
 * @param interval 轮询间隔（毫秒）
 * @param onProgress 进度回调
 * @returns 最终项目状态
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

    // 终止条件
    if (
      project.status === "completed" ||
      project.status === "failed" ||
      project.status === "review_required"
    ) {
      return project;
    }

    // 等待下一次轮询
    await new Promise((resolve) => setTimeout(resolve, interval));
  }

  return abortController;
}
