import React from "react";
import { useProjectStore } from "./store/useProjectStore";
import { UploadPage } from "./pages/UploadPage";
import { ProcessingPage } from "./pages/ProcessingPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { ErrorPage } from "./pages/ErrorPage";
import { Toast } from "./components/common/Toast";
import { DevToolbar } from "./components/layout/DevToolbar";
import { LayerConfirmModal } from "./components/gerber/LayerConfirmModal";
import { AiSettingsModal } from "./components/settings/AiSettingsModal";

export const App: React.FC = () => {
  const { jobStatus } = useProjectStore();

  const renderActivePage = () => {
    switch (jobStatus) {
      case "idle":
      case "file_selected":
      case "uploading":
        return <UploadPage />;
      case "parsing":
      case "layer_confirmation":
      case "generating":
        return <ProcessingPage />;
      case "review_required":
      case "completed":
        return <WorkspacePage />;
      case "failed":
        return <ErrorPage />;
      default:
        return <UploadPage />;
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background text-on-background">
      {renderActivePage()}
      
      {/* 全局组件 - 始终渲染，由状态控制显示 */}
      <LayerConfirmModal />
      <AiSettingsModal />
      <Toast />
      {import.meta.env.DEV && <DevToolbar />}
    </div>
  );
};

export default App;
