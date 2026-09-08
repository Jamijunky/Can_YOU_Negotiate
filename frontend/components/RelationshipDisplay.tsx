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

function getStatus(value: number, inverse: boolean = false): string {
  const v = inverse ? 100 - value : value;
  if (v >= 75) return "HIGH";
  if (v >= 55) return "GOOD";
  if (v >= 35) return "FAIR";
  if (v >= 15) return "LOW";
  return "CRIT";
}

function getDetailText(label: string, value: number): string {
  if (label === "RAPPORT") {
    if (value >= 60) return "Emotional connection is strong";
    if (value >= 35) return "Cautious connection forming";
    if (value >= 15) return "Distant, guarded";
    return "No emotional bond";
  }
  if (label === "TRUST") {
    if (value >= 60) return "Believes the negotiator";
    if (value >= 35) return "Watching for deception";
    if (value >= 15) return "Suspicious of motives";
    return "Thinks they are lying";
  }
  if (label === "RESISTANCE") {
    if (value >= 60) return "Actively pushing back";
    if (value >= 35) return "Reluctant, hesitant";
    if (value >= 15) return "Beginning to yield";
    return "Compliant";
  }
  if (label === "COOPERATION") {
    if (value >= 60) return "Working together";
    if (value >= 35) return "Open to dialogue";
    if (value >= 15) return "Refusing to engage";
    return "Active non-cooperation";
  }
  return "";
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
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-3">
        RELATIONSHIP_DYNAMICS
      </div>
      <div className="space-y-3">
        {metrics.map((m) => {
          const color = getBarColor(m.value, m.inverse);
          const status = getStatus(m.value, m.inverse);
          const detail = getDetailText(m.label, m.value);
          return (
            <div key={m.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] text-[#f4f0e6]/70 uppercase tracking-wider">
                  {m.label}
                </span>
                <span className="font-mono text-[10px] font-bold uppercase" style={{ color }}>
                  {status}
                </span>
              </div>
              <div className="relative h-2 bg-[#f4f0e6]/5 overflow-hidden rounded-sm">
                <div
                  className="absolute inset-y-0 left-0 transition-all duration-700 ease-out rounded-sm"
                  style={{ width: `${m.value}%`, backgroundColor: color, boxShadow: `0 0 8px ${color}40` }}
                />
                {/* Tick marks */}
                <div className="absolute inset-y-0 left-[25%] w-px bg-[#f4f0e6]/10" />
                <div className="absolute inset-y-0 left-[50%] w-px bg-[#f4f0e6]/10" />
                <div className="absolute inset-y-0 left-[75%] w-px bg-[#f4f0e6]/10" />
              </div>
              <div className="font-serif text-[9px] text-[#f4f0e6]/30 mt-0.5 italic">
                {detail}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

export default RelationshipDisplay;
