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
      if (room) {
        room.disconnect();
      }
    } catch (e) {
      console.warn("Error disconnecting room:", e);
    }
    onDisconnect();
  }, [room, onDisconnect]);

  const remoteParticipants = useRemoteParticipants();
  const hasAgent = remoteParticipants.some(
    (p) =>
      (p.kind as unknown as number) === 4 ||
      p.identity.startsWith("agent-")
  );

  const [dispatchStep, setDispatchStep] = useState(0);
  const dispatchTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const effectiveState: VoiceAssistantState =
    state === "connecting" && (audioTrack || hasAgent) ? "listening" : (state as VoiceAssistantState);
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
    ? Math.min(
        DISPATCH_PROGRESS_MAX,
        ((dispatchStep + 1) / DISPATCH_MESSAGES.length) * 100
      )
    : 100;

  return (
    <div className="flex flex-col items-center justify-center p-6 min-h-[220px] relative">
      {/* Decorative crosshair */}
      <div
        className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-10"
        aria-hidden="true"
      >
        <div className="w-64 h-64 border border-[#1e1e1e] rounded-full" />
        <div className="absolute w-full h-[1px] bg-[#1e1e1e]" />
        <div className="absolute h-full w-[1px] bg-[#1e1e1e]" />
      </div>

      {tacticalHold && (
        <div className="z-20 mb-4 px-4 py-2 bg-[#d99a4e] border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e] animate-pulse">
          <p className="font-mono text-xs font-black uppercase text-[#1e1e1e] tracking-wider">
            [ TACTICAL HOLD ACTIVE: Mic muted. Formulate your strategy. Subject
            is waiting on the line. ]
          </p>
        </div>
      )}

      <div className="mb-4 flex flex-col items-center z-10">
        <div
          className={`font-serif text-3xl md:text-4xl font-black uppercase tracking-tighter transition-colors text-center whitespace-nowrap ${
            tacticalHold
              ? "text-[#d99a4e]"
              : effectiveState === "speaking" ||
                  effectiveState === "listening"
                ? "text-[#d99a4e]"
                : "text-[#1e1e1e]"
          }`}
          aria-live="polite"
          aria-label={`Connection status: ${
            tacticalHold
              ? "Hold"
              : isDispatching
                ? DISPATCH_MESSAGES[dispatchStep]
                : effectiveState
          }`}
        >
          [
          {tacticalHold
            ? "HOLD // THINK TIME"
            : isDispatching
              ? DISPATCH_MESSAGES[dispatchStep]
              : effectiveState}
          ]
        </div>
        {isDispatching && (
          <div className="mt-2 font-mono text-[10px] uppercase tracking-widest text-[#1e1e1e]/60 animate-pulse">
            (Connecting to subject... this should only take a few seconds)
          </div>
        )}
        <div className="h-16 mt-4 flex items-center justify-center">
          {audioTrack && !tacticalHold && (
            <BarVisualizer
              state={effectiveState}
              barCount={9}
              trackRef={audioTrack}
              className="h-16 w-64 text-[#1e1e1e]"
            />
          )}
          {isDispatching && !tacticalHold && (
            <div className="h-16 flex flex-col items-center justify-center gap-3 w-64">
              <div
                className="w-full h-2 bg-[#1e1e1e]/10 border border-[#1e1e1e]/30"
                role="progressbar"
                aria-valuenow={Math.round(dispatchProgress)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Connection progress"
              >
                <div
                  className="h-full bg-[#d99a4e] transition-all duration-700 ease-out"
                  style={{ width: `${dispatchProgress}%` }}
                />
              </div>
              <span className="font-mono text-[10px] tracking-widest text-[#1e1e1e]/50 animate-pulse uppercase">
                Securing comms link
              </span>
            </div>
          )}
          {tacticalHold && (
            <div className="h-16 flex items-center justify-center font-mono text-sm tracking-widest text-[#1e1e1e]/60">
              [ COMMS MUTED FOR TACTICAL DELIBERATION ]
            </div>
          )}
        </div>
      </div>

      {/* Control Actions bar */}
      <div className="z-10 mt-4 flex flex-wrap items-center justify-center gap-4">
        <button
          onClick={toggleHold}
          aria-label={tacticalHold ? "Resume communications" : "Put call on tactical hold"}
          className={`font-mono text-xs md:text-sm font-black px-4 py-2 border-2 border-[#1e1e1e] transition-all flex items-center gap-2 shadow-[3px_3px_0_0_#1e1e1e] ${
            tacticalHold
              ? "bg-[#22c55e] text-[#1e1e1e] hover:bg-[#16a34a]"
              : "bg-[#d99a4e] text-[#1e1e1e] hover:bg-[#b8803c]"
          }`}
        >
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              tacticalHold ? "bg-[#1e1e1e] animate-ping" : "bg-[#dc2626]"
            }`}
            aria-hidden="true"
          />
          {tacticalHold ? "RESUME COMMS [UNPAUSE]" : "TACTICAL HOLD // THINK TIME"}
        </button>

        <button
          onClick={handleDisconnect}
          aria-label="Disconnect call"
          className="bg-[#dc2626] hover:bg-[#b91c1c] text-white font-mono text-xs md:text-sm font-black px-5 py-2.5 border-2 border-[#1e1e1e] shadow-[3px_3px_0_0_#1e1e1e] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0_#1e1e1e] transition-all cursor-pointer flex items-center gap-2"
        >
          <span className="w-2.5 h-2.5 bg-white rounded-full inline-block" aria-hidden="true" />
          DISCONNECT // END CALL
        </button>
      </div>
      <AudioCover isDispatching={isDispatching} isHolding={tacticalHold} />
    </div>
  );
});

export default SimulationUI;
