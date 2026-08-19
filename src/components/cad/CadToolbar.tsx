import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const CadToolbar: React.FC = () => {
  const {
    cadTransform,
    setCadTransform,
    resetCadView,
    viewMode,
    setViewMode,
    showToast
  } = useProjectStore();

  const handleZoomIn = () => {
    setCadTransform({ scale: Math.min(cadTransform.scale * 1.25, 4.0) });
  };

  const handleZoomOut = () => {
    setCadTransform({ scale: Math.max(cadTransform.scale / 1.25, 0.4) });
  };

  const handleScale1To1 = () => {
    setCadTransform({ scale: 1.0, x: 0, y: 0 });
    showToast("视图已缩放到 1:1 标准比例", "info");
  };

  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      showToast("已进入全屏模式", "info");
    } else {
      document.exitFullscreen().catch(() => {});
      showToast("已退出全屏模式", "info");
    }
  };

  return (
    <div className="absolute top-panel-padding left-1/2 -translate-x-1/2 bg-surface-container/90 border border-outline-variant flex items-center p-1 z-20 shadow-[0_4px_16px_rgba(0,0,0,0.6)] backdrop-blur-md">
      {/* 视图模式切换 */}
      <div className="flex items-center bg-surface-container-low border border-outline-variant mr-2 p-0.5 font-label-caps text-label-caps">
        <button
          onClick={() => setViewMode("pcb_only")}
          className={`px-2.5 py-1 transition-colors ${
            viewMode === "pcb_only"
              ? "bg-primary-container text-on-primary-fixed font-bold"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          原始 PCB
        </button>
        <button
          onClick={() => setViewMode("fixture_only")}
          className={`px-2.5 py-1 transition-colors ${
            viewMode === "fixture_only"
              ? "bg-primary-container text-on-primary-fixed font-bold"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          治具设计
        </button>
        <button
          onClick={() => setViewMode("all")}
          className={`px-2.5 py-1 transition-colors ${
            viewMode === "all"
              ? "bg-primary-container text-on-primary-fixed font-bold"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          叠加
        </button>
      </div>

      <div className="w-px h-5 bg-outline-variant mx-1"></div>

      {/* 缩放操作 */}
      <button
        onClick={handleZoomIn}
        className="w-8 h-8 flex items-center justify-center text-on-surface hover:text-primary-container hover:bg-surface-container-highest transition-colors"
        title="放大 (Zoom In)"
      >
        <span className="material-symbols-outlined text-[20px]">zoom_in</span>
      </button>

      <button
        onClick={handleZoomOut}
        className="w-8 h-8 flex items-center justify-center text-on-surface hover:text-primary-container hover:bg-surface-container-highest transition-colors"
        title="缩小 (Zoom Out)"
      >
        <span className="material-symbols-outlined text-[20px]">zoom_out</span>
      </button>

      <div className="w-px h-5 bg-outline-variant mx-1"></div>

      <button
        onClick={resetCadView}
        className="w-8 h-8 flex items-center justify-center text-on-surface hover:text-primary-container hover:bg-surface-container-highest transition-colors"
        title="适应窗口 (Fit to Screen)"
      >
        <span className="material-symbols-outlined text-[20px]">fit_screen</span>
      </button>

      <button
        onClick={handleScale1To1}
        className="px-2 h-8 flex items-center justify-center text-on-surface hover:text-primary-container hover:bg-surface-container-highest transition-colors font-data-mono text-[12px] font-bold"
        title="1:1 原比例"
      >
        1:1
      </button>

      <div className="w-px h-5 bg-outline-variant mx-1"></div>

      <button
        onClick={handleToggleFullscreen}
        className="w-8 h-8 flex items-center justify-center text-on-surface hover:text-primary-container hover:bg-surface-container-highest transition-colors"
        title="全屏模式 (Fullscreen)"
      >
        <span className="material-symbols-outlined text-[20px]">fullscreen</span>
      </button>
    </div>
  );
};
