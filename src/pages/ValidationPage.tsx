import React, { useEffect, useMemo, useState } from "react";
import { OverlayViewer } from "../components/validation/OverlayViewer";

interface FeatureScore {
  name?: string;
  feature?: string;
  status: string;
  iou?: number | null;
  hausdorffMm?: number | null;
  hausdorff_mm?: number | null;
  centroidErrorMm?: number | null;
  hole_position_error_mm?: number | null;
  hole_diameter_error_mm?: number | null;
  generatedCount?: number;
  referenceCount?: number;
  unmatched_feature_count?: number;
}

interface Manufacturing {
  cnc?: { tested?: boolean; result?: string | null };
  assembly?: { tested?: boolean; pcbFit?: string | null };
  waveSolder?: { tested?: boolean; result?: string | null };
}

interface CaseItem {
  caseId: string;
  description: string;
  status: string;
  lifecycle?: string;
  kind?: string;
  hasInput: boolean;
  hasReferenceDxf: boolean;
  hasGeneratedDxf: boolean;
  hasReport: boolean;
  notes?: string;
  history?: { status: string; time: string }[];
  manufacturing?: Manufacturing;
  report?: { overall?: string; features?: FeatureScore[] } | null;
}

const FEATURE_OVERRIDE_TYPE: Record<string, string> = {
  locating_pins: "modify_locating_pin",
  clamps: "modify_clamp",
  solder_openings: "modify_solder_opening",
  keepout_regions: "modify_keepout",
  sink: "modify_pocket",
  pressure_relief: "modify_pressure_relief",
};

const FEATURES = [
  "pcb_outline",
  "fixture_body",
  "sink",
  "locating_pins",
  "solder_openings",
  "keepout_regions",
  "clamps",
  "spring_clips",
  "solder_barriers",
  "handholds",
  "pressure_relief",
  "conveyor_rails",
];

const STATUS_CLASS: Record<string, string> = {
  PASS: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  WARNING: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  FAIL: "text-rose-400 border-rose-500/40 bg-rose-500/10",
  NOT_AVAILABLE: "text-slate-300 border-slate-500/40 bg-slate-500/10",
  passed: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  failed: "text-rose-400 border-rose-500/40 bg-rose-500/10",
  review_required: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  awaiting_input: "text-slate-300 border-slate-500/40 bg-slate-500/10",
  awaiting_reference: "text-slate-300 border-slate-500/40 bg-slate-500/10",
  awaiting_reference_dxf: "text-slate-300 border-slate-500/40 bg-slate-500/10",
  ready: "text-sky-300 border-sky-500/40 bg-sky-500/10",
};

function Badge({ value }: { value: string }) {
  return (
    <span className={`px-2 py-0.5 text-[11px] uppercase tracking-wide border ${STATUS_CLASS[value] || "text-on-surface-variant border-outline-variant"}`}>
      {value}
    </span>
  );
}

function featureName(item: FeatureScore | undefined) {
  return item?.feature || item?.name || "";
}

function findFeature(features: FeatureScore[] | undefined, name: string) {
  return features?.find((f) => featureName(f) === name);
}

function num(value: number | null | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "—";
}

