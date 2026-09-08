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
import type { PersonaKey, Difficulty, ScenarioData } from "@/lib/types";
import {
  BACKEND_URL,
  CUSTOM_PERSONA_DEBOUNCE_MS,
} from "@/lib/constants";

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

  const [scenarioData, setScenarioData] = useState<ScenarioData>(
    DEFAULT_SCENARIOS.robber
  );

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
      } catch (e) {
        console.error("Failed to generate intel preview, using local fallback", e);
        if (active) {
          setScenarioData(DEFAULT_SCENARIOS[persona] || DEFAULT_SCENARIOS.robber);
        }
      } finally {
        if (active) setIsGeneratingIntel(false);
      }
    };

    const timer = setTimeout(
      () => {
        generate();
      },
      persona === "custom" ? CUSTOM_PERSONA_DEBOUNCE_MS : 0
    );

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [persona, difficulty, refreshTrigger]);

  // Separate effect for custom persona - debounce customMotive changes
  useEffect(() => {
    if (persona !== "custom") return;
    const timer = setTimeout(() => {
      setRefreshTrigger((t) => t + 1);
    }, CUSTOM_PERSONA_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [customMotive, persona]);

  const connect = useCallback(async () => {
    if (isConnecting || token) return;
    try {
      setIsConnecting(true);

      const finalScenarioData =
        scenarioData || DEFAULT_SCENARIOS[persona] || DEFAULT_SCENARIOS.robber;

      const roomName = `english-${persona}-${Math.floor(Math.random() * 10000)}`;

      const metaObj: Record<string, unknown> = {
        difficulty,
        dynamicScenario: true,
        trainingMode,
        ...finalScenarioData,
      };

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
      const message = e instanceof Error ? e.message : "Unknown error";
      addToast("Connection error: " + message, "error");
    } finally {
      setIsConnecting(false);
    }
  }, [
    isConnecting,
    token,
    persona,
    difficulty,
    trainingMode,
    customAge,
    customProfession,
    customMotive,
    scenarioData,
    addToast,
  ]);

  const [tacticalHold, setTacticalHold] = useState(false);

  const disconnect = useCallback(() => {
    setToken(null);
    setTacticalHold(false);
  }, []);

  const currentName = useMemo(() => {
    if (isGeneratingIntel) return "...";
    if (scenarioData?.name) return scenarioData.name.toUpperCase();
    return getDefaultName(persona);
  }, [isGeneratingIntel, scenarioData, persona]);

  const currentIntel = isGeneratingIntel
    ? "REFRESHING INTEL..."
    : scenarioData?.intel || "No intel available.";

  return (
    <main
      className={`min-h-screen flex flex-col items-center justify-start overflow-x-hidden relative py-12 px-4 transition-colors duration-700 ${
        token ? "bg-[#0f0f0f]" : "bg-[#f4f0e6]"
      }`}
    >
      {/* Background EKG line */}
      <div
        className={`fixed top-0 left-0 bottom-0 w-48 md:w-64 pointer-events-none transition-opacity duration-700 ${
          token ? "opacity-[0.02]" : "opacity-[0.04]"
        }`}
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 300 1200"
          className={`w-full h-full fill-none ${
            token ? "stroke-[#f4f0e6]" : "stroke-black"
          }`}
          strokeWidth="8"
          preserveAspectRatio="none"
        >
          <path
            d="M150,0 L150,300 L50,350 L250,400 L150,450 L150,700 L20,750 L280,800 L150,850 L150,1200"
            strokeLinejoin="miter"
            strokeLinecap="square"
          />
        </svg>
      </div>

      {!token && (
        <div className="max-w-4xl w-full flex flex-col items-center text-center z-10 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Title */}
          <div className="relative mt-12">
            <div className="absolute -inset-2 bg-[#d99a4e] translate-x-2 translate-y-3 -z-10 mix-blend-multiply opacity-80" />
            <div className="absolute -left-8 -top-6 bg-[#1e1e1e] text-[#f4f0e6] font-mono text-xl px-4 py-1 rotate-[-5deg] z-10">
              Can you
            </div>
            <h1 className="text-7xl md:text-9xl font-serif font-black tracking-tighter text-[#1e1e1e] uppercase border-4 border-[#1e1e1e] px-6 py-2 bg-[#f4f0e6]">
              Negotiate
            </h1>
            <div className="absolute -right-8 -bottom-4 text-[#dc2626] font-serif font-black text-6xl md:text-8xl rotate-[15deg] z-10 drop-shadow-md">
              ?
            </div>
          </div>

          <p className="text-xl md:text-2xl font-serif text-[#1e1e1e]/80 italic mt-8 max-w-lg bg-[#f4f0e6]/80 p-2 whitespace-pre-line text-center">
            {"De-escalation via verbal interrupt.\nCalm the subject."}
          </p>

          {/* Mission brief */}
          <div className="w-full max-w-2xl bg-[#f4f0e6] border-4 border-[#1e1e1e] p-8 text-left relative mt-8 shadow-[8px_8px_0_0_#d99a4e]">
            <div className="absolute -top-3 left-4 bg-[#f4f0e6] px-2 text-sm font-bold uppercase tracking-widest text-[#d99a4e]">
              MISSION_BRIEF
            </div>
            <ol className="text-left font-serif text-lg space-y-4 text-[#1e1e1e]/90 leading-relaxed">
              <li className="flex gap-4">
                <span className="font-mono text-[#d99a4e] font-bold">/01</span>
                <span>
                  The subject is highly panicked and will immediately begin a
                  hostile rant.
                </span>
              </li>
              <li className="flex gap-4">
                <span className="font-mono text-[#d99a4e] font-bold">/02</span>
                <span>
                  Listen closely for clues and pull the right threads to uncover
                  their <strong className="font-black">hidden backstory</strong>.
                </span>
              </li>
              <li className="flex gap-4">
                <span className="font-mono text-[#d99a4e] font-bold">/03</span>
                <span>
                  Use empathy to lower their{" "}
                  <strong className="font-black">Stress Level</strong> and force
                  a peaceful surrender.
                </span>
              </li>
            </ol>
          </div>
        </div>
      )}

      <div className="z-10 mt-12 w-full max-w-4xl flex justify-center">
        {report ? (
          <div className="flex flex-col items-center bg-[#f4f0e6] border-4 border-[#1e1e1e] p-8 shadow-[12px_12px_0_0_#d99a4e] w-full max-w-2xl relative">
            <div className="absolute -top-4 bg-[#d99a4e] text-[#1e1e1e] font-mono font-black text-xl px-4 border-2 border-[#1e1e1e]">
              POST-ACTION DEBRIEF
            </div>
            <div className="w-full mt-4">
              <ParsedReport text={report} />
            </div>
            <div className="mt-8 flex flex-wrap justify-center gap-6 w-full">
              <button
                onClick={() => {
                  setReport(null);
                  setRefreshTrigger((r) => r + 1);
                }}
                className="bg-[#1e1e1e] text-[#f4f0e6] font-mono font-bold text-xl px-8 py-4 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#d99a4e] hover:translate-y-1 hover:shadow-[2px_2px_0_0_#d99a4e] transition-all"
              >
                RETRY WITH NEW SUBJECT
              </button>
              <button
                onClick={() => setReport(null)}
                className="bg-white/80 text-[#1e1e1e] font-mono font-bold text-xl px-8 py-4 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e] hover:translate-y-1 hover:shadow-[2px_2px_0_0_#1e1e1e] transition-all"
              >
                BACK TO PROFILE
              </button>
              <button
                onClick={() => {
                  setReport(null);
                  setPersona("robber");
                  setDifficulty("medium");
                  setRefreshTrigger((r) => r + 1);
                }}
                className="bg-white/40 text-[#1e1e1e] font-mono font-bold text-xl px-8 py-4 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e] hover:translate-y-1 hover:shadow-[2px_2px_0_0_#1e1e1e] transition-all"
              >
                HOME
              </button>
            </div>
          </div>
        ) : !token ? (
          <div className="flex flex-col items-center gap-8 w-full">
            <div className="flex gap-4 w-full max-w-lg">
              <div className="flex flex-col gap-2 flex-1">
                <label
                  htmlFor="persona-select"
                  className="font-mono text-sm font-bold tracking-widest text-[#1e1e1e] opacity-70"
                >
                  SUBJECT_PROFILE
                </label>
                <select
                  id="persona-select"
                  value={persona}
                  onChange={(e) => setPersona(e.target.value as PersonaKey)}
                  className="w-full bg-[#f4f0e6] text-[#1e1e1e] border-4 border-[#1e1e1e] font-serif font-bold text-xl p-3 shadow-[6px_6px_0_0_#d99a4e] focus:outline-none focus:ring-0 appearance-none rounded-none cursor-pointer"
                >
                  {(Object.keys(PERSONA_LABELS) as PersonaKey[]).map((key) => (
                    <option key={key} value={key}>
                      {PERSONA_LABELS[key]}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-2 w-48">
                <label
                  htmlFor="difficulty-select"
                  className="font-mono text-sm font-bold tracking-widest text-[#1e1e1e] opacity-70"
                >
                  DIFFICULTY
                </label>
                <select
                  id="difficulty-select"
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value as Difficulty)}
                  className="w-full bg-[#f4f0e6] text-[#1e1e1e] border-4 border-[#1e1e1e] font-serif font-bold text-xl p-3 shadow-[6px_6px_0_0_#d99a4e] focus:outline-none focus:ring-0 appearance-none rounded-none cursor-pointer"
                >
                  <option value="low">LOW</option>
                  <option value="medium">MEDIUM</option>
                  <option value="high">HIGH</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-3 mt-2">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={trainingMode}
                  onChange={(e) => setTrainingMode(e.target.checked)}
                  className="w-4 h-4 accent-[#d99a4e]"
                />
                <span className="font-mono text-xs font-bold tracking-widest text-[#1e1e1e]/70 uppercase group-hover:text-[#1e1e1e] transition-colors">
                  Training Mode
                </span>
              </label>
              <span className="font-serif text-xs text-[#1e1e1e]/40 italic">
                real-time coaching hints
              </span>
            </div>

            {persona === "custom" && (
              <div className="w-full max-w-xl bg-[#1e1e1e] text-[#f4f0e6] p-6 border-4 border-[#d99a4e] shadow-[8px_8px_0_0_#d99a4e] flex flex-col gap-4 mt-2">
                <h3 className="font-mono text-sm font-bold tracking-widest text-[#d99a4e]">
                  CUSTOM_GENERATOR
                </h3>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label
                      htmlFor="custom-name"
                      className="text-xs font-bold font-mono opacity-80 mb-1 block"
                    >
                      NAME
                    </label>
                    <input
                      id="custom-name"
                      type="text"
                      value={customName}
                      onChange={(e) => setCustomName(e.target.value)}
                      className="w-full bg-transparent border-b-2 border-[#f4f0e6] p-2 font-serif text-lg focus:outline-none"
                    />
                  </div>
                  <div className="w-24">
                    <label
                      htmlFor="custom-age"
                      className="text-xs font-bold font-mono opacity-80 mb-1 block"
                    >
                      AGE
                    </label>
                    <input
                      id="custom-age"
                      type="number"
                      min="1"
                      max="120"
                      value={customAge}
                      onChange={(e) => setCustomAge(e.target.value)}
                      className="w-full bg-transparent border-b-2 border-[#f4f0e6] p-2 font-serif text-lg focus:outline-none"
                    />
                  </div>
                  <div className="flex-1">
                    <label
                      htmlFor="custom-profession"
                      className="text-xs font-bold font-mono opacity-80 mb-1 block"
                    >
                      PROFESSION
                    </label>
                    <input
                      id="custom-profession"
                      type="text"
                      value={customProfession}
                      onChange={(e) => setCustomProfession(e.target.value)}
                      className="w-full bg-transparent border-b-2 border-[#f4f0e6] p-2 font-serif text-lg focus:outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="custom-motive"
                    className="text-xs font-bold font-mono opacity-80 mb-1 block"
                  >
                    SITUATION / MOTIVE
                  </label>
                  <textarea
                    id="custom-motive"
                    value={customMotive}
                    onChange={(e) => setCustomMotive(e.target.value)}
                    maxLength={2000}
                    className="w-full bg-transparent border-2 border-[#f4f0e6] p-2 font-serif text-lg h-24 focus:outline-none resize-none"
                  />
                </div>
              </div>
            )}

            {/* Persona Dossier Preview */}
            <div className="w-full max-w-lg mt-4 bg-[#1e1e1e]/5 border border-[#1e1e1e]/15 border-l-4 border-l-[#d99a4e] p-4 relative">
              <div className="font-mono text-[10px] font-bold tracking-widest text-[#d99a4e] uppercase mb-2 flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isGeneratingIntel ? "bg-[#d99a4e] animate-pulse" : "bg-[#22c55e]"
                  }`}
                  aria-hidden="true"
                />
                INTEL_PREVIEW
              </div>
              <p
                className={`font-serif text-sm text-[#1e1e1e]/80 leading-relaxed transition-opacity duration-300 ${
                  isGeneratingIntel ? "opacity-50 italic" : "opacity-100"
                }`}
              >
                {currentIntel}
              </p>
            </div>

            <div className="flex flex-col items-center gap-3 mt-2">
              <button
                onClick={connect}
                disabled={isConnecting}
                aria-label={isConnecting ? "Connecting to negotiation room" : "Connect to negotiation"}
                className={`px-10 py-4 font-mono font-bold text-lg uppercase tracking-widest text-[#f4f0e6] transition-all ${
                  isConnecting
                    ? "bg-[#1e1e1e]/40 cursor-not-allowed opacity-60"
                    : "bg-[#1e1e1e] hover:bg-[#dc2626] shadow-[5px_5px_0_0_#d99a4e] hover:shadow-[2px_2px_0_0_#d99a4e] hover:translate-y-[3px] hover:translate-x-[3px]"
                }`}
              >
                {isConnecting ? "CONNECTING..." : "CONNECT TO NEGOTIATION"}
              </button>
              {!isConnecting && (
                <p className="font-mono text-[10px] text-[#1e1e1e]/35 tracking-widest uppercase">
                  Microphone required
                </p>
              )}
            </div>
          </div>
        ) : (
          /* ── Active session container ─────────────────────────────── */
          <div className="w-full max-w-4xl bg-[#0f0f0f] border border-[#f4f0e6]/10 shadow-[0_0_60px_rgba(0,0,0,0.8)] relative mt-8 overflow-hidden">

            {/* Subtle scanline overlay */}
            <div
              className="absolute inset-0 pointer-events-none z-[1]"
              style={{
                backgroundImage:
                  "repeating-linear-gradient(to bottom, transparent 0px, transparent 3px, rgba(0,0,0,0.06) 3px, rgba(0,0,0,0.06) 4px)",
              }}
              aria-hidden="true"
            />

            {/* Top chrome bar */}
            <div className="relative z-10 flex items-center justify-between px-4 py-2 border-b border-[#f4f0e6]/10 bg-[#1a1a1a]">
              {/* Left — blinking live indicator */}
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#dc2626] glow-red" aria-hidden="true" />
                <span className="font-mono text-[10px] font-bold tracking-widest text-[#f4f0e6]/50 uppercase">
                  LIVE_FEED
                </span>
              </div>
              {/* Right — subject name badge */}
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-[#f4f0e6]/30 tracking-widest uppercase">SUBJECT:</span>
                <span className="font-mono text-xs font-black tracking-widest text-[#d99a4e] uppercase">
                  {currentName}
                </span>
              </div>
            </div>

            {/* Content — stress gauge sidebar + main panels */}
            <div className="relative z-10 flex gap-0">
              <LiveKitRoom
                serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
                token={token}
                connect={!!token}
                onDisconnected={disconnect}
                audio={true}
                video={false}
                className="flex-1 min-w-0 flex"
              >
                {/* Stress gauge — no longer absolute; sits in its own column */}
                <div className="shrink-0 border-r border-[#f4f0e6]/8 bg-[#141414] flex items-stretch">
                  <MissionStatus onReport={setReport} />
                </div>

                {/* Main panel column */}
                <div className="flex-1 min-w-0 flex flex-col p-4 gap-3">
                  <LiveKitErrorBoundary>
                    <IntelDisplay intel={currentIntel} />
                  </LiveKitErrorBoundary>
                  <LiveKitErrorBoundary>
                    <RelationshipDisplay />
                  </LiveKitErrorBoundary>
                  <LiveKitErrorBoundary>
                    <EscalationIndicator />
                  </LiveKitErrorBoundary>
                  <LiveKitErrorBoundary>
                    <ObjectiveDisplay />
                  </LiveKitErrorBoundary>
                  <LiveKitErrorBoundary>
                    <EmotionalArc />
                  </LiveKitErrorBoundary>
                  {trainingMode && (
                    <LiveKitErrorBoundary>
                      <CoachingHints />
                    </LiveKitErrorBoundary>
                  )}
                  <LiveKitErrorBoundary>
                    <Watchdog onDisconnect={disconnect} isHolding={tacticalHold} />
                  </LiveKitErrorBoundary>

                  {/* Divider before controls */}
                  <div className="w-full h-px bg-[#f4f0e6]/8 my-1" aria-hidden="true" />

                  <LiveKitErrorBoundary>
                    <SimulationUI
                      subjectName={currentName}
                      tacticalHold={tacticalHold}
                      setTacticalHold={setTacticalHold}
                      onDisconnect={disconnect}
                    />
                  </LiveKitErrorBoundary>

                  {/* Divider before transcript */}
                  <div className="w-full h-px bg-[#f4f0e6]/8 my-1" aria-hidden="true" />

                  <LiveKitErrorBoundary>
                    <div className="w-full flex justify-center">
                      <LiveTranscriptFeed subjectName={currentName} />
                    </div>
                  </LiveKitErrorBoundary>
                </div>

                <LiveKitErrorBoundary>
                  <RoomAudioRenderer />
                </LiveKitErrorBoundary>
              </LiveKitRoom>
            </div>
          </div>
        )}
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
