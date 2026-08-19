import React from "react";
import { TopNavBar } from "../components/layout/TopNavBar";
import { StatusBar } from "../components/layout/StatusBar";
import { LayerTreePanel } from "../components/layers/LayerTreePanel";
import { CadViewer } from "../components/cad/CadViewer";
import { InspectionPanel } from "../components/inspection/InspectionPanel";
import { ParameterDrawer } from "../components/parameters/ParameterDrawer";
import { AiAssistantDrawer } from "../components/ai/AiAssistantDrawer";
import { ReviewBanner } from "../components/inspection/ReviewBanner";

export const WorkspacePage: React.FC = () => {
  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-background text-on-background">
      <TopNavBar />

      {/* Review 状态独立占据顶部空间，不遮挡 CAD 和左右面板 */}
      <ReviewBanner />
      {/* Main CAD Workspace Layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* 左侧图层管理面板 */}
        <LayerTreePanel />

        {/* 中间核心 SVG CAD 交互视口 */}
        <CadViewer />

        {/* 右侧设计检查与治具详情面板 */}
        <InspectionPanel />

        {/* 浮动工程参数抽屉 */}
        <ParameterDrawer />

        {/* 浮动 AI 工程助手抽屉 */}
        <AiAssistantDrawer />

      </div>

      <StatusBar />
    </div>
  );
};
