"use client";

import { memo } from "react";

const IntelDisplay = memo(function IntelDisplay({ intel }: { intel: string }) {
  return (
    <div
      className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 border-l-2 border-l-[#dc2626] p-3 text-left mb-3"
      role="complementary"
      aria-label="Subject intelligence briefing"
    >
      {/* Unified panel header style */}
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#dc2626] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#dc2626] animate-pulse" aria-hidden="true" />
        SUBJECT_INTEL
      </div>
      <p className="font-serif text-sm text-[#f4f0e6]/85 leading-relaxed">{intel}</p>
    </div>
  );
});

export default IntelDisplay;
