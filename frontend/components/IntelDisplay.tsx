"use client";

import { memo } from "react";

const IntelDisplay = memo(function IntelDisplay({ intel }: { intel: string }) {
  return (
    <div
      className="mb-6 p-4 bg-[#1e1e1e] border-l-4 border-[#dc2626] font-serif text-sm text-[#f4f0e6] text-left leading-relaxed"
      role="complementary"
      aria-label="Subject intelligence briefing"
    >
      <strong className="font-mono uppercase tracking-widest text-[#dc2626] text-xs block mb-1">
        Subject Intel:
      </strong>
      <span className="text-[#f4f0e6]/90">{intel}</span>
    </div>
  );
});

export default IntelDisplay;
