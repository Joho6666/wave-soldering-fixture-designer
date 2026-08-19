import React, { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { fixtureApi } from "../../services/api";

export const InspectionPanel: React.FC = () => {
  const {
    currentProject,
    jobStatus,
    fixtureResult,
    locateIssue,
    overrideDrc,
    regenerate,
    previewSvg,
    resetCadView,
    showToast
  } = useProjectStore();

  const [isDownloading, setIsDownloading] = useState(false);

  const issues = fixtureResult.issues || [];
  const passedCount = issues.filter((issue) => issue.severity === "info").length;
  const hasPendingReview = (fixtureResult.reviewItems || []).some((item) => item.mandatory && item.status === "pending");
  const hasBlockingDrc = issues.some((issue) => (issue.severity === "blocking" || issue.severity === "error") && !issue.confirmed);
  const canDownloadProduction = !hasPendingReview && !hasBlockingDrc;
  const totalCount = issues.length;
  const reviewCount = (fixtureResult.reviewItems || []).filter((item) => item.mandatory && item.status === "pending").length;
  const checkLabel = jobStatus === "review_required"
    ? `待确认 ${reviewCount} 项`
    : issues.length === 0
      ? "未发现 DRC 问题"
      : `${passedCount}/${totalCount} PASS`;

    const handleDownloadPreviewDxf = async () => {
    if (!currentProject?.id) {
      showToast("当前任务不存在", "error");
      return;
    }
    setIsDownloading(true);
    try {
      const blob = await fixtureApi.downloadPreviewDxf(currentProject.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${currentProject.name.replace(/\.zip$/i, "")}-preview.dxf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      showToast("预览 DXF 已开始下载", "success");
    } catch (error) {
      showToast(`预览 DXF 下载失败: ${(error as Error).message}`, "error");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadDxf = async () => {
    if (!currentProject?.id) {
      showToast("当前任务不存在，无法下载 DXF", "error");
      return;
    }
    setIsDownloading(true);
    showToast("正在下载后端生成的 DXF 工程图纸...", "info");

    try {
      const blob = await fixtureApi.downloadDxf(currentProject.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${currentProject.name.replace(/\.zip$/i, "")}-fixture.dxf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      showToast("DXF 已开始下载", "success");
    } catch (error) {
      showToast(`DXF 下载失败: ${(error as Error).message}`, "error");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      await regenerate();
      showToast("已提交真实重新生成任务", "info");
    } catch {
      // regenerate 已显示具体错误
    }
  };

  return (
    <aside className="w-sidebar-width h-full bg-surface-container border-l border-outline-variant flex flex-col z-30 shrink-0">
      {/* 1. 设计检查 (CHECK) */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        <div className="p-panel-padding border-b border-outline-variant bg-surface-container-low flex justify-between items-center sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary-container text-[20px]">fact_check</span>
            <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
              设计检查 (CHECK)
            </h3>
          </div>
          <div
            className={`px-2 py-0.5 border font-data-mono text-[12px] font-bold ${
              jobStatus === "completed" && issues.length > 0 && passedCount === totalCount
                ? "bg-[#4ade80]/10 border-[#4ade80] text-[#4ade80]"
                : "bg-tertiary-container/20 border-tertiary-container text-tertiary-container"
            }`}
          >
            {checkLabel}
          </div>
        </div>

        <div className="p-2 flex flex-col gap-2">
          {issues.map((issue) => {
            const isFinding = issue.severity !== "info";
            const isBlocking = issue.severity === "blocking" || issue.severity === "error";

            if (isFinding) {
              return (
                <div
                  key={issue.id}
                  className="bg-[#3e2e00]/25 p-3 border border-tertiary-container relative overflow-hidden group shadow-sm"
                >
                  <div className="absolute top-0 left-0 w-1 h-full bg-tertiary-container"></div>
                  <div className="flex gap-2 items-start pl-1">
                    <span className="material-symbols-outlined text-tertiary-container text-[18px] mt-0.5 animate-pulse">
                      warning
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="font-body-sm text-[12px] text-tertiary-container font-bold">
                          {issue.title}
                        </p>
                        <span className={`font-label-caps text-[9px] px-1 rounded-sm ${issue.confirmed ? "bg-emerald-800 text-white" : isBlocking ? "bg-red-600 text-white" : "bg-tertiary-container text-on-tertiary"}`}>
                          {issue.confirmed ? "OVERRIDDEN" : isBlocking ? "BLOCKING" : "DRC VIOLATION"}
                        </span>
                      </div>

                      <p className="font-body-sm text-[11px] text-on-surface-variant mt-1 leading-tight">
                        {issue.description}
                      </p>

                      {issue.currentValue !== undefined && issue.requiredValue !== undefined && (
                        <div className="mt-2 bg-[#101317] p-1.5 border border-[#3e2e00] flex justify-between items-center font-data-mono text-[11px]">
                          <span className="text-on-surface-variant text-[10px]">实测:</span>
                          <span className="text-error font-bold">
                            {(issue.currentValue ?? 0).toFixed(2)} {issue.unit}
                          </span>
                          <span className="text-on-surface-variant text-[10px]">要求:</span>
                          <span className="text-on-surface">
                            ≥ {(issue.requiredValue ?? 0).toFixed(2)} {issue.unit}
                          </span>
                        </div>
                      )}

                      <div className="mt-2 flex items-center justify-between gap-2">
                        <button
                          onClick={() => locateIssue(issue)}
                          className="px-2 py-1 bg-surface border border-tertiary-container/50 hover:border-tertiary-container text-tertiary-container font-data-mono text-[11px] flex items-center gap-1 transition-colors"
                        >
                          <span className="material-symbols-outlined text-[14px]">my_location</span>
                          在图纸中定位
                        </button>

                        {issue.confirmed ? (
                          <span className="text-[10px] font-data-mono text-[#4ade80] flex items-center gap-0.5">
                            <span className="material-symbols-outlined text-[12px]">verified</span>
                            已放行
                          </span>
                        ) : (
                          <button
                            onClick={() => overrideDrc(issue.id)}
                            className="text-[10px] font-label-caps text-on-surface-variant hover:text-primary-container transition-colors flex items-center gap-0.5"
                            title="工程师放行确认此 DRC 规则"
                          >
                            <span className="material-symbols-outlined text-[12px]">verified_user</span>
                            放行确认
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            }

            // 通过项
            return (
              <div
                key={issue.id}
                className="bg-surface p-2 border border-outline-variant flex gap-2 items-start opacity-75 hover:opacity-100 transition-opacity"
              >
                <span className="material-symbols-outlined text-[#4ade80] text-[18px] mt-0.5">
                  check_circle
                </span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <p className="font-body-sm text-[12px] text-on-surface font-medium">
                      {issue.title}
                    </p>
                    {issue.confirmed && (
                      <span className="text-[10px] text-primary-container font-data-mono">(人工确认)</span>
                    )}
                  </div>
                  <p className="font-data-mono text-[10px] text-on-surface-variant mt-0.5">
                    {issue.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* 2. 治具信息 (PROPS) */}
        <div className="p-panel-padding border-y border-outline-variant bg-surface-container-low flex items-center gap-2 mt-2 sticky top-[41px] z-10">
          <span className="material-symbols-outlined text-on-surface-variant text-[20px]">info</span>
          <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
            治具信息 (PROPS)
          </h3>
        </div>

        <div className="p-3 bg-surface-container">
          <table className="w-full text-left border-collapse font-data-mono text-[11px]">
            <tbody>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">PCB 尺寸</td>
                <td className="py-1.5 text-on-surface text-right">
                  {(fixtureResult.pcb?.width ?? 0).toFixed(2)} × {(fixtureResult.pcb?.height ?? 0).toFixed(2)} mm
                </td>
              </tr>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">治具尺寸</td>
                <td className="py-1.5 text-on-surface text-right">
                  {(fixtureResult.fixture?.width ?? 0).toFixed(2)} × {(fixtureResult.fixture?.height ?? 0).toFixed(2)} mm
                </td>
              </tr>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">PCB 数量</td>
                <td className="py-1.5 text-on-surface text-right">1 拼</td>
              </tr>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">定位销 / 压扣</td>
                <td className="py-1.5 text-on-surface text-right">
                  {fixtureResult.locatingPins} 销 / {fixtureResult.clamps} 扣
                </td>
              </tr>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">BOT 避位区</td>
                <td className="py-1.5 text-on-surface text-right">
                  {fixtureResult.keepoutRegions} 处
                </td>
              </tr>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">TOP 上锡窗口</td>
                <td className="py-1.5 text-on-surface text-right">
                  {fixtureResult.solderWindows} 处
                </td>
              </tr>
              <tr className="border-b border-outline-variant/60">
                <td className="py-1.5 text-on-surface-variant">治具材质</td>
                <td className="py-1.5 text-on-surface text-right">
                  {fixtureResult.fixture.material || "未提供"}
                </td>
              </tr>
              <tr>
                <td className="py-1.5 text-on-surface-variant">板材厚度</td>
                <td className="py-1.5 text-on-surface text-right">
                  {(fixtureResult.fixture?.thickness ?? 0) > 0 ? `${(fixtureResult.fixture?.thickness ?? 0).toFixed(1)} mm` : "未提供（待工程确认）"}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. 底部操作栏 */}
      <div className="p-panel-padding border-t border-outline-variant bg-surface-container-high flex flex-col gap-2">
        <button
          onClick={handleDownloadDxf}
          disabled={isDownloading || !canDownloadProduction}
          title={!canDownloadProduction ? `生产未就绪: ${hasPendingReview ? "存在待审核项 " : ""}${hasBlockingDrc ? "存在 DRC blocking/error" : ""}` : ""}
          className="w-full h-10 bg-primary-container text-on-primary-fixed font-headline-md text-body-md font-bold hover:bg-surface-tint glow-cyan transition-colors flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isDownloading ? (
            <>
              <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
              正在准备 DXF...
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[18px]">download</span>
              {!canDownloadProduction ? "生产未就绪" : "下载生产 DXF"}
            </>
          )}
        </button>

        <button
          onClick={handleDownloadPreviewDxf}
          disabled={isDownloading}
          className="w-full h-8 bg-transparent border border-outline-variant text-on-surface font-body-sm text-[11px] hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-1"
        >
          <span className="material-symbols-outlined text-[14px]">preview</span>
          下载预览 DXF (NOT FOR PRODUCTION)
        </button>

        <div className="flex gap-2">
          <button
            onClick={() => {
              if (!previewSvg) {
                showToast("后端尚未返回 SVG 预览", "error");
                return;
              }
              resetCadView();
              showToast("当前 CAD 视口正在显示后端 SVG 预览", "success");
            }}
            className="flex-1 py-1.5 bg-transparent border border-outline-variant text-on-surface font-body-sm text-[11px] hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">image</span>
            预览图
          </button>
          <button
            onClick={handleRegenerate}
            className="flex-1 py-1.5 bg-transparent border border-outline-variant text-on-surface font-body-sm text-[11px] hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">refresh</span>
            重新生成
          </button>
        </div>

        {/* Version Info Footer */}
        <div className="mt-2 pt-2 border-t border-outline-variant text-[10px] text-outline font-body-sm">
          <div className="flex justify-between">
            <span>App {fixtureResult?.softwareVersion || '0.4.0'}</span>
            <span>Engine {fixtureResult?.algorithmVersion || '-'}</span>
            <span>Rules {fixtureResult?.ruleProfileVersion || '-'}</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

