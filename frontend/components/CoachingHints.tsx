"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { CoachingHint } from "@/lib/types";

const CATEGORY_COLORS: Record<CoachingHint["category"], string> = {
  empathy:     "#22c55e",
  patience:    "#d99a4e",
  technique:   "#f4f0e6",
  warning:     "#dc2626",
  opportunity: "#d99a4e",
};

const CATEGORY_LABELS: Record<CoachingHint["category"], string> = {
  empathy:     "EMPATHY",
  patience:    "PATIENCE",
  technique:   "TECHNIQUE",
  warning:     "WARNING",
  opportunity: "OPPTY",
};

const CoachingHints = memo(function CoachingHints() {
  const [hints, setHints]         = useState<CoachingHint[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "coachingHint" && data.text) {
        setHints((prev) =>
          [...prev, {
            id: data.id || `hint-${Date.now()}`,
            text: data.text,
            category: data.category || "technique",
            timestamp: data.timestamp || Date.now(),
          }].slice(-8)
        );
      }
    } catch { /* ignore */ }
  }, []);

  useDataChannel(handleData);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [hints]);

  const visible = hints.filter((h) => !dismissed.has(h.id));
  if (visible.length === 0) return null;

  return (
    <div className="p-3 border-b border-[#f4f0e6]/8" role="region" aria-label="Coaching hints">
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        TRAINING_MODE // COACHING_HINTS
      </div>
      <div ref={scrollRef} className="space-y-1.5 max-h-28 overflow-y-auto thin-scroll">
        {visible.map((hint) => (
          <div
            key={hint.id}
            className="flex items-start gap-2 p-1.5 border-l-2 bg-white/4 animate-in fade-in duration-300"
            style={{ borderColor: CATEGORY_COLORS[hint.category] }}
          >
            <span
              className="font-mono text-[7px] font-bold shrink-0 mt-px tracking-widest uppercase"
              style={{ color: CATEGORY_COLORS[hint.category] }}
            >
              {CATEGORY_LABELS[hint.category]}
            </span>
            <p className="font-serif text-[10px] text-[#f4f0e6]/60 leading-snug flex-1">{hint.text}</p>
            <button
              onClick={() => setDismissed((p) => new Set([...p, hint.id]))}
              className="text-[#f4f0e6]/20 hover:text-[#f4f0e6]/50 text-xs shrink-0 transition-colors"
              aria-label="Dismiss hint"
            >×</button>
          </div>
        ))}
      </div>
    </div>
  );
});

export default CoachingHints;
