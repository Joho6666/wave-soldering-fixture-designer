import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const TopNavBar: React.FC = () => {
  const {
    jobStatus,
    uploadedFileMeta,
    currentProject,
    toggleParameterDrawer,
    toggleAiDrawer,
    isParameterDrawerOpen,
    isAiDrawerOpen,
    resetProject,
    loadNormalDemo,
    toggleAiSettingsModal,
    showToast
  } = useProjectStore();

  const projectName = uploadedFileMeta?.name || currentProject?.name || "未加载项目";

  return (
    <header className="bg-surface border-b border-outline-variant flex justify-between items-center h-toolbar-height px-panel-padding w-full z-40 shrink-0">
      {/* Brand & Project Info */}
      <div className="flex items-center gap-container-gap">
        <button
          onClick={resetProject}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          title="点击返回首页"
        >
          <span className="material-symbols-outlined text-primary-container fill-1">memory</span>
          <span className="font-headline-md text-headline-md font-bold text-primary-container tracking-tight">
            WAVE-FIXTURE AI
          </span>
        </button>

        {jobStatus !== "idle" ? (
          <>
            <div className="h-4 w-px bg-outline-variant mx-2"></div>
            <span className="font-data-mono text-body-sm text-on-surface-variant">
              项目: <span className="text-on-surface font-semibold">{projectName}</span>
            </span>
          </>
        ) : (
          <button
            onClick={loadNormalDemo}
            className="ml-3 px-3 py-1 bg-surface-container-high border border-primary-container/80 text-primary-container font-headline-md text-xs font-semibold rounded hover:bg-surface-tint/15 transition-colors flex items-center gap-1.5 shadow-sm"
            title="无需上传文件，一键载入工业级治具演示"
          >
            <span className="material-symbols-outlined text-[15px] text-amber-300">auto_awesome</span>
            <span>演示案例 (Demo)</span>
          </button>
        )}
      </div>

      {/* Nav Actions */}
      <div className="flex items-center gap-2">
        {(jobStatus === "completed" || jobStatus === "review_required") && (
          <>
            {/* 工程参数按钮 */}
            <button
              onClick={() => toggleParameterDrawer()}
              className={`px-3 py-1.5 border text-body-sm flex items-center gap-1.5 transition-colors ${
                isParameterDrawerOpen
                  ? "bg-surface-container-highest border-primary-container text-primary-container"
                  : "bg-surface border-outline-variant text-on-surface hover:bg-surface-container-high"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">tune</span>
              <span>工程参数</span>
            </button>

            {/* AI 工程助手按钮 */}
            <button
              onClick={() => toggleAiDrawer()}
              className={`px-3 py-1.5 border text-body-sm flex items-center gap-1.5 transition-colors ${
                isAiDrawerOpen
                  ? "bg-surface-container-highest border-primary-container text-primary-container"
                  : "bg-surface border-outline-variant text-on-surface hover:bg-surface-container-high"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">psychology</span>
              <span>AI 工程助手</span>
            </button>
          </>
        )}

        {/* 帮助与设置 */}
        <button
          onClick={() => showToast("WAVE-FIXTURE AI v0.1 波峰焊治具工业 CAD 辅助设计系统", "info")}
          className="p-1.5 text-on-surface-variant hover:text-primary-container transition-colors rounded"
          title="系统帮助"
        >
          <span className="material-symbols-outlined text-[20px]">help</span>
        </button>

        <button
          onClick={() => toggleAiSettingsModal(true)}
          className="p-1.5 text-on-surface-variant hover:text-primary-container transition-colors rounded"
          title="AI 服务配置"
        >
          <span className="material-symbols-outlined text-[20px]">settings</span>
        </button>

        {/* 用户头像占位 */}
        <div className="w-8 h-8 rounded-DEFAULT bg-surface-container-highest border border-outline-variant flex items-center justify-center text-primary-container ml-1">
          <span className="material-symbols-outlined text-[18px]">engineering</span>
        </div>
      </div>
    </header>
  );
};
