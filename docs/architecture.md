# Local AI Teacher — Architecture & Low-Level Design

## 1. Purpose

A fully local, privacy-preserving desktop application that acts as an interactive AI teacher. All inference — speech recognition, language generation, and speech synthesis — runs on-device. This removes network dependency, protects student data, and keeps the app usable offline. The core engineering constraint is fitting a full voice pipeline (STT + SLM + TTS + vector search) inside 4–8 GB of RAM on a consumer laptop.

## 2. High-Level Architecture

```
Microphone input
      │
      ▼
Silero VAD (detects speech)
      │
      ▼
Faster-Whisper (speech to text)
      │
      ▼
┌─────────────────────────────────────────┐
│ LangGraph orchestrator                   │
│ (state machine + routing)                │
│                                           │
│  ChromaDB RAG   ──context──▶  Ollama SLM │
│  (grade-level                (4-bit      │
│   collections)                Gemma)     │
└─────────────────────────────────────────┘
      │
      ▼
Piper TTS (sentence-level streaming)
      │
      ▼
Speaker output
```

The whole pipeline is wrapped in a PyQt6 desktop shell, which also owns the grade-level selector, live transcription feed, response text, and citations.

### Component responsibilities

| Component | Role | Resource footprint |
|---|---|---|
| Silero VAD | Detects speech start/end on an open mic stream | Negligible |
| Faster-Whisper (Tiny/Base) | Converts captured audio to text on CPU | < 500 MB RAM |
| LangGraph | Central state machine; manages multi-turn memory and conditional routing (e.g. forcing grade selection before init) | Low |
| ChromaDB | Vector store, one isolated collection per grade (`std_8_science`, etc.) so retrieval never crosses grade levels | Low, disk-backed |
| Ollama + Gemma 3 (1B) / Gemma 4 (E2B), 4-bit GGUF | Generates the tutor's response from the transcript + retrieved context | ~1.5–2.5 GB RAM |
| Piper TTS | Converts response text to speech, streamed sentence by sentence | Low |
| PyQt6 | Desktop UI: grade dropdown, live transcript, response text, citations | Low |

## 3. Low-Level Design

### 3.1 Speech capture and transcription

- A continuous microphone stream is monitored by **Silero VAD**. It classifies short audio frames as speech/silence.
- Once speech is detected and a configurable **silence threshold** is reached (marking end of utterance), the buffered audio segment is handed off — not the raw stream — to **Faster-Whisper**.
- Faster-Whisper (CTranslate2-optimized) runs the Tiny or Base model entirely on CPU and returns a transcript string. This keeps memory under 500 MB, leaving headroom for the LLM.
- Design detail: VAD and STT are decoupled via a buffer handoff so the mic thread is never blocked waiting on transcription.

### 3.2 Orchestration (LangGraph)

- LangGraph holds the **conversation state machine**. Key responsibilities:
  - Force a **grade-level selection** before any query is processed (conditional routing / gating node).
  - Maintain **multi-turn memory** so follow-up questions retain context.
  - Route the transcribed query to the correct ChromaDB collection and then to Ollama.
  - Handle **error states**: unclear/empty transcription, empty retrieval results.
- This is implemented as a graph of nodes (VAD/STT ingestion → grade check → retrieval → generation → TTS dispatch) rather than a linear script, so new nodes (e.g. a moderation step) can be inserted without restructuring the pipeline.

### 3.3 Retrieval (ChromaDB)

- Textbooks (1st–12th standard) are cleaned and chunked at ingestion time.
- Each grade gets its **own isolated Chroma collection** (e.g. `std_3_math`, `std_8_science`) — this is a hard isolation boundary, not just a metadata filter, to guarantee a 3rd-grade query can never surface 12th-grade content.
- At query time, LangGraph selects the collection matching the user's chosen standard and retrieves top-k relevant chunks as context for the LLM.

### 3.4 Generation (Ollama + SLM)

