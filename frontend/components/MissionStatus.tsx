"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useRef, useEffect, useState } from "react";
import {
  ESCALATION_DISPLAY_MS,
  SURRENDER_THRESHOLD_PERCENT,
} from "@/lib/constants";
import type { StatusMessage } from "@/lib/types";

const MissionStatus = memo(function MissionStatus({
  onReport,
}: {
  onReport: (r: string) => void;
}) {
  const [surrendered, setSurrendered] = useState(false);
  const [escalated, setEscalated] = useState(false);
  const [stress, setStress] = useState(85);
  const escalationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleStatusData = useCallback(
    (msg: { payload: Uint8Array }) => {
      try {
        const data: StatusMessage = JSON.parse(
          new TextDecoder().decode(msg.payload)
        );
        if (data.type === "surrender") {
          setSurrendered(true);
        } else if (data.type === "escalate") {
          setEscalated(true);
          if (escalationTimerRef.current) clearTimeout(escalationTimerRef.current);
          escalationTimerRef.current = setTimeout(
            () => setEscalated(false),
            ESCALATION_DISPLAY_MS
          );
        } else if (data.type === "stress" && data.level !== undefined) {
          setStress(data.level);
        } else if (data.type === "report" && data.content) {
          onReport(data.content);
        }
      } catch (e) {
        console.error("Failed to parse status data channel message:", e);
      }
    },
    [onReport]
  );

  useEffect(() => {
    return () => {
      if (escalationTimerRef.current) clearTimeout(escalationTimerRef.current);
    };
  }, []);

  useDataChannel(handleStatusData);

  const stressColor =
    stress > 80 ? "#dc2626" : stress > 20 ? "#d99a4e" : "#22c55e";

  const stressGlow =
    stress > 80 ? "0 0 8px #dc262680" : stress > 20 ? "0 0 6px #d99a4e60" : "0 0 6px #22c55e60";

  return (
    <>
      {/* Stress gauge sidebar — sits on dark session bg, so use light-on-dark colors */}
      <div
        className="flex flex-col items-center w-10 shrink-0 py-2"
        role="meter"
        aria-label="Subject stress level"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={stress}
        aria-valuetext={`Stress ${stress}%`}
      >
        <span className="font-mono text-[7px] font-bold text-[#f4f0e6]/50 tracking-widest mb-1.5 uppercase">
          STRESS
        </span>
        <div className="flex-1 w-3.5 bg-[#f4f0e6]/5 border border-[#f4f0e6]/15 relative overflow-hidden">
          {/* Fill bar */}
          <div
            className="absolute bottom-0 left-0 right-0 transition-[height] duration-300 ease-out"
            style={{
              height: `${stress}%`,
              backgroundColor: stressColor,
              boxShadow: stressGlow,
            }}
          />
          {/* Win-threshold line */}
          <div
            className="absolute left-0 right-0 h-px bg-[#22c55e]"
            style={{ bottom: `${SURRENDER_THRESHOLD_PERCENT}%`, opacity: 0.5 }}
          />
          {/* Quarter grid lines */}
          {[25, 50, 75].map((pct) => (
            <div
              key={pct}
              className="absolute left-0 right-0 h-px bg-[#f4f0e6]/10"
              style={{ bottom: `${pct}%` }}
            />
          ))}
        </div>
        <span className="font-mono text-[9px] font-bold text-[#f4f0e6]/70 mt-1.5 tabular-nums" style={{ color: stressColor }}>
          {stress}%
        </span>
        <span className="font-mono text-[6px] text-[#22c55e]/70 mt-0.5 leading-tight text-center tracking-tight">
          WIN<br />&lt;30
        </span>
      </div>

      {/* Surrender screen */}
      {surrendered && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#1e1e1e]/95 backdrop-blur-sm p-6"
          role="alert"
          aria-label="Mission accomplished - subject surrendered"
        >
          <div className="text-center transform -rotate-2">
            <h1 className="text-6xl md:text-8xl font-black font-serif text-[#d99a4e] tracking-tighter uppercase drop-shadow-[8px_8px_0_rgba(244,240,230,0.08)]">
              Mission<br />Accomplished
            </h1>
            <p className="mt-6 text-[#f4f0e6] font-mono text-xl tracking-widest border-t-2 border-b-2 border-[#d99a4e] inline-block py-2 px-4">
              SUBJECT SURRENDERED
            </p>
          </div>
          <p className="mt-8 text-[#f4f0e6]/60 font-mono text-sm tracking-wider animate-pulse">
            Generating post-action debrief report...
          </p>
        </div>
      )}

      {/* Escalate screen */}
      {escalated && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#dc2626]/90 backdrop-blur-sm p-6"
          role="alert"
          aria-label="Mission failed - subject escalated"
        >
          <div className="text-center transform rotate-2">
            <h1 className="text-6xl md:text-8xl font-black font-serif text-[#1e1e1e] tracking-tighter uppercase drop-shadow-[8px_8px_0_rgba(244,240,230,0.15)]">
              Mission<br />Failed
            </h1>
            <p className="mt-6 text-[#1e1e1e] font-mono font-bold text-xl tracking-widest border-t-4 border-b-4 border-[#1e1e1e] inline-block py-2 px-4 bg-[#f4f0e6]">
              SUBJECT ESCALATED
            </p>
          </div>
          <p className="mt-8 text-[#1e1e1e] font-mono text-sm font-bold tracking-wider animate-pulse">
            Generating post-action debrief report...
          </p>
        </div>
      )}
    </>
  );
});

export default MissionStatus;
