import React from "react";
import { TopNavBar } from "../components/layout/TopNavBar";
import { StatusBar } from "../components/layout/StatusBar";
import { DropZone } from "../components/upload/DropZone";

export const UploadPage: React.FC = () => {
  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-background text-on-background">
      <TopNavBar />

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto flex items-center justify-center p-panel-padding relative">
        {/* Radial Technical Grid background */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage: "radial-gradient(#3b494c 1px, transparent 1px)",
            backgroundSize: "16px 16px"
          }}
        ></div>

        <DropZone />
      </main>

      <StatusBar />
    </div>
  );
};
