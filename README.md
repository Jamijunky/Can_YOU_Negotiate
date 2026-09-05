# Can You Negotiate?

A real-time, voice-first crisis negotiation simulator built for the DataForge x Rime Hackathon.

Instead of typing back and forth with a bot, you pick up a live line with a cornered, panicked subject and have to de-escalate them using only your voice. 

---

## Links

- **Live Web App**: [https://can-you-negotiate.vercel.app](https://can-you-negotiate.vercel.app)
- **GitHub**: [https://github.com/Jamijunky/Can_YOU_Negotiate](https://github.com/Jamijunky/Can_YOU_Negotiate)
- **Deliverables & Breakdown**: [DELIVERABLES.md](./DELIVERABLES.md)
- **Latency Benchmarks & Voice Test Notes**: [RIME_EVIDENCE.md](./RIME_EVIDENCE.md)

---

## Why Voice (and why text doesn't work here)

Standard text chatbots can't simulate negotiation. In real crises, what matters is tone, hesitation, panic, and above all, the ability to cut someone off before they do something stupid.

We built this simulator to solve three practical voice engineering problems:

1. **True mid-sentence barge-in**: When the subject starts spiraling into a frantic monologue, you can talk right over them. The audio cuts out in ~250ms, and more importantly, the AI forgets the rest of the sentence it never got to say and reacts to being interrupted.
2. **Distinct acoustic personalities via Rime Mist v3**: A terrified 22-year-old thief sounds totally different from an aggressive white-collar fraudster. We map character archetype and gender to specific Rime voices (`marley`, `marsh`, `colin`, `amber`, etc.) so the pitch, breathiness, and emotional strain fit the story.
3. **No text spoilers & no broken bubbles**: The transcript doesn't dump the whole paragraph the second the AI starts thinking. Words stream at a natural speaking rate (~2.8 words/sec). When the user pauses for a couple seconds to think, their words stay together in one turn bubble instead of splintering into separate cards.
4. **Tactical Hold**: Negotiators need a second to check their notes or confer with a partner. Hit `[ TACTICAL HOLD ]` to mute the mic and pause watchdog timeouts without dropping the call.

---

## How It Works

```
Browser (Next.js 16 + LiveKit Audio)
   │
   ▼  WebRTC (<50ms audio relay)
LiveKit Cloud
   │
   ▼  Real-time session
Python Agent (LiveKit Agents framework)
   ├─ VAD: Silero (detects barge-in within 300ms)
   ├─ STT: Whisper-large-v3-turbo on Groq (<150ms)
   ├─ LLM: GPT-OSS-120B on Groq
   ├─ TTS: Rime Mist v3 via WebSocket
   └─ Memory: Prunes unspoken speech on interrupt + tracks stress (1-100)
```

---

## Rime Voice Setup

We use `livekit-plugins-rime` with model `mistv3` over WebSocket streaming. 

| Persona & Archetype | Gender | Voice Used | Why |
| :--- | :--- | :--- | :--- |
| Cornered Thief (Panicked / Desperate) | Female | `marley` | High breathiness, vocal exhaustion, erratic rhythm |
| Cornered Thief (Panicked / Desperate) | Male | `marsh` | Panicky pitch shifts, unstable delivery |
| Scammed Investor (Aggressive / Paranoid) | Male | `colin` | Tense, defensive, fast staccato attack |
| Scammed Investor (Aggressive / Paranoid) | Female | `amber` | Sharp, suspicious, agitated pitch |
| Embezzler / Founder (Calculating / Erratic) | Male | `trent` | Cold composure that cracks under direct questioning |
| Embezzler / Founder (Calculating / Erratic) | Female | `reese` | Guarded, defensive, evasive pacing |

---

## Running It Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- LiveKit Cloud account
- Rime API key
- Groq API key

### 1. Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Fill in `backend/.env` with your `LIVEKIT_*`, `GROQ_API_KEY`, and `RIME_API_KEY`. Then start the agent:
```bash
python agent.py dev
```

### 2. Frontend
In another terminal:
```bash
cd frontend
npm install
cp .env.example .env.local
```
Fill in `frontend/.env.local` with your `NEXT_PUBLIC_LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `GROQ_API_KEY`.
```bash
npm run dev
```
Open `http://localhost:3000` in Chrome, click connect, and speak into your mic.

---

## What to Try When Testing

1. **Cut the subject off**: When they start rambling, firmly say *"Stop talking and listen to me!"* Notice how the Rime voice immediately cuts off, the comms log chops off at the exact word spoken, and they push back on being interrupted.
2. **Use Tactical Hold**: Click the `[ TACTICAL HOLD // THINK TIME ]` button. Your mic mutes and the room won't time out while you plan your next move.
3. **Surrender or Fail**: If you listen and de-escalate, their stress drops below 20 and they surrender. If you bluff or dismiss them, stress hits 100 and the call fails. Either way, you get a full post-action debrief card grading your negotiation.
