"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";

interface StressPoint { level: number; timestamp: number; }

const MAX_POINTS = 40;
const WIN_THRESHOLD = 30;
const ESCALATE_THRESHOLD = 75;

function lineColor(level: number): string {
  if (level <= WIN_THRESHOLD) return "#27ae60";
  if (level <= 50) return "#c8893e";
  if (level <= ESCALATE_THRESHOLD) return "#c8893e";
  return "#c0392b";
}

function trend(pts: StressPoint[]): "↑" | "↓" | "—" | "" {
  if (pts.length < 3) return "";
  const recent = pts.slice(-3).reduce((s, p) => s + p.level, 0) / 3;
  const prev   = pts.slice(-6, -3);
  if (!prev.length) return "";
  const prevAvg = prev.reduce((s, p) => s + p.level, 0) / prev.length;
  if (recent - prevAvg > 5)  return "↑";
  if (prevAvg - recent > 5)  return "↓";
  return "—";
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
  const t = trend(history);

  const W = 220, H = 44, PAD = 3;
  const pts = history.map((p, i) => {
    const x = history.length === 1 ? W / 2 : PAD + (i / (history.length - 1)) * (W - PAD * 2);
    const y = H - PAD - (p.level / 100) * (H - PAD * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const pathD = pts.length > 1 ? `M ${pts.join(" L ")}` : "";
  const last = pts.length > 0 ? pts[pts.length - 1].split(",") : null;
  const color = current !== null ? lineColor(current) : "#c8893e";

  return (
    <div className="border-b border-white/8 p-4" role="region" aria-label="Stress arc">
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase">Stress Arc</div>
        {current !== null && (
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[9px]" style={{ color, opacity: 0.7 }}>{t}</span>
            <span className="font-mono text-[10px] font-bold tabular-nums" style={{ color }}>{current}%</span>
          </div>
        )}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height: 44 }}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Stress: ${current ?? "unknown"}%. Trend: ${t || "unknown"}`}
      >
        {/* Threshold bands */}
        <line x1={0} y1={H - PAD - (WIN_THRESHOLD / 100) * (H - PAD * 2)}
              x2={W} y2={H - PAD - (WIN_THRESHOLD / 100) * (H - PAD * 2)}
              stroke="#27ae60" strokeWidth="0.5" strokeDasharray="2,3" opacity="0.25" />
        <line x1={0} y1={H - PAD - (ESCALATE_THRESHOLD / 100) * (H - PAD * 2)}
              x2={W} y2={H - PAD - (ESCALATE_THRESHOLD / 100) * (H - PAD * 2)}
              stroke="#c0392b" strokeWidth="0.5" strokeDasharray="2,3" opacity="0.25" />

        {pathD && (
          <path d={pathD} fill="none" stroke={color} strokeWidth="1.2"
                strokeLinejoin="round" strokeLinecap="round" opacity="0.8" />
        )}

        {last && (
          <circle cx={last[0]} cy={last[1]} r="2" fill={color} stroke="#0d0d0d" strokeWidth="1" />
        )}

        {history.length === 0 && (
          <text x={W / 2} y={H / 2 + 3} textAnchor="middle"
                fill="rgba(255,255,255,0.1)" fontSize="7" fontFamily="monospace">
            collecting...
          </text>
        )}
      </svg>

      <div className="flex justify-between mt-1">
        <span className="font-mono text-[8px] text-white/15">&lt;{WIN_THRESHOLD}% win</span>
        <span className="font-mono text-[8px] text-white/15">&gt;{ESCALATE_THRESHOLD}% escalate</span>
      </div>
    </div>
  );
});

export default EmotionalArc;
