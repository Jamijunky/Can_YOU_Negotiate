# Rime Voice Evidence & Acceptance Tests

## Why Voice Matters Here

Text chatbots don't work for crisis negotiation. The whole dynamic hinges on pacing, pauses, emotional crack in the voice, and whether you can interrupt someone before they pull a trigger. 

We used Rime's `mistv3` voice model connected to LiveKit's WebRTC agent pipeline to test full-duplex conversational voice with sub-second interruption and realistic character acting.

---

## Latency Numbers (Measured Live)

| Step | What We Used | Observed Latency |
| :--- | :--- | :--- |
| **Barge-in detection (VAD)** | Silero VAD (0.3s speech threshold) | ~300ms |
| **WebRTC audio roundtrip** | LiveKit Cloud | ~40 - 65ms |
| **STT transcription** | Whisper Large v3 on Groq | ~200 - 240ms |
| **LLM response generation** | GPT-OSS-120B / Llama 3 on Groq | ~500 - 620ms |
| **TTS first audio chunk (TTFB)** | Rime Mist v3 (WebSocket) | ~220 - 280ms |
| **Total time from user speech to subject audio stopping** | Silero VAD + LiveKit buffer flush | **~250 - 350ms** |

---

## Acceptance Tests

### 1. The Mid-Sentence Interruption Test
- **Setup**: Start a call with Maria (The Cornered Thief).
- **Behavior**: She starts ranting immediately: *"I don't know what to do! Everything is falling apart... I didn't want to hurt anybody, but the alarm went off and now there are sirens everywhere! Don't you dare come in here!"*
- **Action**: Around word 6 or 7, speak loudly: *"Maria, hold on! Stop and take a deep breath."*
- **Expected Outcome**:
  - Rime audio stops playing in under 350ms.
  - The transcript box cuts off with `...` right around where she stopped talking, instead of showing the rest of the monologue.
  - Her internal chat context replaces the unsaid words with a note that she got cut off.
  - Her next response reacts directly to being interrupted (*"Don't tell me to breathe! You don't know what's happening!"*).

### 2. Voice Persona Mapping
We tested different Rime voices to find which ones actually sound distressed or defensive rather than robotic:
- **`marley`**: Best female voice for panicked/frantic delivery. High breathiness and natural pauses.
- **`marsh`**: Best male voice for someone on the verge of tears or spiraling out of control.
- **`colin`**: Fast, aggressive attack. Works well for hostile, suspicious characters.
- **`amber`**: Sharp and agitated tone.
- **`trent` / `reese`**: Lower-energy, defensive pacing for calculating or cornered corporate characters.

### 3. Progressive Transcript Playout
- **Problem observed during testing**: Dumping the entire 35-word LLM reply into the UI comms log immediately spoiled the line before the voice had even uttered the first two words. If the user interrupted, the chat log made no sense.
- **Fix**: Words now stream to the UI in chunks of 3 at ~2.8 words/second, matching speech pacing. If you cut the subject off, what's on screen matches what you actually heard.
