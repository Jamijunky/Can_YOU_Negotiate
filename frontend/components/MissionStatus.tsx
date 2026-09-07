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
      {/* Stress bar + label container */}
      <div
        className="absolute top-0 left-0 bottom-0 z-30 flex flex-row"
        role="meter"
        aria-label="Subject stress level"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={stress}
        aria-valuetext={`Stress ${stress}%`}
      >
        <div className="relative w-24 flex flex-col justify-end">
          <div className="absolute top-2 right-0 font-mono text-[10px] font-bold px-1.5 py-0.5 bg-[#1e1e1e] text-[#f4f0e6] whitespace-nowrap pointer-events-none select-none">
            STRESS: {stress}
          </div>
          <div className="absolute bottom-0 right-0 top-0 w-3 bg-[#1e1e1e]/10 border-r border-[#1e1e1e]/20 flex flex-col justify-end overflow-hidden">
            <div
              className="absolute left-0 right-0 h-0.5 bg-[#f4f0e6] z-40 shadow-[0_0_4px_rgba(0,0,0,0.5)]"
              style={{ bottom: `${SURRENDER_THRESHOLD_PERCENT}%` }}
              title="Surrender Threshold"
            />
            <div
              className="absolute left-4 text-[10px] font-mono font-bold text-[#1e1e1e] whitespace-nowrap rotate-[-90deg] origin-bottom-left"
              style={{ bottom: `${SURRENDER_LABEL_OFFSET_PERCENT}%` }}
            >
              SURRENDER_ZONE
            </div>
            <div
              className="w-full transition-all duration-1000 ease-out"
              style={{
                height: `${stress}%`,
                backgroundColor: stressColor,
                boxShadow: stress > 80 ? "0 0 10px #dc2626" : "none",
              }}
            />
          </div>
        </div>
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
