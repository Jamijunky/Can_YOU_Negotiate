"use client";

import {
  LiveKitRoom,
  RoomAudioRenderer,
} from "@livekit/components-react";
import React, { useCallback, useState, useEffect, useMemo } from "react";
import "@livekit/components-styles";

import ParsedReport from "@/components/ParsedReport";
import MissionStatus from "@/components/MissionStatus";
import IntelDisplay from "@/components/IntelDisplay";
import LiveTranscriptFeed from "@/components/LiveTranscriptFeed";
import SimulationUI from "@/components/SimulationUI";
import Watchdog from "@/components/Watchdog";
import RelationshipDisplay from "@/components/RelationshipDisplay";
import EscalationIndicator from "@/components/EscalationIndicator";
import EmotionalArc from "@/components/EmotionalArc";
import CoachingHints from "@/components/CoachingHints";
import ObjectiveDisplay from "@/components/ObjectiveDisplay";
import { LiveKitErrorBoundary } from "@/components/LiveKitErrorBoundary";
import { ToastProvider, useToast } from "@/components/Toast";
import { DEFAULT_SCENARIOS, PERSONA_LABELS, getDefaultName } from "@/lib/scenarios";
import type { PersonaKey, Difficulty, ScenarioData, Scenario } from "@/lib/types";
import { BACKEND_URL, CUSTOM_PERSONA_DEBOUNCE_MS } from "@/lib/constants";

// ── Personality bar component (used in dossier preview) ─────────────
function PersonalityBar({ label, value, color = "#c8893e" }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[9px] tracking-widest opacity-40 uppercase w-20 shrink-0">{label}</span>
      <div className="flex-1 h-px bg-white/10 relative">
        <div
          className="absolute inset-y-0 left-0 h-full"
          style={{ width: `${Math.round(value * 100)}%`, backgroundColor: color, opacity: 0.8 }}
        />
      </div>
      <span className="font-mono text-[9px] opacity-30 w-6 text-right">{Math.round(value * 10)}</span>
    </div>
  );
}

