"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState } from "react";
import type { Relationship } from "@/lib/types";

const INITIAL_RELATIONSHIP: Relationship = {
  rapport: 20,
  trust: 10,
  compliancePressure: 80,
  cooperationLevel: 15,
};

function getBarColor(value: number, inverse: boolean = false): string {
  const v = inverse ? 100 - value : value;
  if (v >= 70) return "#22c55e";
  if (v >= 40) return "#d99a4e";
  return "#dc2626";
}

const RelationshipDisplay = memo(function RelationshipDisplay() {
  const [relationship, setRelationship] = useState<Relationship>(INITIAL_RELATIONSHIP);

  const handleData = useCallback((msg: { payload: Uint8Array }) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === "relationship") {
        setRelationship({
          rapport: data.rapport ?? 20,
          trust: data.trust ?? 10,
          compliancePressure: data.compliancePressure ?? 80,
          cooperationLevel: data.cooperationLevel ?? 15,
        });
      }
    } catch {
      // ignore
    }
  }, []);

  useDataChannel(handleData);

  const metrics = [
    { label: "RAPPORT", value: relationship.rapport, inverse: false },
    { label: "TRUST", value: relationship.trust, inverse: false },
    { label: "RESISTANCE", value: relationship.compliancePressure, inverse: true },
    { label: "COOPERATION", value: relationship.cooperationLevel, inverse: false },
  ];

  return (
    <div className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 p-3 text-left" role="region" aria-label="Relationship status">
      <div className="space-y-2.5">
        {metrics.map((m) => {
          const color = getBarColor(m.value, m.inverse);
          return (
            <div key={m.label} className="flex items-center gap-3">
              <span className="font-mono text-[9px] text-[#f4f0e6]/50 w-24 shrink-0 uppercase tracking-wider">
                {m.label}
              </span>
              <div className="flex-1 h-1.5 bg-[#f4f0e6]/5 overflow-hidden rounded-sm relative">
                <div
                  className="absolute inset-y-0 left-0 transition-all duration-700 ease-out rounded-sm"
                  style={{ width: `${m.value}%`, backgroundColor: color }}
                />
                <div className="absolute inset-y-0 left-[25%] w-px bg-[#f4f0e6]/8" />
                <div className="absolute inset-y-0 left-[50%] w-px bg-[#f4f0e6]/8" />
                <div className="absolute inset-y-0 left-[75%] w-px bg-[#f4f0e6]/8" />
              </div>
              <span className="font-mono text-[10px] text-[#f4f0e6]/40 w-8 text-right shrink-0">
                {m.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
});

export default RelationshipDisplay;
