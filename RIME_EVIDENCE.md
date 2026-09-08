# RIME_EVIDENCE.md

## Hard Voice Claim

**Removing speech from this product destroys it.** Crisis negotiation is fundamentally a voice-first, full-duplex interaction. The entire simulation depends on:

- Real-time interruption (barge-in) where the negotiator cuts off a spiraling subject
- Emotional vocal delivery that conveys panic, desperation, and escalation
- Natural pacing with pauses, stammers, and breathless speech
- No text spoilers — words must stream at speaking rate, not dump as a paragraph

A text-based version would be a chatbot with a play button. The voice *is* the product.

---

## Voice-Specific Challenge Solved

**Full-duplex interruption and recovery under emotional load.**

We built a crisis negotiation simulator where an AI subject (played by Rime TTS) can be interrupted mid-sentence by the user. The system must:

1. Detect the user's barge-in within 300ms (Silero VAD)
2. Stop Rime audio playback immediately (~250ms)
3. Discard the unsaid portion of the subject's response
4. Have the AI react to being interrupted in its next turn
5. Keep the transcript consistent with what was actually spoken

This is a realistic, high-stakes voice interaction — not a chatbot with a microphone.

---

## Acceptance Test: Mid-Sentence Interruption

### Setup
- **Rime Model**: `mistv3`
- **Rime Speaker**: `marley` (female, panicked persona)
- **Transport**: WebSocket (`use_websocket=True`)
- **Latency Mode**: `reduce_latency=True`
- **STT**: Deepgram Nova-3 (streaming, with Smart Format + punctuation)
- **LLM**: Qwen 3.8-27B on Groq (temperature 0.82, max 400 tokens)
- **VAD**: Silero (0.3s speech threshold)
- **Transport**: LiveKit Cloud WebRTC

### Procedure
1. Connect to the simulator and select "The Cornered Thief" (Maria) scenario
2. The subject begins speaking immediately: *"I don't know what to do! Everything is falling apart... I didn't want to hurt anybody, but the alarm went off and now there are sirens everywhere! Don't you dare come in here!"*
3. Around word 6-7, speak firmly: **"Maria, hold on! Stop and take a deep breath."**
4. Observe the following within 500ms:

### Expected Results
| Metric | Target | Measured |
|--------|--------|----------|
| VAD detection of user barge-in | < 300ms | ~300ms |
| Rime audio stop (silence) | < 350ms | ~250-350ms |
| Transcript cutoff consistency | Matches audio | PASS - Transcript shows `...` at cutoff point |
| AI context discard | Unspoken words removed | PASS - Agent receives interrupt signal, discards unsaid text |
| Next AI response | Reacts to interruption | PASS - Subject pushes back: *"Don't tell me to breathe!"* |

### Result
**PASS.** The subject's Rime audio cuts off promptly when the negotiator interrupts. The transcript reflects only what was spoken. The AI's next response acknowledges the interruption naturally. The negotiation continues without requiring a restart.

---

## Voice Persona Mapping

Rime `mistv3` voices are mapped to character archetypes based on vocal characteristics:

| Persona | Gender | Voice | Rationale |
|---------|--------|-------|-----------|
| Cornered Thief (Panicked) | Female | `marley` | High breathiness, vocal exhaustion, erratic rhythm |
| Cornered Thief (Panicked) | Male | `marsh` | Panicky pitch shifts, unstable delivery |
| Scammed Investor (Aggressive) | Male | `colin` | Fast staccato attack, tense delivery |
| Scammed Investor (Aggressive) | Female | `amber` | Sharp, suspicious, agitated pitch |
| Embezzler (Calculating) | Male | `trent` | Cold composure that cracks under pressure |
| Embezzler (Calculating) | Female | `reese` | Guarded, defensive, evasive pacing |

---

## Stress Case: Agent Disconnect During Active Negotiation

### Setup
- Begin a negotiation session
- Subject is at Stage 2 (Hostile), stress at 70%

### Procedure
1. Kill the backend agent process mid-conversation
2. Observe frontend behavior

### Expected Results
- Frontend shows connection error with retry option
- Retry resets to home page (fresh session)
- No orphaned audio or zombie connections

### Result
**PASS.** The error boundary catches the disconnect, displays a clear error message, and the retry button redirects to home for a clean restart.

---

## Configuration

| Parameter | Value |
|-----------|-------|
| **Rime Model** | `mistv3` |
| **Rime Transport** | WebSocket (`use_websocket=True`) |
| **Rime Latency Mode** | `reduce_latency=True` |
| **Rime Speed Alpha** | `1.05` |
| **STT Model** | Deepgram `nova-3` |
| **STT Language** | `en-US` |
| **STT Smart Format** | `True` |
| **STT Punctuate** | `True` |
| **LLM Provider** | Groq |
| **LLM Model** | `qwen/qwen3.8-27b` |
| **LLM Temperature** | `0.82` |
| **LLM Max Tokens** | `400` |
| **VAD** | Silero (0.3s threshold) |
| **Transport** | LiveKit Cloud WebRTC |
| **TTS Text Transforms** | `filter_markdown`, `filter_emoji`, `filter_inner_thoughts` |

---

## Limitations

1. **Rime WebSocket cold start**: First TTS request after idle may have +200ms latency due to connection establishment. Subsequent requests are fast.
2. **VAD sensitivity**: Very quiet speech may not trigger VAD, causing the subject to keep talking. The negotiator can use Tactical Hold to pause.
3. **Free tier constraints**: Render free tier has CPU limitations that can cause VAD overload after ~2 minutes of continuous conversation. Production deployment would use a paid tier.
4. **Single-language**: Currently English only. Rime supports multilingual models but we focused on English for the hackathon scope.
5. **Transcript is final-only**: Deepgram intermediate transcriptions are not shown (they were unreliable). There's a ~0.5s delay before user text appears in the transcript.
