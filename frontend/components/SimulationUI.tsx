"use client";

import {
  BarVisualizer,
  useVoiceAssistant,
  useRemoteParticipants,
  useRoomContext,
} from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import AudioCover from "./AudioCover";
import {
  DISPATCH_INTERVAL_MS,
  DISPATCH_PROGRESS_MAX,
  DISPATCH_MESSAGES,
} from "@/lib/constants";
import type { VoiceAssistantState } from "@/lib/types";

const SimulationUI = memo(function SimulationUI({
  tacticalHold,
  setTacticalHold,
  onDisconnect,
}: {
  subjectName: string;
  tacticalHold: boolean;
  setTacticalHold: (val: boolean | ((prev: boolean) => boolean)) => void;
  onDisconnect: () => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();
  const room = useRoomContext();

  const toggleHold = useCallback(async () => {
    const nextHold = !tacticalHold;
    setTacticalHold(nextHold);
    try {
      if (room?.localParticipant) {
        await room.localParticipant.setMicrophoneEnabled(!nextHold);
      }
    } catch (e) {
      console.warn("Failed to toggle mic track on tactical hold:", e);
    }
  }, [tacticalHold, room, setTacticalHold]);

  const handleDisconnect = useCallback(() => {
    try {
      if (room) room.disconnect();
    } catch (e) {
      console.warn("Error disconnecting room:", e);
    }
    onDisconnect();
  }, [room, onDisconnect]);

  const remoteParticipants = useRemoteParticipants();
  const hasAgent = remoteParticipants.some(
    (p) => (p.kind as unknown as number) === 4 || p.identity.startsWith("agent-")
  );

  const [dispatchStep, setDispatchStep] = useState(0);
  const dispatchTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const effectiveState: VoiceAssistantState =
    state === "connecting" && (audioTrack || hasAgent)
      ? "listening"
      : (state as VoiceAssistantState);
  const isDispatching = effectiveState === "connecting";

  useEffect(() => {
    if (isDispatching) {
      setDispatchStep(0);
      dispatchTimerRef.current = setInterval(() => {
        setDispatchStep((prev) => (prev + 1) % DISPATCH_MESSAGES.length);
      }, DISPATCH_INTERVAL_MS);
    } else {
      if (dispatchTimerRef.current) {
        clearInterval(dispatchTimerRef.current);
        dispatchTimerRef.current = null;
      }
    }
    return () => {
      if (dispatchTimerRef.current) clearInterval(dispatchTimerRef.current);
    };
  }, [isDispatching]);

  const dispatchProgress = isDispatching
    ? Math.min(DISPATCH_PROGRESS_MAX, ((dispatchStep + 1) / DISPATCH_MESSAGES.length) * 100)
    : 100;

  // Status text color: amber during active comms, muted otherwise
  const statusColor =
    tacticalHold
      ? "#d99a4e"
      : effectiveState === "speaking" || effectiveState === "listening"
      ? "#d99a4e"
      : effectiveState === "thinking"
      ? "#f4f0e6"
      : "#f4f0e6";

  return (
    <div className="flex flex-col items-center justify-center p-6 min-h-[200px] relative">

      {/* Tactical hold banner */}
      {tacticalHold && (
        <div className="z-20 mb-4 w-full flex justify-center">
          <div className="px-4 py-2 bg-[#d99a4e] border border-[#1e1e1e] shadow-[3px_3px_0_0_#1e1e1e] animate-pulse">
            <p className="font-mono text-[11px] font-black uppercase text-[#1e1e1e] tracking-wider text-center">
              [ TACTICAL HOLD — MIC MUTED. FORMULATE STRATEGY. ]
            </p>
          </div>
        </div>
      )}

      {/* Status label */}
      <div className="mb-3 flex flex-col items-center z-10">
        <div
          className="font-mono text-2xl md:text-3xl font-black uppercase tracking-widest text-center tabular-nums transition-colors duration-300"
          style={{ color: statusColor }}
          aria-live="polite"
          aria-label={`Connection status: ${
            tacticalHold ? "Hold" : isDispatching ? DISPATCH_MESSAGES[dispatchStep] : effectiveState
          }`}
        >
          [&thinsp;
          {tacticalHold
            ? "HOLD // THINK TIME"
            : isDispatching
            ? DISPATCH_MESSAGES[dispatchStep]
            : effectiveState}
          &thinsp;]
        </div>

        {isDispatching && (
          <p className="mt-1.5 font-mono text-[10px] uppercase tracking-widest text-[#f4f0e6]/40 animate-pulse text-center">
            Connecting to subject — this should only take a few seconds
          </p>
        )}

        {/* Audio visualizer / progress / hold indicator */}
        <div className="h-14 mt-3 flex items-center justify-center w-full max-w-xs">
          {audioTrack && !tacticalHold && (
            <BarVisualizer
              state={effectiveState}
              barCount={11}
              trackRef={audioTrack}
              className="h-14 w-full text-[#d99a4e]"
            />
          )}

          {isDispatching && !tacticalHold && (
            <div className="w-full flex flex-col items-center gap-2">
              {/* Progress bar */}
              <div
                className="w-full h-1.5 bg-[#f4f0e6]/8 border border-[#f4f0e6]/10 overflow-hidden relative"
                role="progressbar"
                aria-valuenow={Math.round(dispatchProgress)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Connection progress"
              >
                <div
                  className="absolute inset-y-0 left-0 bg-[#d99a4e] transition-all duration-700 ease-out"
                  style={{
                    width: `${dispatchProgress}%`,
                    boxShadow: "0 0 8px rgba(217,154,78,0.6)",
                  }}
                />
              </div>
              <span className="font-mono text-[9px] tracking-widest text-[#f4f0e6]/35 uppercase animate-pulse">
                SECURING COMMS LINK
              </span>
            </div>
          )}

          {tacticalHold && (
            <div className="h-14 flex items-center justify-center font-mono text-xs tracking-widest text-[#f4f0e6]/40 text-center">
              [ COMMS MUTED FOR TACTICAL DELIBERATION ]
            </div>
          )}
        </div>
      </div>

      {/* Control buttons */}
      <div className="z-10 mt-2 flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={toggleHold}
          aria-label={tacticalHold ? "Resume communications" : "Put call on tactical hold"}
          className={`font-mono text-xs font-black px-5 py-2.5 border-2 border-[#1e1e1e] transition-all flex items-center gap-2 shadow-[3px_3px_0_0_#1e1e1e] hover:translate-x-px hover:translate-y-px hover:shadow-[2px_2px_0_0_#1e1e1e] ${
            tacticalHold
              ? "bg-[#22c55e] text-[#1e1e1e] hover:bg-[#16a34a]"
              : "bg-[#d99a4e] text-[#1e1e1e] hover:bg-[#b8803c]"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              tacticalHold ? "bg-[#1e1e1e] animate-ping" : "bg-[#1e1e1e]"
            }`}
            aria-hidden="true"
          />
          {tacticalHold ? "RESUME COMMS" : "TACTICAL HOLD"}
        </button>

        <button
          onClick={handleDisconnect}
          aria-label="Disconnect call"
          className="bg-[#dc2626] hover:bg-[#b91c1c] text-[#f4f0e6] font-mono text-xs font-black px-5 py-2.5 border-2 border-[#1e1e1e] shadow-[3px_3px_0_0_#1e1e1e] hover:translate-x-px hover:translate-y-px hover:shadow-[2px_2px_0_0_#1e1e1e] transition-all cursor-pointer flex items-center gap-2"
        >
          <span className="w-2 h-2 bg-[#f4f0e6] rounded-full inline-block shrink-0" aria-hidden="true" />
          END CALL
        </button>
      </div>

      <AudioCover isDispatching={isDispatching} isHolding={tacticalHold} />
    </div>
  );
});

export default SimulationUI;
