# Can You Negotiate?

A real-time, voice-first crisis negotiation simulator built for the **DataForge x Rime Hackathon**.

Pick up a live line with a cornered, panicked subject. De-escalate them using only your voice. If you listen, they surrender. If you bluff, they escalate. Every word matters.

**Live Demo**: [can-you-negotiate.vercel.app](https://can-you-negotiate.vercel.app)

---

## Why Voice

Standard text chatbots cannot simulate negotiation. In real crises, tone, hesitation, panic, and the ability to cut someone off are what matter. This product is **impossible without voice**:

- **True mid-sentence barge-in**: Interrupt the subject mid-sentence. Audio stops in ~250ms, the AI discards unsaid words, and reacts to being interrupted.
- **Emotional vocal delivery via Rime Mist v3**: A terrified thief sounds different from an aggressive fraudster. Voice is mapped to character personality.
- **No text spoilers**: Words stream at natural speaking rate (~2.8 words/sec). The transcript matches what you hear, not what the AI planned to say.
- **Full-duplex**: The subject can speak while you speak. No push-to-talk, no turn-taking awkwardness.

---

## Architecture

```
Browser (Next.js 16 + LiveKit Audio)
   │
   ▼  WebRTC (<50ms audio relay)
LiveKit Cloud
   │
   ▼  Real-time session
Python Agent (LiveKit Agents 1.7.1)
   ├─ VAD: Silero (barge-in detection ~300ms)
   ├─ STT: Deepgram Nova-3 (streaming, Smart Format)
   ├─ LLM: Qwen 3.8-27B on Groq (temp 0.82, 400 tokens)
   ├─ TTS: Rime Mist v3 (WebSocket, reduce_latency=True)
   └─ State: Stress meter (1-100), relationship tracking, escalation chain
```

---

## Rime Integration

| Parameter | Value |
|-----------|-------|
| Model | `mistv3` |
| Transport | WebSocket (`use_websocket=True`) |
| Latency Mode | `reduce_latency=True` |
| Speed Alpha | `1.05` |

### Voice-to-Character Mapping

| Persona | Gender | Voice | Why |
|---------|--------|-------|-----|
| Cornered Thief (Panicked) | Female | `marley` | High breathiness, vocal exhaustion |
| Cornered Thief (Panicked) | Male | `marsh` | Panicky pitch shifts |
| Scammed Investor (Aggressive) | Male | `colin` | Fast staccato, tense delivery |
| Scammed Investor (Aggressive) | Female | `amber` | Sharp, agitated pitch |
| Embezzler (Calculating) | Male | `trent` | Cold composure that cracks |
| Embezzler (Calculating) | Female | `reese` | Guarded, evasive pacing |

---

## Hard Voice Problem: Full-Duplex Interruption

**The challenge**: When the negotiator interrupts a spiraling subject, the system must stop Rime audio, discard unsaid words, and have the AI react to being interrupted — all within 500ms.

**Our solution**:
1. Silero VAD detects user speech onset (~300ms)
2. LiveKit interrupts the Rime audio stream (~250ms)
3. Agent receives interrupt signal, discards unsaid LLM output
4. Agent's next response acknowledges the interruption
5. Transcript shows only what was actually spoken

**Acceptance test and results**: See [RIME_EVIDENCE.md](./RIME_EVIDENCE.md)

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- LiveKit Cloud account (free tier works)
- Rime API key
- Groq API key
- Deepgram API key

### 1. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python agent.py dev
```

### 2. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your API keys
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), click Connect, and speak into your mic.

### Environment Variables

**Backend** (`backend/.env`):
```
LIVEKIT_URL=wss://your-domain.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
GROQ_API_KEY=your_groq_key
RIME_API_KEY=your_rime_key
```

**Frontend** (`frontend/.env.local`):
```
NEXT_PUBLIC_LIVEKIT_URL=wss://your-domain.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
GROQ_API_KEY=your_groq_key
```

---

## Third-Party Services

| Service | Purpose | Pricing |
|---------|---------|---------|
| [LiveKit Cloud](https://livekit.io) | WebRTC transport, room management | Free tier (50 min/mo) |
| [Rime AI](https://rime.ai) | Text-to-speech (mistv3) | Hackathon credits |
| [Groq](https://groq.com) | LLM inference (Qwen 3.8-27B) | Free tier |
| [Deepgram](https://deepgram.com) | Speech-to-text (Nova-3) | Free tier |
| [Vercel](https://vercel.com) | Frontend hosting | Free tier |
| [Render](https://render.com) | Backend hosting | Free tier |

---

## Known Limitations

1. **Free tier CPU**: Render free tier can cause Silero VAD overload after ~2 minutes of continuous use. Production would use a paid tier.
2. **English only**: Rime supports multilingual but we focused on English for scope.
3. **Transcript delay**: Deepgram final transcriptions have ~0.5s latency before appearing.
4. **Single session**: Each connection creates a new room. No session persistence across page reloads.

---

## Project Structure

```
├── backend/
│   ├── agent.py              # LiveKit agent with negotiation logic
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Backend environment template
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Main page with LiveKit connection
│   │   ├── error.tsx         # Error boundary
│   │   └── api/
│   │       ├── token/route.ts    # LiveKit token endpoint
│   │       └── scenario/route.ts # AI scenario generation
│   ├── components/
│   │   ├── LiveTranscriptFeed.tsx  # Live transcript display
│   │   ├── MissionStatus.tsx       # Stress meter + surrender/escalation
│   │   ├── SimulationUI.tsx        # Connection UI + controls
│   │   ├── IntelDisplay.tsx        # Scenario intelligence display
│   │   ├── EmotionalArc.tsx        # Stress history graph
│   │   ├── EscalationIndicator.tsx # Escalation stage display
│   │   ├── RelationshipDisplay.tsx # Rapport/trust metrics
│   │   ├── CoachingHints.tsx       # Training mode hints
│   │   └── LiveKitErrorBoundary.tsx # Component error isolation
│   ├── lib/
│   │   ├── types.ts          # TypeScript type definitions
│   │   ├── constants.ts      # Configuration constants
│   │   └── scenarios.ts      # 21 persona scenarios with OCEAN scores
│   └── .env.example          # Frontend environment template
├── render.yaml               # Render deployment config
├── RIME_EVIDENCE.md          # Hackathon evidence document
└── README.md                 # This file
```

---

## License

Built for the DataForge x Rime Hackathon 2026.
