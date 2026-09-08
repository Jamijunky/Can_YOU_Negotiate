"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";
import { ESCALATION_STAGE_LABELS, type EscalationStage } from "@/lib/types";

interface EscalationData {
  stage: EscalationStage;
  turnsInStage: number;
  totalTurns: number;
}

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
    } catch (e) {
      // ignore
    }
  }, []);

  useDataChannel(handleData);

  const stageInfo = ESCALATION_STAGE_LABELS[escalation.stage];

  return (
    <div className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 p-3 text-left" role="region" aria-label="Escalation stage">
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2">
        ESCALATION_CHAIN
      </div>

      {/* Stage dots */}
      <div className="flex items-center gap-1 mb-2">
        {(Object.keys(ESCALATION_STAGE_LABELS) as unknown as EscalationStage[]).map((s) => (
          <div
            key={s}
            className="flex-1 h-1.5 rounded-full transition-all duration-500"
            style={{
              backgroundColor: s <= escalation.stage ? stageInfo.color : "rgba(244,240,230,0.1)",
              opacity: s <= escalation.stage ? 1 : 0.3,
            }}
          />
        ))}
      </div>

      {/* Current stage label */}
      <div className="flex items-center justify-between">
        <span
          className="font-mono text-xs font-black tracking-wider"
          style={{ color: stageInfo.color }}
        >
          STAGE {escalation.stage}: {stageInfo.label}
        </span>
        <span className="font-mono text-[9px] text-[#f4f0e6]/40">
          TURN {escalation.totalTurns}
        </span>
      </div>

      {/* Description */}
      <p className="font-serif text-[11px] text-[#f4f0e6]/50 mt-1 leading-snug">
        {stageInfo.description}
      </p>
    </div>
  );
});

export default EscalationIndicator;
