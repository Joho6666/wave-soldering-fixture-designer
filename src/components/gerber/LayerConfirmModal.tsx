import React, { useState, useEffect } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { fixtureApi } from "../../services/api";
import { GerberLayer, GerberLayerType, LAYER_TYPE_NAMES } from "../../types/gerber";

export const LayerConfirmModal: React.FC = () => {
  const {
    isLayerConfirmModalOpen,
    toggleLayerConfirmModal,
    currentProject,
    analysis,
    setAnalysis,
    confirmLayers,
    showToast
  } = useProjectStore();

  const [layersState, setLayersState] = useState<GerberLayer[]>(() => analysis.layers);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 当 analysis 更新或弹窗打开时保持同步
  useEffect(() => {
    if (analysis.layers.length > 0) {
      setLayersState(analysis.layers);
    } else if (isLayerConfirmModalOpen && currentProject?.id) {
      fixtureApi
        .getAnalysis(currentProject.id)
        .then((data) => {
          setAnalysis(data);
          setLayersState(data.layers);
        })
        .catch(() => {});
    }
  }, [analysis.layers, isLayerConfirmModalOpen, currentProject?.id, setAnalysis]);

  if (!isLayerConfirmModalOpen) return null;

  const handleTypeChange = (id: string, newType: GerberLayerType) => {
    setLayersState((prev) =>
      prev.map((l) => (l.id === id ? { ...l, type: newType, confidence: 1.0, confirmed: true } : l))
    );
  };

  const handleConfirmAndContinue = async () => {
    const hasOutline = layersState.some((l) => l.type === "board_outline");
    if (!hasOutline) {
      showToast("请至少指定一层为【PCB 外形层】", "warning");
      return;
    }

    setIsSubmitting(true);
    try {
      await confirmLayers(layersState);
      toggleLayerConfirmModal(false);
    } catch (error) {
      showToast(`提交图层映射失败: ${(error as Error).message}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = async () => {
    setIsSubmitting(true);
    try {
      await confirmLayers(layersState);
      toggleLayerConfirmModal(false);
    } catch {
      toggleLayerConfirmModal(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-surface-container border border-primary-container shadow-[0_0_30px_rgba(0,229,255,0.2)] rounded p-6 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-outline-variant pb-4 mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary-container fill-1">layers</span>
            <h2 className="font-headline-md text-headline-md text-primary-container font-bold">
              确认 Gerber 图层映射
            </h2>
          </div>
          <span className="font-data-mono text-body-sm text-on-surface-variant">
            {layersState.filter((l) => l.confidence < 0.9 || l.type === "unknown").length} 项待人工核对
          </span>
        </div>

        {/* Description */}
        <p className="text-body-sm text-on-surface-variant mb-4">
          系统已自动预判各文件层用途。请复核关键图层（特别是 PCB 外形与阻焊层），确认无误后点击“确认并继续”。
        </p>

        {/* Table Content */}
        <div className="flex-1 overflow-y-auto border border-outline-variant rounded bg-surface">
          <table className="w-full text-left font-data-mono text-body-sm">
            <thead className="bg-surface-container-high text-on-surface-variant border-b border-outline-variant sticky top-0 z-10">
              <tr>
                <th className="p-3">文件名 (File)</th>
                <th className="p-3">系统预判 (Auto-Type)</th>
                <th className="p-3">人工指定 (Dropdown)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {layersState.map((layer) => {
                const isLowConfidence = layer.confidence < 0.9 || layer.type === "unknown";

                return (
                  <tr
                    key={layer.id}
                    className={`hover:bg-surface-container-high/60 transition-colors ${
                      isLowConfidence ? "bg-tertiary-container/5" : ""
                    }`}
                  >
                    <td className="p-3 font-semibold text-on-surface flex items-center gap-2">
                      {isLowConfidence && (
                        <span className="w-1.5 h-1.5 rounded-full bg-tertiary-container"></span>
                      )}
                      {layer.filename}
                    </td>

                    <td className="p-3">
                      <span className={isLowConfidence ? "text-tertiary-container font-medium" : "text-on-surface-variant"}>
                        {LAYER_TYPE_NAMES[layer.type]} ({Math.round(layer.confidence * 100)}%)
                      </span>
                    </td>

                    <td className="p-3">
                      <select
                        value={layer.type}
                        onChange={(e) => handleTypeChange(layer.id, e.target.value as GerberLayerType)}
                        className="bg-surface-container border border-outline-variant text-on-surface px-2 py-1 text-xs focus:border-primary-container focus:outline-none rounded"
                      >
                        <option value="board_outline">PCB 外形层</option>
                        <option value="top_silkscreen">TOP 丝印</option>
                        <option value="bottom_silkscreen">BOT 丝印</option>
                        <option value="top_soldermask">TOP 阻焊</option>
                        <option value="bottom_soldermask">BOT 阻焊</option>
                        <option value="drill">钻孔层</option>
                        <option value="top_copper">TOP 铜层</option>
                        <option value="bottom_copper">BOT 铜层</option>
                        <option value="unknown">未识别 / 其他</option>
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-outline-variant">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleSkip}
            className="px-6 py-2 border border-outline-variant text-on-surface font-body-md hover:bg-surface-container-highest transition-colors rounded disabled:opacity-50"
          >
            跳过
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleConfirmAndContinue}
            className="px-8 py-2 bg-primary-container text-on-primary-fixed font-headline-md font-bold hover:bg-surface-tint glow-cyan transition-colors rounded flex items-center gap-1.5 disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[18px]">check</span>
            {isSubmitting ? "正在出图..." : "确认并继续"}
          </button>
        </div>
      </div>
    </div>
  );
};
