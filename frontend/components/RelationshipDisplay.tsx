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
  if (v >= 65) return "#16a34a";
  if (v >= 35) return "#d99a4e";
  return "#dc2626";
}

function statusLabel(value: number, inverse: boolean): string {
  const v = inverse ? 100 - value : value;
  if (v >= 65) return "HIGH";
  if (v >= 35) return "MED";
  return "CRIT";
}

const RelationshipDisplay = memo(function RelationshipDisplay() {
  const [rel, setRel] = useState<Relationship>(INITIAL);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "relationship") {
        setRel({
          rapport:            data.rapport            ?? 20,
          trust:              data.trust              ?? 10,
          compliancePressure: data.compliancePressure ?? 80,
          cooperationLevel:   data.cooperationLevel   ?? 15,
        });
      }
    } catch { /* ignore */ }
  }, []);

  useDataChannel(handleData);

  const metrics = [
    { label: "RAPPORT",     value: rel.rapport,            inverse: false },
    { label: "TRUST",       value: rel.trust,              inverse: false },
    { label: "RESISTANCE",  value: rel.compliancePressure, inverse: true  },
    { label: "COOPERATION", value: rel.cooperationLevel,   inverse: false },
  ];

  return (
    <div className="p-3 border-b-2 border-[#1e1e1e]/15" role="region" aria-label="Relationship dynamics">
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#d99a4e] uppercase mb-2.5 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        RELATIONSHIP_DYNAMICS
      </div>
      <div className="space-y-2">
        {metrics.map((m) => {
          const color = barColor(m.value, m.inverse);
          const label = statusLabel(m.value, m.inverse);
          return (
            <div key={m.label}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="font-mono text-[9px] text-[#1e1e1e]/50 uppercase tracking-wider">{m.label}</span>
                <span className="font-mono text-[8px] font-bold tracking-wider" style={{ color }}>{label}</span>
              </div>
              <div className="h-1.5 bg-[#1e1e1e]/10 border border-[#1e1e1e]/10 relative overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 transition-all duration-700 ease-out"
                  style={{ width: `${m.value}%`, backgroundColor: color, boxShadow: `0 0 4px ${color}60` }}
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
