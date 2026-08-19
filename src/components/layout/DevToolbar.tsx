import React, { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const DevToolbar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const {
    jobStatus,
    setJobStatus,
    loadNormalDemo,
    loadErrorDemo,
    toggleLayerConfirmModal
  } = useProjectStore();

  return (
    <div className="fixed bottom-10 right-4 z-50 flex flex-col items-end gap-1 select-none opacity-90 hover:opacity-100 transition-opacity">
      {collapsed ? (
        <button
          onClick={() => setCollapsed(false)}
          className="bg-surface-container-high border border-primary-container text-primary-container px-2 py-1 font-data-mono text-[11px] hover:bg-surface-container-highest transition-colors shadow-lg"
          title="展开开发调试工具"
        >
          ⚙ 开发调试
        </button>
      ) : (
        <div className="bg-surface-container border border-outline-variant p-2 flex flex-col gap-1.5 shadow-2xl backdrop-blur-md min-w-[220px]">
          <div className="flex items-center justify-between border-b border-outline-variant pb-1">
            <span className="font-label-caps text-label-caps text-primary-container">开发测试面板 (DEV)</span>
            <button
              onClick={() => setCollapsed(true)}
              className="text-on-surface-variant hover:text-on-surface text-xs"
            >
              收起
            </button>
          </div>

          <div className="grid grid-cols-2 gap-1 font-data-mono text-[10px]">
            <button
              onClick={loadNormalDemo}
              className="px-2 py-1 bg-surface-bright text-on-surface border border-outline-variant hover:border-primary-container text-left"
            >
              ▶ 载入标准项目
            </button>
            <button
              onClick={loadErrorDemo}
              className="px-2 py-1 bg-surface-bright text-error border border-error/40 hover:border-error text-left"
            >
              ⚠ 载入异常项目
            </button>
            <button
              onClick={() => setJobStatus("idle")}
              className={`px-2 py-1 border text-left ${
                jobStatus === "idle" ? "border-primary-container text-primary-container" : "border-outline-variant text-on-surface"
              }`}
            >
              状态: 上传页
            </button>
            <button
              onClick={() => setJobStatus("generating")}
              className={`px-2 py-1 border text-left ${
                jobStatus === "generating" ? "border-primary-container text-primary-container" : "border-outline-variant text-on-surface"
              }`}
            >
              状态: 生成中
            </button>
            <button
              onClick={() => setJobStatus("completed")}
              className={`px-2 py-1 border text-left ${
                jobStatus === "completed" ? "border-primary-container text-primary-container" : "border-outline-variant text-on-surface"
              }`}
            >
              状态: CAD工作台
            </button>
            <button
              onClick={() => setJobStatus("failed")}
              className={`px-2 py-1 border text-left ${
                jobStatus === "failed" ? "border-error text-error" : "border-outline-variant text-on-surface"
              }`}
            >
              状态: 错误页
            </button>
            <button
              onClick={() => toggleLayerConfirmModal(true)}
              className="px-2 py-1 bg-surface-bright text-tertiary-container border border-outline-variant hover:border-tertiary-container text-left col-span-2"
            >
              ⊞ 弹出图层人工确认
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
