"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { TranscriptItem } from "@/lib/types";

const LiveTranscriptFeed = memo(function LiveTranscriptFeed({
  subjectName,
  thinking = false,
}: {
  subjectName: string;
  thinking?: boolean;
}) {
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const seenIds = useRef<Set<string>>(new Set());

  const handleData = useCallback(
    (msg: { payload: Uint8Array }) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(msg.payload));
        if (data.type === "transcript" && data.text) {
          const id = data.id || `${data.speaker}-${data.text.slice(0, 30)}-${Date.now()}`;

          // Dedup: skip if we've seen this exact id
          if (seenIds.current.has(id)) return;

          // Also skip exact text duplicate from same speaker within 2s
          setTranscripts((prev) => {
            const last = prev[prev.length - 1];
            if (
              last &&
              last.speaker === data.speaker &&
              Date.now() - last.finalizedAt < 2000 &&
              last.text.trim() === data.text.trim()
            ) {
              return prev;
            }

            seenIds.current.add(id);

            const timeStr = new Date().toLocaleTimeString([], {
              hour12: false,
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            });

            return [
              ...prev,
              {
                id,
                speaker: data.speaker as "user" | "agent",
                senderName:
                  data.speaker === "user"
                    ? "You"
                    : subjectName || data.senderName || "Subject",
                text: data.text,
                timestamp: timeStr,
                isFinal: true,
                finalizedAt: Date.now(),
              },
            ];
          });
        }
      } catch (e) {
        console.error("Transcript parse error:", e);
      }
    },
    [subjectName]
  );

  useDataChannel(handleData);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  return (
    <div
      className={`flex flex-col h-full bg-[#f4f0e6] transition-opacity duration-500 ${
        thinking ? "opacity-40" : "opacity-100"
      }`}
      role="log"
      aria-label="Live conversation"
      aria-live="polite"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b-2 border-[#1e1e1e]/15">
        <div className="flex items-center gap-2">
          <span
            className="w-1.5 h-1.5 rounded-full bg-[#22c55e] glow-green"
            aria-hidden="true"
          />
          <span className="font-mono text-[10px] font-bold tracking-widest text-[#1e1e1e]/50 uppercase">
            COMMS_LOG // LIVE_TRANSCRIPT
          </span>
        </div>
        <span className="font-mono text-[10px] text-[#1e1e1e]/30 uppercase tracking-widest">
          {transcripts.length > 0
            ? `${transcripts.length} ${transcripts.length === 1 ? "exchange" : "exchanges"}`
            : "Waiting..."}
        </span>
      </div>

      {/* Conversation entries */}
      <div className="flex-1 overflow-y-auto thin-scroll-light px-6 py-5 space-y-6">
        {transcripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 select-none">
            <p className="font-mono text-xs text-[#1e1e1e]/20 tracking-widest uppercase text-center leading-loose">
              On the line<br />
              <span className="text-[10px]">Start speaking to begin</span>
            </p>
          </div>
        ) : (
          transcripts.map((t) => {
            const isUser = t.speaker === "user";
            return (
              <div
                key={t.id}
                className="space-y-1 animate-in fade-in slide-in-from-bottom-1 duration-300"
              >
                {/* Speaker label + timestamp */}
                <div className="flex items-baseline gap-2">
                  <span
                    className="font-mono text-[11px] font-bold tracking-wide uppercase"
                    style={{ color: isUser ? "#16a34a" : "#d99a4e" }}
                  >
                    {t.senderName}
                  </span>
                  <span className="font-mono text-[9px] text-[#1e1e1e]/25 tabular-nums">
                    {t.timestamp}
                  </span>
                </div>
                {/* Full message — Playfair, no truncation */}
                <p
                  className={`font-serif leading-relaxed ${
                    isUser
                      ? "text-[16px] text-[#1e1e1e]/90"
                      : "text-[15px] text-[#1e1e1e]/72"
                  }`}
                >
                  {t.text}
                </p>
              </div>
            );
          })
        )}

        {/* Thinking indicator inline */}
        {thinking && (
          <div className="flex items-center gap-2 animate-in fade-in duration-300">
            <span
              className="font-mono text-[11px] font-bold tracking-wide uppercase text-[#d99a4e]"
            >
              {subjectName}
            </span>
            <span className="font-serif text-[14px] text-[#1e1e1e]/35 italic">
              thinking...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
});

export default LiveTranscriptFeed;
