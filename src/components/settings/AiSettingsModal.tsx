import React, { useState, useEffect } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { fixtureApi } from "../../services/api";
import { AiSettingsResponse, AiTestConnectionResponse } from "../../types/settings";

export const AiSettingsModal: React.FC = () => {
  const { isAiSettingsOpen, toggleAiSettingsModal, showToast } = useProjectStore();

  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiProvider, setAiProvider] = useState("openai_compatible");
  const [aiBaseUrl, setAiBaseUrl] = useState("https://api.openai.com/v1");
  const [aiModel, setAiModel] = useState("gpt-4o-mini");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiApiKeyMasked, setAiApiKeyMasked] = useState("");
  const [aiTimeoutMs, setAiTimeoutMs] = useState(10000);

  const [showKeyPlaintext, setShowKeyPlaintext] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<AiTestConnectionResponse | null>(null);

  useEffect(() => {
    if (!isAiSettingsOpen) return;
    setTestResult(null);
    setAiApiKey("");
    setIsLoading(true);

    fixtureApi
      .getAiSettings()
      .then((data: AiSettingsResponse) => {
        setAiEnabled(data.aiEnabled);
        setAiProvider(data.aiProvider || "openai_compatible");
        setAiBaseUrl(data.aiBaseUrl || "https://api.openai.com/v1");
        setAiModel(data.aiModel || "gpt-4o-mini");
        setAiApiKeyMasked(data.aiApiKeyMasked || "");
        setAiTimeoutMs(data.aiTimeoutMs || 10000);
      })
      .catch((err) => {
        showToast(`加载 AI 设置失败: ${(err as Error).message}`, "error");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [isAiSettingsOpen, showToast]);

  if (!isAiSettingsOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const updated = await fixtureApi.updateAiSettings({
        aiEnabled,
        aiProvider,
        aiBaseUrl,
        aiModel,
        aiApiKey: aiApiKey.trim() ? aiApiKey.trim() : undefined,
        aiTimeoutMs: Number(aiTimeoutMs) || 10000,
      });

      setAiApiKeyMasked(updated.aiApiKeyMasked);
      setAiApiKey("");
      showToast("AI 服务配置已成功保存", "success");
      toggleAiSettingsModal(false);
    } catch (err) {
      showToast(`保存 AI 配置失败: ${(err as Error).message}`, "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      // 若用户输入了新的 API Key 或更新了设置，先临时保存或直接测试
      if (aiApiKey.trim() || aiModel) {
        await fixtureApi.updateAiSettings({
          aiEnabled,
          aiProvider,
          aiBaseUrl,
          aiModel,
          aiApiKey: aiApiKey.trim() ? aiApiKey.trim() : undefined,
          aiTimeoutMs: Number(aiTimeoutMs) || 10000,
        });
      }
      const res = await fixtureApi.testAiConnection();
      setTestResult(res);
    } catch (err) {
      setTestResult({
        ok: false,
        message: `测试请求失败: ${(err as Error).message}`,
      });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="w-full max-w-xl bg-surface-container border border-primary-container/40 shadow-[0_0_35px_rgba(0,229,255,0.15)] rounded p-6 flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-outline-variant pb-4 mb-4">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary-container fill-1 text-2xl">
              psychology
            </span>
            <div>
              <h2 className="font-headline-md text-headline-md text-primary-container font-bold">
                AI 工程助手配置
              </h2>
              <p className="text-body-sm text-on-surface-variant">
                配置 OpenAI 兼容格式大模型 API（如 DeepSeek、通义千问、OpenAI 等）
              </p>
            </div>
          </div>
          <button
            onClick={() => toggleAiSettingsModal(false)}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors"
            title="关闭"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Loading Skeleton */}
        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-on-surface-variant">
            <span className="material-symbols-outlined animate-spin text-3xl text-primary-container">
              progress_activity
            </span>
            <span className="font-data-mono text-body-sm">正在加载配置...</span>
          </div>
        ) : (
          <form onSubmit={handleSave} className="flex-1 overflow-y-auto space-y-4 pr-1">
            {/* AI 开关 */}
            <div className="flex items-center justify-between p-3.5 bg-surface rounded border border-outline-variant">
              <div>
                <span className="font-bold text-body-md text-on-surface block">
                  启用 AI 助手 (AI Assistant)
                </span>
                <span className="text-xs text-on-surface-variant">
                  关闭时 AI 抽屉仅允许查看历史，不调用外部模型 API
                </span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiEnabled}
                  onChange={(e) => setAiEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-container"></div>
              </label>
            </div>

            {/* Provider 选择 */}
            <div>
              <label className="block font-data-mono text-body-sm text-on-surface mb-1.5 font-semibold">
                服务商类型 (Provider)
              </label>
              <select
                value={aiProvider}
                onChange={(e) => setAiProvider(e.target.value)}
                className="w-full bg-surface border border-outline-variant text-on-surface p-2.5 text-body-sm rounded font-data-mono focus:border-primary-container focus:outline-none"
              >
                <option value="openai_compatible">OpenAI 兼容协议 (OpenAI Compatible API)</option>
              </select>
            </div>

            {/* Base URL */}
            <div>
              <label className="block font-data-mono text-body-sm text-on-surface mb-1.5 font-semibold">
                接口地址 (Base URL)
              </label>
              <input
                type="text"
                value={aiBaseUrl}
                onChange={(e) => setAiBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                required
                className="w-full bg-surface border border-outline-variant text-on-surface p-2.5 text-body-sm rounded font-data-mono focus:border-primary-container focus:outline-none"
              />
              <span className="text-[11px] text-on-surface-variant block mt-1">
                支持 DashScope (https://dashscope.aliyuncs.com/compatible-mode/v1)、DeepSeek (https://api.deepseek.com/v1) 等
              </span>
            </div>

            {/* Model Name */}
            <div>
              <label className="block font-data-mono text-body-sm text-on-surface mb-1.5 font-semibold">
                模型名称 (Model)
              </label>
              <input
                type="text"
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                placeholder="gpt-4o-mini 或 deepseek-chat 或 qwen-plus"
                required
                className="w-full bg-surface border border-outline-variant text-on-surface p-2.5 text-body-sm rounded font-data-mono focus:border-primary-container focus:outline-none"
              />
            </div>

            {/* API Key */}
            <div>
              <label className="block font-data-mono text-body-sm text-on-surface mb-1.5 font-semibold">
                API Key
              </label>
              <div className="relative flex items-center">
                <input
                  type={showKeyPlaintext ? "text" : "password"}
                  value={aiApiKey}
                  onChange={(e) => setAiApiKey(e.target.value)}
                  placeholder={
                    aiApiKeyMasked ? `已配置: ${aiApiKeyMasked} (留空保持不变)` : "sk-..."
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2.5 pr-10 text-body-sm rounded font-data-mono focus:border-primary-container focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowKeyPlaintext(!showKeyPlaintext)}
                  className="absolute right-2.5 text-on-surface-variant hover:text-on-surface transition-colors"
                  title={showKeyPlaintext ? "隐藏密文" : "显示明文"}
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {showKeyPlaintext ? "visibility_off" : "visibility"}
                  </span>
                </button>
              </div>
              <span className="text-[11px] text-on-surface-variant block mt-1">
                {aiApiKeyMasked ? `当前后端已保存: ${aiApiKeyMasked}。若无需更改请留空。` : "凭据仅在后端安全存储，前端不显示明文。"}
              </span>
            </div>

            {/* Timeout */}
            <div>
              <label className="block font-data-mono text-body-sm text-on-surface mb-1.5 font-semibold">
                超时时间 (毫秒, ms)
              </label>
              <input
                type="number"
                value={aiTimeoutMs}
                onChange={(e) => setAiTimeoutMs(Number(e.target.value))}
                min={1000}
                max={60000}
                step={1000}
                required
                className="w-full bg-surface border border-outline-variant text-on-surface p-2.5 text-body-sm rounded font-data-mono focus:border-primary-container focus:outline-none"
              />
            </div>

            {/* Test Connection Result Box */}
            {testResult && (
              <div
                className={`p-3 rounded border text-body-sm flex items-start gap-2.5 font-data-mono ${
                  testResult.ok
                    ? "bg-[#4ade80]/10 border-[#4ade80]/40 text-[#4ade80]"
                    : "bg-error/10 border-error/40 text-error"
                }`}
              >
                <span className="material-symbols-outlined text-[20px] shrink-0 mt-0.5">
                  {testResult.ok ? "check_circle" : "error"}
                </span>
                <div className="flex-1 break-all">{testResult.message}</div>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-4 mt-4 border-t border-outline-variant">
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={isTesting || isSaving}
                className="px-4 py-2 border border-outline-variant text-on-surface text-body-sm hover:bg-surface-container-highest transition-colors rounded flex items-center gap-1.5 disabled:opacity-50"
              >
                {isTesting ? (
                  <>
                    <span className="material-symbols-outlined text-[16px] animate-spin">
                      progress_activity
                    </span>
                    <span>正在测试...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">network_check</span>
                    <span>测试连接</span>
                  </>
                )}
              </button>

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => toggleAiSettingsModal(false)}
                  className="px-5 py-2 border border-outline-variant text-on-surface text-body-sm hover:bg-surface-container-highest transition-colors rounded"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={isSaving || isTesting}
                  className="px-6 py-2 bg-primary-container text-on-primary-fixed font-bold text-body-sm hover:bg-surface-tint glow-cyan transition-colors rounded flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isSaving ? (
                    <>
                      <span className="material-symbols-outlined text-[16px] animate-spin">
                        progress_activity
                      </span>
                      <span>保存中...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[16px]">save</span>
                      <span>保存配置</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
