"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";
import { ESCALATION_STAGE_LABELS, type EscalationStage } from "@/lib/types";

interface EscalationData {
  stage: EscalationStage;
  turnsInStage: number;
  totalTurns: number;
}

const STAGES = Object.keys(ESCALATION_STAGE_LABELS) as unknown as EscalationStage[];

const EscalationIndicator = memo(function EscalationIndicator() {
  const [esc, setEsc] = useState<EscalationData>({ stage: 0, turnsInStage: 0, totalTurns: 0 });

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "escalation") {
        setEsc({ stage: data.stage ?? 0, turnsInStage: data.turnsInStage ?? 0, totalTurns: data.totalTurns ?? 0 });
      }
    } catch { /* ignore */ }
  }, []);

  useDataChannel(handleData);

  const info = ESCALATION_STAGE_LABELS[esc.stage];

  return (
    <div className="border-b border-white/8 p-4" role="region" aria-label="Escalation stage">
      <div className="flex items-center justify-between mb-3">
        <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase">Escalation</div>
        <div className="font-mono text-[9px] text-white/15 tabular-nums">T{esc.totalTurns}</div>
      </div>

      {/* Pip track */}
      <div className="flex gap-1 mb-2" aria-hidden="true">
        {STAGES.map((s) => {
          const active = s <= esc.stage;
          const current = s === esc.stage;
          return (
            <div
              key={s}
              className="flex-1 h-1 transition-all duration-500"
              style={{
                backgroundColor: active ? info.color : "rgba(255,255,255,0.06)",
                boxShadow: current ? `0 0 4px ${info.color}` : "none",
              }}
            />
          );
        })}
      </div>

      {/* Label + description */}
      <div className="font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: info.color }}>
        {info.label}
      </div>
      <p className="font-mono text-[9px] text-white/25 mt-0.5 leading-snug">{info.description}</p>
    </div>
  );
});

export default EscalationIndicator;
