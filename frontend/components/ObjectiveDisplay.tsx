"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";

interface ObjectiveData {
  text: string;
  strategy: string;
}

const ObjectiveDisplay = memo(function ObjectiveDisplay() {
  const [objective, setObjective] = useState<ObjectiveData>({ text: "", strategy: "" });
  const [beliefs, setBeliefs] = useState<string[]>([]);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "objective") {
        setObjective({
          text: data.text || "",
          strategy: data.strategy || "",
        });
      } else if (data.type === "beliefs" && Array.isArray(data.beliefs)) {
        setBeliefs(data.beliefs.slice(-6));
      }
    } catch {
      // ignore
    }
  }, []);

  useDataChannel(handleData);

  if (!objective.text && beliefs.length === 0) return null;

  return (
    <div className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 p-3 text-left" role="region" aria-label="Subject objective and beliefs">
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        SUBJECT MIND
      </div>

      {objective.text && (
        <div className="mb-2">
          <div className="font-mono text-[9px] text-[#f4f0e6]/40 uppercase tracking-wider mb-0.5">Objective</div>
          <p className="font-serif text-[11px] text-[#f4f0e6]/80 leading-snug">{objective.text}</p>
        </div>
      )}

      {objective.strategy && (
        <div className="mb-2">
          <div className="font-mono text-[9px] text-[#f4f0e6]/40 uppercase tracking-wider mb-0.5">Strategy</div>
          <p className="font-serif text-[11px] text-[#f4f0e6]/60 leading-snug italic">{objective.strategy}</p>
        </div>
      )}

      {beliefs.length > 0 && (
        <div>
          <div className="font-mono text-[9px] text-[#f4f0e6]/40 uppercase tracking-wider mb-1">Current Beliefs</div>
          <ul className="space-y-0.5">
            {beliefs.map((b, i) => (
              <li key={i} className="font-serif text-[10px] text-[#f4f0e6]/50 leading-snug flex items-start gap-1">
                <span className="text-[#d99a4e] shrink-0" aria-hidden="true">-</span>
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
