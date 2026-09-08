"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { CoachingHint } from "@/lib/types";

// All colors kept within the established palette
const CATEGORY_COLORS: Record<CoachingHint["category"], string> = {
  empathy: "#22c55e",
  patience: "#d99a4e",
  technique: "#f4f0e6",
  warning: "#dc2626",
  opportunity: "#c084fc",
};

const CATEGORY_LABELS: Record<CoachingHint["category"], string> = {
  empathy: "EMPATHY",
  patience: "PATIENCE",
  technique: "TECHNIQUE",
  warning: "WARNING",
  opportunity: "OPPTY",
};

const CoachingHints = memo(function CoachingHints() {
  const [hints, setHints] = useState<CoachingHint[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "coachingHint" && data.text) {
        setHints((prev) => {
          const next = [
            ...prev,
            {
              id: data.id || `hint-${Date.now()}`,
              text: data.text,
              category: data.category || "technique",
              timestamp: data.timestamp || Date.now(),
            },
          ];
          return next.slice(-8);
        });
      }
    } catch {
      // ignore
    }
  }, []);

  useDataChannel(handleData);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [hints]);

  const visibleHints = hints.filter((h) => !dismissed.has(h.id));

  if (visibleHints.length === 0) return null;

  return (
    <div
      className="w-full bg-[#1e1e1e] border border-[#d99a4e]/40 p-3 text-left"
      role="region"
      aria-label="Coaching hints"
    >
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        TRAINING_MODE // COACHING_HINTS
      </div>

      <div ref={scrollRef} className="space-y-2 max-h-32 overflow-y-auto">
        {visibleHints.map((hint) => (
          <div
            key={hint.id}
            className="flex items-start gap-2 p-2 border-l-2 bg-white/5 animate-in fade-in slide-in-from-left-2 duration-300"
            style={{ borderColor: CATEGORY_COLORS[hint.category] }}
          >
            <span
              className="font-mono text-[8px] font-bold px-1 py-0.5 shrink-0 mt-0.5 border"
              style={{
                color: CATEGORY_COLORS[hint.category],
                borderColor: `${CATEGORY_COLORS[hint.category]}40`,
                backgroundColor: `${CATEGORY_COLORS[hint.category]}12`,
              }}
            >
              {CATEGORY_LABELS[hint.category]}
            </span>
            <p className="font-serif text-[11px] text-[#f4f0e6]/80 leading-snug flex-1">
              {hint.text}
            </p>
            <button
              onClick={() => setDismissed((prev) => new Set([...prev, hint.id]))}
              className="text-[#f4f0e6]/30 hover:text-[#f4f0e6]/60 text-xs shrink-0 transition-colors"
              aria-label="Dismiss hint"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
});

export default CoachingHints;