export const ValidationPage: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overlay, setOverlay] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const [highlight, setHighlight] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState("");
  const [overrideWkt, setOverrideWkt] = useState("");
  const [busy, setBusy] = useState(false);

  const selected = useMemo(() => cases.find((c) => c.caseId === selectedId) || null, [cases, selectedId]);
  const features = selected?.report?.features;

  const reload = () => {
    fetch("/api/validation/cases")
      .then((r) => r.json())
      .then((data) => {
        const list: CaseItem[] = data.cases || [];
        setCases(list);
        setSelectedId((prev) => prev || list[0]?.caseId || null);
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    reload();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetch(`/api/validation/cases/${selectedId}/overlay`)
      .then((r) => r.text())
      .then(setOverlay)
      .catch(() => setOverlay(""));
  }, [selectedId, selected?.hasGeneratedDxf, selected?.hasReport]);

  const visibleFeatures = FEATURES.filter((name) => filter === "all" || filter === name);

  const regenerate = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/validation/cases/${selectedId}/regenerate`, { method: "POST" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || res.statusText);
      }
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const submitOverride = async () => {
    const overrideType = highlight ? FEATURE_OVERRIDE_TYPE[highlight] : undefined;
    if (!selectedId || !highlight || !overrideType || overrideReason.trim().length < 8 || !overrideWkt.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/validation/cases/${selectedId}/overrides`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: overrideType,
          featureId: highlight,
          sourceIds: [],
          newGeometry: { wkt: overrideWkt.trim() },
          reason: overrideReason.trim(),
          engineer: "field-engineer",
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || res.statusText);
      }
      setOverrideReason("");
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 overflow-hidden bg-background text-on-background flex flex-col">
      <header className="h-14 border-b border-outline-variant px-4 flex items-center justify-between bg-surface">
        <div className="flex items-center gap-3">
          <a href="/" className="font-semibold text-primary-container">WAVE-FIXTURE</a>
          <span className="text-on-surface-variant text-sm">Field Validation CAD QA</span>
        </div>
        <a href="/" className="text-xs text-on-surface-variant hover:text-on-surface">返回设计工作台</a>
      </header>

      <div className="flex-1 grid grid-cols-12 min-h-0">
        <aside className="col-span-3 border-r border-outline-variant overflow-auto p-3 space-y-3">
          <h2 className="text-sm uppercase tracking-wider text-primary-container">Golden Cases</h2>
          {error && <div className="text-rose-400 text-sm">{error}</div>}
          {cases.map((item) => (
            <button
              key={item.caseId}
              onClick={() => setSelectedId(item.caseId)}
              className={`w-full text-left p-3 border ${selectedId === item.caseId ? "border-primary-container bg-surface-container-high" : "border-outline-variant bg-surface-container"}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-sm">{item.caseId}</span>
                <Badge value={item.report?.overall || item.status} />
              </div>
              <p className="text-xs text-on-surface-variant line-clamp-3">{item.description}</p>
              <div className="mt-2 text-[10px] font-mono text-on-surface-variant">{item.lifecycle || "IMPORTED"} · {item.kind}</div>
            </button>
          ))}
        </aside>

        <section className="col-span-9 min-h-0 grid grid-rows-[auto_1fr_auto]">
          {!selected ? (
            <div className="p-4 text-on-surface-variant">No case selected.</div>
          ) : (
            <>
              <div className="p-3 border-b border-outline-variant flex items-center gap-3">
                <h1 className="text-xl font-semibold">{selected.caseId}</h1>
                <Badge value={selected.report?.overall || selected.status} />
                <Badge value={selected.lifecycle || "IMPORTED"} />
                <button className="ml-auto text-xs border px-2 py-1" disabled={busy} onClick={regenerate}>
                  {busy ? "Working…" : "Regenerate"}
                </button>
              </div>
              <div className="min-h-0 p-3">
                <OverlayViewer
                  svg={overlay}
                  emptyMessage="awaiting engineer DXF"
                  highlightFeature={highlight}
                />
              </div>
              <div className="border-t border-outline-variant grid grid-cols-12 min-h-[220px]">
                <div className="col-span-7 overflow-auto">
                  <div className="flex items-center gap-2 p-2 text-xs">
                    <span>Feature filter</span>
                    <select value={filter} onChange={(e) => setFilter(e.target.value)} className="bg-surface border border-outline-variant text-xs">
                      <option value="all">all</option>
                      {FEATURES.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>
                  </div>
                  <table className="w-full text-xs font-mono">
                    <thead className="bg-surface-container-low text-on-surface-variant">
                      <tr>
                        <th className="text-left p-2">Feature</th>
                        <th className="text-left p-2">Status</th>
                        <th className="text-left p-2">IoU</th>
                        <th className="text-left p-2">Hausdorff</th>
                        <th className="text-left p-2">Centroid</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleFeatures.map((name) => {
                        const row = findFeature(features, name);
                        const status = row?.status || "NOT_AVAILABLE";
                        return (
                          <tr
                            key={name}
                            className={`border-t border-outline-variant cursor-pointer ${highlight === name ? "bg-surface-container-high" : ""}`}
                            onClick={() => setHighlight(name)}
                            data-testid={`feature-row-${name}`}
                          >
                            <td className="p-2">{name}</td>
                            <td className="p-2">
                              <button
                                className="underline"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setHighlight(name);
                                }}
                              >
                                {status}
                              </button>
                            </td>
                            <td className="p-2">{num(row?.iou)}</td>
                            <td className="p-2">{num(row?.hausdorffMm ?? row?.hausdorff_mm)}</td>
                            <td className="p-2">{num(row?.centroidErrorMm ?? row?.hole_position_error_mm)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="col-span-5 border-l border-outline-variant p-3 text-xs space-y-3 overflow-auto">
                  <div>
                    <h3 className="uppercase tracking-wide text-on-surface-variant mb-1">Software Validation</h3>
                    <p>Status: {selected.report?.overall || selected.status}</p>
                    <p>Input: {selected.hasInput ? "yes" : "no"} · Reference DXF: {selected.hasReferenceDxf ? "yes" : "no"}</p>
                  </div>
                  <div>
                    <h3 className="uppercase tracking-wide text-on-surface-variant mb-1">Physical Validation</h3>
                    <p>CNC: {selected.manufacturing?.cnc?.tested ? selected.manufacturing.cnc.result : "0 / not tested"}</p>
                    <p>Assembly: {selected.manufacturing?.assembly?.tested ? selected.manufacturing.assembly.pcbFit : "0 / not tested"}</p>
                    <p>Wave: {selected.manufacturing?.waveSolder?.tested ? selected.manufacturing.waveSolder.result : "0 / not tested"}</p>
                  </div>
                  <div>
                    <h3 className="uppercase tracking-wide text-on-surface-variant mb-1">Engineer override</h3>
                    <p className="text-on-surface-variant">Does not edit DXF. Structured JSON only. Reason required.</p>
                    <textarea
                      className="w-full h-16 bg-surface border border-outline-variant p-1"
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="why this feature must change"
                    />
                    <textarea
                      className="w-full h-16 bg-surface border border-outline-variant p-1 mt-1"
                      value={overrideWkt}
                      onChange={(e) => setOverrideWkt(e.target.value)}
                      placeholder="newGeometry WKT (Polygon for openings/keepouts; never POINT 0 0)"
                    />
                    <button
                      className="mt-1 border px-2 py-1"
                      disabled={busy || !highlight || !FEATURE_OVERRIDE_TYPE[highlight || ""] || !overrideWkt.trim()}
                      onClick={submitOverride}
                    >
                      Save override for {highlight || "feature"}
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};
