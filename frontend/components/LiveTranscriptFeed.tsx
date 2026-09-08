"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { TranscriptItem } from "@/lib/types";

const LiveTranscriptFeed = memo(function LiveTranscriptFeed({
  subjectName,
}: {
  subjectName: string;
}) {
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  const handleData = useCallback(
    (msg: { payload: Uint8Array }) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(msg.payload));
        if (data.type === "transcript" && data.text) {
          const now = Date.now();
          const timeStr = new Date().toLocaleTimeString([], {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });

          setTranscripts((prev) => {
            const last = prev.length > 0 ? prev[prev.length - 1] : null;

            // Only skip exact character-for-character duplicates within 3 seconds
            if (
              last &&
              last.speaker === data.speaker &&
              now - last.finalizedAt < 3000 &&
              data.text.trim() === last.text.trim()
            ) {
              return prev;
            }

            // New entry — always add, no merging
            return [
              ...prev,
              {
                id: data.id || `${data.speaker}-${now}-${Math.random().toString(36).slice(2)}`,
                speaker: data.speaker,
                senderName:
                  data.speaker === "user"
                    ? "You"
                    : subjectName || data.senderName || "Subject",
                text: data.text,
                timestamp: timeStr,
                isFinal: true,
                finalizedAt: now,
              },
            ];
          });
        }
      } catch (e) {
        console.error("Failed to parse transcript message:", e);
      }
    },
    [subjectName]
  );

  useDataChannel(handleData);

  return (
    <div
      className="flex flex-col h-full bg-[#f4f0e6]"
      role="log"
      aria-label="Live conversation"
      aria-live="polite"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b-2 border-[#1e1e1e]/15 bg-[#f4f0e6]">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] glow-green" aria-hidden="true" />
          <span className="font-mono text-[10px] font-bold tracking-widest text-[#1e1e1e]/50 uppercase">
            COMMS_LOG // LIVE_TRANSCRIPT
          </span>
        </div>
        <span className="font-mono text-[10px] text-[#1e1e1e]/30 uppercase tracking-widest">
          {transcripts.length > 0 ? `${transcripts.length} exchanges` : "Waiting..."}
        </span>
      </div>

      {/* Entries */}
      <div className="flex-1 overflow-y-auto thin-scroll-light px-5 py-4 space-y-5">
        {transcripts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="font-mono text-xs text-[#1e1e1e]/25 tracking-widest uppercase text-center leading-loose">
              Audio channel open<br />
              <span className="text-[10px]">Start speaking to begin</span>
            </p>
          </div>
        ) : (
          transcripts.map((t) => {
            const isUser = t.speaker === "user";
            return (
              <div key={t.id} className="space-y-1">
                {/* Speaker + timestamp */}
                <div className="flex items-baseline gap-2">
                  <span
                    className="font-mono text-[10px] font-bold tracking-wider uppercase"
                    style={{ color: isUser ? "#16a34a" : "#d99a4e" }}
                  >
                    [{t.senderName}]
                  </span>
                  <span className="font-mono text-[9px] text-[#1e1e1e]/30 tabular-nums">
                    {t.timestamp}
                  </span>
                </div>
                {/* Full message — Playfair serif, no truncation */}
                <p className={`font-serif text-[15px] leading-relaxed ${
                  isUser ? "text-[#1e1e1e]/90" : "text-[#1e1e1e]/75"
                }`}>
                  {t.text}
                </p>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
});

export default LiveTranscriptFeed;
