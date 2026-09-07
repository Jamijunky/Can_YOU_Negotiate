"use client";

import { memo } from "react";
import { useVoiceAssistant } from "@livekit/components-react";

const IntelDisplay = memo(function IntelDisplay({ intel }: { intel: string }) {
  const { state } = useVoiceAssistant();
  const isSpeaking = state === "speaking";

  return (
    <div
      className={`mb-6 p-3 bg-white/10 border border-[#f4f0e6]/20 font-serif text-sm text-[#f4f0e6]/90 text-left transition-opacity duration-300 ${
        isSpeaking ? "opacity-40" : "opacity-100"
      }`}
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
