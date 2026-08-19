import React, { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import { DEFAULT_PARAMETERS } from "../../types/fixture";

export const ParameterDrawer: React.FC = () => {
  const {
    isParameterDrawerOpen,
    toggleParameterDrawer,
    parameters,
    fixtureResult,
    updateParameters,
    regenerate,
    resetParameters,
    showToast
  } = useProjectStore();

  const [formParams, setFormParams] = useState(parameters);

  // 同步外部变化
  React.useEffect(() => {
    setFormParams(parameters);
  }, [parameters]);

  if (!isParameterDrawerOpen) return null;

  const handleApplyAndRegenerate = async () => {
    updateParameters(formParams);
    toggleParameterDrawer(false);
    try {
      await regenerate();
      showToast("已应用参数，后端正在重新生成真实治具...", "info");
    } catch {
      // regenerate 已显示具体错误
    }
  };

  const handleReset = () => {
    resetParameters();
    setFormParams({ ...DEFAULT_PARAMETERS });
  };

  return (
    <div className="fixed inset-y-0 right-0 top-toolbar-height bottom-8 w-[360px] bg-surface-container border-l border-outline-variant z-40 shadow-2xl flex flex-col backdrop-blur-md animate-slide-in">
      {/* Header */}
      <div className="p-panel-padding border-b border-outline-variant bg-surface-container-low flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary-container text-[20px]">tune</span>
          <h2 className="font-headline-md text-headline-md text-on-surface font-semibold">
            工程参数 (PARAMETERS)
          </h2>
        </div>
        <button
          onClick={() => toggleParameterDrawer(false)}
          className="text-on-surface-variant hover:text-on-surface p-1 transition-colors"
        >
          <span className="material-symbols-outlined text-[18px]">close</span>
        </button>
      </div>

      {/* Form Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* 基础工艺参数 */}
        <div>
          <h3 className="font-label-caps text-label-caps text-primary-container uppercase tracking-wider mb-3">
            基础工艺间隙
          </h3>

          <div className="space-y-3 font-data-mono text-body-sm">
            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>沉板间隙 (Clearance)</span>
                <span className="text-on-surface font-bold">{(formParams.sinkClearanceMm ?? 0.2).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.05"
                min="0.1"
                max="1.0"
                value={formParams.sinkClearanceMm}
                onChange={(e) =>
                  setFormParams({ ...formParams, sinkClearanceMm: parseFloat(e.target.value) || 0.2 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>BOT 避位安全距离</span>
                <span className="text-on-surface font-bold">{(formParams.keepoutClearanceMm ?? 0.7).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.05"
                min="0.4"
                max="2.0"
                value={formParams.keepoutClearanceMm}
                onChange={(e) =>
                  setFormParams({ ...formParams, keepoutClearanceMm: parseFloat(e.target.value) || 0.7 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>TOP 上锡安全距离</span>
                <span className="text-on-surface font-bold">{(formParams.solderClearanceMm ?? 3.0).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.1"
                min="1.0"
                max="5.0"
                value={formParams.solderClearanceMm}
                onChange={(e) =>
                  setFormParams({ ...formParams, solderClearanceMm: parseFloat(e.target.value) || 3.0 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>铣刀清角半径 (Corner Radius)</span>
                <span className="text-on-surface font-bold">{(formParams.filletRadiusMm ?? 1.85).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.05"
                min="1.0"
                max="3.5"
                value={formParams.filletRadiusMm ?? 1.85}
                onChange={(e) =>
                  setFormParams({ ...formParams, filletRadiusMm: parseFloat(e.target.value) || 1.85 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>弹簧卡孔半径 (Spring Clip)</span>
                <span className="text-on-surface font-bold">{(formParams.springClipRadiusMm ?? 2.45).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.05"
                min="1.5"
                max="4.0"
                value={formParams.springClipRadiusMm ?? 2.45}
                onChange={(e) =>
                  setFormParams({ ...formParams, springClipRadiusMm: parseFloat(e.target.value) || 2.45 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>避位区内倒角 (Keepout Fillet)</span>
                <span className="text-on-surface font-bold">{(formParams.keepoutInnerFilletMm ?? 1.5).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.1"
                min="0.0"
                max="3.0"
                value={formParams.keepoutInnerFilletMm ?? 1.5}
                onChange={(e) =>
                  setFormParams({ ...formParams, keepoutInnerFilletMm: parseFloat(e.target.value) || 1.5 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>焊圆外径最小值 (Solder Min Dia)</span>
                <span className="text-on-surface font-bold">{(formParams.solderMinOuterDiameterMm ?? 3.0).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.1"
                min="1.5"
                max="6.0"
                value={formParams.solderMinOuterDiameterMm ?? 3.0}
                onChange={(e) =>
                  setFormParams({ ...formParams, solderMinOuterDiameterMm: parseFloat(e.target.value) || 3.0 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>

            <div>
              <div className="flex justify-between text-on-surface-variant mb-1">
                <span>最小材料壁厚 (Min Material Web)</span>
                <span className="text-on-surface font-bold">{(formParams.minimumMaterialWebMm ?? 2.0).toFixed(2)} mm</span>
              </div>
              <input
                type="number"
                step="0.1"
                min="1.0"
                max="5.0"
                value={formParams.minimumMaterialWebMm ?? 2.0}
                onChange={(e) =>
                  setFormParams({ ...formParams, minimumMaterialWebMm: parseFloat(e.target.value) || 2.0 })
                }
                className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* 治具外形与夹持 */}
        <div>
          <h3 className="font-label-caps text-label-caps text-primary-container uppercase tracking-wider mb-3">
            治具外形与边距
          </h3>

          <div className="space-y-3 font-data-mono text-body-sm">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>X边距</span>
                  <span className="text-on-surface font-bold">{(formParams.fixtureMarginXmm ?? 20.0).toFixed(1)}mm</span>
                </div>
                <input
                  type="number"
                  step="1.0"
                  min="10.0"
                  max="60.0"
                  value={formParams.fixtureMarginXmm ?? 20.0}
                  onChange={(e) =>
                    setFormParams({ ...formParams, fixtureMarginXmm: parseFloat(e.target.value) || 20.0 })
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                />
              </div>
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>Y边距</span>
                  <span className="text-on-surface font-bold">{(formParams.fixtureMarginYmm ?? 30.0).toFixed(1)}mm</span>
                </div>
                <input
                  type="number"
                  step="1.0"
                  min="15.0"
                  max="80.0"
                  value={formParams.fixtureMarginYmm ?? 30.0}
                  onChange={(e) =>
                    setFormParams({ ...formParams, fixtureMarginYmm: parseFloat(e.target.value) || 30.0 })
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>外框圆角</span>
                  <span className="text-on-surface font-bold">{(formParams.fixtureCornerRadiusMm ?? 5.0).toFixed(1)}mm</span>
                </div>
                <input
                  type="number"
                  step="0.5"
                  min="0.0"
                  max="15.0"
                  value={formParams.fixtureCornerRadiusMm ?? 5.0}
                  onChange={(e) =>
                    setFormParams({ ...formParams, fixtureCornerRadiusMm: parseFloat(e.target.value) || 5.0 })
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                />
              </div>
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>尺寸取整步进</span>
                  <span className="text-on-surface font-bold">{(formParams.fixtureSizeRoundStepMm ?? 5.0).toFixed(1)}mm</span>
                </div>
                <input
                  type="number"
                  step="1.0"
                  min="1.0"
                  max="20.0"
                  value={formParams.fixtureSizeRoundStepMm ?? 5.0}
                  onChange={(e) =>
                    setFormParams({ ...formParams, fixtureSizeRoundStepMm: parseFloat(e.target.value) || 5.0 })
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                />
              </div>
            </div>

            <div>
              <span className="text-on-surface-variant block mb-1">当前治具尺寸（后端计算）</span>
              <input
                type="text"
                value={(fixtureResult.fixture?.width ?? 0) > 0 ? `${(fixtureResult.fixture?.width ?? 0).toFixed(2)} × ${(fixtureResult.fixture?.height ?? 0).toFixed(2)} mm` : "等待后端计算"}
                disabled
                className="w-full bg-surface-container-low border border-outline-variant/60 text-on-surface-variant p-2 text-xs cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* 辅件规格与安装位 */}
        <div>
          <h3 className="font-label-caps text-label-caps text-primary-container uppercase tracking-wider mb-3">
            辅件与安装位
          </h3>

          <div className="space-y-3 font-data-mono text-body-sm">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>压扣孔径</span>
                  <span className="text-on-surface font-bold">{(formParams.clampHoleDiameterMm ?? 3.4).toFixed(1)}mm</span>
                </div>
                <input
                  type="number"
                  step="0.1"
                  min="2.0"
                  max="6.0"
                  value={formParams.clampHoleDiameterMm ?? 3.4}
                  onChange={(e) =>
                    setFormParams({ ...formParams, clampHoleDiameterMm: parseFloat(e.target.value) || 3.4 })
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                />
              </div>
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>压扣偏移</span>
                  <span className="text-on-surface font-bold">{(formParams.clampOffsetMm ?? 10.0).toFixed(1)}mm</span>
                </div>
                <input
                  type="number"
                  step="0.5"
                  min="5.0"
                  max="25.0"
                  value={formParams.clampOffsetMm ?? 10.0}
                  onChange={(e) =>
                    setFormParams({ ...formParams, clampOffsetMm: parseFloat(e.target.value) || 10.0 })
                  }
                  className="w-full bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>取手位宽×高</span>
                  <span className="text-on-surface font-bold">{(formParams.handholdWidthMm ?? 20.0).toFixed(0)}×{(formParams.handholdHeightMm ?? 40.0).toFixed(0)}</span>
                </div>
                <div className="flex gap-1">
                  <input
                    type="number"
                    step="1.0"
                    min="10.0"
                    max="40.0"
                    value={formParams.handholdWidthMm ?? 20.0}
                    onChange={(e) =>
                      setFormParams({ ...formParams, handholdWidthMm: parseFloat(e.target.value) || 20.0 })
                    }
                    className="w-1/2 bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                  />
                  <input
                    type="number"
                    step="1.0"
                    min="20.0"
                    max="80.0"
                    value={formParams.handholdHeightMm ?? 40.0}
                    onChange={(e) =>
                      setFormParams({ ...formParams, handholdHeightMm: parseFloat(e.target.value) || 40.0 })
                    }
                    className="w-1/2 bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-on-surface-variant mb-1">
                  <span>轨道 / 挡锡条宽</span>
                  <span className="text-on-surface font-bold">{(formParams.railWidthMm ?? 5.0).toFixed(0)}/{(formParams.solderBarrierWidthMm ?? 10.0).toFixed(0)}</span>
                </div>
                <div className="flex gap-1">
                  <input
                    type="number"
                    step="0.5"
                    min="2.0"
                    max="15.0"
                    value={formParams.railWidthMm ?? 5.0}
                    onChange={(e) =>
                      setFormParams({ ...formParams, railWidthMm: parseFloat(e.target.value) || 5.0 })
                    }
                    className="w-1/2 bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                  />
                  <input
                    type="number"
                    step="0.5"
                    min="4.0"
                    max="25.0"
                    value={formParams.solderBarrierWidthMm ?? 10.0}
                    onChange={(e) =>
                      setFormParams({ ...formParams, solderBarrierWidthMm: parseFloat(e.target.value) || 10.0 })
                    }
                    className="w-1/2 bg-surface border border-outline-variant text-on-surface p-2 text-xs focus:border-primary-container focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-panel-padding border-t border-outline-variant bg-surface-container-high flex flex-col gap-2">
        <button
          onClick={handleApplyAndRegenerate}
          className="w-full py-2.5 bg-primary-container text-on-primary-fixed font-headline-md font-bold hover:bg-surface-tint glow-cyan transition-colors flex items-center justify-center gap-1.5"
        >
          <span className="material-symbols-outlined text-[18px]">sync</span>
          应用并重新生成
        </button>

        <button
          onClick={handleReset}
          className="w-full py-1.5 bg-transparent border border-outline-variant text-on-surface font-body-sm hover:bg-surface-container-highest transition-colors"
        >
          恢复自动参数
        </button>
      </div>
    </div>
  );
};
