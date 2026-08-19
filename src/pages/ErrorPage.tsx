import React, { useState } from "react";
import { TopNavBar } from "../components/layout/TopNavBar";
import { StatusBar } from "../components/layout/StatusBar";
import { useProjectStore } from "../store/useProjectStore";
import { DiagnosticLog } from "../types/project";

export const ErrorPage: React.FC = () => {
  const [showLogs, setShowLogs] = useState(true);
  const {
    currentProject,
    setJobStatus,
    resetProject,
    toggleLayerConfirmModal
  } = useProjectStore();

  const error = currentProject?.error;
  const errorCode = error?.code || currentProject?.errorCode || "UNKNOWN";
  const errorTitle = error?.title || "处理失败";
  const errorMessage = error?.message || currentProject?.errorMessage || "未知错误";
  const errorDetails = error?.details || [];

  const logs: DiagnosticLog[] = currentProject?.logs?.length ? currentProject.logs : [
    { time: "14:02:11", level: "info", message: "文件加载完成" },
    { time: "14:02:12", level: "info", message: "检测到 17 个 Gerber 文件" },
    { time: "14:02:12", level: "info", message: "正在识别 Board Outline" },
    { time: "14:02:13", level: "error", message: "未找到可信 PCB 外形层" },
    { time: "14:02:13", level: "error", message: "任务终止 (Job halted)" }
  ];

  const handleRetry = () => {
    if (currentProject?.id) {
      setJobStatus("parsing");
    }
  };

  const getErrorActions = () => {
    switch (errorCode) {
      case "OUTLINE_NOT_FOUND":
      case "MISSING_OUTLINE_LAYER":
      case "INVALID_OUTLINE":
      case "UNKNOWN_CRITICAL_LAYER":
      case "MISSING_DRILL_LAYER":
      case "INVALID_EXCELLON":
        return (
          <>
            <button
              onClick={() => toggleLayerConfirmModal(true)}
              className="bg-primary-container text-on-primary-fixed font-headline-md px-6 py-2.5 rounded font-bold hover:bg-surface-tint glow-cyan transition-colors flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">layers</span>
              手动选择 PCB 外形层
            </button>
            <button
              onClick={resetProject}
              className="bg-transparent border border-outline-variant text-on-surface font-body-md px-6 py-2.5 rounded hover:bg-surface-container-highest hover:border-on-surface-variant transition-colors flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">upload</span>
              重新上传文件
            </button>
          </>
        );
      
      case "NETWORK_ERROR":
        return (
          <>
            <button
              onClick={handleRetry}
              className="bg-primary-container text-on-primary-fixed font-headline-md px-6 py-2.5 rounded font-bold hover:bg-surface-tint glow-cyan transition-colors flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">refresh</span>
              重试
            </button>
          </>
        );
      
      default:
        return (
          <button
            onClick={resetProject}
            className="bg-primary-container text-on-primary-fixed font-headline-md px-6 py-2.5 rounded font-bold hover:bg-surface-tint glow-cyan transition-colors flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">upload</span>
            重新上传
          </button>
        );
    }
  };

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-background text-on-background">
      <TopNavBar />

      <main className="flex-1 flex items-center justify-center relative cyber-grid p-panel-padding overflow-y-auto">
        <div className="max-w-2xl w-full bg-surface-container border border-error/50 p-8 rounded relative overflow-hidden glow-error z-10">
          {/* Top border red line */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-error-container via-error to-error-container"></div>

          <div className="absolute top-0 right-0 p-3 opacity-60 font-data-mono text-[11px] text-error">
            ERR_CODE: {errorCode}
          </div>

          <div className="flex flex-col md:flex-row gap-6 items-start mt-2">
            {/* Warning Icon Box */}
            <div className="flex-shrink-0 flex items-center justify-center w-14 h-14 bg-error-container/20 border border-error/40 rounded relative">
              <span className="material-symbols-outlined text-4xl text-error fill-1">warning</span>
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-error rounded-full animate-ping"></div>
            </div>

            {/* Content Area */}
            <div className="flex-grow space-y-5">
              <div>
                <h1 className="font-headline-lg text-headline-lg text-error mb-2 tracking-tight font-bold">
                  {errorTitle}
                </h1>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  {errorMessage}
                </p>
              </div>

              {/* Diagnostic Box */}
              <div className="bg-surface border border-outline-variant rounded p-4">
                <div
                  onClick={() => setShowLogs(!showLogs)}
                  className="flex items-center justify-between cursor-pointer border-b border-outline-variant pb-2 mb-3"
                >
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm text-on-surface-variant">analytics</span>
                    <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider">
                      诊断日志 (DIAGNOSTIC LOG)
                    </span>
                  </div>
                  <span className="material-symbols-outlined text-sm text-on-surface-variant">
                    {showLogs ? "expand_less" : "expand_more"}
                  </span>
                </div>

                {showLogs && (
                  <div className="space-y-3 font-data-mono text-[11px]">
                    {/* 错误详情 */}
                    {errorDetails.length > 0 && (
                      <div className="space-y-2 border-b border-outline-variant/40 pb-3">
                        {errorDetails.map((detail, idx) => (
                          <div key={idx} className="flex items-start gap-2">
                            <span className="material-symbols-outlined text-error text-[16px] mt-0.5 fill-1">info</span>
                            <div>
                              <span className="text-on-surface-variant">{detail}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 日志行 */}
                    <div className="bg-surface-container-lowest p-2.5 rounded text-on-surface-variant space-y-1 font-data-mono text-[10px]">
                      {logs.map((lg: DiagnosticLog, i: number) => (
                        <div key={i} className="flex gap-2">
                          <span className="opacity-50">[{lg.time}]</span>
                          <span className={lg.level === "error" ? "text-error font-bold" : "text-on-surface"}>
                            {lg.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                {getErrorActions()}
              </div>
            </div>
          </div>
        </div>
      </main>

      <StatusBar />
    </div>
  );
};
