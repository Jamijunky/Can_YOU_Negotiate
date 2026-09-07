"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useRef, useEffect, useState } from "react";
import {
  ESCALATION_DISPLAY_MS,
  SURRENDER_THRESHOLD_PERCENT,
  SURRENDER_LABEL_OFFSET_PERCENT,
} from "@/lib/constants";
import type { StatusMessage } from "@/lib/types";

const MissionStatus = memo(function MissionStatus({
  onReport,
}: {
  onReport: (r: string) => void;
}) {
  const [surrendered, setSurrendered] = useState(false);
  const [escalated, setEscalated] = useState(false);
  const [stress, setStress] = useState(90);
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
    stress > 80 ? "#dc2626" : stress > 20 ? "#d99a4e" : "#16a34a";

  return (
    <>
      {/* Stress gauge sidebar */}
      <div className="flex flex-col items-center w-12 shrink-0" role="meter" aria-label="Subject stress level" aria-valuemin={0} aria-valuemax={100} aria-valuenow={stress} aria-valuetext={`Stress ${stress}%`}>
        <span className="font-mono text-[8px] font-bold text-[#1e1e1e] tracking-widest mb-1">STRESS</span>
        <div className="flex-1 w-4 bg-[#1e1e1e]/10 border border-[#1e1e1e]/30 relative overflow-hidden rounded-sm">
          <div
            className="absolute bottom-0 left-0 right-0 transition-all duration-1000 ease-out"
            style={{ height: `${stress}%`, backgroundColor: stressColor, boxShadow: stress > 80 ? `0 0 6px ${stressColor}` : "none" }}
          />
          <div className="absolute left-0 right-0 h-px bg-[#16a34a]" style={{ bottom: `${SURRENDER_THRESHOLD_PERCENT}%` }} />
        </div>
        <span className="font-mono text-[10px] font-bold text-[#1e1e1e] mt-1">{stress}%</span>
        <span className="font-mono text-[6px] text-[#16a34a] mt-0.5 leading-none text-center">WIN<br/>&lt;30%</span>
      </div>

      {/* Surrender screen */}
      {surrendered && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#1e1e1e]/90 backdrop-blur-sm p-6"
          role="alert"
          aria-label="Mission accomplished - subject surrendered"
        >
          <div className="text-center transform -rotate-2">
            <h1 className="text-6xl md:text-8xl font-black font-serif text-[#d99a4e] tracking-tighter uppercase drop-shadow-[8px_8px_0_rgba(244,240,230,0.1)]">
              Mission<br />Accomplished
            </h1>
            <p className="mt-6 text-[#f4f0e6] font-mono text-xl tracking-widest border-t-2 border-b-2 border-[#d99a4e] inline-block py-2">
              SUBJECT SURRENDERED
            </p>
          </div>
          <p className="mt-8 text-[#f4f0e6]/70 font-mono text-sm tracking-wider animate-pulse">
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
            <h1 className="text-6xl md:text-8xl font-black font-serif text-[#1e1e1e] tracking-tighter uppercase drop-shadow-[8px_8px_0_rgba(244,240,230,0.2)]">
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
