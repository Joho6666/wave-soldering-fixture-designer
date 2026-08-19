import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const StatusBar: React.FC = () => {
  const { jobStatus, hoverCoordinate, cadTransform } = useProjectStore();

  const statusTextMap: Record<string, { label: string; color: string }> = {
    idle: { label: "等待上传", color: "text-on-surface-variant" },
    file_selected: { label: "已选择文件", color: "text-primary-container" },
    uploading: { label: "正在上传", color: "text-primary-container" },
    parsing: { label: "正在解析", color: "text-primary-container" },
    layer_confirmation: { label: "待确认图层", color: "text-tertiary-container" },
    generating: { label: "正在生成", color: "text-primary-container" },
    review_required: { label: "需要人工确认", color: "text-tertiary-container" },
    completed: { label: "设计完成", color: "text-[#4ade80]" },
    failed: { label: "生成失败", color: "text-error" },
  };

  const statusConfig = statusTextMap[jobStatus] || { label: "就绪", color: "text-on-surface-variant" };
  const zoomPercent = Math.round(cadTransform.scale * 100);

  return (
    <footer className="h-8 bg-surface-container-low border-t border-outline-variant w-full flex justify-between items-center px-panel-padding z-40 shrink-0 font-data-mono text-data-mono text-on-surface-variant cursor-default">
      <div className="font-label-caps text-label-caps text-on-surface-variant">
        WAVE-FIXTURE AI v0.1 | SCALE 1:1
      </div>

      <div className="flex items-center gap-6">
        <span>单位: MM</span>
        <span>网格: 1.0mm</span>

        <div className="w-px h-3 bg-outline-variant"></div>

        {hoverCoordinate ? (
          <span className="text-primary-container">
            X: {hoverCoordinate.x.toFixed(2)} Y: {hoverCoordinate.y.toFixed(2)}
          </span>
        ) : (
          <span>X: -- Y: --</span>
        )}

        <div className="w-px h-3 bg-outline-variant"></div>

        <span>缩放: {zoomPercent}%</span>

        <div className="w-px h-3 bg-outline-variant"></div>

        <span>
          状态: <span className={`font-semibold ${statusConfig.color}`}>{statusConfig.label}</span>
        </span>
      </div>
    </footer>
  );
};
