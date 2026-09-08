"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";

interface ObjectiveData { text: string; strategy: string; }

const ObjectiveDisplay = memo(function ObjectiveDisplay() {
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

  if (!objective.text && beliefs.length === 0) return null;

  return (
    <div className="border-b border-white/8 p-4" role="region" aria-label="Subject objective and beliefs">
      <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase mb-3">
        Subject Mind
      </div>

      {objective.text && (
        <div className="mb-2.5">
          <div className="font-mono text-[8px] text-white/20 uppercase tracking-wider mb-1">Objective</div>
          <p className="font-mono text-[10px] text-white/45 leading-snug">{objective.text}</p>
        </div>
      )}

      {objective.strategy && (
        <div className="mb-2.5">
          <div className="font-mono text-[8px] text-white/20 uppercase tracking-wider mb-1">Strategy</div>
          <p className="font-mono text-[10px] text-white/30 leading-snug">{objective.strategy}</p>
        </div>
      )}

      {beliefs.length > 0 && (
        <div>
          <div className="font-mono text-[8px] text-white/20 uppercase tracking-wider mb-1.5">Current Beliefs</div>
          <ul className="space-y-1">
            {beliefs.map((b, i) => (
              <li key={i} className="font-mono text-[9px] text-white/25 leading-snug flex gap-1.5">
                <span className="text-white/15 shrink-0">—</span>
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
