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

// What each state actually means in plain human language
const STATE_HUMAN: Record<string, { label: string; subtext: string; color: string }> = {
  listening:  { label: "Listening",       subtext: "Say something.",               color: "#16a34a"  },
  speaking:   { label: "They're talking", subtext: "Let them finish.",             color: "#d99a4e"  },
  thinking:   { label: "Thinking...",     subtext: "Processing what you said.",    color: "#1e1e1e"  },
  idle:       { label: "On the line",     subtext: "Say something to continue.",   color: "#1e1e1e"  },
  connecting: { label: "Connecting...",   subtext: "",                             color: "#1e1e1e"  },
};

interface SimulationUIProps {
  subjectName: string;
  tacticalHold: boolean;
  setTacticalHold: (val: boolean | ((prev: boolean) => boolean)) => void;
  onDisconnect: () => void;
  // Callback so parent can dim the transcript during thinking
  onThinking?: (thinking: boolean) => void;
}

const SimulationUI = memo(function SimulationUI({
  tacticalHold,
  setTacticalHold,
  onDisconnect,
  onThinking,
}: SimulationUIProps) {
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
  const isThinking    = effectiveState === "thinking";

  // Notify parent when thinking state changes
  useEffect(() => {
    onThinking?.(isThinking && !tacticalHold);
  }, [isThinking, tacticalHold, onThinking]);

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

  const stateKey = tacticalHold ? "idle" : (effectiveState as string);
  const stateInfo = STATE_HUMAN[stateKey] ?? { label: stateKey, subtext: "", color: "#1e1e1e" };

  return (
    <div className="p-4 bg-[#f4f0e6]">

      {/* Tactical hold banner */}
      {tacticalHold && (
        <div className="mb-3 px-3 py-1.5 bg-[#d99a4e] border-2 border-[#1e1e1e] flex justify-center shadow-[2px_2px_0_0_#1e1e1e]">
          <p className="font-mono text-[10px] font-black uppercase tracking-widest text-[#1e1e1e]">
            MIC MUTED — Take your time. They're waiting.
          </p>
        </div>
      )}

      {/* State display */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* State dot */}
          <span
            className="w-2.5 h-2.5 rounded-full shrink-0"
            style={{
              backgroundColor: stateInfo.color,
              boxShadow: isThinking
                ? "none"
                : effectiveState === "listening"
                ? `0 0 0 0 ${stateInfo.color}40`
                : "none",
              animation:
                effectiveState === "listening" && !tacticalHold
                  ? "glow-green 1.8s ease-in-out infinite"
                  : effectiveState === "speaking"
                  ? "glow-amber 1.2s ease-in-out infinite"
                  : "none",
            }}
            aria-hidden="true"
          />
          <div>
            <div
              className="font-mono text-sm font-black uppercase tracking-widest"
              style={{ color: stateInfo.color }}
              aria-live="polite"
            >
              {tacticalHold ? "On hold" : isDispatching ? DISPATCH_MESSAGES[dispatchStep] : stateInfo.label}
            </div>
            {stateInfo.subtext && !tacticalHold && !isDispatching && (
              <div className="font-mono text-[9px] text-[#1e1e1e]/30 tracking-wider mt-0.5">
                {stateInfo.subtext}
              </div>
            )}
          </div>
        </div>

        {/* Compact visualizer — only when subject is speaking */}
        {audioTrack && effectiveState === "speaking" && !tacticalHold && (
          <BarVisualizer
            state={effectiveState}
            barCount={7}
            trackRef={audioTrack}
            className="h-8 w-20 text-[#d99a4e]"
          />
        )}
      </div>

      {/* Dispatch progress */}
      {isDispatching && (
        <div className="mb-3 flex flex-col gap-1.5">
          <div
            className="w-full h-1.5 bg-[#1e1e1e]/10 border border-[#1e1e1e]/15"
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
          <span className="font-mono text-[9px] text-[#1e1e1e]/25 uppercase tracking-widest animate-pulse text-center">
            Securing comms link...
          </span>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={toggleHold}
          aria-label={tacticalHold ? "Resume communications" : "Tactical hold — mute mic to think"}
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
