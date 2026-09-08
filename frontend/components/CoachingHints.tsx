"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { CoachingHint } from "@/lib/types";

const CATEGORY_COLOR: Record<CoachingHint["category"], string> = {
  empathy:     "#27ae60",
  patience:    "#c8893e",
  technique:   "rgba(255,255,255,0.4)",
  warning:     "#c0392b",
  opportunity: "#c8893e",
};

const CATEGORY_LABEL: Record<CoachingHint["category"], string> = {
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
    <div className="border-b border-white/8 p-4" role="region" aria-label="Coaching hints">
      <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase mb-2">
        Training Hints
      </div>
      <div ref={scrollRef} className="space-y-1.5 max-h-28 overflow-y-auto thin-scroll">
        {visible.map((hint) => (
          <div
            key={hint.id}
            className="flex items-start gap-2 border-l border-white/8 pl-2"
            style={{ borderColor: `${CATEGORY_COLOR[hint.category]}40` }}
          >
            <span
              className="font-mono text-[7px] font-bold shrink-0 mt-0.5 tracking-widest uppercase"
              style={{ color: CATEGORY_COLOR[hint.category], opacity: 0.7 }}
            >
              {CATEGORY_LABEL[hint.category]}
            </span>
            <p className="font-mono text-[10px] text-white/35 leading-snug flex-1">{hint.text}</p>
            <button
              onClick={() => setDismissed((p) => new Set([...p, hint.id]))}
              className="font-mono text-[10px] text-white/15 hover:text-white/40 transition-colors shrink-0"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
});

export default CoachingHints;
