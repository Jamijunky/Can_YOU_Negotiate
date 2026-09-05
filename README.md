# Negotiate-It: Real-Time Crisis Negotiation Simulator

[![LiveKit](https://img.shields.io/badge/LiveKit-WebRTC%20Full--Duplex-brightgreen)](https://livekit.io/)
[![Rime](https://img.shields.io/badge/Rime-Mist%20v3%20Expressive%20TTS-blue)](https://rime.ai/)
[![Groq](https://img.shields.io/badge/Groq-Llama%20%26%20Whisper-orange)](https://groq.com/)

> **DataForge x Rime Hackathon Submission**  
> An autonomous, full-duplex conversational AI crisis negotiation simulator solving real-time verbal interruptions, dynamic acoustic profiling, and adversarial behavioral calibration.

---

## 🔗 Deliverable Links

- **GitHub Repository**: [https://github.com/Jamijunky/Can_YOU_Negotiate](https://github.com/Jamijunky/Can_YOU_Negotiate)
- **Demo Video Walkthrough**: *[Link to Loom / Video Demo]* *(Placeholder: Add your video demonstration link here)*
- **Live Deployment**: *[Link to Live Hosted App]* *(Placeholder: Add your hosted URL if deployed)*
- **Technical Evidence & Proof**: [RIME_EVIDENCE.md](./RIME_EVIDENCE.md)

---

## 🎯 Overview & Hard Voice Claim

In hostage and crisis negotiation, **text cannot substitute for voice**. Critical human cues—vocal tremor, frantic speech tempo, sudden outbursts, and the ability to verbally break in and cut off a spiraling individual—dictate survival.

**Negotiate-It** proves that voice AI can operate in high-stakes conversational environments where:
1. **Verbal Interruptions are Handled with Sub-500ms Precision**: When a human negotiator cuts off a ranting subject, audio playback halts instantly, stale speech context is pruned, and the subject reacts like an actual human being whose sentence was broken.
2. **Acoustic Personas Match Character Identity**: Every subject profile dynamically receives a gender- and archetype-congruent voice powered by **Rime's `mistv3`** model (e.g. frantic male vs. paranoid female vs. cold corporate sociopath).
3. **Synchronized Dialogue Pacing (Zero Spoilers)**: The dialogue transcript streams in sync with vocal articulation (~2.8 words/sec) rather than spoiling future speech ahead of time.
4. **Tactical Comms Hold ("Think Time")**: Real crisis negotiators need strategic timeouts; a tactical hold button mutes comms and pauses timeouts while formulating responses.
5. **Self-Calibrating Cognition Engine**: A 4-stage cognitive engine tracks stress levels in real-time, logs outcomes into an `ExperienceStore` SQLite database, and dynamically calibrates resistance thresholds across 100+ simulated profiles.

---

## 🏗️ Architecture

```
                               ┌────────────────────────────────────────┐
                               │             USER / BROWSER             │
                               │  - Next.js 16 (React 19, Tailwind)    │
                               │  - LiveKit Components React SDK        │
                               │  - Real-time Audio Visualizer & Comms  │
                               └──────────────────┬─────────────────────┘
                                                  │ WebRTC Audio & Data
                                                  ▼
                               ┌────────────────────────────────────────┐
                               │           LIVEKIT CLOUD / RTC          │
                               │  - Full-Duplex WebRTC Room Server      │
                               │  - Sub-50ms Global Audio Relay         │
                               └──────────────────┬─────────────────────┘
                                                  │ WebRTC Session
                                                  ▼
               ┌────────────────────────────────────────────────────────────────────────┐
               │                        PYTHON AGENT BACKEND                            │
               │  - LiveKit Agents v1.7 Framework                                       │
               │  - VAD: Silero (300ms speech endpointing & barge-in detection)         │
               │  - STT: OpenAI Whisper-large-v3 via Groq (Ultra low-latency STT)       │
               │  - LLM: GPT-OSS-120B / Llama 3 via Groq API (<600ms TTFT)              │
               │  - TTS: Rime Mist v3 (WebSocket Streaming, Dynamic Speaker Selection)  │
               │  - Interruption Handler: LiveKit SpeechHandle playout estimation       │
               │  - Cognition Engine: ExperienceStore + LearningCalibrationEngine       │
               └────────────────────────────────────────────────────────────────────────┘
```

---

## 🎙️ Exact Rime Configuration

- **Provider**: `livekit-plugins-rime`
- **Model ID**: `mistv3`
- **Transport**: WebSocket streaming (`use_websocket=True`)
- **Dynamic Speaker Selection Table**:

| Character Archetype | Female Voice | Male Voice | Expressive Delivery Rationale |
| :--- | :--- | :--- | :--- |
| **Panicked / Desperate** (Robber, Cornered) | `marley` | `marsh` | High breathiness, frantic cadence, vocal instability |
| **Paranoid / Aggressive** (Conspiracy, Scammed) | `amber` | `colin` | Sharp staccato attacks, suspicious pitch shifts |
| **Deceptive / Calculating** (Embezzler, Founder) | `reese` | `trent` | Monotone masking, abrupt emotional breakaways |
| **Erratic / Volatile** (Hostile hostage taker) | `marley` | `marsh` | Sudden loudness modulation, rapid vocal inflection |

---

## ⚡ Core Voice Innovations

### 1. Zero-Leak Real-Time Interruption Recovery
- When the user speaks, Silero VAD fires barge-in within 300ms.
- The assistant immediately calculates `elapsed * 2.6` words to truncate the speech buffer down to what was *physically heard*.
- The internal LLM memory prunes the unspoken text and appends `[Negotiator interrupted you here; you did not finish saying the rest of your statement]`, preventing the AI from assuming the user heard unspoken plans.

### 2. Streamed Transcript (No Spoilers) & Bubble Grouping
- Real-time words stream to the web UI at conversational pacing (~2.8 words/sec). If the subject is cut off after 4 words, the transcript box only shows those 4 words with an ellipsis (`...`).
- Consecutive user speech segments during natural 2-3 second pauses are intelligently merged into a single turn bubble rather than fragmenting.

### 3. Tactical Hold ("Think Time")
- Crisis negotiators can engage **`[ TACTICAL HOLD // THINK TIME ]`** to mute the microphone track and suspend room timeouts while strategizing without breaking immersion.

### 4. Continuous Experience Calibration (100+ Profile Run)
- An automated audit run across 100 diverse demographic & psychological profiles verified the AI's resistance to bluffs, de-escalation pathways, and post-action debrief generation.
- Recorded in [`audit_100_profiles_report.json`](./audit_100_profiles_report.json).

---

## 🚀 Quickstart & Setup Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- LiveKit Cloud project ([livekit.io](https://livekit.io/))
- Rime API Key ([rime.ai](https://rime.ai/))
- Groq API Key ([groq.com](https://groq.com/))

---

### Step 1: Clone Repository
```bash
git clone https://github.com/Jamijunky/Can_YOU_Negotiate.git
cd Can_YOU_Negotiate
```

---

### Step 2: Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure `backend/.env`:
```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
GROQ_API_KEY=gsk_...
RIME_API_KEY=your_rime_key
```

Run the backend agent worker:
```bash
python agent.py dev
```

---

### Step 3: Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
cp .env.example .env.local
```

Configure `frontend/.env.local`:
```env
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
GROQ_API_KEY=gsk_...
```

Start the web interface:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in Chrome.

---

## 🎮 How to Play / Test
1. Select a **Subject Profile** (e.g. *The Cornered Thief*, *The Scammed Investor*, or *Custom*).
2. Choose **Difficulty** (`LOW`, `MEDIUM`, `HIGH`).
3. Click **CONNECT TO NEGOTIATION**.
4. The subject will immediately initiate an emotional, frantic phone call.
5. **Test Verbal Barge-in**: While the subject is ranting, speak firmly: *"Stop right there! Put the weapon down and listen to me!"*
   - Notice the Rime voice immediately stops.
   - The subject responds directly to your interrupt.
6. **Use Tactical Hold**: Press **`[ TACTICAL HOLD // THINK TIME ]`** whenever you need to strategize quietly.
7. Upon resolution, a complete **Post-Action Debrief Report** with category grading (Empathy, De-escalation, Active Listening) will be generated!

---

## 🧪 Testing & Verification

Run backend unit tests and verification suites:
```bash
cd backend
pytest -v
```

---

## 📄 License & Attribution
Built for the **DataForge x Rime Voice AI Challenge 2026**.
