"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useRef } from "react";

interface StressPoint {
  level: number;
  timestamp: number;
}

const MAX_POINTS = 40;
const SURRENDER_THRESHOLD = 30;
const ESCALATION_THRESHOLD = 75;

function getLineColor(level: number): string {
  if (level <= SURRENDER_THRESHOLD) return "#22c55e";
  if (level <= 50) return "#d99a4e";
  if (level <= ESCALATION_THRESHOLD) return "#f97316";
  return "#dc2626";
}

function getTrend(points: StressPoint[]): string {
  if (points.length < 3) return "";
  const recent = points.slice(-3);
  const avg = recent.reduce((s, p) => s + p.level, 0) / recent.length;
  const prev = points.slice(-6, -3);
  if (prev.length === 0) return "";
  const prevAvg = prev.reduce((s, p) => s + p.level, 0) / prev.length;
  const diff = avg - prevAvg;
  if (diff > 5) return "RISING";
  if (diff < -5) return "FALLING";
  return "STABLE";
}

const EmotionalArc = memo(function EmotionalArc() {
  const [history, setHistory] = useState<StressPoint[]>([]);
  const svgRef = useRef<SVGSVGElement>(null);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "stress" && typeof data.level === "number") {
        setHistory((prev) => {
          const next = [...prev, { level: data.level, timestamp: Date.now() }];
          return next.length > MAX_POINTS ? next.slice(-MAX_POINTS) : next;
        });
      }
    } catch (e) {
      // ignore
    }
  }, []);

  useDataChannel(handleData);

  const current = history.length > 0 ? history[history.length - 1].level : null;
  const trend = getTrend(history);

  // Build SVG path
  const W = 280;
  const H = 60;
  const PAD = 4;
  const points = history.map((p, i) => {
    const x = history.length === 1 ? W / 2 : PAD + (i / (history.length - 1)) * (W - PAD * 2);
    const y = H - PAD - (p.level / 100) * (H - PAD * 2);
    return `${x},${y}`;
  });
  const pathD = points.length > 1 ? `M ${points.join(" L ")}` : "";
  const lastPoint = points.length > 0 ? points[points.length - 1].split(",") : null;
  const lineColor = current !== null ? getLineColor(current) : "#d99a4e";

  return (
    <div className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 p-3 text-left" role="region" aria-label="Emotional arc">
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
          EMOTIONAL_ARC
        </span>
        {current !== null && (
          <span className="flex items-center gap-2">
            {trend === "RISING" && <span className="text-[#dc2626]">&#9650;</span>}
            {trend === "FALLING" && <span className="text-[#22c55e]">&#9660;</span>}
            {trend === "STABLE" && <span className="text-[#d99a4e]">&#9644;</span>}
            <span style={{ color: lineColor }} className="font-black text-xs">
              {current}%
            </span>
          </span>
        )}
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-12"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Stress level: ${current ?? "N/A"}%. Trend: ${trend || "collecting data"}`}
      >
        {/* Threshold lines */}
        <line x1={0} y1={H - PAD - (SURRENDER_THRESHOLD / 100) * (H - PAD * 2)} x2={W} y2={H - PAD - (SURRENDER_THRESHOLD / 100) * (H - PAD * 2)} stroke="#22c55e" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />
        <line x1={0} y1={H - PAD - (ESCALATION_THRESHOLD / 100) * (H - PAD * 2)} x2={W} y2={H - PAD - (ESCALATION_THRESHOLD / 100) * (H - PAD * 2)} stroke="#dc2626" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />

        {/* Stress line */}
        {pathD && (
          <path
            d={pathD}
            fill="none"
            stroke={lineColor}
            strokeWidth="1.5"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}

        {/* Current point */}
        {lastPoint && (
          <circle
            cx={lastPoint[0]}
            cy={lastPoint[1]}
            r="2.5"
            fill={lineColor}
            stroke="#1e1e1e"
            strokeWidth="1"
          />
        )}

        {/* Empty state */}
        {history.length === 0 && (
          <text x={W / 2} y={H / 2} textAnchor="middle" fill="#f4f0e6" fontSize="8" opacity="0.3" fontFamily="monospace">
            [collecting data...]
          </text>
        )}
      </svg>

      {/* Legend */}
      <div className="flex items-center justify-between mt-1 font-mono text-[8px] text-[#f4f0e6]/30">
        <span className="flex items-center gap-1">
          <span className="w-2 h-px bg-[#22c55e]" /> &lt;30% SURRENDER
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-px bg-[#dc2626]" /> &gt;75% ESCALATE
        </span>
      </div>
    </div>
  );
});

export default EmotionalArc;
