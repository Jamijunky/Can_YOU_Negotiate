"use client";

import { memo } from "react";

// Small rotating tips shown under intel — adds a human voice to the UI
const NEGOTIATOR_TIPS = [
  "Let them vent. Silence is a tool.",
  "Name what they feel. Don't fix it.",
  "Ask: what do they need right now?",
  "People don't surrender to logic. They surrender to trust.",
  "Mirror their words back. It works every time.",
  "The angrier they get, the slower you speak.",
  "Find the fear under the anger.",
  "They're not irrational. You just don't know enough yet.",
];

const tip = NEGOTIATOR_TIPS[Math.floor(Math.random() * NEGOTIATOR_TIPS.length)];

const IntelDisplay = memo(function IntelDisplay({ intel }: { intel: string }) {
  return (
    <div
      className="p-3 border-b-2 border-[#1e1e1e]/15"
      role="complementary"
      aria-label="Subject intelligence briefing"
    >
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#dc2626] uppercase mb-1.5 flex items-center gap-1.5">
        <span className="w-1 h-1 bg-[#dc2626] shrink-0" aria-hidden="true" />
        SUBJECT_INTEL
      </div>
      <p className="font-serif text-[12px] text-[#1e1e1e]/70 leading-relaxed">{intel}</p>
      <div className="mt-2 pt-2 border-t border-[#1e1e1e]/8">
        <p className="font-mono text-[9px] text-[#d99a4e]/70 italic leading-snug">
          ↳ {tip}
        </p>
      </div>
    </div>
  );
});

export default IntelDisplay;
