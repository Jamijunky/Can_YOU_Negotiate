"use client";

import { useSessionMessages } from "@livekit/components-react";
import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { ReceivedMessage } from "@livekit/components-core";
import type { TranscriptItem } from "@/lib/types";

const LiveTranscriptFeed = memo(function LiveTranscriptFeed({
  subjectName,
  thinking = false,
}: {
  subjectName: string;
  thinking?: boolean;
}) {
  // Primary: LiveKit's own session messages — captures both user + agent transcripts natively
  const { messages } = useSessionMessages();

  // Secondary: also listen to the agent's data-channel broadcast (fallback / agent-side transcripts)
  const [dcTranscripts, setDcTranscripts] = useState<TranscriptItem[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const seenIds = useRef<Set<string>>(new Set());

  const handleData = useCallback(
    (msg: { payload: Uint8Array }) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(msg.payload));
        if (data.type === "transcript" && data.text) {
          const id = data.id || `dc-${data.speaker}-${data.text.slice(0, 20)}`;
          if (seenIds.current.has(id)) return;
          seenIds.current.add(id);

          const timeStr = new Date().toLocaleTimeString([], {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });

          setDcTranscripts((prev) => {
            // Only skip exact character duplicates within 3s
            const last = prev[prev.length - 1];
            if (
              last &&
              last.speaker === data.speaker &&
              Date.now() - last.finalizedAt < 3000 &&
              data.text.trim() === last.text.trim()
            ) return prev;

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
      } catch { /* ignore */ }
    },
    [subjectName]
  );
  useDataChannel(handleData);

  // Build the displayed list: prefer session messages (native), merge with DC transcripts
  // Session messages give us both user + agent. DC transcripts are the agent's re-broadcast.
  const displayed = useRef<TranscriptItem[]>([]);

  // Merge session messages + DC transcripts, deduplicating by text similarity
  const merged: TranscriptItem[] = [];
  const usedDcIds = new Set<string>();

  // Convert session messages
  (messages as ReceivedMessage[]).forEach((m, i) => {
    const type = (m as { type?: string }).type;
    const message = (m as { message?: string }).message || "";
    if (!message.trim()) return;

    const isUser = type === "userTranscript";
    const timeStr = m.timestamp
      ? new Date(m.timestamp).toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
      : "";

    merged.push({
      id: `session-${i}-${type}`,
      speaker: isUser ? "user" : "agent",
      senderName: isUser ? "You" : subjectName || "Subject",
      text: message,
      timestamp: timeStr,
      isFinal: true,
      finalizedAt: m.timestamp ?? 0,
    });
  });

  // Fill in DC transcripts that aren't already covered by session messages
  dcTranscripts.forEach((dc) => {
    const alreadyCovered = merged.some(
      (s) =>
        s.speaker === dc.speaker &&
        Math.abs(s.finalizedAt - dc.finalizedAt) < 5000 &&
        (s.text.includes(dc.text) || dc.text.includes(s.text) || s.text.trim() === dc.text.trim())
    );
    if (!alreadyCovered) {
      usedDcIds.add(dc.id);
      merged.push(dc);
    }
  });

  // Sort by timestamp
  merged.sort((a, b) => (a.finalizedAt ?? 0) - (b.finalizedAt ?? 0));
  displayed.current = merged;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, dcTranscripts]);

  const items = displayed.current;

  return (
    <div
      className={`flex flex-col h-full bg-[#f4f0e6] transition-opacity duration-500 ${thinking ? "opacity-40" : "opacity-100"}`}
      role="log"
      aria-label="Live conversation"
      aria-live="polite"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b-2 border-[#1e1e1e]/15">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] glow-green" aria-hidden="true" />
          <span className="font-mono text-[10px] font-bold tracking-widest text-[#1e1e1e]/50 uppercase">
            COMMS_LOG // LIVE_TRANSCRIPT
          </span>
        </div>
        <span className="font-mono text-[10px] text-[#1e1e1e]/30 uppercase tracking-widest">
          {items.length > 0 ? `${items.length} exchanges` : "Waiting..."}
        </span>
      </div>

      {/* Entries */}
      <div className="flex-1 overflow-y-auto thin-scroll-light px-5 py-4 space-y-5">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 select-none">
            <p className="font-mono text-xs text-[#1e1e1e]/25 tracking-widest uppercase text-center leading-loose">
              Audio channel open<br />
              <span className="text-[10px] opacity-60">Start speaking to begin</span>
            </p>
          </div>
        ) : (
          items.map((t) => {
            const isUser = t.speaker === "user";
            return (
              <div key={t.id} className="space-y-1">
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
        {/* Thinking indicator — inline at the bottom of the conversation */}
        {thinking && (
          <div className="flex items-center gap-2 pt-2 animate-in fade-in duration-300">
            <span className="font-mono text-[10px] font-bold text-[#d99a4e] uppercase tracking-wider">
              {subjectName}
            </span>
            <span className="font-serif text-[13px] text-[#1e1e1e]/40 italic">
              is thinking...
            </span>
          </div>
        )}
      </div>
    </div>
  );
});

export default LiveTranscriptFeed;
