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
  const scrollRef = useRef<HTMLDivElement>(null);
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
            const MERGE_WINDOW_MS = 8000;

            // Exact duplicate
            if (last && now - last.finalizedAt < MERGE_WINDOW_MS) {
              if (data.text.toLowerCase().trim() === last.text.toLowerCase().trim()) return prev;
            }

            // Merge consecutive user messages
            if (
              data.speaker === "user" &&
              last?.speaker === "user" &&
              now - last.finalizedAt < MERGE_WINDOW_MS
            ) {
              if (last.text.toLowerCase().includes(data.text.toLowerCase())) return prev;
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...last,
                id: data.id || last.id,
                text: last.text + " " + data.text,
                isFinal: true,
                finalizedAt: now,
                timestamp: timeStr,
              };
              return updated;
            }

            return [
              ...prev,
              {
                id: data.id || `${data.speaker}-${now}-${Math.random().toString(36).slice(2)}`,
                speaker: data.speaker,
                senderName: data.speaker === "user" ? "YOU" : subjectName || data.senderName || "SUBJECT",
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
      className="flex flex-col h-full bg-[#0a0a0a]"
      role="log"
      aria-label="Live conversation transcript"
      aria-live="polite"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b border-white/8">
        <div className="flex items-center gap-2">
          <span
            className="w-1.5 h-1.5 rounded-full bg-[#27ae60]"
            style={{ animation: "pulse-green 2s ease-in-out infinite" }}
            aria-hidden="true"
          />
          <span className="font-mono text-[9px] tracking-[0.2em] text-white/30 uppercase">
            Comms Log
          </span>
        </div>
        <span className="font-mono text-[9px] text-white/15 tracking-widest uppercase">
          {transcripts.length} {transcripts.length === 1 ? "entry" : "entries"}
        </span>
      </div>

      {/* Transcript entries */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto thin-scroll px-4 py-3 space-y-0"
      >
        {transcripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 select-none">
            <div className="font-mono text-[10px] text-white/15 tracking-[0.2em] uppercase text-center leading-relaxed">
              Audio channel open<br />
              <span className="text-white/10">Speak to begin negotiation</span>
            </div>
            {/* Idle waveform placeholder */}
            <div className="flex items-end gap-px h-6" aria-hidden="true">
              {Array.from({ length: 18 }).map((_, i) => (
                <div
                  key={i}
                  className="w-px bg-white/8"
                  style={{ height: `${4 + Math.sin(i * 0.8) * 3}px` }}
                />
              ))}
            </div>
          </div>
        ) : (
          transcripts.map((t, idx) => {
            const isUser = t.speaker === "user";
            const prevSpeaker = idx > 0 ? transcripts[idx - 1].speaker : null;
            const speakerChanged = prevSpeaker !== t.speaker;

            return (
              <div
                key={t.id}
                className={`${speakerChanged && idx > 0 ? "mt-4" : "mt-1"}`}
              >
                {/* Speaker + timestamp — only shown when speaker changes */}
                {speakerChanged && (
                  <div className={`flex items-center gap-2 mb-1 ${isUser ? "flex-row-reverse" : ""}`}>
                    <span
                      className="font-mono text-[9px] font-bold tracking-[0.15em] uppercase"
                      style={{ color: isUser ? "#27ae60" : "#c8893e" }}
                    >
                      {t.senderName}
                    </span>
                    <span className="font-mono text-[8px] text-white/15">{t.timestamp}</span>
                  </div>
                )}

                {/* Message bubble */}
                <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[82%] px-3 py-2 font-mono text-[12px] leading-relaxed ${
                      isUser
                        ? "text-white/75 bg-white/5 border-r-2"
                        : "text-white/65 bg-[#111] border-l-2"
                    }`}
                    style={{
                      borderColor: isUser ? "#27ae60" : "#c8893e",
                    }}
                  >
                    {t.text}
                  </div>
                </div>

                {/* Timestamp for non-speaker-change messages */}
                {!speakerChanged && (
                  <div className={`flex mt-0.5 ${isUser ? "justify-end" : "justify-start"}`}>
                    <span className="font-mono text-[8px] text-white/10 px-3">{t.timestamp}</span>
                  </div>
                )}
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
