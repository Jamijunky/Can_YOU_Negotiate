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
    stress > 80 ? "#dc2626" :
    stress > 50 ? "#f97316" :
    stress > 20 ? "#d99a4e" :
    "#22c55e";

  return (
    <>
      {/* ── Stress gauge sidebar ── */}
      <div
        className="flex flex-col items-center px-2 py-3 w-10 shrink-0"
        role="meter"
        aria-label={`Subject stress: ${stress}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={stress}
      >
        <span className="font-mono text-[7px] tracking-widest text-[#f4f0e6]/25 uppercase mb-1.5 [writing-mode:vertical-rl] rotate-180">
          STRESS
        </span>
        <div className="flex-1 w-3 bg-[#f4f0e6]/5 border border-[#f4f0e6]/10 relative overflow-hidden min-h-[60px]">
          <div
            className="absolute bottom-0 left-0 right-0 transition-[height] duration-500 ease-out"
            style={{ height: `${stress}%`, backgroundColor: stressColor, boxShadow: `0 0 6px ${stressColor}80` }}
          />
          {/* Win threshold */}
          <div
            className="absolute left-0 right-0 h-px bg-[#22c55e]/40"
            style={{ bottom: `${SURRENDER_THRESHOLD_PERCENT}%` }}
          />
        </div>
        <span className="font-mono text-[8px] font-bold tabular-nums mt-1" style={{ color: stressColor }}>
          {stress}
        </span>
      </div>

      {/* ── Surrender overlay ── */}
      {surrendered && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#0f0f0f]/95 backdrop-blur-sm p-8"
          role="alert"
          aria-label="Mission accomplished"
        >
          <div className="text-center transform -rotate-1">
            <p className="font-mono text-[10px] tracking-[0.3em] text-[#d99a4e]/60 uppercase mb-4">
              Outcome: Success
            </p>
            <h1 className="font-serif text-6xl md:text-7xl font-black text-[#d99a4e] tracking-tighter uppercase leading-none">
              Mission<br />Accomplished
            </h1>
            <div className="mt-6 inline-block border-2 border-[#d99a4e]/50 px-4 py-1">
              <span className="font-mono text-sm tracking-[0.25em] text-[#f4f0e6]">SUBJECT SURRENDERED</span>
            </div>
          </div>
          <p className="font-mono text-[10px] text-[#f4f0e6]/30 tracking-widest uppercase mt-8 animate-pulse">
            Generating debrief report...
          </p>
        </div>
      )}

      {/* ── Escalation overlay ── */}
      {escalated && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#dc2626]/90 backdrop-blur-sm p-8"
          role="alert"
          aria-label="Mission failed"
        >
          <div className="text-center transform rotate-1">
            <p className="font-mono text-[10px] tracking-[0.3em] text-[#1e1e1e] uppercase mb-4">
              Outcome: Failure
            </p>
            <h1 className="font-serif text-6xl md:text-7xl font-black text-[#1e1e1e] tracking-tighter uppercase leading-none">
              Mission<br />Failed
            </h1>
            <div className="mt-6 inline-block border-2 border-[#1e1e1e] px-4 py-1 bg-[#f4f0e6]">
              <span className="font-mono text-sm tracking-[0.25em] font-bold text-[#1e1e1e]">SUBJECT ESCALATED</span>
            </div>
          </div>
          <p className="font-mono text-[10px] text-[#1e1e1e] tracking-widest uppercase mt-8 animate-pulse">
            Generating debrief report...
          </p>
        </div>
      )}
    </>
  );
});

export default MissionStatus;
