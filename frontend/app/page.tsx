'use client';

import {
  LiveKitRoom,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  BarVisualizer,
  useVoiceAssistant,
  useDataChannel,
  useRemoteParticipants,
  useRoomContext,
} from '@livekit/components-react';
import '@livekit/components-styles';
import { useCallback, useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

function ParsedReport({ text }: { text: string }) {
  const summaryMatch = text.match(/\*\*Grading Summary\*\*([\s\S]*?)(?=\*\*Advice\*\*|$)/);
  const adviceMatch = text.match(/\*\*Advice\*\*([\s\S]*)/);

  let summaryLines = summaryMatch ? summaryMatch[1].trim().split('\n') : [];
  let adviceText = adviceMatch ? adviceMatch[1].trim() : text;

  if (summaryLines.length === 0 && adviceText === text) {
    // Fallback if formatting doesn't match perfectly
    return <div className="font-serif prose prose-sm text-[#1e1e1e]"><ReactMarkdown>{text}</ReactMarkdown></div>;
  }

  return (
    <div className="w-full flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 bg-white/40 p-6 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e]">
        {summaryLines.map((line, i) => {
           const match = line.match(/\*\*(.*?):\*\*\s*(.*)/);
           if (match) {
             const cat = match[1].replace(/\*/g, '').trim();
             const grade = match[2].trim();
             const isGood = grade.includes('A') || grade.includes('B');
             const isMid = grade.includes('C');
             return (
               <div key={i} className="flex justify-between items-center border-b-2 border-[#1e1e1e]/10 pb-3 last:border-0 last:pb-0">
                 <span className="font-serif font-bold text-lg text-[#1e1e1e] uppercase tracking-wide">{cat}</span>
                 <span className={`font-mono font-black text-2xl px-4 py-1 border-2 border-[#1e1e1e] shadow-[2px_2px_0_0_#1e1e1e] ${isGood ? 'bg-[#4ade80]' : isMid ? 'bg-[#facc15]' : 'bg-[#dc2626] text-white'}`}>
                   {grade}
                 </span>
               </div>
             )
           }
           return null;
        })}
      </div>
      
      <div className="bg-white/80 p-6 border-l-8 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e]">
         <h4 className="font-mono uppercase tracking-widest text-sm font-black mb-3 text-[#dc2626]">Actionable Advice</h4>
         <div className="font-serif text-[#1e1e1e]/90 leading-relaxed">
           <ReactMarkdown>{adviceText}</ReactMarkdown>
         </div>
      </div>
    </div>
  )
}

function MissionStatus({ onReport }: { onReport: (r: string) => void }) {
  const [surrendered, setSurrendered] = useState(false);
  const [escalated, setEscalated] = useState(false);
  const [stress, setStress] = useState(90);

  useDataChannel((msg) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === 'surrender') {
        setSurrendered(true);
      } else if (data.type === 'escalate') {
        setEscalated(true);
        setTimeout(() => setEscalated(false), 5000);
      } else if (data.type === 'stress') {
        setStress(data.level);
      } else if (data.type === 'report') {
        onReport(data.content);
      }
    } catch (e) {}
  });

  return (
    <>
      {/* Stress bar — left side vertical */}
      <div className="absolute top-0 left-0 bottom-0 w-3 bg-[#1e1e1e]/10 border-r border-[#1e1e1e]/20 z-30 flex flex-col justify-end overflow-hidden">
        {/* Surrender threshold marker */}
        <div className="absolute bottom-[20%] left-0 right-0 h-0.5 bg-[#f4f0e6] z-40 shadow-[0_0_4px_rgba(0,0,0,0.5)]" title="Surrender Threshold" />
        <div className="absolute bottom-[22%] left-4 text-[10px] font-mono font-bold text-[#1e1e1e] whitespace-nowrap rotate-[-90deg] origin-bottom-left">SURRENDER_ZONE</div>
        <div
          className="w-full transition-all duration-1000 ease-out"
          style={{
            height: `${stress}%`,
            backgroundColor: stress > 80 ? '#dc2626' : stress > 20 ? '#d99a4e' : '#16a34a',
            boxShadow: stress > 80 ? '0 0 10px #dc2626' : 'none',
          }}
        />
      </div>
      <div className="absolute top-2 left-6 z-30 font-mono text-xs font-bold px-2 py-1 bg-[#1e1e1e] text-[#f4f0e6]">
        STRESS: {stress}%
      </div>

      {/* Surrender screen */}
      {surrendered && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#1e1e1e]/90 backdrop-blur-sm p-6">
          <div className="text-center transform -rotate-2">
            <h1 className="text-6xl md:text-8xl font-black font-serif text-[#d99a4e] tracking-tighter uppercase drop-shadow-[8px_8px_0_rgba(244,240,230,0.1)]">
              Mission<br />Accomplished
            </h1>
            <p className="mt-6 text-[#f4f0e6] font-mono text-xl tracking-widest border-t-2 border-b-2 border-[#d99a4e] inline-block py-2">
              SUBJECT SURRENDERED
            </p>
          </div>
          <p className="mt-8 text-[#f4f0e6]/70 font-mono text-sm tracking-wider animate-pulse">
            Generating post-action debrief report...
          </p>
        </div>
      )}

      {/* Escalate screen */}
      {escalated && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-[#dc2626]/90 backdrop-blur-sm p-6">
          <div className="text-center transform rotate-2">
            <h1 className="text-6xl md:text-8xl font-black font-serif text-[#1e1e1e] tracking-tighter uppercase drop-shadow-[8px_8px_0_rgba(244,240,230,0.2)]">
              Mission<br />Failed
            </h1>
            <p className="mt-6 text-[#1e1e1e] font-mono font-bold text-xl tracking-widest border-t-4 border-b-4 border-[#1e1e1e] inline-block py-2 px-4 bg-[#f4f0e6]">
              SUBJECT ESCALATED
            </p>
          </div>
          <p className="mt-8 text-[#1e1e1e] font-mono text-sm font-bold tracking-wider animate-pulse">
            Generating post-action debrief report...
          </p>
        </div>
      )}
    </>
  );
}

