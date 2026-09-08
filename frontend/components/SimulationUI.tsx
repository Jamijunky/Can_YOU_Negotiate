"use client";

import {
  BarVisualizer,
  useVoiceAssistant,
  useRemoteParticipants,
  useRoomContext,
} from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import AudioCover from "./AudioCover";
import { DISPATCH_INTERVAL_MS, DISPATCH_PROGRESS_MAX, DISPATCH_MESSAGES } from "@/lib/constants";
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
    const next = !tacticalHold;
    setTacticalHold(next);
    try {
      if (room?.localParticipant) await room.localParticipant.setMicrophoneEnabled(!next);
    } catch (e) { console.warn("Mic toggle failed:", e); }
  }, [tacticalHold, room, setTacticalHold]);

  const handleDisconnect = useCallback(() => {
    try { room?.disconnect(); } catch { /* ignore */ }
    onDisconnect();
  }, [room, onDisconnect]);

  const remoteParticipants = useRemoteParticipants();
  const hasAgent = remoteParticipants.some(
    (p) => (p.kind as unknown as number) === 4 || p.identity.startsWith("agent-")
  );

  const [dispatchStep, setDispatchStep] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const effectiveState: VoiceAssistantState =
    state === "connecting" && (audioTrack || hasAgent) ? "listening" : (state as VoiceAssistantState);
  const isDispatching = effectiveState === "connecting";

  useEffect(() => {
    if (isDispatching) {
      setDispatchStep(0);
      timerRef.current = setInterval(() => {
        setDispatchStep((p) => (p + 1) % DISPATCH_MESSAGES.length);
      }, DISPATCH_INTERVAL_MS);
    } else {
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isDispatching]);

  const dispatchProgress = isDispatching
    ? Math.min(DISPATCH_PROGRESS_MAX, ((dispatchStep + 1) / DISPATCH_MESSAGES.length) * 100)
    : 100;

  const statusLabel = tacticalHold
    ? "HOLD // THINK TIME"
    : isDispatching
    ? DISPATCH_MESSAGES[dispatchStep]
    : effectiveState === "listening" ? "LISTENING"
    : effectiveState === "speaking"  ? "SPEAKING"
    : effectiveState === "thinking"  ? "THINKING..."
    : effectiveState === "idle"      ? "STANDBY"
    : (effectiveState as string).toUpperCase();

  const statusColor = tacticalHold     ? "#d99a4e"
    : effectiveState === "speaking"    ? "#d99a4e"
    : effectiveState === "listening"   ? "#d99a4e"
    : "#1e1e1e";

  return (
    <div className="p-4 bg-[#f4f0e6]">

      {/* Tactical hold banner */}
      {tacticalHold && (
        <div className="mb-3 px-3 py-1.5 bg-[#d99a4e] border-2 border-[#1e1e1e] flex justify-center shadow-[2px_2px_0_0_#1e1e1e]">
          <p className="font-mono text-[10px] font-black uppercase tracking-widest text-[#1e1e1e]">
            TACTICAL HOLD — MIC MUTED — FORMULATE STRATEGY
          </p>
        </div>
      )}

      {/* Status label */}
      <div className="mb-3 flex flex-col items-center gap-2">
        <div
          className="font-mono text-lg font-black uppercase tracking-widest text-center"
          style={{ color: statusColor }}
          aria-live="polite"
        >
          [{statusLabel}]
        </div>

        {isDispatching && (
          <p className="font-mono text-[10px] text-[#1e1e1e]/40 tracking-widest uppercase animate-pulse text-center">
            (Connecting to subject... this should only take a few seconds)
          </p>
        )}

        {/* Visualizer / progress */}
        <div className="w-full max-w-xs">
          {audioTrack && !tacticalHold && !isDispatching && (
            <BarVisualizer
              state={effectiveState}
              barCount={9}
              trackRef={audioTrack}
              className="h-12 w-full text-[#1e1e1e]"
            />
          )}
          {isDispatching && (
            <div className="flex flex-col items-center gap-1.5 w-full">
              <div
                className="w-full h-2 bg-[#1e1e1e]/10 border border-[#1e1e1e]/20"
                role="progressbar"
                aria-valuenow={Math.round(dispatchProgress)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full bg-[#d99a4e] transition-all duration-700"
                  style={{ width: `${dispatchProgress}%` }}
                />
              </div>
              <span className="font-mono text-[9px] tracking-widest text-[#1e1e1e]/30 uppercase animate-pulse">
                Securing comms link
              </span>
            </div>
          )}
          {tacticalHold && (
            <div className="h-12 flex items-center justify-center">
              <span className="font-mono text-xs text-[#1e1e1e]/40 tracking-widest">
                [ COMMS MUTED FOR TACTICAL DELIBERATION ]
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Controls — matching lobby button style */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={toggleHold}
          aria-label={tacticalHold ? "Resume communications" : "Tactical hold"}
          className={`font-mono text-xs font-black px-5 py-2.5 border-2 border-[#1e1e1e] transition-all flex items-center gap-2 shadow-[3px_3px_0_0_#1e1e1e] hover:translate-x-px hover:translate-y-px hover:shadow-[2px_2px_0_0_#1e1e1e] ${
            tacticalHold
              ? "bg-[#22c55e] text-[#1e1e1e] hover:bg-[#16a34a]"
              : "bg-[#d99a4e] text-[#1e1e1e] hover:bg-[#b8803c]"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 bg-[#1e1e1e] ${tacticalHold ? "animate-ping" : ""}`}
            aria-hidden="true"
          />
          {tacticalHold ? "RESUME COMMS [UNPAUSE]" : "TACTICAL HOLD // THINK TIME"}
        </button>

        <button
          onClick={handleDisconnect}
          aria-label="End call"
          className="bg-[#dc2626] hover:bg-[#b91c1c] text-white font-mono text-xs font-black px-5 py-2.5 border-2 border-[#1e1e1e] shadow-[3px_3px_0_0_#1e1e1e] hover:translate-x-px hover:translate-y-px hover:shadow-[2px_2px_0_0_#1e1e1e] transition-all flex items-center gap-2"
        >
          <span className="w-2 h-2 bg-white rounded-full shrink-0" aria-hidden="true" />
          DISCONNECT // END CALL
        </button>
      </div>

      <AudioCover isDispatching={isDispatching} isHolding={tacticalHold} />
    </div>
  );
});

export default SimulationUI;
