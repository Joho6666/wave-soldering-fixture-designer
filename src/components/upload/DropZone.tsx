import React, { useRef, useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { analyzeZipFile } from "../../utils/zipHelper";
import { fixtureApi } from "../../services/api";

export const DropZone: React.FC = () => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    sourceFile,
    uploadedFileMeta,
    setSourceFile,
    setUploadedFileMeta,
    setCurrentProject,
    hydrateJob,
    setAnalysis,
    setJobStatus,
    loadNormalDemo,
    showToast
  } = useProjectStore();

  const handleFileProcess = async (file: File) => {
    // MVP 正式输入只接受完整 Gerber ZIP 制造文件包。
    const validExtensions = [".zip"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();

    if (!validExtensions.includes(ext)) {
      showToast(`不支持的文件格式: ${file.name}，请上传 Gerber / DXF / ZIP 文件`, "error");
      return;
    }

    setIsAnalyzing(true);

    try {
      // 保存真实源文件
      setSourceFile(file);
      
      if (file.name.toLowerCase().endsWith(".zip")) {
        // ZIP 文件前端真实解构
        const summary = await analyzeZipFile(file);
        setUploadedFileMeta({
          name: file.name,
          size: file.size,
          fileCount: summary.fileCount,
          gerberCount: summary.gerberCount,
          drillCount: summary.drillCount,
          dxfCount: summary.dxfCount
        });


        setAnalysis({
          width: 0,
          height: 0,
          fileCount: summary.fileCount,
          holeCount: 0,
          outlineClosed: false,
          outlineAreaMm2: 0,
          layers: summary.layers
        });

        setJobStatus("file_selected");
        showToast(`成功解析 ZIP 归档，检测到 ${summary.fileCount} 个制造文件`, "success");
      } else {
        // 单文件
        setUploadedFileMeta({
          name: file.name,
          size: file.size,
          fileCount: 1,
          gerberCount: ext.includes(".gbr") || ext.includes(".ger") ? 1 : 0,
          drillCount: ext.includes(".drl") ? 1 : 0,
          dxfCount: ext.includes(".dxf") ? 1 : 0
        });
        setJobStatus("file_selected");
        showToast(`已添加文件: ${file.name}`, "info");
      }
    } catch (err) {
      showToast("文件读取失败，请检查 ZIP 文件是否损坏", "error");
      setSourceFile(null);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileProcess(e.target.files[0]);
    }
  };

  const handleStartGeneration = async () => {
    if (!sourceFile) {
      showToast("源文件丢失，请重新上传", "error");
      return;
    }

    try {
      setJobStatus("uploading");
      
      // 创建后端 Job。后端负责实际解析、生成、DRC 与导出。
      const project = await fixtureApi.createJob(sourceFile);
      setCurrentProject(project);

      // 当前 MVP 后端可能在响应前同步完成；无论同步或异步，都先进入
      // Processing，由其轮询/水合真实结果后再展示 Workspace。
      if (project.status === "completed" || project.status === "review_required") {
        await hydrateJob(project.id);
      } else {
        setJobStatus(project.status);
      }
    } catch (error) {
      showToast("创建任务失败: " + (error as Error).message, "error");
      setJobStatus("failed");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <div className="w-full max-w-2xl bg-surface-container border border-outline-variant p-8 relative z-10 rounded">
      {/* Header Text */}
      <div className="text-center mb-8">
        <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2 tracking-tight">
          开始生成波峰焊治具
        </h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          上传 PCB Gerber 文件，自动分析 PCB 结构并生成治具 CAD 工程图。
        </p>
      </div>

      {/* Upload Drop Zone */}
      {!uploadedFileMeta ? (
        <div
          id="upload-zone"
          tabIndex={0}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed transition-all duration-200 rounded p-10 flex flex-col items-center justify-center cursor-pointer ${
            isDragOver
              ? "border-primary-container bg-surface-container-high glow-cyan"
              : "border-outline-variant bg-surface-container-low hover:border-primary-container hover:bg-surface-container-high"
          }`}
        >
          <span className="material-symbols-outlined text-4xl text-primary-container mb-4">
            cloud_upload
          </span>
          <p className="font-headline-md text-headline-md text-on-surface mb-2 text-center">
            拖放完整 Gerber ZIP 制造文件包到这里 或 点击选择
          </p>
          <p className="font-data-mono text-data-mono text-outline">
            仅支持 .ZIP（ZIP 内可包含 Gerber / Drill 制造文件）
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={handleInputChange}
          />
        </div>
      ) : (
        /* File Uploaded Summary Card */
        <div className="bg-surface-container-low border border-primary-container/60 p-6 rounded relative">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-primary-container/10 border border-primary-container/40 flex items-center justify-center text-primary-container">
                <span className="material-symbols-outlined text-2xl fill-1">folder_zip</span>
              </div>
              <div>
                <h3 className="font-headline-md text-headline-md text-on-surface font-semibold">
                  {uploadedFileMeta.name}
                </h3>
                <div className="flex items-center gap-4 mt-2 font-data-mono text-data-mono text-on-surface-variant">
                  <span>{formatFileSize(uploadedFileMeta.size)}</span>
                  <span>•</span>
                  <span className="text-primary-container font-semibold">
                    检测到 {uploadedFileMeta.fileCount} 个制造文件
                  </span>
                </div>
                <p className="text-body-sm text-[#4ade80] flex items-center gap-1 mt-2">
                  <span className="material-symbols-outlined text-[16px]">check_circle</span>
                  文件读取正常，可直接启动智能分析
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                setSourceFile(null);
                setUploadedFileMeta(null);
                setJobStatus("idle");
              }}
              className="text-on-surface-variant hover:text-error p-1 transition-colors"
              title="移除文件并重新选择"
            >
              <span className="material-symbols-outlined text-[20px]">delete</span>
            </button>
          </div>
        </div>
      )}

      {/* Action Button */}
      <div className="mt-8 flex flex-col items-center gap-3">
        <button
          onClick={handleStartGeneration}
          disabled={!uploadedFileMeta || isAnalyzing}
          className={`py-3 px-12 font-headline-md text-headline-md border transition-all duration-200 w-full sm:w-auto flex items-center justify-center gap-2 rounded ${
            uploadedFileMeta && !isAnalyzing
              ? "bg-primary-container text-on-primary-fixed border-primary-container font-bold hover:bg-surface-tint glow-cyan cursor-pointer"
              : "bg-surface-bright text-on-surface-variant opacity-50 cursor-not-allowed border-outline-variant"
          }`}
        >
          {isAnalyzing ? (
            <>
              <span className="material-symbols-outlined animate-spin text-[20px]">progress_activity</span>
              正在分析文件目录...
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[20px]">bolt</span>
              开始智能生成
            </>
          )}
        </button>

        {!uploadedFileMeta && (
          <div className="flex flex-col items-center gap-1.5 pt-1">
            <span className="text-[11px] text-outline font-data-mono">或者直接体验：</span>
            <button
              type="button"
              onClick={loadNormalDemo}
              className="px-6 py-2 bg-surface-container-high border border-primary-container/70 hover:border-primary-container text-primary-container font-headline-md text-xs font-semibold rounded hover:bg-surface-tint/15 transition-all flex items-center gap-2 shadow-sm"
            >
              <span className="material-symbols-outlined text-[16px] text-amber-300">auto_awesome</span>
              一键载入工业级治具演示案例 (180×120mm 双面混装主板)
            </button>
          </div>
        )}
      </div>

      {/* Flow Indicator Steps */}
      <div className="mt-10 pt-6 border-t border-outline-variant">
        <div className="flex justify-between items-center relative">
          <div className="absolute top-1/2 left-0 w-full h-px bg-outline-variant -z-10 -translate-y-1/2"></div>

          <div className="flex flex-col items-center bg-surface-container px-2">
            <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center mb-1.5 z-10 border-2 border-surface-container glow-cyan">
              <span className="material-symbols-outlined text-sm fill-1">upload_file</span>
            </div>
            <span className="font-label-caps text-label-caps text-primary-container">UPLOAD</span>
          </div>

          <div className="flex flex-col items-center bg-surface-container px-2">
            <div className="w-8 h-8 rounded-full bg-surface-bright text-on-surface-variant flex items-center justify-center mb-1.5 z-10 border border-outline-variant">
              <span className="material-symbols-outlined text-sm">memory</span>
            </div>
            <span className="font-label-caps text-label-caps text-on-surface-variant">IDENTIFY PCB</span>
          </div>

          <div className="flex flex-col items-center bg-surface-container px-2">
            <div className="w-8 h-8 rounded-full bg-surface-bright text-on-surface-variant flex items-center justify-center mb-1.5 z-10 border border-outline-variant">
              <span className="material-symbols-outlined text-sm">precision_manufacturing</span>
            </div>
            <span className="font-label-caps text-label-caps text-on-surface-variant">GENERATE FIXTURE</span>
          </div>

          <div className="flex flex-col items-center bg-surface-container px-2">
            <div className="w-8 h-8 rounded-full bg-surface-bright text-on-surface-variant flex items-center justify-center mb-1.5 z-10 border border-outline-variant">
              <span className="material-symbols-outlined text-sm">download</span>
            </div>
            <span className="font-label-caps text-label-caps text-on-surface-variant">DOWNLOAD DXF</span>
          </div>
        </div>
      </div>
    </div>
  );
};
