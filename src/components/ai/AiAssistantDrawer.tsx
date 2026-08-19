import React, { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { AiMessage } from "../../types/ai";

export const AiAssistantDrawer: React.FC = () => {
  const {
    isAiDrawerOpen, toggleAiDrawer, currentProject, aiMessages, aiIsLoading, aiError,
    sendAiMessage, applyAiCommand, rejectAiCommand, clearAiConversation,
  } = useProjectStore();
  const [input, setInput] = useState("");
  if (!isAiDrawerOpen) return null;

  const send = async () => {
    const message = input.trim();
    if (!message) return;
    setInput("");
    await sendAiMessage(message);
  };

  return (
    <div className="fixed inset-y-0 right-0 top-toolbar-height bottom-8 w-[380px] bg-surface-container border-l border-outline-variant z-40 shadow-2xl flex flex-col">
      <div className="p-panel-padding border-b border-outline-variant bg-surface-container-low flex items-center justify-between">
        <div>
          <h2 className="font-headline-md text-on-surface font-semibold">AI 工程助手</h2>
          <p className="font-data-mono text-[10px] text-on-surface-variant">Job: {currentProject?.id || "未加载"}</p>
        </div>
        <div className="flex gap-1">
          <button onClick={clearAiConversation} className="text-xs text-on-surface-variant px-2" title="清空会话">清空</button>
          <button onClick={() => toggleAiDrawer(false)} className="text-on-surface-variant p-1"><span className="material-symbols-outlined text-[18px]">close</span></button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {aiMessages.length === 0 && <p className="text-sm text-on-surface-variant">输入自然语言，例如：把避位间距改为 1.0 mm。AI 只会提出结构化命令，修改几何前必须确认。</p>}
        {aiMessages.map((message: AiMessage) => (
          <div key={message.id} className={message.role === "user" ? "text-right" : "text-left"}>
            <div className="inline-block max-w-[95%] p-3 text-[12px] whitespace-pre-wrap bg-surface border border-outline-variant text-on-surface text-left">{message.content}</div>
            {message.command && message.command.requiresConfirmation && message.commandStatus === "pending" && (
              <div className="mt-2 p-2 border border-tertiary-container bg-[#3e2e00]/30 text-left">
                <p className="text-tertiary-container text-xs font-bold">待确认命令：{message.command.kind}</p>
                <p className="text-[11px] text-on-surface-variant mt-1">{message.command.reason}</p>
                {message.command.parameters && <pre className="text-[10px] text-on-surface mt-2 overflow-auto">{JSON.stringify(message.command.parameters, null, 2)}</pre>}
                <div className="flex gap-2 mt-2">
                  <button onClick={() => void applyAiCommand(message)} className="px-2 py-1 bg-primary-container text-on-primary-fixed text-xs">应用并重新生成</button>
                  <button onClick={() => rejectAiCommand(message.id)} className="px-2 py-1 border border-outline-variant text-xs text-on-surface">拒绝</button>
                </div>
              </div>
            )}
            {message.commandStatus === "applied" && <p className="text-[10px] text-[#4ade80] mt-1">命令已提交确定性几何引擎</p>}
            {message.commandStatus === "rejected" && <p className="text-[10px] text-on-surface-variant mt-1">命令已拒绝</p>}
          </div>
        ))}
        {aiIsLoading && <p className="text-xs text-primary-container">正在请求后端 AI Provider…</p>}
        {aiError && <p className="text-xs text-error">{aiError}</p>}
      </div>

      <div className="p-3 border-t border-outline-variant bg-surface-container-high">
        {!currentProject && <p className="text-[10px] text-on-surface-variant mb-2">请先上传并解析 Job。</p>}
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
          placeholder="输入工程指令… (Enter 发送，Shift+Enter 换行)"
          rows={3}
          className="w-full bg-surface border border-outline-variant text-on-surface px-3 py-2 text-xs resize-none focus:border-primary-container focus:outline-none"
        />
        <button onClick={() => void send()} disabled={!currentProject || !input.trim() || aiIsLoading} className="w-full mt-2 py-2 bg-primary-container text-on-primary-fixed disabled:opacity-40 text-sm font-semibold rounded hover:bg-surface-tint transition-colors">发送</button>
      </div>
    </div>
  );
};
