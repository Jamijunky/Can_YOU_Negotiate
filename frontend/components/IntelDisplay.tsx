"use client";

import { memo } from "react";

const IntelDisplay = memo(function IntelDisplay({ intel }: { intel: string }) {
  return (
    <div
      className="mb-6 p-3 bg-white/10 border border-[#f4f0e6]/20 font-serif text-sm text-[#f4f0e6]/90 text-left"
      role="complementary"
      aria-label="Subject intelligence briefing"
    >
      <strong className="font-mono uppercase tracking-widest text-[#dc2626] text-xs mr-2">
        Subject Intel:
      </strong>
      {intel}
    </div>
  );
});

export default IntelDisplay;