interface TranscriptItem {
  id: string;
  speaker: 'user' | 'agent';
  senderName: string;
  text: string;
  timestamp: string;
}

function LiveTranscriptFeed({ subjectName }: { subjectName: string }) {
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);

  useDataChannel((msg) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      if (data.type === 'transcript' && data.text) {
        const timeStr = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setTranscripts((prev) => {
          // If agent speech: update by ID if streaming/interrupted, or add new bubble
          if (data.speaker === 'agent') {
            if (data.id) {
              const idx = prev.findIndex(item => item.id === data.id);
              if (idx !== -1) {
                const updated = [...prev];
                updated[idx] = {
                  ...updated[idx],
                  text: data.text,
                };
                return updated;
              }
            }
            return [
              ...prev,
              {
                id: data.id || `${Date.now()}-${Math.random()}`,
                speaker: 'agent',
                senderName: data.senderName || subjectName || 'SUBJECT',
                text: data.text,
                timestamp: timeStr,
              }
            ];
          }

          // If user speech: if the last message in the feed was also from the user, merge/append to it so natural pauses don't fragment into multiple bubbles!
          if (data.speaker === 'user') {
            const lastItem = prev.length > 0 ? prev[prev.length - 1] : null;
            if (lastItem && lastItem.speaker === 'user') {
              const updated = [...prev];
              // Avoid duplicating exact repeat segments if STT re-transcribed
              const newText = lastItem.text.includes(data.text)
                ? lastItem.text
                : `${lastItem.text} ${data.text}`;
              updated[updated.length - 1] = {
                ...lastItem,
                text: newText,
                timestamp: timeStr,
              };
              return updated;
            }

            // New user turn
            return [
              ...prev,
              {
                id: data.id || `user-${Date.now()}-${Math.random()}`,
                speaker: 'user',
                senderName: 'YOU',
                text: data.text,
                timestamp: timeStr,
              }
            ];
          }

          return prev;
        });
      }
    } catch (e) {}
  });

  return (
    <div className="w-full max-w-2xl mt-6 bg-[#1e1e1e] border-2 border-[#d99a4e] p-4 text-left shadow-[6px_6px_0_0_#1e1e1e]">
      <div className="flex items-center justify-between border-b border-[#f4f0e6]/20 pb-2 mb-3">
        <div className="font-mono text-xs font-bold tracking-widest text-[#d99a4e] uppercase flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" />
          COMMS_LOG // LIVE_TRANSCRIPT
        </div>
        <span className="font-mono text-[10px] text-[#f4f0e6]/50 uppercase">CONVERSATION STREAM</span>
      </div>

      <div className="h-44 overflow-y-auto space-y-2 pr-1 flex flex-col-reverse select-text font-mono text-xs">
        {transcripts.length === 0 ? (
          <div className="text-[#f4f0e6]/40 italic py-6 text-center">
            [Audio channel open. Speak into microphone to negotiate...]
          </div>
        ) : (
          [...transcripts].reverse().map((t) => (
            <div
              key={t.id}
              className={`p-2 border-l-2 leading-relaxed ${
                t.speaker === 'user'
                  ? 'border-[#22c55e] bg-white/5 text-[#f4f0e6]'
                  : 'border-[#d99a4e] bg-[#d99a4e]/10 text-[#f4f0e6]'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] mb-1 opacity-70">
                <span className={t.speaker === 'user' ? 'text-[#22c55e] font-bold' : 'text-[#d99a4e] font-bold'}>
                  [{t.senderName}]
                </span>
                <span>{t.timestamp}</span>
              </div>
              <p className="text-sm font-serif tracking-normal">{t.text}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SimulationUI({
  subjectName,
  tacticalHold,
  setTacticalHold,
}: {
  subjectName: string;
  tacticalHold: boolean;
  setTacticalHold: (val: boolean | ((prev: boolean) => boolean)) => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();
  const room = useRoomContext();

  const toggleHold = useCallback(async () => {
    const nextHold = !tacticalHold;
    setTacticalHold(nextHold);
    try {
      if (room?.localParticipant) {
        await room.localParticipant.setMicrophoneEnabled(!nextHold);
      }
    } catch (e) {
      console.warn("Failed to toggle mic track on tactical hold:", e);
    }
  }, [tacticalHold, room, setTacticalHold]);

  return (
    <div className="flex flex-col items-center justify-center p-6 min-h-[350px] relative">
      {/* Decorative crosshair */}
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-10">
        <div className="w-64 h-64 border border-[#1e1e1e] rounded-full" />
        <div className="absolute w-full h-[1px] bg-[#1e1e1e]" />
        <div className="absolute h-full w-[1px] bg-[#1e1e1e]" />
      </div>

      {tacticalHold && (
        <div className="z-20 mb-4 px-4 py-2 bg-[#d99a4e] border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e] animate-pulse">
          <p className="font-mono text-xs font-black uppercase text-[#1e1e1e] tracking-wider">
            [ TACTICAL HOLD ACTIVE: Mic muted. Formulate your strategy. Subject is waiting on the line. ]
          </p>
        </div>
      )}

      <div className="mb-4 flex flex-col items-center z-10">
        <div className={`font-serif text-3xl md:text-4xl font-black uppercase tracking-tighter transition-colors ${tacticalHold ? 'text-[#d99a4e]' : state === 'speaking' ? 'text-[#d99a4e]' : 'text-[#1e1e1e]'}`}>
          [ STATUS: {tacticalHold ? 'HOLD // THINK TIME' : state} ]
        </div>
        <div className="h-16 mt-4 flex items-center justify-center">
          {audioTrack && !tacticalHold && (
            <BarVisualizer
              state={state}
              barCount={9}
              trackRef={audioTrack}
              className="h-16 w-64 text-[#1e1e1e]"
            />
          )}
          {tacticalHold && (
            <div className="h-16 flex items-center justify-center font-mono text-sm tracking-widest text-[#1e1e1e]/60">
              [ COMMS MUTED FOR TACTICAL DELIBERATION ]
            </div>
          )}
        </div>
      </div>

      {/* Real-time two-way transcript box */}
      <div className="w-full flex justify-center z-10">
        <LiveTranscriptFeed subjectName={subjectName} />
      </div>

      {/* Control Actions bar */}
      <div className="z-10 mt-6 flex flex-wrap items-center justify-center gap-4">
        <button
          onClick={toggleHold}
          className={`font-mono text-xs md:text-sm font-black px-4 py-2 border-2 border-[#1e1e1e] transition-all flex items-center gap-2 shadow-[3px_3px_0_0_#1e1e1e] ${
            tacticalHold
              ? 'bg-[#22c55e] text-[#1e1e1e] hover:bg-[#16a34a]'
              : 'bg-[#d99a4e] text-[#1e1e1e] hover:bg-[#b8803c]'
          }`}
        >
          <span className={`w-2.5 h-2.5 rounded-full ${tacticalHold ? 'bg-[#1e1e1e] animate-ping' : 'bg-[#dc2626]'}`} />
          {tacticalHold ? 'RESUME COMMS [UNPAUSE]' : 'TACTICAL HOLD // THINK TIME'}
        </button>

        <div className="bg-[#1e1e1e] p-1 border-2 border-[#d99a4e]" data-lk-theme="default">
          <VoiceAssistantControlBar />
        </div>
      </div>
    </div>
  );
}

function Watchdog({ onDisconnect, isHolding }: { onDisconnect: () => void; isHolding: boolean }) {
  const { state } = useVoiceAssistant();
  const participants = useRemoteParticipants();
  const room = useRoomContext();

  useEffect(() => {
    if (room.state === 'connected' && participants.length === 0) {
      const t = setTimeout(() => {
        alert("Connection Lost: The subject disconnected unexpectedly.");
        room.disconnect();
        onDisconnect();
      }, 5000);
      return () => clearTimeout(t);
    }
  }, [participants.length, room.state, room, onDisconnect]);

  useEffect(() => {
    // If tactical hold is active, negotiator is deliberately thinking; do not time out
    if (isHolding) return;

    if (state === 'listening' || state === 'thinking') {
      const t = setTimeout(() => {
         alert("Network timeout: The comms link stalled. Automatically dropping the call to prevent freezing.");
         room.disconnect();
         onDisconnect();
      }, 45000);
      return () => clearTimeout(t);
    }
  }, [state, room, onDisconnect, isHolding]);

  return null;
}


export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [persona, setPersona] = useState('robber');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [viewState, setViewState] = useState('home');

  const [customName, setCustomName] = useState('Alex');
  const [customAge, setCustomAge] = useState('35');
  const [customProfession, setCustomProfession] = useState('Accountant');
  const [customMotive, setCustomMotive] = useState('Caught embezzling funds and is holding the boss hostage.');

  const [isConnecting, setIsConnecting] = useState(false);
  const [difficulty, setDifficulty] = useState('medium');
  const [report, setReport] = useState<string | null>(null);

  const [scenarioData, setScenarioData] = useState<any>(null);

  const [isGeneratingIntel, setIsGeneratingIntel] = useState(false);

  useEffect(() => {
    let active = true;
    const generate = async () => {
      try {
        setIsGeneratingIntel(true);
        setScenarioData(null); // clear old intel
        const scenarioRes = await fetch('/api/scenario', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ persona, difficulty, customMotive })
        });
        const scenarioJson = await scenarioRes.json();
        if (active && scenarioRes.ok) {
          setScenarioData(scenarioJson);
        }
      } catch (e) {
        console.error("Failed to generate intel preview", e);
      } finally {
        if (active) setIsGeneratingIntel(false);
      }
    };

    const timer = setTimeout(() => {
      generate();
    }, persona === 'custom' ? 800 : 0);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [persona, difficulty, customMotive, refreshTrigger]);

  const connect = useCallback(async () => {
    try {
      setIsConnecting(true);
      
      let finalScenarioData = scenarioData;
      // If still generating or missing, generate it on demand
      if (!finalScenarioData) {
        const scenarioRes = await fetch('/api/scenario', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ persona, difficulty, customMotive })
        });
        finalScenarioData = await scenarioRes.json();
        if (!scenarioRes.ok) throw new Error(finalScenarioData.error || 'Failed to generate scenario');
        setScenarioData(finalScenarioData);
      }

      // Step 2: Fetch LiveKit Token with Metadata
      const roomName = `english-${persona}-${Math.floor(Math.random() * 10000)}`;
      let url = `/api/token?room=${roomName}`;
      
      const metaObj: any = { 
        difficulty,
        dynamicScenario: true,
        ...finalScenarioData
      };
      
      if (persona === 'custom') {
        metaObj.age = customAge;
        metaObj.profession = customProfession;
        metaObj.motive = customMotive;
      }
      
      url += `&metadata=${encodeURIComponent(JSON.stringify(metaObj))}`;
      const res = await fetch(url);
      const data = await res.json();
      if (res.ok) setToken(data.token);
      else alert('Failed to connect: ' + data.error);
    } catch (e: any) {
      alert('Connection error: ' + e.message);
    } finally {
      setIsConnecting(false);
    }
  }, [persona, difficulty, customName, customAge, customProfession, customMotive, scenarioData]);

  const [tacticalHold, setTacticalHold] = useState(false);

  const disconnect = useCallback(() => {
    setToken(null);
    setTacticalHold(false);
  }, []);

  const currentName = scenarioData?.name ? scenarioData.name.toUpperCase() : (persona === 'robber' ? 'MARIA' : persona === 'scammed' ? 'ARTHUR' : persona === 'founder' ? 'SAM' : customName.toUpperCase());
  const currentIntel = scenarioData?.intel ? scenarioData.intel : "Generating fresh intel...";


  return (
    <main className="min-h-screen bg-[#f4f0e6] flex flex-col items-center justify-start overflow-x-hidden relative py-12 px-4">
      {/* Background EKG line (Left side) */}
      <div className="fixed top-0 left-0 bottom-0 w-48 md:w-64 opacity-[0.04] pointer-events-none">
        <svg viewBox="0 0 300 1200" className="w-full h-full stroke-black fill-none" strokeWidth="8" preserveAspectRatio="none">
          <path d="M150,0 L150,300 L50,350 L250,400 L150,450 L150,700 L20,750 L280,800 L150,850 L150,1200" strokeLinejoin="miter" strokeLinecap="square" />
        </svg>
      </div>

      <div className="max-w-4xl w-full flex flex-col items-center text-center z-10 space-y-8">

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

        <p className="text-xl md:text-2xl font-serif text-[#1e1e1e]/80 italic mt-8 max-w-lg bg-[#f4f0e6]/80 p-2">
          De-escalation via verbal interrupt. Calm the subject.
        </p>

        {/* Mission brief */}
        <div className="w-full max-w-2xl bg-[#f4f0e6] border-4 border-[#1e1e1e] p-8 text-left relative mt-8 shadow-[8px_8px_0_0_#d99a4e]">
          <div className="absolute -top-3 left-4 bg-[#f4f0e6] px-2 text-sm font-bold uppercase tracking-widest text-[#d99a4e]">
            MISSION_BRIEF
          </div>
          <ol className="text-left font-serif text-lg space-y-4 text-[#1e1e1e]/90 leading-relaxed">
            <li className="flex gap-4">
              <span className="font-mono text-[#d99a4e] font-bold">/01</span>
              <span>The subject is highly panicked and will immediately begin a hostile rant.</span>
            </li>
            <li className="flex gap-4">
              <span className="font-mono text-[#d99a4e] font-bold">/02</span>
              <span>Listen closely for clues and pull the right threads to uncover their <strong className="font-black">hidden backstory</strong>.</span>
            </li>
            <li className="flex gap-4">
              <span className="font-mono text-[#d99a4e] font-bold">/03</span>
              <span>Use empathy to lower their <strong className="font-black">Stress Level</strong> and force a peaceful surrender.</span>
            </li>
          </ol>
        </div>
      </div>

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
                onClick={() => { setReport(null); setRefreshTrigger(r => r + 1); }}
                className="bg-[#1e1e1e] text-[#f4f0e6] font-mono font-bold text-xl px-8 py-4 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#d99a4e] hover:translate-y-1 hover:shadow-[2px_2px_0_0_#d99a4e] transition-all"
              >
                RETRY WITH NEW SUBJECT
              </button>
              <button
                onClick={() => { setReport(null); }}
                className="bg-white/80 text-[#1e1e1e] font-mono font-bold text-xl px-8 py-4 border-2 border-[#1e1e1e] shadow-[4px_4px_0_0_#1e1e1e] hover:translate-y-1 hover:shadow-[2px_2px_0_0_#1e1e1e] transition-all"
              >
                BACK TO PROFILE
              </button>
              <button
                onClick={() => { setReport(null); setPersona('robber'); setDifficulty('medium'); setRefreshTrigger(r => r + 1); }}
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
                <label className="font-mono text-sm font-bold tracking-widest text-[#1e1e1e] opacity-70">
                  SUBJECT_PROFILE
                </label>
                <select
                  value={persona}
                  onChange={(e) => setPersona(e.target.value)}
                  className="w-full bg-[#f4f0e6] text-[#1e1e1e] border-4 border-[#1e1e1e] font-serif font-bold text-xl p-3 shadow-[6px_6px_0_0_#d99a4e] focus:outline-none focus:ring-0 appearance-none rounded-none cursor-pointer"
                >
                  <option value="robber">01 - The Cornered Thief</option>
                  <option value="scammed">02 - The Scammed Investor</option>
                  <option value="founder">03 - The Betrayed Founder</option>
                  <option value="custom">04 - [ CREATE CUSTOM ]</option>
                </select>
              </div>

              <div className="flex flex-col gap-2 w-48">
                <label className="font-mono text-sm font-bold tracking-widest text-[#1e1e1e] opacity-70">
                  DIFFICULTY
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full bg-[#f4f0e6] text-[#1e1e1e] border-4 border-[#1e1e1e] font-serif font-bold text-xl p-3 shadow-[6px_6px_0_0_#d99a4e] focus:outline-none focus:ring-0 appearance-none rounded-none cursor-pointer"
                >
                  <option value="low">LOW</option>
                  <option value="medium">MEDIUM</option>
                  <option value="high">HIGH</option>
                </select>
              </div>
            </div>

            {persona === 'custom' && (
              <div className="w-full max-w-xl bg-[#1e1e1e] text-[#f4f0e6] p-6 border-4 border-[#d99a4e] shadow-[8px_8px_0_0_#d99a4e] flex flex-col gap-4 mt-2">
                <h3 className="font-mono text-sm font-bold tracking-widest text-[#d99a4e]">CUSTOM_GENERATOR</h3>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="text-xs font-bold font-mono opacity-80 mb-1 block">NAME</label>
                    <input type="text" value={customName} onChange={e => setCustomName(e.target.value)} className="w-full bg-transparent border-b-2 border-[#f4f0e6] p-2 font-serif text-lg focus:outline-none" />
                  </div>
                  <div className="w-24">
                    <label className="text-xs font-bold font-mono opacity-80 mb-1 block">AGE</label>
                    <input type="number" value={customAge} onChange={e => setCustomAge(e.target.value)} className="w-full bg-transparent border-b-2 border-[#f4f0e6] p-2 font-serif text-lg focus:outline-none" />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs font-bold font-mono opacity-80 mb-1 block">PROFESSION</label>
                    <input type="text" value={customProfession} onChange={e => setCustomProfession(e.target.value)} className="w-full bg-transparent border-b-2 border-[#f4f0e6] p-2 font-serif text-lg focus:outline-none" />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-bold font-mono opacity-80 mb-1 block">SITUATION / MOTIVE</label>
                  <textarea value={customMotive} onChange={e => setCustomMotive(e.target.value)} className="w-full bg-transparent border-2 border-[#f4f0e6] p-2 font-serif text-lg h-24 focus:outline-none resize-none" />
                </div>
              </div>
            )}

            {/* Persona Dossier Preview */}
            <div className="w-full max-w-lg mt-4 bg-white/50 p-4 border-l-4 border-[#1e1e1e] font-serif text-sm text-[#1e1e1e]/80">
              <strong className="font-mono uppercase tracking-widest text-xs mb-1 block">Intel:</strong>
              {currentIntel}
            </div>

            <button
              onClick={connect}
              disabled={isConnecting}
              className={`px-8 py-4 font-mono font-bold text-xl uppercase tracking-widest text-[#f4f0e6] transition-all
                ${isConnecting ? 'bg-[#1e1e1e]/50 cursor-not-allowed' : 'bg-[#1e1e1e] hover:bg-[#dc2626] shadow-[4px_4px_0_0_#d99a4e] hover:shadow-[2px_2px_0_0_#d99a4e] hover:translate-y-[2px] hover:translate-x-[2px]'}
              `}
            >
              {isConnecting ? 'CONNECTING TO ROOM...' : 'CONNECT TO NEGOTIATION'}
            </button>
          </div>
        ) : (
          <div className="w-full max-w-4xl bg-[#f4f0e6] border-4 border-[#1e1e1e] shadow-[12px_12px_0_0_#1e1e1e] relative overflow-hidden p-6 mt-8">
            <div className="absolute top-0 right-0 bg-[#d99a4e] text-[#1e1e1e] font-mono text-xs font-bold px-3 py-1 border-b-4 border-l-4 border-[#1e1e1e]">
              LIVE_FEED // SUBJECT: {currentName}
            </div>
            {/* Dossier Display during connection */}
            <div className="mb-6 p-3 bg-white/50 border border-[#1e1e1e]/20 font-serif text-sm text-[#1e1e1e]/90 text-left">
              <strong className="font-mono uppercase tracking-widest text-[#dc2626] text-xs mr-2">Subject Intel:</strong>
              {currentIntel}
            </div>
            
            <LiveKitRoom
              serverUrl={process.env.NEXT_PUBLIC_LIVEKIT_URL}
              token={token}
              connect={true}
              onDisconnected={disconnect}
              audio={true}
              video={false}
            >
              <Watchdog onDisconnect={disconnect} isHolding={tacticalHold} />
              <SimulationUI
                subjectName={currentName}
                tacticalHold={tacticalHold}
                setTacticalHold={setTacticalHold}
              />
              <MissionStatus onReport={setReport} />
              <RoomAudioRenderer />
            </LiveKitRoom>
          </div>
        )}
      </div>
    </main>
  );
}
