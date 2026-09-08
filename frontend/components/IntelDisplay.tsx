"use client";

import { memo } from "react";

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
    </div>
  );
});

export default IntelDisplay;
