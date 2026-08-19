import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const Toast: React.FC = () => {
  const { toast, hideToast } = useProjectStore();

  if (!toast) return null;

  const bgStyles = {
    success: "bg-surface-container-high border-primary-container text-primary-container",
    warning: "bg-surface-container-high border-tertiary-container text-tertiary-container",
    error: "bg-surface-container-high border-error text-error",
    info: "bg-surface-container-high border-outline-variant text-on-surface"
  }[toast.type];

  const iconName = {
    success: "check_circle",
    warning: "warning",
    error: "cancel",
    info: "info"
  }[toast.type];

  return (
    <div className="fixed top-14 right-6 z-50 flex items-center gap-2 px-4 py-2.5 border shadow-[0_4px_20px_rgba(0,0,0,0.6)] backdrop-blur-md transition-all animate-bounce-short">
      <div className={`flex items-center gap-2 font-data-mono text-body-sm ${bgStyles} p-2 border`}>
        <span className="material-symbols-outlined text-[18px]">{iconName}</span>
        <span>{toast.message}</span>
        <button
          onClick={hideToast}
          className="ml-2 hover:opacity-75 transition-opacity"
        >
          <span className="material-symbols-outlined text-[14px]">close</span>
        </button>
      </div>
    </div>
  );
};
