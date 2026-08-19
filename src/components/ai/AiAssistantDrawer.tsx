import React, { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { AiMessage, AiCommand } from "../../types/ai";

const COMMAND_TITLES: Record<string, { label: string; icon: string; color: string }> = {
  apply_recipe_preset: { label: "工艺配方预设建设", icon: "auto_awesome", color: "text-amber-300" },
  set_locating_pins: { label: "定位孔方案建设", icon: "push_pin", color: "text-cyan-300" },
  add_custom_region: { label: "自定义区域建设", icon: "crop_square", color: "text-emerald-300" },
  auto_fix_drc: { label: "DRC 缺陷自动修复", icon: "build_circle", color: "text-rose-300" },
  update_parameters: { label: "工程参数微调", icon: "tune", color: "text-primary-container" },
  regenerate: { label: "重新计算出图", icon: "refresh", color: "text-on-surface" },
};

export const AiAssistantDrawer: React.FC = () => {
  const {
    isAiDrawerOpen,
    toggleAiDrawer,
    currentProject,
    aiMessages,
    aiIsLoading,
    aiError,
    sendAiMessage,
    applyAiCommand,
    rejectAiCommand,
    clearAiConversation,
  } = useProjectStore();

  const [input, setInput] = useState("");
  if (!isAiDrawerOpen) return null;

  const send = async (textToSend?: string) => {
    const message = (textToSend || input).trim();
    if (!message) return;
    if (!textToSend) setInput("");
    await sendAiMessage(message);
  };

  const renderCommandBody = (command: AiCommand) => {
    switch (command.kind) {
      case "apply_recipe_preset":
        return (
          <div className="space-y-1.5 mt-2">
            <div className="flex justify-between items-center text-on-surface font-semibold text-[11px] bg-surface p-1.5 rounded border border-outline-variant/60">
              <span>配方名称:</span>
              <span className="text-amber-300">{command.presetName || command.presetId}</span>
            </div>
            {command.parameters && (
              <div className="grid grid-cols-2 gap-1 text-[10px] font-data-mono bg-surface-container-lowest p-2 rounded">
                {Object.entries(command.parameters).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-on-surface-variant">
                    <span>{k.replace("Mm", "")}:</span>
                    <span className="text-on-surface font-bold">{v}mm</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "set_locating_pins":
        return (
          <div className="space-y-1.5 mt-2">
            <div className="flex justify-between text-on-surface text-[11px] bg-surface p-1.5 rounded border border-outline-variant/60">
              <span>选定定位孔:</span>
              <span className="text-cyan-300 font-bold font-data-mono">
                {command.pinDrillIds?.join(", ") || "自动匹配"}
              </span>
            </div>
          </div>
        );

      case "add_custom_region":
        return (
          <div className="space-y-1.5 mt-2 text-[10px] font-data-mono bg-surface p-2 rounded border border-outline-variant/60">
            <div className="flex justify-between text-on-surface">
              <span>类型 / 标识:</span>
              <span className="text-emerald-300 font-bold">
                {command.regionType === "keepout" ? "BOT 避位槽" : "TOP 透锡槽"} ({command.label || "自定义"})
              </span>
            </div>
            <div className="flex justify-between text-on-surface-variant">
              <span>中心坐标:</span>
              <span className="text-on-surface">({command.x?.toFixed(1)}, {command.y?.toFixed(1)}) mm</span>
            </div>
            <div className="flex justify-between text-on-surface-variant">
              <span>矩形尺寸:</span>
              <span className="text-on-surface">{command.width?.toFixed(1)} × {command.height?.toFixed(1)} mm</span>
            </div>
          </div>
        );

      case "auto_fix_drc":
        return (
          <div className="space-y-1.5 mt-2">
            {command.targetIssueIds && command.targetIssueIds.length > 0 && (
              <div className="text-[10px] text-rose-300 bg-rose-950/40 p-1.5 rounded border border-rose-800/60">
                目标缺陷: {command.targetIssueIds.join(", ")}
              </div>
            )}
            {command.suggestedParameters && (
              <div className="grid grid-cols-2 gap-1 text-[10px] font-data-mono bg-surface p-2 rounded border border-outline-variant/60">
                {Object.entries(command.suggestedParameters).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-on-surface-variant">
                    <span>{k.replace("Mm", "")}:</span>
                    <span className="text-emerald-400 font-bold">{v}mm</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "update_parameters":
        return (
          command.parameters && (
            <div className="grid grid-cols-2 gap-1 text-[10px] font-data-mono bg-surface p-2 rounded border border-outline-variant/60 mt-2">
              {Object.entries(command.parameters).map(([k, v]) => (
                <div key={k} className="flex justify-between text-on-surface-variant">
                  <span>{k.replace("Mm", "")}:</span>
                  <span className="text-primary-container font-bold">{v}mm</span>
                </div>
              ))}
            </div>
          )
        );

      default:
        return null;
    }
  };

  const quickPrompts = [
    "按汽车电子高可靠性标准配置",
    "选择对角大孔作为定位销",
    "帮我自动修复当前壁厚不足",
  ];

  return (
    <div className="fixed inset-y-0 right-0 top-toolbar-height bottom-8 w-[380px] bg-surface-container border-l border-outline-variant z-40 shadow-2xl flex flex-col animate-slide-in">
      {/* Header */}
      <div className="p-panel-padding border-b border-outline-variant bg-surface-container-low flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary-container fill-1 text-[22px]">smart_toy</span>
          <div>
            <h2 className="font-headline-md text-on-surface font-semibold text-[13px]">AI 治具建设与审查 Copilot</h2>
            <p className="font-data-mono text-[10px] text-on-surface-variant">
              Job: {currentProject?.id || "未加载"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={clearAiConversation} className="text-xs text-on-surface-variant hover:text-on-surface px-2 py-1 transition-colors" title="清空会话">
            清空
          </button>
          <button onClick={() => toggleAiDrawer(false)} className="text-on-surface-variant hover:text-on-surface p-1 transition-colors">
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {aiMessages.length === 0 && (
          <div className="text-center py-6 space-y-3">
            <span className="material-symbols-outlined text-primary-container text-4xl">architecture</span>
            <p className="text-xs text-on-surface font-semibold">AI 助手已就绪，可深度参与治具建设与审查</p>
            <p className="text-[11px] text-on-surface-variant">支持工艺配方推荐、定位孔优选、非标区域开槽及 DRC 自动修复。</p>

            <div className="pt-2 flex flex-col gap-1.5">
              <span className="text-[10px] text-outline uppercase font-data-mono">常用建设指令推荐：</span>
              {quickPrompts.map((q) => (
                <button
                  key={q}
                  onClick={() => void send(q)}
                  disabled={!currentProject || aiIsLoading}
                  className="text-left text-[11px] p-2 bg-surface hover:bg-surface-container-high border border-outline-variant rounded text-on-surface transition-colors disabled:opacity-40"
                >
                  👉 {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {aiMessages.map((message: AiMessage) => {
          const isUser = message.role === "user";
          const cmdMeta = message.command ? COMMAND_TITLES[message.command.kind] || { label: message.command.kind, icon: "build", color: "text-primary-container" } : null;

          return (
            <div key={message.id} className={isUser ? "text-right" : "text-left"}>
              <div
                className={`inline-block max-w-[95%] p-3 text-[12px] whitespace-pre-wrap rounded ${
                  isUser
                    ? "bg-primary-container/15 text-primary-container border border-primary-container/30 text-left font-data-mono"
                    : "bg-surface border border-outline-variant text-on-surface text-left shadow-sm"
                }`}
              >
                {message.content}
              </div>

              {/* Structured Command Proposal Card */}
              {message.command && message.command.requiresConfirmation && message.commandStatus === "pending" && cmdMeta && (
                <div className="mt-2 p-3 border border-tertiary-container/80 bg-[#3e2e00]/40 rounded text-left shadow-md">
                  <div className="flex items-center gap-1.5 border-b border-tertiary-container/40 pb-1.5 mb-1.5">
                    <span className={`material-symbols-outlined text-[16px] ${cmdMeta.color}`}>
                      {cmdMeta.icon}
                    </span>
                    <p className={`text-xs font-bold ${cmdMeta.color}`}>
                      {cmdMeta.label}
                    </p>
                  </div>

                  <p className="text-[11px] text-on-surface-variant leading-snug">
                    {message.command.reason}
                  </p>

                  {renderCommandBody(message.command)}

                  <div className="flex gap-2 mt-3 pt-2 border-t border-tertiary-container/30">
                    <button
                      onClick={() => void applyAiCommand(message)}
                      className="flex-1 py-1.5 bg-primary-container text-on-primary-fixed hover:bg-surface-tint glow-cyan font-bold text-xs rounded transition-colors flex items-center justify-center gap-1"
                    >
                      <span className="material-symbols-outlined text-[14px]">check</span>
                      批准并出图
                    </button>
                    <button
                      onClick={() => rejectAiCommand(message.id)}
                      className="px-3 py-1.5 border border-outline-variant hover:bg-surface-container-highest text-xs text-on-surface rounded transition-colors"
                    >
                      拒绝
                    </button>
                  </div>
                </div>
              )}

              {message.commandStatus === "applied" && (
                <p className="text-[10px] text-[#4ade80] mt-1 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[12px]">verified</span>
                  建设指令已批准并完成确定性出图
                </p>
              )}
              {message.commandStatus === "rejected" && (
                <p className="text-[10px] text-on-surface-variant mt-1">
                  已拒绝该建议
                </p>
              )}
              {message.commandStatus === "failed" && (
                <p className="text-[10px] text-error mt-1">
                  执行失败，请检查参数约束
                </p>
              )}
            </div>
          );
        })}

        {aiIsLoading && (
          <div className="flex items-center gap-2 text-xs text-primary-container p-2 bg-primary-container/5 rounded">
            <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
            <span>正在分析治具几何与工艺规则…</span>
          </div>
        )}
        {aiError && (
          <div className="p-2 text-xs text-error bg-error/10 border border-error/30 rounded">
            {aiError}
          </div>
        )}
      </div>

      {/* Input Box */}
      <div className="p-3 border-t border-outline-variant bg-surface-container-high">
        {!currentProject && (
          <p className="text-[10px] text-amber-300 mb-2">提示：请先上传 Gerber 任务以获得完整几何上下文。</p>
        )}
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void send();
            }
          }}
          disabled={!currentProject || aiIsLoading}
          placeholder="输入建设指令，例如：按汽车电子高可靠性配置 / 选择对角定位销…"
          rows={3}
          className="w-full bg-surface border border-outline-variant text-on-surface px-3 py-2 text-xs resize-none focus:border-primary-container focus:outline-none rounded font-data-mono"
        />
        <button
          onClick={() => void send()}
          disabled={!currentProject || !input.trim() || aiIsLoading}
          className="w-full mt-2 py-2 bg-primary-container text-on-primary-fixed disabled:opacity-40 text-sm font-semibold rounded hover:bg-surface-tint glow-cyan transition-colors flex items-center justify-center gap-1.5"
        >
          <span className="material-symbols-outlined text-[16px]">send</span>
          发送指令
        </button>
      </div>
    </div>
  );
};
