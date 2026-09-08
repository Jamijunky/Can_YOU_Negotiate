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
    <div className="p-3 border-b border-[#f4f0e6]/8" role="region" aria-label="Escalation stage">
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        ESCALATION_CHAIN
      </div>

      {/* Stage pip track */}
      <div className="flex items-center gap-1 mb-2" aria-hidden="true">
        {STAGES.map((s) => {
          const active = s <= esc.stage;
          const current = s === esc.stage;
          return (
            <div
              key={s}
              className="flex-1 h-1.5 transition-all duration-500"
              style={{
                backgroundColor: active ? info.color : "rgba(244,240,230,0.08)",
                boxShadow: current ? `0 0 6px ${info.color}` : "none",
                opacity: active ? 1 : 0.3,
              }}
            />
          );
        })}
      </div>

      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] font-black tracking-wider uppercase" style={{ color: info.color }}>
          STAGE {esc.stage}: {info.label}
        </span>
        <span className="font-mono text-[9px] text-[#f4f0e6]/30 tabular-nums">TURN {esc.totalTurns}</span>
      </div>
      <p className="font-serif text-[11px] text-[#f4f0e6]/40 mt-0.5 leading-snug">{info.description}</p>
    </div>
  );
});

export default EscalationIndicator;
