import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const ReviewBanner: React.FC = () => {
  const { jobStatus, fixtureResult, acceptReview, rejectReview } = useProjectStore();
  const pending = (fixtureResult.reviewItems || []).filter((item) => item.status === "pending");
  if (jobStatus !== "review_required" && pending.length === 0) return null;

  return (
    <div className="w-full shrink-0 bg-[#3e2e00]/95 border-b border-tertiary-container px-4 py-3 shadow-xl backdrop-blur-md max-h-56 overflow-y-auto">
      <div className="flex items-start gap-3">
        <span className="material-symbols-outlined text-tertiary-container">rule</span>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <p className="font-bold text-tertiary-container">
              需工程师审核确认项（{pending.length} 项待处理）
            </p>
            <span className="font-data-mono text-[10px] text-amber-200">
              {jobStatus === "review_required" ? "🔒 DXF 最终下载已锁定" : "✅ 审核已就绪"}
            </span>
          </div>
          <div className="mt-2 grid gap-2">
            {(fixtureResult.reviewItems || []).map((item) => {
              const isPending = item.status === "pending";
              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between text-left text-[11px] text-on-surface border-t border-tertiary-container/30 pt-1.5"
                >
                  <div className="flex-1 pr-2">
                    <span className="font-semibold text-amber-300">[{item.title}]</span> — {item.description}
                    <span className="ml-2 text-[10px] text-on-surface-variant font-data-mono">
                      (置信度: {(((item.confidence ?? 0.5) * 100).toFixed(0))}% | 状态: {item.status})
                    </span>
                  </div>
                  {isPending && (
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => acceptReview(item.id)}
                        className="px-2 py-0.5 bg-emerald-700/80 hover:bg-emerald-600 text-white rounded text-[10px] transition-colors"
                      >
                        接受
                      </button>
                      <button
                        onClick={() => rejectReview(item.id)}
                        className="px-2 py-0.5 bg-rose-800/80 hover:bg-rose-700 text-white rounded text-[10px] transition-colors"
                      >
                        拒绝
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-[10px] text-on-surface-variant">
            提示：所有待确认特征经工程师确认后，系统将自动重新计算治具几何并解锁最终生产 DXF。
          </p>
        </div>
      </div>
    </div>
  );
};
