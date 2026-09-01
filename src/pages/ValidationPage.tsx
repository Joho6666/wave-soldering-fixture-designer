import React, { useEffect, useMemo, useState } from "react";

interface FeatureScore {
  name: string;
  status: string;
  iou?: number | null;
  hausdorff_mm?: number | null;
  hole_position_error_mm?: number | null;
  hole_diameter_error_mm?: number | null;
  expected_count?: number;
  generated_count?: number;
  unmatched_feature_count?: number;
}

interface CaseItem {
  caseId: string;
  description: string;
  status: string;
  hasInput: boolean;
  hasReferenceDxf: boolean;
  hasGeneratedDxf: boolean;
  hasReport: boolean;
  notes?: string;
  report?: {
    overall?: string;
    features?: FeatureScore[];
  } | null;
}

const STATUS_CLASS: Record<string, string> = {
  PASS: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  WARNING: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  FAIL: "text-rose-400 border-rose-500/40 bg-rose-500/10",
  passed: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  failed: "text-rose-400 border-rose-500/40 bg-rose-500/10",
  review_required: "text-amber-300 border-amber-500/40 bg-amber-500/10",
  awaiting_input: "text-slate-300 border-slate-500/40 bg-slate-500/10",
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

function metric(features: FeatureScore[] | undefined, name: string, key: keyof FeatureScore): string {
  const item = features?.find((f) => f.name === name);
  const raw = item?.[key];
  if (typeof raw === "number") return raw.toFixed(3);
  return "—";
}

function statusOf(features: FeatureScore[] | undefined, name: string): string {
  return features?.find((f) => f.name === name)?.status || "—";
}

export const ValidationPage: React.FC = () => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overlay, setOverlay] = useState<string>("");

  const selected = useMemo(() => cases.find((c) => c.caseId === selectedId) || null, [cases, selectedId]);
  const features = selected?.report?.features;

  useEffect(() => {
    fetch("/api/validation/cases")
      .then((r) => r.json())
      .then((data) => {
        const list: CaseItem[] = data.cases || [];
        setCases(list);
        if (list[0]) setSelectedId(list[0].caseId);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetch(`/api/validation/cases/${selectedId}/overlay`)
      .then((r) => r.text())
      .then(setOverlay)
      .catch(() => setOverlay(""));
  }, [selectedId]);

  return (
    <div className="fixed inset-0 overflow-auto bg-background text-on-background">
      <header className="h-14 border-b border-outline-variant px-4 flex items-center justify-between bg-surface">
        <div className="flex items-center gap-3">
          <a href="/" className="font-semibold text-primary-container">WAVE-FIXTURE</a>
          <span className="text-on-surface-variant text-sm">Golden Validation</span>
        </div>
        <a href="/" className="text-xs text-on-surface-variant hover:text-on-surface">返回设计工作台</a>
      </header>

      <div className="p-4 grid grid-cols-12 gap-4 min-h-[calc(100vh-56px)]">
        <aside className="col-span-3 space-y-3">
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
              <div className="mt-2 grid grid-cols-2 gap-1 text-[10px] font-mono text-on-surface-variant">
                <div>Fixture IoU {metric(item.report?.features, "fixture_outline", "iou")}</div>
                <div>Sink IoU {metric(item.report?.features, "sink_region", "iou")}</div>
                <div>Keepout {metric(item.report?.features, "keepout_regions", "iou")}</div>
                <div>Solder {metric(item.report?.features, "solder_windows", "iou")}</div>
                <div>Pin {metric(item.report?.features, "locating_pins", "hole_position_error_mm")}</div>
                <div>Hole {metric(item.report?.features, "clamp_holes", "hole_position_error_mm")}</div>
              </div>
            </button>
          ))}
        </aside>

        <section className="col-span-9">
          {!selected ? (
            <div className="text-on-surface-variant">No case selected.</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-semibold">{selected.caseId}</h1>
                <Badge value={selected.report?.overall || selected.status} />
              </div>
              <p className="text-sm text-on-surface-variant">{selected.description}</p>
              <p className="text-xs text-amber-300">
                Input PCB: {selected.hasInput ? "present" : "missing"} · Reference DXF: {selected.hasReferenceDxf ? "present" : "missing"} · Generated DXF: {selected.hasGeneratedDxf ? "present" : "missing"}
              </p>
              {selected.notes && <p className="text-xs text-on-surface-variant">{selected.notes}</p>}

              <div className="grid grid-cols-3 gap-3 h-[420px]">
                <div className="border border-outline-variant bg-surface-container p-2 flex flex-col">
                  <div className="text-xs mb-2 text-on-surface-variant">Reference DXF</div>
                  <div className="flex-1 flex items-center justify-center text-xs text-on-surface-variant">
                    {selected.hasReferenceDxf ? "Engineer reference loaded" : "No engineer DXF — overlay unavailable"}
                  </div>
                </div>
                <div className="border border-outline-variant bg-surface-container p-2 flex flex-col">
                  <div className="text-xs mb-2 text-on-surface-variant">Generated DXF</div>
                  <div className="flex-1 flex items-center justify-center text-xs text-on-surface-variant">
                    {selected.hasGeneratedDxf ? "Generated fixture available" : "Not generated"}
                  </div>
                </div>
                <div className="border border-outline-variant bg-black p-2 flex flex-col">
                  <div className="text-xs mb-2 text-on-surface-variant">Difference Overlay</div>
                  <div className="flex-1 overflow-hidden" dangerouslySetInnerHTML={{ __html: overlay }} />
                  <div className="text-[10px] text-on-surface-variant mt-2 space-x-3">
                    <span className="text-emerald-400">Green: match</span>
                    <span className="text-amber-300">Amber: generated only</span>
                    <span className="text-rose-400">Red: reference only</span>
                  </div>
                </div>
              </div>

              <table className="w-full text-xs font-mono border border-outline-variant">
                <thead className="bg-surface-container-low text-on-surface-variant">
                  <tr>
                    <th className="text-left p-2">Feature</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-left p-2">IoU</th>
                    <th className="text-left p-2">Hausdorff</th>
                    <th className="text-left p-2">Hole pos</th>
                    <th className="text-left p-2">Unmatched</th>
                  </tr>
                </thead>
                <tbody>
                  {["fixture_outline", "sink_region", "keepout_regions", "solder_windows", "locating_pins", "clamp_holes", "spring_clips", "rails", "barriers"].map((name) => (
                    <tr key={name} className="border-t border-outline-variant">
                      <td className="p-2">{name}</td>
                      <td className="p-2">{statusOf(features, name)}</td>
                      <td className="p-2">{metric(features, name, "iou")}</td>
                      <td className="p-2">{metric(features, name, "hausdorff_mm")}</td>
                      <td className="p-2">{metric(features, name, "hole_position_error_mm")}</td>
                      <td className="p-2">{features?.find((f) => f.name === name)?.unmatched_feature_count ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
