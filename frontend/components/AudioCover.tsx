"use client";

import { useEffect, useRef } from "react";

let sharedAudioContext: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!sharedAudioContext || sharedAudioContext.state === "closed") {
    sharedAudioContext = new (window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
  }
  return sharedAudioContext;
}

export default function AudioCover({
  isDispatching,
  isHolding,
}: {
  isDispatching: boolean;
  isHolding: boolean;
}) {
  const oscRef = useRef<OscillatorNode | null>(null);
  const gainRef = useRef<GainNode | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const ctx = getAudioContext();
    let osc: OscillatorNode | null = null;
    let gain: GainNode | null = null;

    if (isDispatching) {
      osc = ctx.createOscillator();
      gain = ctx.createGain();
      osc.type = "square";
      osc.frequency.setValueAtTime(400, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.05, ctx.currentTime + 0.05);
      gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.4);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.5);
    } else if (isHolding) {
      osc = ctx.createOscillator();
      gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(60, ctx.currentTime);
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.02, ctx.currentTime + 0.5);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
    }

    oscRef.current = osc;
    gainRef.current = gain;

    return () => {
      if (gainRef.current && isHolding) {
        try {
          gainRef.current.gain.linearRampToValueAtTime(
            0,
            ctx.currentTime + 0.2
          );
        } catch {
          // Context may already be closed
        }
      }
      if (oscRef.current) {
        try {
          oscRef.current.stop(ctx.currentTime + 0.2);
        } catch {
          // Oscillator may already be stopped
        }
      }
      oscRef.current = null;
      gainRef.current = null;
    };
  }, [isDispatching, isHolding]);

  return null;
}
