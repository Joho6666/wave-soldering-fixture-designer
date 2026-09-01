import React, { useMemo, useRef, useState } from "react";

export interface OverlayViewerProps {
  svg: string;
  emptyMessage?: string;
  highlightFeature?: string | null;
}

const LAYER_IDS = ["generated", "reference", "difference"] as const;

export const OverlayViewer: React.FC<OverlayViewerProps> = ({
  svg,
  emptyMessage = "awaiting engineer DXF",
  highlightFeature,
}) => {
  const [pan, setPan] = useState({ x: 0, y: 0, scale: 1 });
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);
  const [layers, setLayers] = useState({ generated: true, reference: true, difference: true });
  const wrapRef = useRef<HTMLDivElement>(null);

  const awaiting = !svg || svg.includes("awaiting engineer DXF") || svg.includes("No reference");

  const decorated = useMemo(() => {
    if (!svg) return "";
    let next = svg;
    for (const id of LAYER_IDS) {
      const display = layers[id] ? "inline" : "none";
      next = next.replace(
        new RegExp(`id="${id}"`, "g"),
        `id="${id}" style="display:${display}"`,
      );
    }
    if (highlightFeature) {
      next = next.replace(
        `data-feature="${highlightFeature}"`,
        `data-feature="${highlightFeature}" stroke="#fbbf24" stroke-width="1.2"`,
      );
    }
    return next;
  }, [svg, layers, highlightFeature]);

  const onWheel = (event: React.WheelEvent) => {
    event.preventDefault();
    const factor = event.deltaY < 0 ? 1.12 : 0.9;
    setPan((p) => ({ ...p, scale: Math.min(8, Math.max(0.25, p.scale * factor)) }));
  };

  const onDown = (event: React.MouseEvent) => {
    setDrag({ x: event.clientX - pan.x, y: event.clientY - pan.y });
  };
  const onMove = (event: React.MouseEvent) => {
    if (!drag) return;
    setPan((p) => ({ ...p, x: event.clientX - drag.x, y: event.clientY - drag.y }));
  };

  return (
    <div className="flex flex-col h-full bg-black border border-outline-variant">
      <div className="flex items-center gap-3 px-2 py-1 text-[11px] text-on-surface-variant">
        {LAYER_IDS.map((id) => (
          <label key={id} className="inline-flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox"
              checked={layers[id]}
              onChange={() => setLayers((s) => ({ ...s, [id]: !s[id] }))}
            />
            {id}
          </label>
        ))}
        <span className="ml-auto text-sky-400">Generated blue</span>
        <span className="text-emerald-400">Reference green</span>
        <span className="text-amber-300">Diff highlight</span>
      </div>
      <div
        ref={wrapRef}
        className="flex-1 overflow-hidden cursor-grab"
        onWheel={onWheel}
        onMouseDown={onDown}
        onMouseMove={onMove}
        onMouseUp={() => setDrag(null)}
        onMouseLeave={() => setDrag(null)}
        data-testid="overlay-stage"
      >
        {awaiting ? (
          <div className="h-full flex items-center justify-center text-sm text-slate-400" data-testid="overlay-empty">
            {emptyMessage}
          </div>
        ) : (
          <div
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${pan.scale})`, transformOrigin: "0 0" }}
            dangerouslySetInnerHTML={{ __html: decorated }}
          />
        )}
      </div>
    </div>
  );
};
