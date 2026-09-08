"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useRef, useEffect, useState } from "react";
import { ESCALATION_DISPLAY_MS, SURRENDER_THRESHOLD_PERCENT } from "@/lib/constants";
import type { StatusMessage } from "@/lib/types";

const MissionStatus = memo(function MissionStatus({
  onReport,
}: {
  onReport: (r: string) => void;
}) {
  const [surrendered, setSurrendered] = useState(false);
  const [escalated, setEscalated]     = useState(false);
  const [stress, setStress]           = useState(85);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data: StatusMessage = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "surrender") {
        setSurrendered(true);
      } else if (data.type === "escalate") {
        setEscalated(true);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => setEscalated(false), ESCALATION_DISPLAY_MS);
      } else if (data.type === "stress" && data.level !== undefined) {
        setStress(data.level);
      } else if (data.type === "report" && data.content) {
        onReport(data.content);
      }
    } catch (e) {
      console.error("Status parse error:", e);
    }
  }, [onReport]);

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  useDataChannel(handleData);

  const stressColor =
    stress > 80 ? "#c0392b" :
    stress > 50 ? "#c8893e" :
    stress > 20 ? "#c8893e" :
    "#27ae60";

  return (
    <>
      {/* ── Stress gauge ── */}
      <div
        className="flex flex-col items-center px-3 py-4 gap-1 w-14"
        role="meter"
        aria-label={`Subject stress: ${stress}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={stress}
      >
        <span className="font-mono text-[7px] tracking-[0.15em] text-white/20 uppercase">Stress</span>

        {/* Bar track */}
        <div className="flex-1 w-4 bg-white/4 border border-white/8 relative overflow-hidden min-h-[80px]">
          {/* Fill */}
          <div
            className="absolute bottom-0 left-0 right-0 transition-[height] duration-500"
            style={{ height: `${stress}%`, backgroundColor: stressColor, opacity: 0.85 }}
          />
          {/* Win threshold line */}
          <div
            className="absolute left-0 right-0 h-px"
            style={{ bottom: `${SURRENDER_THRESHOLD_PERCENT}%`, backgroundColor: "#27ae60", opacity: 0.4 }}
          />
          {/* Grid ticks */}
          {[25, 50, 75].map((pct) => (
            <div key={pct} className="absolute left-0 right-0 h-px bg-white/6" style={{ bottom: `${pct}%` }} />
          ))}
        </div>

        <span
          className="font-mono text-[9px] font-bold tabular-nums"
          style={{ color: stressColor }}
        >
          {stress}%
        </span>
        <span className="font-mono text-[6px] text-[#27ae60]/40 leading-tight text-center tracking-tight uppercase">
          Win<br />&lt;30
        </span>
      </div>

      {/* ── Surrender overlay ── */}
      {surrendered && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#0d0d0d]/95 p-8"
          role="alert"
          aria-label="Mission accomplished"
        >
          <div className="text-center">
            <div className="font-mono text-[9px] tracking-[0.3em] text-[#27ae60]/50 uppercase mb-4">
              Outcome: Success
            </div>
            <h2 className="font-serif text-5xl md:text-6xl font-black text-white/90 uppercase tracking-tight leading-none mb-6">
              Subject<br />Surrendered
            </h2>
            <div
              className="inline-block font-mono text-sm tracking-[0.3em] text-[#27ae60] border border-[#27ae60]/40 px-4 py-1"
              style={{ transform: "rotate(-1deg)" }}
            >
              NEGOTIATION SUCCESSFUL
            </div>
          </div>
          <p className="font-mono text-[9px] text-white/20 tracking-wider uppercase mt-8 animate-pulse">
            Generating debrief report...
          </p>
        </div>
      )}

      {/* ── Escalation overlay ── */}
      {escalated && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#c0392b]/15 p-8 border border-[#c0392b]/30"
          role="alert"
          aria-label="Mission failed"
        >
          <div className="text-center">
            <div className="font-mono text-[9px] tracking-[0.3em] text-[#c0392b]/60 uppercase mb-4">
              Outcome: Failure
            </div>
            <h2 className="font-serif text-5xl md:text-6xl font-black text-white/90 uppercase tracking-tight leading-none mb-6">
              Subject<br />Escalated
            </h2>
            <div
              className="inline-block font-mono text-sm tracking-[0.3em] text-[#c0392b] border border-[#c0392b]/50 px-4 py-1"
              style={{ transform: "rotate(1deg)" }}
            >
              NEGOTIATION FAILED
            </div>
          </div>
          <p className="font-mono text-[9px] text-white/20 tracking-wider uppercase mt-8 animate-pulse">
            Generating debrief report...
          </p>
        </div>
      )}
    </>
  );
});

export default MissionStatus;
