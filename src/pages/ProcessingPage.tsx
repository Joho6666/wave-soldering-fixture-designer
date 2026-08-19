import React, { useEffect, useMemo } from "react";
import { TopNavBar } from "../components/layout/TopNavBar";
import { StatusBar } from "../components/layout/StatusBar";
import { useProjectStore } from "../store/useProjectStore";
import { fixtureApi } from "../services/api";

const STATUS_LABELS: Record<string, string> = {
  uploading: "正在上传 Gerber ZIP",
  parsing: "正在解析 Gerber 制造文件",
  layer_confirmation: "需要确认 Gerber 图层",
  generating: "正在生成治具几何",
  review_required: "生成完成，等待人工确认",
  completed: "治具设计完成",
  failed: "任务处理失败",
};

export const ProcessingPage: React.FC = () => {
  const {
    currentProject,
    analysis,
    jobStatus,
    setCurrentProject,
    setJobStatus,
    setAnalysis,
    hydrateJob,
    toggleLayerConfirmModal,
    showToast,
  } = useProjectStore();

  useEffect(() => {
    if (!currentProject?.id) return;

    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const job = await fixtureApi.getJob(currentProject.id);
        if (cancelled) return;

        setCurrentProject(job);
        setJobStatus(job.status);

        if (job.status === "layer_confirmation") {
          try {
            const analysisData = await fixtureApi.getAnalysis(job.id);
            if (!cancelled) {
              setAnalysis(analysisData);
            }
          } catch {
            // 降级使用已有 analysis
          }
          if (!cancelled) {
            toggleLayerConfirmModal(true);
          }
          return;
        }

        if (job.status === "completed" || job.status === "review_required") {
          await hydrateJob(job.id);
          return;
        }

        if (job.status === "failed") {
          return;
        }

        timer = window.setTimeout(poll, 800);
      } catch (error) {
        if (!cancelled) {
          showToast(`读取任务状态失败: ${(error as Error).message}`, "error");
          setJobStatus("failed");
        }
      }
    };

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [currentProject?.id, hydrateJob, setCurrentProject, setJobStatus, showToast, toggleLayerConfirmModal]);

  const logs = currentProject?.logs || [];
  const progress = currentProject?.progress || 0;
  const title = currentProject?.currentStepDescription || STATUS_LABELS[jobStatus] || "正在处理";

  const analysisRows = useMemo(() => [
    ["PCB 尺寸", analysis.width > 0 ? `${analysis.width.toFixed(2)} × ${analysis.height.toFixed(2)} mm` : "等待解析"],
    ["制造文件", analysis.fileCount > 0 ? `${analysis.fileCount} 个` : "等待解析"],
    ["真实钻孔", analysis.holeCount > 0 ? `${analysis.holeCount} 孔` : "等待解析"],
    ["PCB 外形", analysis.outlineClosed ? "已识别闭合外形" : "正在检测"],
  ], [analysis]);

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-background text-on-surface">
      <TopNavBar />
      <div className="w-full h-[2px] bg-surface-variant z-10 shrink-0">
        <div className="h-full bg-primary-container transition-all duration-300 shadow-[0_0_8px_#00e5ff]" style={{ width: `${progress}%` }} />
      </div>

      <main className="flex-1 flex overflow-hidden p-panel-padding">
        <div className="flex-1 flex flex-col md:flex-row gap-container-gap h-full overflow-hidden">
          <section className="flex-[2] bg-surface-container border border-outline-variant flex flex-col overflow-hidden">
            <header className="h-toolbar-height bg-surface-container-high border-b border-outline-variant flex items-center px-panel-padding justify-between shrink-0">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary-container fill-1">memory</span>
                <h2 className="font-headline-md text-headline-md text-on-surface">真实治具生成进程</h2>
              </div>
              <div className="font-data-mono text-data-mono text-primary-container font-bold">{progress}% COMPLETE</div>
            </header>

            <div className="p-5 border-b border-outline-variant bg-surface-container-low">
              <div className="flex gap-3 items-center">
                <span className="material-symbols-outlined text-primary-container animate-spin">progress_activity</span>
                <div>
                  <p className="text-primary-container font-bold">{title}</p>
                  <p className="font-data-mono text-[11px] text-on-surface-variant">任务 ID: {currentProject?.id || "--"}</p>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-2 font-data-mono text-[12px]">
              {logs.length === 0 ? (
                <p className="text-on-surface-variant">等待后端任务日志…</p>
              ) : logs.map((log, index) => (
                <div key={`${log.time}-${index}`} className="flex gap-3 border-b border-outline-variant/30 py-2">
                  <span className="text-on-surface-variant">[{log.time}]</span>
                  <span className={log.level === "error" ? "text-error" : log.level === "warning" ? "text-tertiary-container" : "text-on-surface"}>{log.message}</span>
                </div>
              ))}
            </div>
          </section>

          <aside className="w-full md:w-[320px] flex flex-col gap-container-gap shrink-0">
            <div className="bg-surface-container border border-outline-variant flex-1 flex flex-col overflow-hidden">
              <header className="h-toolbar-height bg-[#1C2128] border-b border-outline-variant flex items-center px-panel-padding">
                <span className="material-symbols-outlined text-on-surface-variant mr-2">analytics</span>
                <h3 className="font-headline-md text-headline-md text-on-surface">后端 PCB 分析</h3>
              </header>
              <div className="p-panel-padding space-y-4 font-data-mono text-body-sm">
                {analysisRows.map(([label, value]) => (
                  <div key={label} className="flex justify-between items-center border-b border-outline-variant pb-2 gap-3">
                    <span className="text-on-surface-variant text-[12px]">{label}</span>
                    <span className="text-on-surface font-semibold text-right">{value}</span>
                  </div>
                ))}
              </div>
              <div className="mt-auto p-panel-padding">
                <div className="h-44 border border-outline-variant bg-[#0D1117] flex flex-col items-center justify-center text-center p-4">
                  <span className="material-symbols-outlined text-primary-container text-4xl mb-3 animate-pulse">precision_manufacturing</span>
                  <p className="text-on-surface font-medium">后端正在处理真实几何</p>
                  <p className="font-data-mono text-[10px] text-primary-container mt-2">{jobStatus.toUpperCase()}</p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
      <StatusBar />
    </div>
  );
};
