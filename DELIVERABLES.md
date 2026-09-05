# Can You Negotiate? - Hackathon Deliverables

This document summarizes all official submission links, project deliverables, and architectural specifications for the **DataForge x Rime Voice AI Challenge 2026**.

---

## 🔗 Official Deliverables

| Deliverable | URL / Reference | Description |
| :--- | :--- | :--- |
| **Live Production Website** | [https://frontend-blush-two-21.vercel.app](https://frontend-blush-two-21.vercel.app) | Live Next.js WebRTC frontend deployed on Vercel |
| **GitHub Repository** | [https://github.com/Jamijunky/Can_YOU_Negotiate](https://github.com/Jamijunky/Can_YOU_Negotiate) | Public GitHub repository containing complete source code |
| **Voice Proof & Benchmarks** | [`RIME_EVIDENCE.md`](./RIME_EVIDENCE.md) | Latency benchmarks, full-duplex interruption tests, and acoustic mapping |
| **Cognition Audit Evidence** | [`audit_100_profiles_report.json`](./audit_100_profiles_report.json) | Automated evaluation across 100 demographic & psychological profiles |

---

## 🎯 Executive Summary & Hard Voice Claim

In crisis and hostage negotiations, **voice is non-negotiable**. Text or turn-based chatbots cannot replicate vocal panic, adrenaline-fueled pacing, sudden outbursts, and critical conversational interrupts.

**Can You Negotiate?** is an autonomous, full-duplex crisis negotiation simulator powered by **Rime Mist v3** and **LiveKit WebRTC**. It solves four critical voice AI frontiers:

1. **Sub-500ms Full-Duplex Barge-in & Context Truncation**: When the human negotiator talks over the subject, Rime audio halts immediately (<250ms), unspoken speech is purged from the LLM's memory, and the subject reacts like a real human whose words were cut short.
2. **Dynamic Character Acoustic Profiling**: Automatically assigns distinct female and male voices (`marley`, `marsh`, `amber`, `colin`, `reese`, `trent`) matched to psychological archetypes (Desperate, Aggressive, Deceptive).
3. **Synchronized Dialogue Pacing (Zero Spoilers)**: The dialogue transcript streams in sync with vocal articulation (~2.8 words/sec) rather than spoiling upcoming dialogue.
4. **Tactical Comms Hold ("Think Time")**: Real crisis negotiators need strategic timeouts; a tactical hold button mutes comms and pauses timeouts while formulating responses.

---

## ⚙️ Technology Stack

- **Voice Synthesis (TTS)**: Rime Mist v3 (`livekit-plugins-rime`, WebSocket streaming)
- **Voice Transport (WebRTC)**: LiveKit Cloud SFU
- **Voice Activity Detection (VAD)**: Silero VAD (0.3s barge-in threshold)
- **Speech-to-Text (STT)**: OpenAI Whisper-large-v3 via Groq LPUs
- **Language Intelligence (LLM)**: GPT-OSS-120B / Llama 3 via Groq API
- **Cognition & Learning**: SQLite ExperienceStore + 4-stage Appraisal/Policy engine
- **Frontend UI**: Next.js 16 (React 19, Tailwind CSS, `@livekit/components-react`)
