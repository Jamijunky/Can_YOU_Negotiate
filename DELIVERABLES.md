# Deliverables & Project Notes

Here is everything built and submitted for the DataForge x Rime Voice AI Challenge 2026.

---

## Deliverable Links

- **Live Web App**: [https://can-you-negotiate.vercel.app](https://can-you-negotiate.vercel.app)
- **GitHub Repository**: [https://github.com/Jamijunky/Can_YOU_Negotiate](https://github.com/Jamijunky/Can_YOU_Negotiate)
- **Voice Benchmarks & Interruption Tests**: [RIME_EVIDENCE.md](./RIME_EVIDENCE.md)
- **100-Profile Stress Test Report**: [audit_100_profiles_report.json](./audit_100_profiles_report.json)

---

## What We Built

A full-duplex crisis negotiation simulator where you talk to an emotionally volatile subject in real time. 

Instead of waiting for a chatbot to finish talking, you can interrupt them mid-sentence, navigate their changing stress levels, and get graded on your negotiation skills when the call ends.

### Key Highlights
- **Sub-500ms Barge-In**: Silero VAD detects user voice within ~300ms. Rime TTS playback halts immediately (~200ms client flush).
- **Context-Aware Interruption**: The agent calculates roughly what fraction of words actually made it out of the speakers before the cutoff, prunes the unspoken words from LLM history, and reacts to being spoken over.
- **Acoustic Matching**: We tested multiple Rime Mist v3 voices (`marley`, `marsh`, `amber`, `colin`, `reese`, `trent`) and mapped them to character archetypes based on breathiness, jitter, and perceived tension.
- **Progressive Transcript Pacing**: The on-screen text streams in real time (~2.8 words/second) alongside the audio instead of printing the whole block ahead of time and spoiling what the AI is about to say.
- **Tactical Think Time**: A dedicated `Tactical Hold` toggle lets the user mute their mic and prevent connection timeouts while they think through their next statement.
- **Debrief Scoring**: Once the negotiation wraps up (surrender or escalation), an LLM evaluator grades the interaction across Empathy, De-escalation, and Active Listening, and gives concrete pointers on what to do better next round.

---

## Stack
- **Audio & RTC**: LiveKit Cloud, `@livekit/components-react`, `livekit-agents` Python SDK
- **Voices**: Rime Mist v3 WebSocket streaming (`livekit-plugins-rime`)
- **Speech-to-Text**: Whisper Large v3 hosted on Groq
- **LLM**: GPT-OSS-120B & Llama 3 via Groq API
- **Frontend**: Next.js 16, Tailwind CSS, TypeScript
- **Deployment**: Vercel (frontend), Render / Docker-ready (backend agent worker)