// ── Dossier panel for the selected scenario ──────────────────────────
function DossierPanel({
  scenario,
  isGenerating,
  intel,
}: {
  scenario: Scenario | null;
  isGenerating: boolean;
  intel: string;
}) {
  if (!scenario) return (
    <div className="flex-1 border border-white/8 bg-[#0f0f0f] p-6 flex items-center justify-center">
      <span className="font-mono text-[11px] text-white/20 tracking-widest animate-pulse">LOADING DOSSIER...</span>
    </div>
  );

  const p = scenario.personality;
  const neuroticism = p?.neuroticism ?? 0.5;
  const agreeableness = p?.agreeableness ?? 0.5;

  return (
    <div className="flex-1 border border-white/8 bg-[#0f0f0f] flex flex-col overflow-hidden">
      {/* Dossier header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/8 bg-[#0a0a0a]">
        <span className="font-mono text-[9px] tracking-[0.2em] opacity-30 uppercase">INCIDENT FILE</span>
        <span
          className="font-mono text-[9px] tracking-[0.2em] uppercase"
          style={{
            color: neuroticism > 0.7 ? "#c0392b" : neuroticism > 0.4 ? "#c8893e" : "#27ae60",
          }}
        >
          THREAT LEVEL: {neuroticism > 0.7 ? "HIGH" : neuroticism > 0.4 ? "MODERATE" : "LOW"}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto thin-scroll p-4 space-y-4">
        {/* Subject ID */}
        <div>
          <div className="font-mono text-[9px] tracking-[0.15em] opacity-30 uppercase mb-1">Subject</div>
          <div className="font-mono text-lg font-bold text-white/90 tracking-wide uppercase">
            {scenario.name}
            <span className="ml-2 font-mono text-[10px] text-white/20 normal-case tracking-wider">
              · {scenario.gender}
            </span>
          </div>
        </div>

        {/* Intel */}
        <div>
          <div className="font-mono text-[9px] tracking-[0.15em] opacity-30 uppercase mb-1.5">Situation Report</div>
          <p
            className={`font-mono text-[11px] text-white/60 leading-relaxed transition-opacity duration-300 ${
              isGenerating ? "opacity-30 animate-pulse" : ""
            }`}
          >
            {intel}
          </p>
        </div>

        {/* Opening line */}
        {scenario.openingLine && (
          <div className="border-l-2 border-[#c0392b]/50 pl-3">
            <div className="font-mono text-[9px] tracking-[0.15em] text-[#c0392b]/50 uppercase mb-1">First words</div>
            <p className="font-mono text-[11px] text-white/50 italic leading-relaxed">
              &ldquo;{scenario.openingLine}&rdquo;
            </p>
          </div>
        )}

        {/* Personality breakdown */}
        {p && (
          <div>
            <div className="font-mono text-[9px] tracking-[0.15em] opacity-30 uppercase mb-2">Psychological Profile</div>
            <div className="space-y-1.5">
              <PersonalityBar label="Volatility" value={p.neuroticism} color="#c0392b" />
              <PersonalityBar label="Hostility" value={1 - p.agreeableness} color="#c8893e" />
              <PersonalityBar label="Openness" value={p.openness} color="#27ae60" />
              <PersonalityBar label="Impulsive" value={1 - p.conscientiousness} color="#c8893e" />
            </div>
          </div>
        )}

        {/* Primary goal */}
        {scenario.primary_goal && (
          <div>
            <div className="font-mono text-[9px] tracking-[0.15em] opacity-30 uppercase mb-1">What they want</div>
            <p className="font-mono text-[11px] text-white/50 leading-relaxed">{scenario.primary_goal}</p>
          </div>
        )}

        {/* Non-negotiables */}
        {scenario.non_negotiables && scenario.non_negotiables.length > 0 && (
          <div>
            <div className="font-mono text-[9px] tracking-[0.15em] text-[#c0392b]/60 uppercase mb-1.5">Will not compromise on</div>
            <ul className="space-y-1">
              {scenario.non_negotiables.map((item, i) => (
                <li key={i} className="font-mono text-[10px] text-[#c0392b]/50 flex gap-2">
                  <span className="opacity-40 shrink-0">×</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Fears — partially redacted */}
        {scenario.fears && scenario.fears.length > 0 && (
          <div>
            <div className="font-mono text-[9px] tracking-[0.15em] opacity-30 uppercase mb-1.5">Known fears</div>
            <ul className="space-y-1">
              {scenario.fears.slice(0, 2).map((fear, i) => (
                <li key={i} className="font-mono text-[10px] text-white/30 flex gap-2">
                  <span className="opacity-40 shrink-0">—</span>
                  <span>{fear}</span>
                </li>
              ))}
              {scenario.fears.length > 2 && (
                <li className="font-mono text-[10px] text-white/15 flex gap-2">
                  <span className="opacity-40 shrink-0">—</span>
                  <span className="bg-white/10 text-transparent select-none px-8">REDACTED</span>
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────
function HomeContent() {
  const [token, setToken] = useState<string | null>(null);
  const [persona, setPersona] = useState<PersonaKey>("robber");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const [customName, setCustomName] = useState("Alex");
  const [customAge, setCustomAge] = useState("35");
  const [customProfession, setCustomProfession] = useState("Accountant");
  const [customMotive, setCustomMotive] = useState(
    "Caught embezzling funds and is holding the boss hostage."
  );

  const [isConnecting, setIsConnecting] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [report, setReport] = useState<string | null>(null);
  const [trainingMode, setTrainingMode] = useState(false);
  const [scenarioData, setScenarioData] = useState<ScenarioData>(DEFAULT_SCENARIOS.robber);
  const [isGeneratingIntel, setIsGeneratingIntel] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    fetch(BACKEND_URL, { method: "GET" }).catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    setIsGeneratingIntel(true);
    setScenarioData(null as unknown as ScenarioData);
    const generate = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        const scenarioRes = await fetch("/api/scenario", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ persona, difficulty, customMotive }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        const scenarioJson = await scenarioRes.json();
        if (active && scenarioRes.ok && scenarioJson.intel) {
          setScenarioData(scenarioJson);
        } else if (active) {
          setScenarioData(DEFAULT_SCENARIOS[persona] || DEFAULT_SCENARIOS.robber);
        }
      } catch {
        if (active) setScenarioData(DEFAULT_SCENARIOS[persona] || DEFAULT_SCENARIOS.robber);
      } finally {
        if (active) setIsGeneratingIntel(false);
      }
    };
    const timer = setTimeout(generate, persona === "custom" ? CUSTOM_PERSONA_DEBOUNCE_MS : 0);
    return () => { active = false; clearTimeout(timer); };
  }, [persona, difficulty, refreshTrigger]);

  useEffect(() => {
    if (persona !== "custom") return;
    const timer = setTimeout(() => setRefreshTrigger((t) => t + 1), CUSTOM_PERSONA_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [customMotive, persona]);

  const connect = useCallback(async () => {
    if (isConnecting || token) return;
    try {
      setIsConnecting(true);
      const finalScenarioData = scenarioData || DEFAULT_SCENARIOS[persona] || DEFAULT_SCENARIOS.robber;
      const roomName = `english-${persona}-${Math.floor(Math.random() * 10000)}`;
      const metaObj: Record<string, unknown> = { difficulty, dynamicScenario: true, trainingMode, ...finalScenarioData };
      if (persona === "custom") {
        metaObj.age = customAge;
        metaObj.profession = customProfession;
        metaObj.motive = customMotive;
      }
      const metadataStr = encodeURIComponent(JSON.stringify(metaObj));
      const res = await fetch(`/api/token?room=${roomName}&metadata=${metadataStr}`);
      const data = await res.json();
      if (res.ok && data.token) {
        setToken(data.token);
      } else {
        addToast("Failed to connect: " + (data.error || "Unknown error"), "error");
      }
    } catch (e: unknown) {
      addToast("Connection error: " + (e instanceof Error ? e.message : "Unknown error"), "error");
    } finally {
      setIsConnecting(false);
    }
  }, [isConnecting, token, persona, difficulty, trainingMode, customAge, customProfession, customMotive, scenarioData, addToast]);

  const [tacticalHold, setTacticalHold] = useState(false);
  const disconnect = useCallback(() => { setToken(null); setTacticalHold(false); }, []);

  const currentName = useMemo(() => {
    if (isGeneratingIntel) return "...";
    if (scenarioData?.name) return scenarioData.name.toUpperCase();
    return getDefaultName(persona);
  }, [isGeneratingIntel, scenarioData, persona]);

  const currentIntel = isGeneratingIntel
    ? "Retrieving situation report..."
    : scenarioData?.intel || "No intel available.";

  const selectedScenario: Scenario | null = scenarioData || DEFAULT_SCENARIOS[persona] || null;

  // ── DEBRIEF VIEW ──────────────────────────────────────────────────
  if (report) {
    return (
      <main className="min-h-screen bg-[#0d0d0d] flex flex-col items-center justify-start py-12 px-4 overflow-x-hidden">
        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="font-mono text-[9px] tracking-[0.2em] text-white/25 uppercase">
              POST-ACTION DEBRIEF // CLASSIFIED
            </div>
            <div className="font-mono text-[9px] tracking-[0.2em] text-[#c8893e]/60 uppercase">
              {new Date().toLocaleDateString("en-US", { year: "numeric", month: "short", day: "2-digit" }).toUpperCase()}
            </div>
          </div>

          <ParsedReport text={report} />

          <div className="mt-8 flex flex-wrap gap-3 border-t border-white/8 pt-6">
            <button
              onClick={() => { setReport(null); setRefreshTrigger((r) => r + 1); }}
              className="font-mono text-xs font-bold tracking-widest uppercase px-6 py-3 bg-white/5 border border-white/15 text-white/60 hover:bg-white/10 hover:text-white/90 transition-colors"
            >
              New Subject
            </button>
            <button
              onClick={() => setReport(null)}
              className="font-mono text-xs font-bold tracking-widest uppercase px-6 py-3 bg-white/5 border border-white/15 text-white/60 hover:bg-white/10 hover:text-white/90 transition-colors"
            >
              Same Subject
            </button>
            <button
              onClick={() => { setReport(null); setPersona("robber"); setDifficulty("medium"); setRefreshTrigger((r) => r + 1); }}
              className="font-mono text-xs font-bold tracking-widest uppercase px-6 py-3 bg-white/5 border border-white/15 text-white/60 hover:bg-white/10 hover:text-white/90 transition-colors"
            >
              Home
            </button>
          </div>
        </div>
      </main>
    );
  }

  // ── ACTIVE SESSION VIEW ───────────────────────────────────────────
  if (token) {
    return (
      <main className="min-h-screen bg-[#0d0d0d] flex flex-col overflow-hidden">
        {/* Top status bar */}
        <div className="shrink-0 flex items-center justify-between px-4 py-1.5 border-b border-white/8 bg-[#0a0a0a]">
          <div className="flex items-center gap-3">
            <span
              className="w-2 h-2 rounded-full bg-[#c0392b] shrink-0"
              style={{ animation: "pulse-red 1.4s ease-in-out infinite" }}
              aria-hidden="true"
            />
            <span className="font-mono text-[9px] tracking-[0.2em] text-white/30 uppercase">Live Negotiation</span>
          </div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-[#c8893e] uppercase">
            Subject: {currentName}
          </div>
          <div className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase">
            {new Date().toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>

        {/* Session body */}
        <div className="flex-1 flex overflow-hidden">
          <LiveKitRoom
            serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
            token={token}
            connect={!!token}
            onDisconnected={disconnect}
            audio={true}
            video={false}
            className="flex-1 flex overflow-hidden"
          >
            {/* ── LEFT COLUMN: intel + gauges ── */}
            <div className="w-72 shrink-0 flex flex-col border-r border-white/8 overflow-y-auto thin-scroll">
              {/* Stress gauge row */}
              <div className="shrink-0 border-b border-white/8 bg-[#0a0a0a]">
                <MissionStatus onReport={setReport} />
              </div>

              {/* Intel */}
              <div className="shrink-0">
                <LiveKitErrorBoundary>
                  <IntelDisplay intel={currentIntel} />
                </LiveKitErrorBoundary>
              </div>

              {/* Relationship bars */}
              <div className="shrink-0">
                <LiveKitErrorBoundary>
                  <RelationshipDisplay />
                </LiveKitErrorBoundary>
              </div>

              {/* Escalation */}
              <div className="shrink-0">
                <LiveKitErrorBoundary>
                  <EscalationIndicator />
                </LiveKitErrorBoundary>
              </div>

              {/* Emotional arc */}
              <div className="shrink-0">
                <LiveKitErrorBoundary>
                  <EmotionalArc />
                </LiveKitErrorBoundary>
              </div>

              {/* Subject mind */}
              <div className="shrink-0">
                <LiveKitErrorBoundary>
                  <ObjectiveDisplay />
                </LiveKitErrorBoundary>
              </div>

              {trainingMode && (
                <div className="shrink-0">
                  <LiveKitErrorBoundary>
                    <CoachingHints />
                  </LiveKitErrorBoundary>
                </div>
              )}
            </div>

            {/* ── RIGHT COLUMN: transcript + controls (dominant) ── */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Transcript — takes most of the space */}
              <div className="flex-1 overflow-hidden">
                <LiveKitErrorBoundary>
                  <LiveTranscriptFeed subjectName={currentName} />
                </LiveKitErrorBoundary>
              </div>

              {/* Controls pinned to bottom */}
              <div className="shrink-0 border-t border-white/8">
                <LiveKitErrorBoundary>
                  <SimulationUI
                    subjectName={currentName}
                    tacticalHold={tacticalHold}
                    setTacticalHold={setTacticalHold}
                    onDisconnect={disconnect}
                  />
                </LiveKitErrorBoundary>
              </div>
            </div>

            <LiveKitErrorBoundary>
              <Watchdog onDisconnect={disconnect} isHolding={tacticalHold} />
            </LiveKitErrorBoundary>
            <LiveKitErrorBoundary>
              <RoomAudioRenderer />
            </LiveKitErrorBoundary>
          </LiveKitRoom>
        </div>
      </main>
    );
  }

  // ── LOBBY VIEW ────────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-[#0d0d0d] flex flex-col overflow-x-hidden">

      {/* ── Top navigation bar ── */}
      <div className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-white/8">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[9px] tracking-[0.25em] text-white/20 uppercase">Crisis Negotiation Simulator</span>
          <span className="font-mono text-[9px] text-white/10">·</span>
          <span className="font-mono text-[9px] tracking-[0.15em] text-white/10 uppercase">v2.1</span>
        </div>
        <div className="font-mono text-[9px] tracking-[0.2em] text-white/15 uppercase">
          {new Date().toLocaleDateString("en-US", { weekday: "short", year: "numeric", month: "short", day: "numeric" }).toUpperCase()}
        </div>
      </div>

      {/* ── Hero ── */}
      <div className="shrink-0 px-6 pt-10 pb-6 border-b border-white/8">
        <div className="max-w-4xl mx-auto flex items-end justify-between gap-8">
          <div>
            {/* Overline */}
            <div className="font-mono text-[9px] tracking-[0.3em] text-[#c8893e]/60 uppercase mb-3">
              Field Training Exercise
            </div>
            {/* Title — the ONE place Playfair is used */}
            <h1 className="font-serif text-5xl md:text-7xl font-black text-white/90 tracking-tight leading-none uppercase">
              Can You<br />Negotiate?
            </h1>
            <p className="font-mono text-[11px] text-white/30 leading-relaxed mt-4 max-w-md">
              You are the negotiator. The subject has goals, fears, and lines they{" "}
              <span className="text-white/50">will not cross</span>. Listen carefully.
              Every word counts.
            </p>
          </div>

          {/* Difficulty + training mode controls */}
          <div className="shrink-0 flex flex-col gap-3 items-end">
            <div>
              <div className="font-mono text-[9px] tracking-[0.15em] text-white/25 uppercase mb-1.5">Difficulty</div>
              <div className="flex gap-1">
                {(["low", "medium", "high"] as Difficulty[]).map((d) => (
                  <button
                    key={d}
                    onClick={() => setDifficulty(d)}
                    className={`font-mono text-[10px] tracking-widest uppercase px-3 py-1.5 border transition-all ${
                      difficulty === d
                        ? d === "high"
                          ? "bg-[#c0392b] border-[#c0392b] text-white"
                          : d === "medium"
                          ? "bg-[#c8893e] border-[#c8893e] text-[#0d0d0d]"
                          : "bg-[#27ae60] border-[#27ae60] text-[#0d0d0d]"
                        : "bg-transparent border-white/10 text-white/25 hover:border-white/25 hover:text-white/40"
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer group">
              <div
                onClick={() => setTrainingMode((v) => !v)}
                className={`w-8 h-4 border transition-colors cursor-pointer flex items-center ${
                  trainingMode ? "bg-[#c8893e]/20 border-[#c8893e]/60" : "bg-white/5 border-white/15"
                }`}
                role="checkbox"
                aria-checked={trainingMode}
                aria-label="Training mode"
                tabIndex={0}
                onKeyDown={(e) => e.key === " " && setTrainingMode((v) => !v)}
              >
                <div
                  className={`w-3 h-3 transition-all mx-px ${
                    trainingMode ? "bg-[#c8893e] translate-x-3" : "bg-white/20 translate-x-0"
                  }`}
                />
              </div>
              <span className={`font-mono text-[9px] tracking-[0.15em] uppercase transition-colors ${
                trainingMode ? "text-[#c8893e]/80" : "text-white/20"
              }`}>
                Training Mode
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* ── Main content: scenario list + dossier ── */}
      <div className="flex-1 flex max-w-4xl w-full mx-auto overflow-hidden" style={{ minHeight: 0 }}>

        {/* Left: incident file list */}
        <div className="w-64 shrink-0 border-r border-white/8 flex flex-col overflow-hidden">
          <div className="px-4 py-2 border-b border-white/8">
            <span className="font-mono text-[9px] tracking-[0.2em] text-white/20 uppercase">Incident Files ({Object.keys(PERSONA_LABELS).length - 1})</span>
          </div>
          <div className="flex-1 overflow-y-auto thin-scroll">
            {(Object.keys(PERSONA_LABELS) as PersonaKey[]).map((key) => {
              const scenario = DEFAULT_SCENARIOS[key];
              const isActive = persona === key;
              const neuroticism = scenario?.personality?.neuroticism ?? 0.5;
              const threatColor = neuroticism > 0.7 ? "#c0392b" : neuroticism > 0.4 ? "#c8893e" : "#27ae60";
              return (
                <button
                  key={key}
                  onClick={() => setPersona(key)}
                  className={`w-full text-left px-4 py-3 border-b border-white/5 flex items-start gap-3 transition-colors ${
                    isActive ? "bg-white/6" : "hover:bg-white/3"
                  }`}
                >
                  {/* Threat indicator */}
                  <div className="mt-1 w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: threatColor, opacity: isActive ? 1 : 0.4 }} />
                  <div className="min-w-0">
                    <div className={`font-mono text-[10px] tracking-wide truncate transition-colors ${
                      isActive ? "text-white/80" : "text-white/30"
                    }`}>
                      {scenario?.name || "Custom"}
                    </div>
                    <div className={`font-mono text-[9px] truncate transition-colors ${
                      isActive ? "text-white/35" : "text-white/15"
                    }`}>
                      {PERSONA_LABELS[key].replace(/^\d+ - /, "")}
                    </div>
                  </div>
                  {isActive && (
                    <div className="ml-auto shrink-0 font-mono text-[8px] text-[#c8893e]/60 self-center">›</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: dossier + connect */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {/* Dossier preview */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <DossierPanel
              scenario={selectedScenario}
              isGenerating={isGeneratingIntel}
              intel={currentIntel}
            />
          </div>

          {/* Custom persona fields */}
          {persona === "custom" && (
            <div className="shrink-0 border-t border-white/8 bg-[#0a0a0a] p-4 grid grid-cols-3 gap-3">
              {[
                { id: "custom-name", label: "Name", value: customName, onChange: setCustomName, type: "text" },
                { id: "custom-age", label: "Age", value: customAge, onChange: setCustomAge, type: "number" },
                { id: "custom-profession", label: "Profession", value: customProfession, onChange: setCustomProfession, type: "text" },
              ].map(({ id, label, value, onChange, type }) => (
                <div key={id}>
                  <label htmlFor={id} className="font-mono text-[9px] tracking-[0.15em] text-white/25 uppercase block mb-1">{label}</label>
                  <input
                    id={id}
                    type={type}
                    value={value}
                    min={type === "number" ? 1 : undefined}
                    max={type === "number" ? 120 : undefined}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 text-white/70 font-mono text-xs p-2 focus:outline-none focus:border-white/25 transition-colors"
                  />
                </div>
              ))}
              <div className="col-span-3">
                <label htmlFor="custom-motive" className="font-mono text-[9px] tracking-[0.15em] text-white/25 uppercase block mb-1">Situation / Motive</label>
                <textarea
                  id="custom-motive"
                  value={customMotive}
                  onChange={(e) => setCustomMotive(e.target.value)}
                  maxLength={2000}
                  className="w-full bg-white/5 border border-white/10 text-white/70 font-mono text-xs p-2 focus:outline-none focus:border-white/25 transition-colors resize-none h-16"
                />
              </div>
            </div>
          )}

          {/* Connect bar */}
          <div className="shrink-0 flex items-center gap-4 px-4 py-3 border-t border-white/8 bg-[#0a0a0a]">
            <div className="flex-1 min-w-0">
              <div className="font-mono text-[9px] tracking-[0.15em] text-white/20 uppercase truncate">
                {selectedScenario?.name
                  ? `Ready to negotiate with ${selectedScenario.name}`
                  : "Select a subject"}
              </div>
            </div>
            <button
              onClick={connect}
              disabled={isConnecting}
              aria-label={isConnecting ? "Connecting..." : "Begin negotiation"}
              className={`font-mono text-[10px] font-bold tracking-[0.2em] uppercase px-6 py-3 border transition-all shrink-0 ${
                isConnecting
                  ? "bg-white/5 border-white/10 text-white/20 cursor-not-allowed"
                  : "bg-[#c0392b] border-[#c0392b] text-white hover:bg-[#962d22] hover:border-[#962d22]"
              }`}
            >
              {isConnecting ? "Connecting..." : "Begin Negotiation ›"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <ToastProvider>
      <HomeContent />
    </ToastProvider>
  );
}