- Ollama serves a **4-bit quantized GGUF model** (Gemma 3 1B or Gemma 4 E2B) locally on `localhost:11434`.
- The orchestrator sends the transcript + retrieved context as the prompt.
- Ollama's **streaming API** is used (not a blocking single response) — this is what enables the sentence-level TTS pipeline below.

### 3.5 Sentence-level streaming to speech (low-latency output)

This is the detail that removes awkward pauses between question and spoken answer:

1. **Prompt execution** — transcript + RAG context sent to Ollama.
2. **Token buffering** — a Python generator accumulates streamed tokens into a text buffer.
3. **Punctuation trigger** — the instant the buffer contains a sentence-ending mark (`.`, `?`, `!`), that sentence is flushed out of the buffer and pushed to Piper TTS immediately (the rest of the response keeps generating in the background).
4. **Concurrent playback** — Piper synthesizes and plays sentence *N* while Ollama is still generating sentence *N+1*. This overlap is what gives the illusion of real-time speech rather than "generate everything, then speak."

### 3.6 UI (PyQt6)

- Grade/standard dropdown (drives which ChromaDB collection is active and gates the LangGraph flow).
- Live transcription feed (shows Faster-Whisper output as it's produced).
- AI response text pane (mirrors what's being spoken).
- Textbook citation display (surfaces which retrieved chunks backed the answer).

### 3.7 Packaging and deployment

- **PyInstaller** compiles the Python logic + PyQt6 UI into a single standalone executable.
- **Inno Setup** (Windows) bundles that executable with the Faster-Whisper binaries and Piper TTS assets into one installer.
- **Ollama pre-flight check**: on launch, the app pings `localhost:11434`. If Ollama isn't running, it silently runs the official Ollama installer and pulls the required model *before* the UI is shown — so the end user never touches a terminal.

## 4. Memory Budget (target: 4–8 GB machine)

| Component | Approx. RAM |
|---|---|
| Faster-Whisper (Tiny/Base) | < 500 MB |
| Ollama + 4-bit Gemma | 1.5–2.5 GB |
| ChromaDB (active collection) | Low, mostly disk-backed |
| Silero VAD, Piper TTS, PyQt6 | Low, combined a few hundred MB |
| **Total (typical)** | **~2.5–3.5 GB**, leaving headroom on a 4 GB machine |

Week 7 of the roadmap is dedicated to stress-testing this budget end-to-end and tuning VAD silence thresholds / quantization if the system thrashes under load.

## 5. Key Design Decisions & Rationale

| Decision | Why |
|---|---|
| Isolated ChromaDB collections per grade instead of one collection with metadata filtering | Hard isolation prevents cross-grade content leakage even if a filter bug occurs |
| Sentence-level streaming instead of full-response-then-speak | Removes the multi-second silence a student would otherwise experience while the full answer generates |
| 4-bit quantized SLM via Ollama instead of a larger cloud-hosted model | Fits the 4–8 GB RAM constraint and keeps everything offline/private |
| LangGraph state machine instead of a linear script | Makes conditional flows (grade gating, error handling, multi-turn memory) explicit and extensible |
| Silent Ollama install/model pull on first launch | Keeps installation frictionless for non-technical users |

## I'd divide the application into 6 major layers:
                    ┌──────────────────────┐
                    │       PyQt6 UI       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Teacher Service    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │     LangGraph        │
                    │ Orchestration/State  │
                    └────┬─────┬─────┬─────┘
                         │     │     │
              ┌──────────┘     │     └──────────┐
              ▼                ▼                ▼
         ┌─────────┐      ┌─────────┐      ┌─────────┐
         │ Audio   │      │   RAG   │      │   LLM   │
         │ Pipeline│      │ Chroma  │      │ Ollama  │
         └────┬────┘      └─────────┘      └────┬────┘
              │                                  │
       ┌──────┴──────┐                           │
       │             │                           │
      VAD           STT                         TTS
    Silero      Faster-Whisper                  Piper
                                                  │
                                                  ▼
                                               Speaker