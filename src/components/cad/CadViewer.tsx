import React, { useRef, useState, useCallback, useEffect, useMemo } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { CadToolbar } from "./CadToolbar";

export const CadViewer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgContainerRef = useRef<HTMLDivElement>(null);
  const {
    cadTransform,
    setCadTransform,
    resetCadView,
    setHoverCoordinate,
    highlightTarget,
    previewSvg,
    visibleLayers,
    toggleManualPin,
    
  } = useProjectStore();
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!containerRef.current || !previewSvg) return;
    Object.entries(visibleLayers).forEach(([layerId, visible]) => {
      const element = containerRef.current?.querySelector(`#${CSS.escape(layerId)}`) as SVGElement | null;
      if (element) element.style.display = visible ? "" : "none";
    });
  }, [previewSvg, visibleLayers]);

  // 绑定 SVG 内部交互（点击钻孔或定位孔候选快速设为/取消定位销）
  useEffect(() => {
    if (!svgContainerRef.current) return;
    const drillGroup = svgContainerRef.current.querySelector("#pcb-drill");
    const candGroup = svgContainerRef.current.querySelector("#locating-pin-candidates");
    const pinsGroup = svgContainerRef.current.querySelector("#locating-pins");

    const handleClick = (e: Event) => {
      const target = e.target as SVGElement;
      if (target && target.tagName.toLowerCase() === "circle") {
        const rawId = target.id || target.getAttribute("id");
        if (rawId) {
          e.stopPropagation();
          const cleanId = rawId.replace(/^pin-cand-/, "").replace(/^pin-/, "");
          toggleManualPin(cleanId);
        }
      }
    };

    drillGroup?.addEventListener("click", handleClick);
    candGroup?.addEventListener("click", handleClick);
    pinsGroup?.addEventListener("click", handleClick);

    return () => {
      drillGroup?.removeEventListener("click", handleClick);
      candGroup?.removeEventListener("click", handleClick);
      pinsGroup?.removeEventListener("click", handleClick);
    };
  }, [previewSvg, toggleManualPin]);

  const handleWheel = useCallback((event: React.WheelEvent<HTMLDivElement>) => {
    const zoomFactor = event.deltaY < 0 ? 1.15 : 0.85;
    const scale = Math.min(Math.max(cadTransform.scale * zoomFactor, 0.4), 4.5);
    setCadTransform({ scale });
  }, [cadTransform.scale, setCadTransform]);

  const handleMouseDown = (event: React.MouseEvent) => {
    if (event.button === 0 || event.button === 1) {
      setIsDragging(true);
      setDragStart({ x: event.clientX - cadTransform.x, y: event.clientY - cadTransform.y });
    }
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (isDragging) {
      setCadTransform({ x: event.clientX - dragStart.x, y: event.clientY - dragStart.y });
    }

    const svgElement = svgContainerRef.current?.querySelector("svg") as SVGSVGElement | null;
    if (svgElement && typeof svgElement.getScreenCTM === "function" && typeof svgElement.createSVGPoint === "function") {
      const ctm = svgElement.getScreenCTM();
      if (ctm) {
        const pt = svgElement.createSVGPoint();
        pt.x = event.clientX;
        pt.y = event.clientY;
        const svgPoint = pt.matrixTransform(ctm.inverse());
        setHoverCoordinate({
          x: Number(svgPoint.x.toFixed(2)),
          y: Number(svgPoint.y.toFixed(2)),
        });
        return;
      }
    }
    setHoverCoordinate(null);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setHoverCoordinate(null);
  };

  const svgViewBox = useMemo(() => {
    if (!previewSvg) return null;
    const match = previewSvg.match(/viewBox=["']([^"']+)["']/i);
    return match ? match[1] : null;
  }, [previewSvg]);

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={() => setIsDragging(false)}
      onMouseLeave={handleMouseLeave}
      onDoubleClick={resetCadView}
      className={`flex-1 relative bg-[#101317] cad-grid-minor flex items-center justify-center overflow-hidden select-none overscroll-contain ${isDragging ? "cursor-grabbing" : "cursor-crosshair"}`}
    >
      <div className="absolute inset-0 cad-grid pointer-events-none z-0" />
      <CadToolbar />
      <div
        className="relative transition-transform duration-75 ease-out z-10 flex items-center justify-center w-[min(88%,900px)] h-[min(82%,650px)]"
        style={{ transform: `translate(${cadTransform.x}px, ${cadTransform.y}px) scale(${cadTransform.scale})`, transformOrigin: "center center" }}
      >
        {previewSvg ? (
          <div
            ref={svgContainerRef}
            className="w-full h-full drop-shadow-[0_10px_30px_rgba(0,0,0,0.8)] [&>svg]:w-full [&>svg]:h-full [&>svg]:max-h-full"
            aria-label="后端生成的治具 SVG 预览"
            dangerouslySetInnerHTML={{ __html: previewSvg }}
          />
        ) : (
          <div className="text-center text-on-surface-variant">
            <span className="material-symbols-outlined text-4xl block mb-3">image_not_supported</span>
            暂未加载 SVG 预览
          </div>
        )}
        {highlightTarget && svgViewBox && (
          <svg
            viewBox={svgViewBox}
            className="absolute inset-0 w-full h-full pointer-events-none z-30 overflow-visible"
            aria-label="DRC 目标定位层"
          >
            <g transform={`translate(${highlightTarget.x}, ${highlightTarget.y})`}>
              <circle
                r={Math.max(highlightTarget.width || 6, highlightTarget.height || 6, 6)}
                fill="rgba(255, 179, 0, 0.2)"
                stroke="#ffb300"
                strokeWidth="0.8"
                strokeDasharray="2 1"
                className="animate-ping"
              />
              <circle
                r={Math.max(highlightTarget.width || 5, highlightTarget.height || 5, 5)}
                fill="rgba(255, 179, 0, 0.15)"
                stroke="#ffb300"
                strokeWidth="0.6"
              />
              <line x1="-6" y1="0" x2="6" y2="0" stroke="#ffb300" strokeWidth="0.6" />
              <line x1="0" y1="-6" x2="0" y2="6" stroke="#ffb300" strokeWidth="0.6" />
              <circle r="1" fill="#ffb300" />
            </g>
          </svg>
        )}
      </div>
      <div className="absolute left-panel-padding top-1/2 -translate-y-1/2 flex flex-col gap-1 z-20">
        <button onClick={resetCadView} className="w-8 h-8 bg-surface-container border border-outline-variant flex items-center justify-center text-on-surface hover:text-primary-container transition-colors" title="重置视角">
          <span className="material-symbols-outlined text-[18px]">center_focus_strong</span>
        </button>
      </div>
    </div>
  );
};
