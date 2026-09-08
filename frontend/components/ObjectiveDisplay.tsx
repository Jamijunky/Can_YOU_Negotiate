"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";

interface ObjectiveData { text: string; strategy: string; }

interface ObjectiveDisplayProps {
  trainingMode: boolean;
}

const ObjectiveDisplay = memo(function ObjectiveDisplay({ trainingMode }: ObjectiveDisplayProps) {
  const [objective, setObjective] = useState<ObjectiveData>({ text: "", strategy: "" });
  const [beliefs, setBeliefs] = useState<string[]>([]);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "objective") {
        setObjective({ text: data.text || "", strategy: data.strategy || "" });
      } else if (data.type === "beliefs" && Array.isArray(data.beliefs)) {
        setBeliefs(data.beliefs.slice(-5));
      }
    } catch { /* ignore */ }
  }, []);

  useDataChannel(handleData);

  // Only render in training mode — not a cheat code during real play
  if (!trainingMode) return null;
  if (!objective.text && beliefs.length === 0) return null;

  return (
    <div className="p-3 border-b-2 border-[#1e1e1e]/15" role="region" aria-label="Subject objective and beliefs">
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        SUBJECT MIND
        <span className="ml-auto font-mono text-[7px] text-[#d99a4e]/40 uppercase tracking-wider">training only</span>
      </div>

      {objective.text && (
        <div className="mb-2">
          <div className="font-mono text-[8px] text-[#1e1e1e]/30 uppercase tracking-wider mb-0.5">Objective</div>
          <p className="font-serif text-[11px] text-[#1e1e1e]/60 leading-snug">{objective.text}</p>
        </div>
      )}

      {objective.strategy && (
        <div className="mb-2">
          <div className="font-mono text-[8px] text-[#1e1e1e]/30 uppercase tracking-wider mb-0.5">Strategy</div>
          <p className="font-serif text-[11px] text-[#1e1e1e]/45 leading-snug italic">{objective.strategy}</p>
        </div>
      )}

      {beliefs.length > 0 && (
        <div>
          <div className="font-mono text-[8px] text-[#1e1e1e]/30 uppercase tracking-wider mb-1">Current Beliefs</div>
          <ul className="space-y-0.5">
            {beliefs.map((b, i) => (
              <li key={i} className="font-serif text-[10px] text-[#1e1e1e]/40 leading-snug flex gap-1">
                <span className="text-[#d99a4e]/50 shrink-0">—</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
});

export default ObjectiveDisplay;
