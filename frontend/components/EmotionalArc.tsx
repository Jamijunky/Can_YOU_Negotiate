"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";

interface StressPoint { level: number; timestamp: number; }

const MAX_POINTS = 40;
const WIN_THRESHOLD = 30;
const ESCALATE_THRESHOLD = 75;

function lineColor(level: number): string {
  if (level <= WIN_THRESHOLD) return "#22c55e";
  if (level <= 50) return "#d99a4e";
  if (level <= ESCALATE_THRESHOLD) return "#f97316";
  return "#dc2626";
}

function getTrend(pts: StressPoint[]): string {
  if (pts.length < 3) return "";
  const recent  = pts.slice(-3).reduce((s, p) => s + p.level, 0) / 3;
  const prev    = pts.slice(-6, -3);
  if (!prev.length) return "";
  const prevAvg = prev.reduce((s, p) => s + p.level, 0) / prev.length;
  if (recent - prevAvg > 5)  return "RISING";
  if (prevAvg - recent > 5)  return "FALLING";
  return "STABLE";
}

const EmotionalArc = memo(function EmotionalArc() {
  const [history, setHistory] = useState<StressPoint[]>([]);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "stress" && typeof data.level === "number") {
        setHistory((prev) => {
          const next = [...prev, { level: data.level, timestamp: Date.now() }];
          return next.length > MAX_POINTS ? next.slice(-MAX_POINTS) : next;
        });
      }
    } catch { /* ignore */ }
  }, []);

  useDataChannel(handleData);

  const current = history.length > 0 ? history[history.length - 1].level : null;
  const trend = getTrend(history);

  const W = 220, H = 48, PAD = 4;
  const pts = history.map((p, i) => {
    const x = history.length === 1 ? W / 2 : PAD + (i / (history.length - 1)) * (W - PAD * 2);
    const y = H - PAD - (p.level / 100) * (H - PAD * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const pathD = pts.length > 1 ? `M ${pts.join(" L ")}` : "";
  const last  = pts.length > 0 ? pts[pts.length - 1].split(",") : null;
  const color = current !== null ? lineColor(current) : "#d99a4e";

  return (
    <div className="p-3 border-b border-[#f4f0e6]/8" role="region" aria-label="Stress arc">
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#d99a4e] uppercase mb-1.5 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
          EMOTIONAL_ARC
        </span>
        {current !== null && (
          <span className="flex items-center gap-1.5">
            {trend === "RISING"  && <span className="text-[#dc2626] text-[10px]">▲</span>}
            {trend === "FALLING" && <span className="text-[#22c55e] text-[10px]">▼</span>}
            {trend === "STABLE"  && <span className="text-[#d99a4e] text-[10px]">—</span>}
            <span className="font-mono font-black text-xs tabular-nums" style={{ color }}>{current}%</span>
          </span>
        )}
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 48 }}
        preserveAspectRatio="none" role="img"
        aria-label={`Stress: ${current ?? "unknown"}%. Trend: ${trend || "collecting"}`}>
        <line x1={0} y1={H - PAD - (WIN_THRESHOLD / 100) * (H - PAD * 2)}
              x2={W} y2={H - PAD - (WIN_THRESHOLD / 100) * (H - PAD * 2)}
              stroke="#22c55e" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />
        <line x1={0} y1={H - PAD - (ESCALATE_THRESHOLD / 100) * (H - PAD * 2)}
              x2={W} y2={H - PAD - (ESCALATE_THRESHOLD / 100) * (H - PAD * 2)}
              stroke="#dc2626" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.3" />
        {pathD && (
          <path d={pathD} fill="none" stroke={color} strokeWidth="1.5"
                strokeLinejoin="round" strokeLinecap="round" />
        )}
        {last && (
          <circle cx={last[0]} cy={last[1]} r="2.5" fill={color} stroke="#141414" strokeWidth="1" />
        )}
        {history.length === 0 && (
          <text x={W / 2} y={H / 2 + 3} textAnchor="middle"
                fill="rgba(244,240,230,0.2)" fontSize="7" fontFamily="monospace">
            [collecting data...]
          </text>
        )}
      </svg>

      <div className="flex items-center justify-between mt-1 font-mono text-[8px] text-[#f4f0e6]/20">
        <span>&lt;30% surrender</span>
        <span>&gt;75% escalate</span>
      </div>
    </div>
  );
});

export default EmotionalArc;
