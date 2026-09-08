"use client";

import { useDataChannel } from "@livekit/components-react";
import { memo, useCallback, useState, useRef, useEffect } from "react";
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

// Human-readable reading of the current state — shown instead of "CRIT/MED/HIGH"
function reading(label: string, value: number, inverse: boolean): string {
  const v = inverse ? 100 - value : value;
  if (label === "RAPPORT") {
    if (v >= 65) return "opening up";
    if (v >= 35) return "cautious";
    return "closed off";
  }
  if (label === "TRUST") {
    if (v >= 65) return "starting to believe you";
    if (v >= 35) return "skeptical";
    return "doesn't trust you";
  }
  if (label === "RESISTANCE") {
    if (v >= 65) return "low — listening";
    if (v >= 35) return "some pushback";
    return "actively resisting";
  }
  if (label === "COOPERATION") {
    if (v >= 65) return "willing to work with you";
    if (v >= 35) return "minimal";
    return "refusing";
  }
  return "";
}

function useFlash(value: number): boolean {
  const [flashing, setFlashing] = useState(false);
  const prev = useRef(value);

  useEffect(() => {
    if (prev.current !== value) {
      prev.current = value;
      setFlashing(true);
      const t = setTimeout(() => setFlashing(false), 600);
      return () => clearTimeout(t);
    }
  }, [value]);

  return flashing;
}

function MetricRow({
  label,
  value,
  inverse,
}: {
  label: string;
  value: number;
  inverse: boolean;
}) {
  const color   = barColor(value, inverse);
  const text    = reading(label, value, inverse);
  const flashing = useFlash(value);

  return (
    <div
      className="transition-all duration-300"
      style={{
        backgroundColor: flashing ? `${color}12` : "transparent",
      }}
    >
      <div className="flex items-center justify-between mb-0.5">
        <span className="font-mono text-[9px] text-[#1e1e1e]/40 uppercase tracking-wider">{label}</span>
        <span
          className="font-serif text-[9px] italic transition-colors duration-300"
          style={{ color: `${color}cc` }}
        >
          {text}
        </span>
      </div>
      <div className="h-1.5 bg-[#1e1e1e]/8 border border-[#1e1e1e]/8 relative overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 transition-all duration-700 ease-out"
          style={{
            width: `${value}%`,
            backgroundColor: color,
            boxShadow: flashing ? `0 0 8px ${color}` : `0 0 3px ${color}50`,
          }}
        />
      </div>
    </div>
  );
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

  return (
    <div className="p-3 border-b-2 border-[#1e1e1e]/15" role="region" aria-label="Relationship dynamics">
      <div className="font-mono text-[9px] font-bold tracking-[0.18em] text-[#1e1e1e]/30 uppercase mb-2.5">
        How they're responding
      </div>
      <div className="space-y-2.5">
        <MetricRow label="RAPPORT"     value={rel.rapport}            inverse={false} />
        <MetricRow label="TRUST"       value={rel.trust}              inverse={false} />
        <MetricRow label="RESISTANCE"  value={rel.compliancePressure} inverse={true}  />
        <MetricRow label="COOPERATION" value={rel.cooperationLevel}   inverse={false} />
      </div>
    </div>
  );
});

export default RelationshipDisplay;
