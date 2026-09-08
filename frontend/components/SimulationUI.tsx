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

// Maps assistant state to a terse label
const STATE_LABELS: Record<string, string> = {
  connecting:  "connecting",
  listening:   "listening",
  speaking:    "subject speaking",
  thinking:    "processing",
  idle:        "standby",
};

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
    } catch (e) {
      console.warn("Failed to toggle mic:", e);
    }
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

  return (
    <div className="bg-[#0a0a0a]">

      {/* ── Dispatch / connecting state ── */}
      {isDispatching && (
        <div className="px-4 py-4 border-b border-white/8">
          {/* Scrolling dispatch log */}
          <div className="space-y-0.5 mb-3">
            {DISPATCH_MESSAGES.slice(0, dispatchStep + 1).map((msg, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="font-mono text-[9px] text-white/15 shrink-0 tabular-nums">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span
                  className={`font-mono text-[10px] tracking-wider ${
                    i === dispatchStep ? "text-[#c8893e]" : "text-white/20"
                  }`}
                >
                  {msg}
                </span>
                {i < dispatchStep && (
                  <span className="font-mono text-[9px] text-[#27ae60]/60 ml-auto shrink-0">OK</span>
                )}
                {i === dispatchStep && (
                  <span className="font-mono text-[9px] text-[#c8893e] ml-auto shrink-0 blink">_</span>
                )}
              </div>
            ))}
          </div>
          {/* Progress bar */}
          <div
            className="w-full h-px bg-white/8"
            role="progressbar"
            aria-valuenow={Math.round(dispatchProgress)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full bg-[#c8893e] transition-all duration-700"
              style={{ width: `${dispatchProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Active call state ── */}
      {!isDispatching && (
        <div className="px-4 py-3 flex items-center gap-4 border-b border-white/8">
          {/* State indicator */}
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{
                backgroundColor:
                  tacticalHold ? "#c8893e"
                  : effectiveState === "speaking" ? "#c8893e"
                  : effectiveState === "listening" ? "#27ae60"
                  : effectiveState === "thinking" ? "#c8893e"
                  : "rgba(255,255,255,0.2)",
                animation:
                  effectiveState === "listening" && !tacticalHold
                    ? "pulse-green 1.5s ease-in-out infinite"
                    : effectiveState === "speaking"
                    ? "pulse-amber 1.2s ease-in-out infinite"
                    : "none",
              }}
              aria-hidden="true"
            />
            <span
              className="font-mono text-[10px] tracking-[0.15em] uppercase"
              style={{
                color: tacticalHold ? "rgba(200,137,62,0.6)"
                  : effectiveState === "listening" ? "rgba(39,174,96,0.8)"
                  : effectiveState === "speaking" ? "rgba(200,137,62,0.8)"
                  : "rgba(255,255,255,0.25)",
              }}
              aria-live="polite"
            >
              {tacticalHold ? "hold" : STATE_LABELS[effectiveState] ?? effectiveState}
            </span>
          </div>

          {/* Tactical hold notice */}
          {tacticalHold && (
            <span className="font-mono text-[9px] text-[#c8893e]/40 tracking-wider uppercase">
              mic muted — formulate strategy
            </span>
          )}

          {/* Visualizer */}
          {audioTrack && !tacticalHold && effectiveState === "speaking" && (
            <div className="flex-1 flex items-center justify-center h-6 max-w-[120px]">
              <BarVisualizer
                state={effectiveState}
                barCount={12}
                trackRef={audioTrack}
                className="h-6 w-full text-[#c8893e]"
              />
            </div>
          )}
        </div>
      )}

      {/* ── Controls ── */}
      <div className="flex items-center gap-2 px-4 py-2.5">
        <button
          onClick={toggleHold}
          aria-label={tacticalHold ? "Resume communications" : "Tactical hold — mute mic"}
          className={`font-mono text-[9px] tracking-[0.15em] uppercase px-4 py-2 border transition-colors ${
            tacticalHold
              ? "bg-[#27ae60]/10 border-[#27ae60]/40 text-[#27ae60]/80 hover:bg-[#27ae60]/20"
              : "bg-white/4 border-white/12 text-white/35 hover:bg-white/8 hover:text-white/55"
          }`}
        >
          {tacticalHold ? "Resume" : "Hold"}
        </button>

        <button
          onClick={handleDisconnect}
          aria-label="End call"
          className="font-mono text-[9px] tracking-[0.15em] uppercase px-4 py-2 border bg-[#c0392b]/10 border-[#c0392b]/40 text-[#c0392b]/70 hover:bg-[#c0392b]/20 hover:text-[#c0392b] transition-colors"
        >
          End Call
        </button>

        {/* Elapsed timer */}
        <ElapsedTimer active={!isDispatching} />
      </div>

      <AudioCover isDispatching={isDispatching} isHolding={tacticalHold} />
    </div>
  );
});

// Simple elapsed time display
function ElapsedTimer({ active }: { active: boolean }) {
  const [seconds, setSeconds] = useState(0);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (active) {
      ref.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    }
    return () => { if (ref.current) clearInterval(ref.current); };
  }, [active]);

  if (!active) return null;

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <span className="font-mono text-[9px] text-white/15 tabular-nums ml-auto tracking-widest">
      {mm}:{ss}
    </span>
  );
}

export default SimulationUI;
