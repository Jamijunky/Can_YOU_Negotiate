"use client";

import { memo } from "react";

const IntelDisplay = memo(function IntelDisplay({ intel }: { intel: string }) {
  return (
    <div
      className="border-b border-white/8 p-4"
      role="complementary"
      aria-label="Subject intelligence briefing"
    >
      <div className="font-mono text-[9px] tracking-[0.2em] text-[#c0392b]/50 uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1 h-1 bg-[#c0392b] shrink-0" aria-hidden="true" />
        Situation
      </div>
      <p className="font-mono text-[11px] text-white/50 leading-relaxed">{intel}</p>
    </div>
  );
});

export default IntelDisplay;
