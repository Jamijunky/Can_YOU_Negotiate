"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect, useRef } from "react";
import type { TranscriptItem } from "@/lib/types";

interface AwarenessState {
  // What the subject has said that matters — extracted keywords/phrases
  revealed: string[];
  // What the subject has explicitly refused or pushed back on
  refused: string[];
  // Topics you've raised but subject hasn't responded to meaningfully
  unresolved: string[];
  // Last thing the subject said — the most recent live context
  lastSubjectLine: string;
  // Last thing you said
  lastYourLine: string;
  // Turn count
  turns: number;
}

// Very lightweight keyword extraction — looks for emotionally charged fragments
// in what the subject says. No AI, just pattern matching on the live transcript.
function extractSignals(transcripts: TranscriptItem[]): AwarenessState {
  const agentLines = transcripts.filter((t) => t.speaker === "agent");
  const userLines  = transcripts.filter((t) => t.speaker === "user");

  const revealed: string[] = [];
  const refused: string[]  = [];

  // Scan subject lines for reveals and refusals
  for (const t of agentLines) {
    const text = t.text.toLowerCase();

    // Refusal patterns
    if (
      text.includes("no") ||
      text.includes("not going to") ||
      text.includes("never") ||
      text.includes("don't trust") ||
      text.includes("won't") ||
      text.includes("stay back") ||
      text.includes("leave me alone") ||
      text.includes("i said")
    ) {
      // Extract a short fragment as the refusal
      const sentence = t.text.split(/[.!?]/)[0].trim();
      if (sentence.length > 8 && sentence.length < 80 && !refused.includes(sentence)) {
        refused.push(sentence);
      }
    }

    // Reveal patterns — personal/emotional disclosure
    if (
      text.includes("because") ||
      text.includes("i just want") ||
      text.includes("they") ||
      text.includes("she") ||
      text.includes("he ") ||
      text.includes("my ") ||
      text.includes("i need") ||
      text.includes("i'm afraid") ||
      text.includes("scared") ||
      text.includes("please") ||
      text.includes("you don't understand") ||
      text.includes("nobody")
    ) {
      const sentence = t.text.split(/[.!?]/)[0].trim();
      if (sentence.length > 12 && sentence.length < 100 && !revealed.includes(sentence)) {
        revealed.push(sentence);
      }
    }
  }

  // Unresolved: things the user raised in the last 3 turns that the subject hasn't acknowledged
  const recentUserLines = userLines.slice(-3);
  const unresolved: string[] = [];
  for (const ul of recentUserLines) {
    const text = ul.text.toLowerCase();
    const agentAfter = agentLines.filter((a) => a.finalizedAt > ul.finalizedAt);
    if (agentAfter.length === 0) {
      // Subject hasn't responded yet
      const fragment = ul.text.split(/[.!?]/)[0].trim();
      if (fragment.length > 6) unresolved.push(fragment);
    }
  }

  return {
    revealed:        revealed.slice(-3),   // last 3 reveals
    refused:         refused.slice(-2),    // last 2 refusals
    unresolved:      unresolved.slice(-2),
    lastSubjectLine: agentLines.length > 0 ? agentLines[agentLines.length - 1].text : "",
    lastYourLine:    userLines.length  > 0 ? userLines[userLines.length - 1].text    : "",
    turns:           agentLines.length,
  };
}

interface ConversationAwarenessProps {
  subjectName: string;
  intel: string; // initial briefing — shown only until conversation has data
}

const ConversationAwareness = memo(function ConversationAwareness({
  subjectName,
  intel,
}: ConversationAwarenessProps) {
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const seenIds = useRef<Set<string>>(new Set());

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "transcript" && data.text) {
        const id = data.id || `${data.speaker}-${data.text.slice(0, 20)}`;
        if (seenIds.current.has(id)) return;
        seenIds.current.add(id);
        setTranscripts((prev) => [
          ...prev,
          {
            id,
            speaker: data.speaker as "user" | "agent",
            senderName: data.speaker === "user" ? "You" : subjectName,
            text: data.text,
            timestamp: "",
            isFinal: true,
            finalizedAt: Date.now(),
          },
        ]);
      }
    } catch { /* ignore */ }
  }, [subjectName]);

  useDataChannel(handleData);

  const awareness = extractSignals(transcripts);
  const hasConversation = transcripts.length > 0;

  return (
    <div className="flex flex-col border-b-2 border-[#1e1e1e]/15">

      {/* ── Situation block — shows pre-call intel until conversation starts ── */}
      <div className="p-3 border-b border-[#1e1e1e]/10">
        <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#dc2626] uppercase mb-1.5 flex items-center gap-1.5">
          <span className="w-1 h-1 bg-[#dc2626] shrink-0" aria-hidden="true" />
          SITUATION
        </div>
        <p className="font-serif text-[12px] text-[#1e1e1e]/65 leading-relaxed">{intel}</p>
      </div>

      {/* ── Live conversational signals — only once conversation has data ── */}
      {hasConversation && (
        <div className="p-3 space-y-3">

          {/* What they've let slip */}
          {awareness.revealed.length > 0 && (
            <div>
              <div className="font-mono text-[8px] text-[#1e1e1e]/35 uppercase tracking-[0.15em] mb-1.5">
                They've let slip
              </div>
              <ul className="space-y-1">
                {awareness.revealed.map((r, i) => (
                  <li key={i} className="font-serif text-[10px] text-[#1e1e1e]/55 leading-snug flex gap-1.5 animate-in fade-in duration-500">
                    <span className="text-[#d99a4e]/50 shrink-0 mt-px">›</span>
                    <span className="line-clamp-2">{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* What they're pushing back on */}
          {awareness.refused.length > 0 && (
            <div>
              <div className="font-mono text-[8px] text-[#dc2626]/50 uppercase tracking-[0.15em] mb-1.5">
                Pushing back on
              </div>
              <ul className="space-y-1">
                {awareness.refused.map((r, i) => (
                  <li key={i} className="font-serif text-[10px] text-[#dc2626]/50 leading-snug flex gap-1.5 animate-in fade-in duration-500">
                    <span className="shrink-0 mt-px">×</span>
                    <span className="line-clamp-2">{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Turn counter — a quiet signal of how long this has been going */}
          <div className="font-mono text-[8px] text-[#1e1e1e]/20 tabular-nums">
            {awareness.turns} {awareness.turns === 1 ? "exchange" : "exchanges"}
          </div>
        </div>
      )}
    </div>
  );
});

export default ConversationAwareness;
