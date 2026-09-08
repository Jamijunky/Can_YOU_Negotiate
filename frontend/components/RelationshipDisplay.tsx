"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useEffect } from "react";
import type { Relationship } from "@/lib/types";

const INITIAL_RELATIONSHIP: Relationship = {
  rapport: 20,
  trust: 10,
  compliancePressure: 80,
  cooperationLevel: 15,
};

function getBarColor(value: number, inverse: boolean = false): string {
  const v = inverse ? 100 - value : value;
  if (v >= 70) return "bg-[#22c55e]";
  if (v >= 40) return "bg-[#d99a4e]";
  return "bg-[#dc2626]";
}

function getLabel(value: number, inverse: boolean = false): string {
  const v = inverse ? 100 - value : value;
  if (v >= 70) return "STRONG";
  if (v >= 40) return "MODERATE";
  return "WEAK";
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
    } catch (e) {
      // ignore parse errors
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
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        RELATIONSHIP_DYNAMICS
      </div>
      <div className="space-y-1.5">
        {metrics.map((m) => (
          <div key={m.label} className="flex items-center gap-2">
            <span className="font-mono text-[9px] text-[#f4f0e6]/60 w-20 shrink-0 uppercase">
              {m.label}
            </span>
            <div className="flex-1 h-1.5 bg-[#f4f0e6]/10 overflow-hidden" role="progressbar" aria-valuenow={m.value} aria-valuemin={0} aria-valuemax={100}>
              <div
                className={`h-full transition-all duration-500 ${getBarColor(m.value, m.inverse)}`}
                style={{ width: `${m.value}%` }}
              />
            </div>
            <span className="font-mono text-[9px] text-[#f4f0e6]/40 w-14 text-right">
              {getLabel(m.value, m.inverse)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});

export default RelationshipDisplay;
