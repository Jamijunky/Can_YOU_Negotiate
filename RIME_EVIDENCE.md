# RIME_EVIDENCE.md

## Demo Video

**YouTube**: https://youtu.be/VxV1gFdveb8

---

## Hard Voice Claim

**Removing speech from this product destroys it.** Crisis negotiation is fundamentally a voice-first, full-duplex interaction. The entire simulation depends on:

- Real-time mid-sentence interruption (barge-in) where the negotiator cuts off a spiraling subject
- Emotional Rime vocal delivery that conveys panic, desperation, and escalation in character
- Natural pacing — words stream at ~2.8 words/sec speaking rate, no text dump
- Silence reactions — the subject responds to the negotiator going quiet, in character
- No push-to-talk: full duplex, the subject can be cut off at any word

A text chatbot with a play button leaves the experience entirely intact. The voice **is** the product.

---

## Voice-Specific Challenge Solved

**Full-duplex interruption and recovery under emotional load** (Interruption and recovery track).

We built a crisis negotiation simulator where the AI subject (voiced by Rime `mistv3`) can be interrupted mid-sentence by the negotiator. The system must:

1. Detect the user's barge-in within ~300ms (Silero VAD)
2. Stop Rime audio playback immediately (~250ms)
3. Discard the unsaid portion of the subject's planned response
4. Have the AI react to being interrupted in its next turn — in character
5. Keep the transcript consistent with what was **actually spoken**, not what was planned

This is realistic, high-stakes interaction — the subject's personality determines how they react to being cut off. A paranoid veteran reacts differently to interruption than a grieving elder.

---

## Rime Configuration

| Parameter | Value |
|-----------|-------|
| **Model** | `mistv3` |
| **Language** | `en-US` |
| **Transport** | WebSocket (`use_websocket=True`) |
| **Latency mode** | `reduce_latency=True` |
| **Speed alpha** | `1.05` |
| **Audio format** | PCM 24kHz (LiveKit default) |
| **Endpoint** | Rime WebSocket via `livekit-plugins-rime` |

---

## Voice-to-Personality Mapping

Rime voices are selected dynamically per session using the subject's OCEAN personality scores (Big Five). A subject's `neuroticism`, `extraversion`, and `agreeableness` map to voice archetype banks. The voice is never hardcoded — it is computed from character data.

| Archetype | Personality Pattern | Female Voices | Male Voices |
|-----------|--------------------|----|-----|
| Frantic / Panicked | neuroticism ≥ 0.7 | `breeze`, `iris`, `rain` | `falcon`, `cove`, `river` |
| Aggressive | extraversion ≥ 0.7, agreeableness < 0.4 | `astra`, `lyra` | `stone`, `storm`, `hawk` |
| Cold / Calculating | neuroticism < 0.3, extraversion < 0.3 | `lyra`, `astra` | `cedar`, `stone`, `marsh` |
| Desperate | agreeableness ≥ 0.7, neuroticism ≥ 0.5 | `willow`, `iris` | `ember`, `marsh`, `cove` |
| Default / Mixed | all other profiles | `lyra`, `astra`, `breeze`, `iris`, `willow`, `rain` | `marsh`, `cove`, `cedar`, `falcon`, `stone`, `river` |

Voice is also deterministically hashed from the subject's name within the archetype bank, so the same character always gets the same voice across runs.

---

## Acceptance Test: Mid-Sentence Interruption

### Configuration used

- **Rime model**: `mistv3`
- **Rime speaker**: `falcon` (male, frantic archetype — mapped from high neuroticism)
- **Transport**: WebSocket (`use_websocket=True`, `reduce_latency=True`)
- **STT**: Deepgram Nova-3, `en-US`, Smart Format + punctuation
- **LLM**: Qwen 3.8-27B on Groq (temperature 0.82, max 600 tokens)
- **VAD**: Silero (speech threshold 0.3s, silence 0.8s, activation 0.7)
- **Transport layer**: LiveKit Cloud WebRTC

