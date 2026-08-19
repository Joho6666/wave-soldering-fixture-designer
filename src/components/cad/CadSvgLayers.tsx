import React from "react";
import { useProjectStore } from "../../store/useProjectStore";

export const CadSvgLayers: React.FC = () => {
  const { visibleLayers, highlightTarget, parameters } = useProjectStore();

  const isDrcHighlighted = highlightTarget?.objectId === "drc-area-03";

  // 根据当前工程参数动态调整沉板与间隙
  const sinkClearance = parameters.sinkClearanceMm; // development demo only
  const cornerRadius = parameters.filletRadiusMm; // development demo only

  return (
    <g id="cad-drawing-root" transform="translate(0, 0)">
      {/* 1. FIXTURE OUTLINE LAYER (治具外框 & 轨道) */}
      {visibleLayers["fixture-outline"] && (
        <g id="layer-fixture-outline">
          {/* 治具外框底板 */}
          <rect
            x="40"
            y="30"
            width="520"
            height="390"
            rx={cornerRadius * 6}
            fill="#101a24"
            fillOpacity="0.85"
            stroke="#1e90ff"
            strokeWidth="2"
          />

          {/* 传送带左右轨道卡槽 */}
          <rect x="40" y="30" width="18" height="390" fill="#152433" stroke="#1e90ff" strokeWidth="1" strokeDasharray="4,2" />
          <rect x="542" y="30" width="18" height="390" fill="#152433" stroke="#1e90ff" strokeWidth="1" strokeDasharray="4,2" />

          {/* 4角提手/把手位 */}
          <rect x="75" y="35" width="40" height="10" rx="3" fill="#0d1516" stroke="#3b494c" strokeWidth="1" />
          <rect x="485" y="35" width="40" height="10" rx="3" fill="#0d1516" stroke="#3b494c" strokeWidth="1" />
          <rect x="75" y="405" width="40" height="10" rx="3" fill="#0d1516" stroke="#3b494c" strokeWidth="1" />
          <rect x="485" y="405" width="40" height="10" rx="3" fill="#0d1516" stroke="#3b494c" strokeWidth="1" />
        </g>
      )}

      {/* 2. SINK REGION LAYER (沉板区台阶) */}
      {visibleLayers["sink-region"] && (
        <g id="layer-sink-region">
          {/* 四周沉板承托面 */}
          <rect
            x={100 - sinkClearance * 10}
            y={70 - sinkClearance * 10}
            width={400 + sinkClearance * 20}
            height={310 + sinkClearance * 20}
            rx="4"
            fill="#9370db"
            fillOpacity="0.18"
            stroke="#9370db"
            strokeWidth="1.5"
          />

          {/* 沉板台阶边缘加强标注 */}
          <rect x="180" y="70" width="240" height="18" fill="#9370db" fillOpacity="0.4" stroke="#9370db" strokeWidth="1" />
          <text x="300" y="83" fill="#ffffff" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle">沉板区</text>

          <rect x="180" y="362" width="240" height="18" fill="#9370db" fillOpacity="0.4" stroke="#9370db" strokeWidth="1" />
          <text x="300" y="375" fill="#ffffff" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle">沉板区</text>

          <rect x="100" y="150" width="18" height="150" fill="#9370db" fillOpacity="0.4" stroke="#9370db" strokeWidth="1" />
          <text x="109" y="225" fill="#ffffff" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle" transform="rotate(-90 109 225)">沉板区</text>

          <rect x="482" y="150" width="18" height="150" fill="#9370db" fillOpacity="0.4" stroke="#9370db" strokeWidth="1" />
          <text x="491" y="225" fill="#ffffff" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle" transform="rotate(90 491 225)">沉板区</text>
        </g>
      )}

      {/* 3. PCB OUTLINE LAYER (PCB 板框) */}
      {visibleLayers["pcb-outline"] && (
        <g id="layer-pcb-outline">
          <rect
            x="110"
            y="80"
            width="380"
            height="290"
            rx="4"
            fill="#091410"
            fillOpacity="0.7"
            stroke="#2e8b57"
            strokeWidth="2"
            strokeDasharray="6,3"
          />
        </g>
      )}

      {/* 4. PCB TRACES & GERBER SIMULATION (走线、铜皮、BGA 与过孔) */}
      {visibleLayers["pcb-copper"] && (
        <g id="layer-pcb-copper" opacity="0.85">
          {/* 中央大型 BGA 芯片封装 */}
          <rect x="250" y="185" width="100" height="80" fill="#12181a" stroke="#d49a6a" strokeWidth="1.5" />
          <rect x="260" y="195" width="80" height="60" fill="#080f11" stroke="#d49a6a" strokeWidth="0.8" />

          {/* BGA 引脚走线簇 */}
          <path d="M 250 200 L 190 150 L 190 120" stroke="#d49a6a" strokeWidth="1" fill="none" />
          <path d="M 250 215 L 205 170 L 160 170" stroke="#d49a6a" strokeWidth="1" fill="none" />
          <path d="M 250 230 L 210 230 L 170 270" stroke="#d49a6a" strokeWidth="1" fill="none" />
          <path d="M 250 245 L 220 275 L 220 310" stroke="#d49a6a" strokeWidth="1" fill="none" />

          <path d="M 350 200 L 410 150 L 410 120" stroke="#d49a6a" strokeWidth="1" fill="none" />
          <path d="M 350 215 L 395 170 L 440 170" stroke="#d49a6a" strokeWidth="1" fill="none" />
          <path d="M 350 230 L 390 230 L 430 270" stroke="#d49a6a" strokeWidth="1" fill="none" />
          <path d="M 350 245 L 380 275 L 380 310" stroke="#d49a6a" strokeWidth="1" fill="none" />

          {/* 阵列贴片电阻电容 (SMD Pads) */}
          {Array.from({ length: 12 }).map((_, i) => (
            <g key={`smd-top-${i}`}>
              <rect x={260 + i * 7} y="105" width="4" height="6" fill="#d49a6a" />
              <rect x={260 + i * 7} y="115" width="4" height="6" fill="#d49a6a" />
            </g>
          ))}

          {Array.from({ length: 8 }).map((_, i) => (
            <g key={`smd-left-${i}`}>
              <rect x="135" y={140 + i * 16} width="6" height="4" fill="#d49a6a" />
              <rect x="145" y={140 + i * 16} width="6" height="4" fill="#d49a6a" />
            </g>
          ))}
        </g>
      )}

      {/* 5. DRILL & VIAS (钻孔与通孔阵列) */}
      {visibleLayers["pcb-drill"] && (
        <g id="layer-pcb-drill">
          {/* 左侧排针通孔阵列 */}
          {Array.from({ length: 10 }).map((_, i) => (
            <g key={`drl-left-${i}`}>
              <circle cx="160" cy={135 + i * 14} r="3.5" fill="#0d1516" stroke="#48cae4" strokeWidth="1" />
              <circle cx="172" cy={135 + i * 14} r="3.5" fill="#0d1516" stroke="#48cae4" strokeWidth="1" />
            </g>
          ))}

          {/* 底部排针通孔 */}
          {Array.from({ length: 10 }).map((_, i) => (
            <g key={`drl-bot-${i}`}>
              <circle cx={250 + i * 12} cy="340" r="3.5" fill="#0d1516" stroke="#48cae4" strokeWidth="1" />
              <circle cx={250 + i * 12} cy="350" r="3.5" fill="#0d1516" stroke="#48cae4" strokeWidth="1" />
            </g>
          ))}
        </g>
      )}

      {/* 6. BOT KEEPOUT REGIONS (BOT 面贴片避位槽) */}
      {visibleLayers["keepout-bot"] && (
        <g id="layer-keepout-bot">
          {/* 顶部中央避位区 */}
          <rect x="230" y="100" width="30" height="35" fill="#32cd32" fillOpacity="0.25" stroke="#32cd32" strokeWidth="1.5" />

          {/* 左侧密集元件避位区 */}
          <rect x="130" y="210" width="40" height="60" fill="#32cd32" fillOpacity="0.25" stroke="#32cd32" strokeWidth="1.5" />
          <text x="150" y="245" fill="#32cd32" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">避位区</text>

          {/* 底部右侧避位区 (包含 DRC 违规目标) */}
          <rect x="360" y="285" width="48" height="32" fill="#32cd32" fillOpacity="0.2" stroke="#32cd32" strokeWidth="1.5" />
        </g>
      )}

      {/* 7. TOP SOLDER WINDOWS (TOP 插件上锡开窗) */}
      {visibleLayers["solder-top"] && (
        <g id="layer-solder-top">
          {/* 右侧长条排针上锡窗口 */}
          <rect x="420" y="140" width="45" height="165" rx="3" fill="#ff8c00" fillOpacity="0.3" stroke="#ff8c00" strokeWidth="1.5" />
          <text x="442" y="225" fill="#ff8c00" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle" transform="rotate(90 442 225)">上锡区</text>

          {/* 底部排针上锡窗口 */}
          <rect x="230" y="330" width="130" height="40" rx="3" fill="#ff8c00" fillOpacity="0.3" stroke="#ff8c00" strokeWidth="1.5" />
          <text x="295" y="355" fill="#ff8c00" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle">上锡区</text>
        </g>
      )}

      {/* 8. SOLDER BARRIERS (挡锡条) */}
      {visibleLayers["solder-barriers"] && (
        <g id="layer-solder-barriers">
          <rect x="412" y="140" width="4" height="165" fill="#fec931" stroke="#ffeac0" strokeWidth="0.8" />
          <rect x="230" y="324" width="130" height="4" fill="#fec931" stroke="#ffeac0" strokeWidth="0.8" />
        </g>
      )}

      {/* 9. LOCATING PINS & CLAMPS (定位销与压扣) */}
      {visibleLayers["locating-pins"] && (
        <g id="layer-locating-pins">
          {/* 4 个角定位销 */}
          {[
            { cx: 70, cy: 55 },
            { cx: 530, cy: 55 },
            { cx: 70, cy: 395 },
            { cx: 530, cy: 395 }
          ].map((pin, i) => (
            <g key={`pin-${i}`}>
              <circle cx={pin.cx} cy={pin.cy} r="10" fill="#00e5ff" fillOpacity="0.25" stroke="#00e5ff" strokeWidth="1.5" />
              <circle cx={pin.cx} cy={pin.cy} r="4" fill="#00e5ff" />
            </g>
          ))}

          {/* PCB 定位销孔 (PCB 内部 2 处) */}
          <circle cx="125" cy="95" r="5" fill="#00ffff" fillOpacity="0.4" stroke="#00ffff" strokeWidth="1.2" />
          <circle cx="475" cy="355" r="5" fill="#00ffff" fillOpacity="0.4" stroke="#00ffff" strokeWidth="1.2" />
        </g>
      )}

      {visibleLayers["clamps"] && (
        <g id="layer-clamps">
          {/* 4 个旋转压扣 */}
          <rect x="90" y="70" width="30" height="8" rx="2" fill="#a9a9a9" stroke="#ffffff" strokeWidth="1" />
          <rect x="480" y="70" width="30" height="8" rx="2" fill="#a9a9a9" stroke="#ffffff" strokeWidth="1" />
          <rect x="90" y="372" width="30" height="8" rx="2" fill="#a9a9a9" stroke="#ffffff" strokeWidth="1" />
          <rect x="480" y="372" width="30" height="8" rx="2" fill="#a9a9a9" stroke="#ffffff" strokeWidth="1" />
        </g>
      )}

      {/* 10. DRC WARNING OVERLAY (DRC 间距不足高亮与警示区) */}
      {visibleLayers["drc-overlay"] && (
        <g id="layer-drc-overlay">
          {/* 区域 #03 违规开窗与避位区临界高亮 */}
          <g transform="translate(345, 305)">
            {/* 斑马斜线填充定义 */}
            <defs>
              <pattern id="drc-stripe" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                <line x1="0" y1="0" x2="0" y2="8" stroke="#ff7b00" strokeWidth="3" opacity="0.6" />
              </pattern>
            </defs>

            {/* 间距干涉多边形 */}
            <polygon
              points="0,0 55,0 55,45 25,45 25,55 0,55"
              fill="url(#drc-stripe)"
              stroke="#ff7b00"
              strokeWidth={isDrcHighlighted ? "3" : "1.5"}
              className={isDrcHighlighted ? "animate-pulse" : ""}
            />

            {/* 间距标注线 */}
            <line x1="15" y1="10" x2="35" y2="10" stroke="#ff7b00" strokeWidth="1.2" />
            <line x1="15" y1="6" x2="15" y2="14" stroke="#ff7b00" strokeWidth="1.2" />
            <line x1="35" y1="6" x2="35" y2="14" stroke="#ff7b00" strokeWidth="1.2" />

            {/* 报警徽标 */}
            <rect x="10" y="16" width="38" height="16" rx="2" fill="#101317" stroke="#ff7b00" strokeWidth="1" />
            <text x="29" y="28" fill="#ff7b00" fontSize="8" fontFamily="JetBrains Mono" fontWeight="bold" textAnchor="middle">
              0.62mm
            </text>

            {/* 警示文本 */}
            <text x="29" y="42" fill="#ffeac0" fontSize="7" fontFamily="JetBrains Mono" textAnchor="middle">
              DRC VIOLATION
            </text>
          </g>
        </g>
      )}

      {/* 11. DIMENSIONS & ANNOTATIONS (尺寸标注层) */}
      {visibleLayers["dimensions"] && (
        <g id="layer-dimensions" opacity="0.75" pointerEvents="none">
          {/* 治具外形顶部尺寸 320.00 mm */}
          <line x1="40" y1="18" x2="560" y2="18" stroke="#849396" strokeWidth="1" />
          <line x1="40" y1="12" x2="40" y2="24" stroke="#849396" strokeWidth="1" />
          <line x1="560" y1="12" x2="560" y2="24" stroke="#849396" strokeWidth="1" />
          <rect x="270" y="10" width="60" height="15" fill="#0d1516" />
          <text x="300" y="21" fill="#849396" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle">320.00 mm</text>

          {/* 治具外形右侧尺寸 210.00 mm */}
          <line x1="575" y1="30" x2="575" y2="420" stroke="#849396" strokeWidth="1" />
          <line x1="569" y1="30" x2="581" y2="30" stroke="#849396" strokeWidth="1" />
          <line x1="569" y1="420" x2="581" y2="420" stroke="#849396" strokeWidth="1" />
          <rect x="568" y="215" width="15" height="40" fill="#0d1516" />
          <text x="576" y="238" fill="#849396" fontSize="9" fontFamily="JetBrains Mono" textAnchor="middle" transform="rotate(90 576 238)">210.00 mm</text>
        </g>
      )}
    </g>
  );
};
