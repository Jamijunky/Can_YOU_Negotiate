"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";
import { ESCALATION_STAGE_LABELS, type EscalationStage } from "@/lib/types";

interface EscalationData {
  stage: EscalationStage;
  turnsInStage: number;
  totalTurns: number;
}

const STAGE_KEYS = Object.keys(ESCALATION_STAGE_LABELS) as unknown as EscalationStage[];

const EscalationIndicator = memo(function EscalationIndicator() {
  const [escalation, setEscalation] = useState<EscalationData>({
    stage: 0,
    turnsInStage: 0,
    totalTurns: 0,
  });

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "escalation") {
        setEscalation({
          stage: data.stage ?? 0,
          turnsInStage: data.turnsInStage ?? 0,
          totalTurns: data.totalTurns ?? 0,
        });
      }
    } catch {
      // ignore
    }
  }, []);

  useDataChannel(handleData);

  const stageInfo = ESCALATION_STAGE_LABELS[escalation.stage];

  return (
    <div className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 p-3 text-left" role="region" aria-label="Escalation stage">
      {/* Header */}
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        ESCALATION_CHAIN
      </div>

      {/* Stage pip track */}
      <div className="flex items-center gap-1.5 mb-2.5" aria-hidden="true">
        {STAGE_KEYS.map((s) => {
          const isActive = s <= escalation.stage;
          const isCurrent = s === escalation.stage;
          return (
            <div key={s} className="flex-1 flex flex-col items-center gap-1">
              <div
                className="w-full h-2 transition-all duration-500"
                style={{
                  backgroundColor: isActive ? stageInfo.color : "rgba(244,240,230,0.08)",
                  boxShadow: isCurrent ? `0 0 6px ${stageInfo.color}` : "none",
                  opacity: isActive ? 1 : 0.35,
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Current stage label + turn counter */}
      <div className="flex items-baseline justify-between mb-1">
        <span
          className="font-mono text-xs font-black tracking-wider"
          style={{ color: stageInfo.color }}
        >
          STAGE {escalation.stage}: {stageInfo.label}
        </span>
        <span className="font-mono text-[9px] text-[#f4f0e6]/40 tabular-nums">
          TURN {escalation.totalTurns}
        </span>
      </div>

      {/* Description */}
      <p className="font-serif text-[11px] text-[#f4f0e6]/50 leading-snug">
        {stageInfo.description}
      </p>
    </div>
  );
});

export default EscalationIndicator;