### Procedure

1. Open [can-you-negotiate.vercel.app](https://can-you-negotiate.vercel.app)
2. Select **"06 – The Unpaid Worker"** (Marcus / high-neuroticism, aggressive)
3. Click **CONNECT TO NEGOTIATION** — subject begins speaking immediately
4. Wait for the subject to begin a long rant (typically 8–12 words in)
5. Interrupt firmly: **"Marcus — stop. I hear you."**
6. Observe behavior within 500ms

### Expected Results

| Observable | Acceptance Criterion | Result |
|-----------|---------------------|--------|
| Rime audio stops | Within 350ms of VAD detection | ✅ ~250–350ms measured |
| Transcript cutoff | Shows only spoken words, not planned text | ✅ Transcript matches audio |
| Agent context | Unsaid words discarded, not replayed | ✅ Agent receives interrupt signal |
| Next subject response | Reacts to being cut off, in character | ✅ Subject pushes back or pivots |
| Application state | No desync, conversation continues | ✅ No restart needed |

### Result

**PASS.** Rime audio cuts within ~300ms of VAD detecting the user's voice. The transcript reflects only what was audibly spoken. The subject's next turn acknowledges being interrupted — in character — rather than continuing the canned speech.

---

## Stress Case: Silence (No Input from Negotiator)

### Procedure

1. Start a negotiation session
2. Let the subject finish speaking
3. Say nothing for 12+ seconds (do not activate Tactical Hold)

### Expected Result

The subject reacts to the silence in a personality-consistent way. A paranoid subject suspects a trap. A desperate subject pleads. An aggressive subject escalates.

### Result

**PASS.** The `_silence_watcher` coroutine fires after 12 seconds of user inactivity. It calls `session.generate_reply()` with a prompt that instructs the LLM to react as the character would to silence. The reaction is personality-driven, not generic.

---

## Stress Case: Agent Disconnect Mid-Negotiation

### Procedure

1. Begin a session at escalation Stage 2 (Hostile), stress ~70%
2. Kill the backend agent process

### Expected Result

- Frontend LiveKitErrorBoundary catches disconnect
- Clear error message displayed
- No zombie audio or stale connections

### Result

**PASS.** Error boundary catches the disconnect. Watchdog component (`Watchdog.tsx`) additionally times out if agent never joins (90s) or drops mid-call (4s grace period).

---

## Repeatable Test

To reproduce the interruption test locally:

```bash
# Terminal 1 — start backend
cd backend
source venv/bin/activate
python agent.py dev

# Terminal 2 — start frontend
cd frontend
npm run dev

# Browser
# 1. Open http://localhost:3000
# 2. Select persona 06 (The Unpaid Worker)
# 3. Click CONNECT TO NEGOTIATION
# 4. Wait for subject to start speaking (first line is immediate)
# 5. Interrupt with "Marcus, hold on." around word 6-8
# 6. Observe transcript — should show partial subject line, then your line, then subject's reaction
```

---

## Limitations

1. **Rime WebSocket cold start**: First TTS request after idle has +200ms latency. Subsequent requests within the session are fast (`reduce_latency=True`).
2. **VAD sensitivity**: Very quiet environments or headset mic may require speaking at normal volume. Whispering may not trigger VAD.
3. **Free tier CPU**: Render free tier causes occasional Silero VAD overload after ~2 min continuous conversation. Production would use paid CPU.
4. **Transcript is final-only**: Deepgram interim transcriptions are not shown — ~0.5s delay before user text appears.
5. **English only**: Currently `en-US`. Rime supports multilingual but English was chosen for hackathon scope.
6. **Silence watcher cooldown**: Subject reacts to silence at most once every 20 seconds to avoid spamming. Consecutive silences after the first reaction are not triggered until the cooldown expires.
