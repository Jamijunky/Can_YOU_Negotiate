"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";
import type { Relationship } from "@/lib/types";

const INITIAL: Relationship = {
  rapport: 20,
  trust: 10,
  compliancePressure: 80,
  cooperationLevel: 15,
};

function barColor(value: number, inverse: boolean): string {
  const v = inverse ? 100 - value : value;
  if (v >= 65) return "#27ae60";
  if (v >= 35) return "#c8893e";
  return "#c0392b";
}

const RelationshipDisplay = memo(function RelationshipDisplay() {
  const [rel, setRel] = useState<Relationship>(INITIAL);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "relationship") {
        setRel({
          rapport:           data.rapport           ?? 20,
          trust:             data.trust             ?? 10,
          compliancePressure: data.compliancePressure ?? 80,
          cooperationLevel:  data.cooperationLevel  ?? 15,
        });
      }
    } catch { /* ignore */ }
  }, []);

  useDataChannel(handleData);

  const metrics = [
    { label: "Rapport",     value: rel.rapport,           inverse: false },
    { label: "Trust",       value: rel.trust,             inverse: false },
    { label: "Resistance",  value: rel.compliancePressure, inverse: true  },
    { label: "Cooperation", value: rel.cooperationLevel,  inverse: false },
  ];

  return (
    <div className="border-b border-white/8 p-4" role="region" aria-label="Relationship dynamics">
      <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase mb-3">
        Subject State
      </div>
      <div className="space-y-2.5">
        {metrics.map((m) => {
          const color = barColor(m.value, m.inverse);
          return (
            <div key={m.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] text-white/30 uppercase tracking-wider">{m.label}</span>
                <span className="font-mono text-[9px] tabular-nums" style={{ color, opacity: 0.7 }}>
                  {m.value}
                </span>
              </div>
              <div className="h-px bg-white/8 relative">
                <div
                  className="absolute inset-y-0 left-0 h-full transition-all duration-700"
                  style={{ width: `${m.value}%`, backgroundColor: color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

export default RelationshipDisplay;
