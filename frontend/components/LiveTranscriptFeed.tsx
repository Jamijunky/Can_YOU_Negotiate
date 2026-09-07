"use client";

import { useDataChannel, useVoiceAssistant } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { TranscriptItem } from "@/lib/types";

const LiveTranscriptFeed = memo(function LiveTranscriptFeed({
  subjectName,
}: {
  subjectName: string;
}) {
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { state } = useVoiceAssistant();
  const isSpeaking = state === "speaking";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts]);

  const handleData = useCallback(
    (msg: { payload: Uint8Array }) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(msg.payload));
        if (data.type === "transcript" && data.text) {
          const timeStr = new Date().toLocaleTimeString([], {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });
          setTranscripts((prev) => {
            if (data.id) {
              const idx = prev.findIndex((item) => item.id === data.id);
              if (idx !== -1) {
                const updated = [...prev];
                updated[idx] = {
                  ...updated[idx],
                  text: data.text,
                  isFinal: data.isFinal ?? true,
                  timestamp: timeStr,
                };
                return updated;
              }
            }

            const lastItem =
              prev.length > 0 ? prev[prev.length - 1] : null;
            if (
              data.speaker === "user" &&
              lastItem &&
              lastItem.speaker === "user"
            ) {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...lastItem,
                id: data.id || lastItem.id,
                text: lastItem.text + " " + data.text,
                isFinal: data.isFinal ?? true,
                timestamp: timeStr,
              };
              return updated;
            }

            return [
              ...prev,
              {
                id:
                  data.id ||
                  `${data.speaker}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
                speaker: data.speaker,
                senderName:
                  data.speaker === "user"
                    ? "YOU"
                    : subjectName || data.senderName || "SUBJECT",
                text: data.text,
                timestamp: timeStr,
                isFinal: data.isFinal ?? true,
              },
            ];
          });
        }
      } catch (e) {
        console.error("Failed to parse transcript data channel message:", e);
      }
    },
    [subjectName]
  );

  useDataChannel(handleData);

  return (
    <div
      className={`w-full max-w-2xl mt-6 bg-[#1e1e1e] border-2 border-[#d99a4e] p-4 text-left shadow-[6px_6px_0_0_#1e1e1e] transition-opacity duration-300 ${
        isSpeaking ? "opacity-40" : "opacity-100"
      }`}
      role="log"
      aria-label="Live conversation transcript"
      aria-live="polite"
    >
      <div className="flex items-center justify-between border-b border-[#f4f0e6]/20 pb-2 mb-3">
        <div className="font-mono text-xs font-bold tracking-widest text-[#d99a4e] uppercase flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" aria-hidden="true" />
          <span>COMMS_LOG // LIVE_TRANSCRIPT</span>
        </div>
        <span className="font-mono text-[10px] text-[#f4f0e6]/50 uppercase">
          CONVERSATION STREAM
        </span>
      </div>

      <div
        ref={scrollRef}
        className="h-44 overflow-y-auto space-y-2 pr-1 flex flex-col select-text font-mono text-xs"
      >
        {transcripts.length === 0 ? (
          <div className="text-[#f4f0e6]/40 italic py-6 text-center">
            [Audio channel open. Speak into microphone to negotiate...]
          </div>
        ) : (
          transcripts.map((t) => (
            <div
              key={t.id}
              className={`p-2 border-l-2 leading-relaxed transition-all duration-150 ${
                t.speaker === "user"
                  ? "border-[#22c55e] bg-white/5 text-[#f4f0e6]"
                  : "border-[#d99a4e] bg-[#d99a4e]/10 text-[#f4f0e6]"
              }`}
            >
              <div className="flex items-center justify-between text-[10px] mb-1 opacity-70">
                <span
                  className={
                    t.speaker === "user"
                      ? "text-[#22c55e] font-bold flex items-center gap-1.5"
                      : "text-[#d99a4e] font-bold"
                  }
                >
                  [{t.senderName}]{" "}
                  {t.speaker === "user" && t.isFinal === false && (
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#22c55e] animate-ping" />
                  )}
                </span>
                <span>{t.timestamp}</span>
              </div>
              <p className="text-sm font-serif tracking-normal">{t.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
});

export default LiveTranscriptFeed;
