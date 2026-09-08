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
    { label: "RAPPORT", value: relationship.rapport, inverse: false, subLabel: relationship.rapport < 30 ? "Distant, guarded" : relationship.rapport < 60 ? "Cautious engagement" : "Opening up" },
    { label: "TRUST", value: relationship.trust, inverse: false, subLabel: relationship.trust < 20 ? "Thinks you are lying" : relationship.trust < 50 ? "Skeptical" : "Starting to believe you" },
    { label: "RESISTANCE", value: relationship.compliancePressure, inverse: true, subLabel: relationship.compliancePressure > 70 ? "Actively pushing back" : relationship.compliancePressure > 40 ? "Some resistance" : "Lowering defenses" },
    { label: "COOPERATION", value: relationship.cooperationLevel, inverse: false, subLabel: relationship.cooperationLevel < 20 ? "Refusing to engage" : relationship.cooperationLevel < 50 ? "Minimal compliance" : "Willing to talk" },
  ];

  return (
    <div className="w-full bg-[#1e1e1e] border border-[#f4f0e6]/20 p-3 text-left" role="region" aria-label="Relationship dynamics">
      {/* Panel header — matches ObjectiveDisplay / EmotionalArc style */}
      <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-3 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-[#d99a4e] animate-pulse" aria-hidden="true" />
        RELATIONSHIP_DYNAMICS
      </div>

      <div className="space-y-3">
        {metrics.map((m) => {
          const color = getBarColor(m.value, m.inverse);
          const statusLabel =
            m.value >= 70 ? (m.inverse ? "HIGH" : "HIGH") :
            m.value >= 40 ? "MED" : (m.inverse ? "LOW" : "CRIT");
          return (
            <div key={m.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[9px] text-[#f4f0e6]/60 uppercase tracking-wider">
                  {m.label}
                </span>
                <span
                  className="font-mono text-[8px] font-bold px-1.5 py-px border"
                  style={{ color, borderColor: `${color}60` }}
                >
                  {statusLabel}
                </span>
              </div>
              <div className="h-2 bg-[#f4f0e6]/5 border border-[#f4f0e6]/10 overflow-hidden relative">
                <div
                  className="absolute inset-y-0 left-0 transition-all duration-700 ease-out"
                  style={{
                    width: `${m.value}%`,
                    backgroundColor: color,
                    boxShadow: `0 0 6px ${color}80`,
                  }}
                />
                {/* Quarter tick marks */}
                {[25, 50, 75].map((pct) => (
                  <div key={pct} className="absolute inset-y-0 w-px bg-[#f4f0e6]/10" style={{ left: `${pct}%` }} />
                ))}
              </div>
              {/* Sub-label row */}
              <p className="font-mono text-[8px] text-[#f4f0e6]/25 mt-0.5 italic">
                {m.subLabel}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
});

export default RelationshipDisplay;
