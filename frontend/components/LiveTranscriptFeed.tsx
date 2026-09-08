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

  // Auto-scroll to latest
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
            const MERGE_WINDOW_MS = 8000;

            // Skip exact duplicate within window
            if (last && now - last.finalizedAt < MERGE_WINDOW_MS) {
              if (data.text.toLowerCase().trim() === last.text.toLowerCase().trim()) return prev;
            }

            // Merge consecutive user utterances (append, don't replace)
            if (
              data.speaker === "user" &&
              last?.speaker === "user" &&
              now - last.finalizedAt < MERGE_WINDOW_MS
            ) {
              if (last.text.toLowerCase().includes(data.text.toLowerCase())) return prev;
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...last,
                text: last.text + " " + data.text,
                isFinal: true,
                finalizedAt: now,
              };
              return updated;
            }

            return [
              ...prev,
              {
                id: data.id || `${data.speaker}-${now}-${Math.random().toString(36).slice(2)}`,
                speaker: data.speaker,
                senderName: data.speaker === "user" ? "You" : subjectName || data.senderName || "Subject",
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
      className="flex flex-col h-full bg-[#0f0f0f]"
      role="log"
      aria-label="Live conversation"
      aria-live="polite"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b border-[#f4f0e6]/8 bg-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] glow-green" aria-hidden="true" />
          <span className="font-mono text-[10px] font-bold tracking-widest text-[#f4f0e6]/40 uppercase">
            COMMS_LOG
          </span>
        </div>
        <span className="font-mono text-[10px] text-[#f4f0e6]/20 uppercase tracking-widest">
          {transcripts.length > 0 ? `${transcripts.length} exchanges` : "waiting..."}
        </span>
      </div>

      {/* Transcript body */}
      <div className="flex-1 overflow-y-auto thin-scroll px-5 py-4 space-y-5">
        {transcripts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="font-mono text-xs text-[#f4f0e6]/20 tracking-widest uppercase text-center">
              Audio channel open<br />
              <span className="text-[#f4f0e6]/12 text-[10px]">Start speaking to begin</span>
            </p>
          </div>
        ) : (
          transcripts.map((t) => {
            const isUser = t.speaker === "user";
            return (
              <div key={t.id} className="space-y-1">
                {/* Speaker label + timestamp */}
                <div className="flex items-baseline gap-2">
                  <span
                    className="font-mono text-[10px] font-bold tracking-wider uppercase"
                    style={{ color: isUser ? "#22c55e" : "#d99a4e" }}
                  >
                    {t.senderName}
                  </span>
                  <span className="font-mono text-[9px] text-[#f4f0e6]/20 tabular-nums">
                    {t.timestamp}
                  </span>
                </div>
                {/* Full message text — no truncation, no bubble */}
                <p className={`font-serif text-[15px] leading-relaxed ${
                  isUser ? "text-[#f4f0e6]/85" : "text-[#f4f0e6]/70"
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
