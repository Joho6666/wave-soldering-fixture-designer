import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

interface LayerItemDef {
  id: string;
  name: string;
  enName: string;
  color: string;
}

export const LayerTreePanel: React.FC = () => {
  const { visibleLayers, toggleLayer, toggleParameterDrawer, fixtureResult } = useProjectStore();

  const inputLayers: LayerItemDef[] = [
    { id: "pcb-outline", name: "PCB 外形", enName: "PCB Outline", color: "#2e8b57" },
    { id: "pcb-copper", name: "PCB 走线铜皮", enName: "Copper Traces", color: "#d49a6a" },
    { id: "pcb-drill", name: "DRL 钻孔", enName: "Drill Holes", color: "#48cae4" },
    { id: "locating-pin-candidates", name: "定位孔候选", enName: "Pin Candidates", color: "#ff9800" },
  ];

  const fixtureLayers: LayerItemDef[] = [
    { id: "sink-region", name: "沉板区", enName: "Counterbore", color: "#9370db" },
    { id: "keepout-bot", name: "BOT 避位区", enName: "Clearance", color: "#32cd32" },
    { id: "solder-top", name: "TOP 上锡区", enName: "Solder Window", color: "#ff8c00" },
    { id: "solder-barriers", name: "挡锡条", enName: "Solder Barrier", color: "#fec931" },
    { id: "locating-pins", name: "定位销", enName: "Locating Pins", color: "#00ffff" },
    { id: "clamps", name: "压扣", enName: "Clamps", color: "#a9a9a9" },
    { id: "fixture-outline", name: "治具外形", enName: "Fixture Outline", color: "#1e90ff" },
    { id: "handholds", name: "取手位", enName: "Handholds", color: "#ab47bc" },
    { id: "rails", name: "轨道", enName: "Rails", color: "#78909c" },
    { id: "barrier-mount-holes", name: "挡锡条螺丝孔", enName: "Barrier Holes", color: "#ffab40" },
    { id: "spring-clips", name: "弹簧卡安装孔", enName: "Spring Clips", color: "#00bcd4" },
  ];

  const gerberSourceLayers: LayerItemDef[] = [
    { id: "gerber-top-copper", name: "顶层铜", enName: "Top Copper", color: "#ff5722" },
    { id: "gerber-bot-copper", name: "底层铜", enName: "Bot Copper", color: "#4caf50" },
    { id: "gerber-top-silk", name: "顶层丝印", enName: "Top Silk", color: "#ffffff" },
    { id: "gerber-bot-silk", name: "底层丝印", enName: "Bot Silk", color: "#ffeb3b" },
    { id: "gerber-top-mask", name: "顶层阻焊", enName: "Top Mask", color: "#9c27b0" },
    { id: "gerber-bot-mask", name: "底层阻焊", enName: "Bot Mask", color: "#009688" },
  ];

  const helperLayers: LayerItemDef[] = [
    { id: "dimensions", name: "尺寸标注", enName: "Dimensions", color: "#849396" },
    { id: "drc-overlay", name: "DRC 警告层", enName: "DRC Issues", color: "#ff7b00" },
  ];

  const renderLayerGroup = (title: string, items: LayerItemDef[]) => (
    <div className="mb-3">
      <div className="text-[10px] font-label-caps text-on-surface-variant px-2 py-1 uppercase tracking-wider bg-surface-container-high/40">
        {title}
      </div>
      <div className="flex flex-col gap-0.5 mt-1">
        {items.map((layer) => {
          const isVisible = visibleLayers[layer.id] ?? true;

          return (
            <div
              key={layer.id}
              onClick={() => toggleLayer(layer.id)}
              className={`flex items-center justify-between px-2.5 py-1.5 cursor-pointer transition-colors ${
                isVisible
                  ? "hover:bg-surface-container-highest text-on-surface"
                  : "hover:bg-surface-container-highest/50 text-on-surface-variant/50"
              }`}
            >
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleLayer(layer.id);
                  }}
                  className="text-[16px] hover:text-primary-container transition-colors"
                  title={isVisible ? "隐藏图层" : "显示图层"}
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {isVisible ? "visibility" : "visibility_off"}
                  </span>
                </button>

                <div
                  className="w-2.5 h-2.5 border border-outline-variant shrink-0"
                  style={{ backgroundColor: isVisible ? layer.color : "transparent" }}
                ></div>

                <span className="font-body-sm text-[12px] truncate">
                  {layer.name} <span className="text-[10px] text-on-surface-variant font-data-mono">({layer.enName})</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <aside className="w-sidebar-width h-full bg-surface-container border-r border-outline-variant flex flex-col z-30 shrink-0">
      {/* Header */}
      <div className="p-panel-padding border-b border-outline-variant bg-surface-container-low flex items-center gap-container-gap">
        <span className="material-symbols-outlined text-primary-container fill-1 text-[24px]">category</span>
        <div>
          <h2 className="font-headline-md text-headline-md text-on-surface font-semibold truncate">
            {fixtureResult.id || "等待后端结果"}
          </h2>
          <p className="font-data-mono text-data-mono text-on-surface-variant">
            {(fixtureResult.fixture?.thickness ?? 0).toFixed(1)}mm 治具板 | 波峰焊
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-outline-variant bg-surface-container-lowest font-label-caps text-label-caps">
        <div className="flex-1 py-2 text-center text-primary-container border-b-2 border-primary-container bg-surface-container-high font-bold">
          图层 (LAYERS)
        </div>
        <button
          onClick={() => toggleParameterDrawer(true)}
          className="flex-1 py-2 text-center text-on-surface-variant hover:bg-surface-container-highest transition-colors"
        >
          参数 (PARAMS)
        </button>
      </div>

      {/* Layer Groups List */}
      <div className="flex-1 overflow-y-auto p-2">
        {renderLayerGroup("输入数据 (INPUT)", inputLayers)}
        {renderLayerGroup("治具生成 (FIXTURE)", fixtureLayers)}
        {renderLayerGroup("辅助显示 (AUXILIARY)", helperLayers)}
        {renderLayerGroup("Gerber 源层 (SOURCE)", gerberSourceLayers)}
      </div>

      {/* Footer Info */}
      <div className="p-2 border-t border-outline-variant bg-surface-container-low text-center">
        <span className="font-data-mono text-[10px] text-on-surface-variant">
          共 {Object.keys(visibleLayers).length} 个图层通道
        </span>
      </div>
    </aside>
  );
};
