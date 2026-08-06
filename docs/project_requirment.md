# Local AI Teacher Application - Project Architecture & Roadmap

## 1. Overview & Problem Analysis
The objective is to build a fully local, privacy-preserving desktop application that acts as an interactive AI Teacher. By relying entirely on on-device inference, this application eliminates network latency, ensures user data privacy (crucial for educational tools geared toward minors), and guarantees accessibility even without internet connectivity.
The core challenge lies in orchestrating multiple local AI models—Speech-to-Text (STT), a Small Language Model (SLM), and Text-to-Speech (TTS)—within the 4–8 GB memory constraints of a standard consumer laptop.

 ## 2. System Architecture
To operate smoothly within the 4–8 GB RAM constraint, the system utilizes a stateful, multi-actor orchestrator to manage asynchronous audio and retrieval pipelines efficiently.
Speech Pipeline (VAD + STT): An open microphone stream is monitored by Silero VAD (Voice Activity Detection). Once speech is detected and a silence threshold is reached, the audio buffer is passed to Faster-Whisper (Tiny or Base model). This runs entirely on the CPU, consuming < 500 MB RAM.
State & Orchestration: LangGraph acts as the central state machine. It manages the multi-turn conversational memory and handles the conditional routing (e.g., prompting the user to select their grade level before initializing).
Retrieval-Augmented Generation (RAG): ChromaDB is structured using isolated Collections based on the user's selected standard (e.g., 'std_8_science'). This prevents a 3rd-grade query from retrieving 12th-grade physics context.
Inference Engine (SLM): Ollama hosts a highly quantized 4-bit (GGUF) model. Optimized choices include Gemma 3 (1B variant) or Gemma 4 E2B, consuming approximately 1.5–2.5 GB of RAM.
Text-to-Speech (TTS): Piper TTS runs on the CPU. It listens to a text queue, generating audio instantly for rapid playback.

## 3. Data Flow: Sentence-Level Streaming
To eliminate awkward pauses between the student's question and the teacher's verbal response, the output pipeline utilizes asynchronous sentence chunking:
Prompt Execution: The transcribed text and retrieved ChromaDB context are sent to Ollama.
Token Buffering: As Ollama streams tokens back, a Python generator aggregates them into a buffer.
Punctuation Trigger: The moment the buffer detects a sentence-ending punctuation mark (., ?, !), that specific string is flushed from the buffer and pushed directly into Piper TTS.
Concurrent Playback: Piper synthesizes and plays the first sentence while Ollama is concurrently generating the second sentence in the background.

## 4. Technology Stack
Component
Technology
Programming Language
Python 3.10+ (Simplifies ML model bindings and orchestration)
Orchestration Framework
LangGraph
LLM Server
Ollama (Local model serving and API management)
Language Model
Gemma 3 (1B) or Gemma 4 (E2B) - 4-bit quantized
Vector Database
ChromaDB (Local, lightweight)
Speech-to-Text
Faster-Whisper (Highly optimized CTranslate2 implementation)
Voice Activity Detection
Silero VAD
Text-to-Speech
piper-tts (Fast, high-quality, lightweight neural TTS)
User Interface
PyQt6 (Lightweight desktop wrapper)
Packaging & Deployment
PyInstaller & Inno Setup


## 5. Deployment & Packaging Strategy
The goal is a frictionless, single-click installation for non-technical end-users.
Executable Wrapper: The core Python logic and desktop UI (PyQt6) will be compiled into a standalone executable using PyInstaller.
Dependency Bundling: The installer (Inno Setup for Windows) will bundle the PyInstaller executable, the Faster-Whisper binaries, and Piper TTS.
Ollama Pre-flight Check: Upon launch, the application checks if Ollama is active on localhost:11434. If missing, it silently executes the official Ollama installation script and automatically pulls the required model before presenting the UI.

## 6. Eight-Week Development Roadmap

### Phase 1: Foundation & RAG Isolation (Weeks 1-2)
Week 1: Clean and chunk the 1st–12th standard textbooks. Initialize ChromaDB and script the ingestion process to map specific textbooks to their designated grade-level collections.
Week 2: Setup the LangGraph state machine. Build the routing logic that forces the user to select a standard, and connect the corresponding ChromaDB collection to the local Ollama instance.

### Phase 2: Asynchronous Audio Handoffs (Weeks 3-4)
Week 3: Implement Silero VAD for the open microphone stream. Wire the VAD triggers to capture audio buffers and pass them to Faster-Whisper for rapid transcription.
Week 4: Build the sentence-level streaming queue. Connect Ollama's streaming API to Piper TTS, ensuring the audio begins playing the moment the first generated sentence is complete.

### Phase 3: Application Assembly (Weeks 5-6)
Week 5: Integrate the isolated VAD, STT, RAG, and TTS nodes into the unified LangGraph orchestrator. Implement error handling for unclear audio or empty database retrievals.
Week 6: Develop the PyQt6 graphical interface. It should feature a dropdown for the user's standard, a live transcription feed, the AI's text response, and textbook citations.

### Phase 4: Compute Optimization & Packaging (Weeks 7-8)
Week 7: Strict memory profiling. Run all components simultaneously on a 4GB RAM machine to ensure no out-of-memory (OOM) crashes occur. Tweak the VAD silence thresholds and quantization levels if the system thrashes.
Week 8: Build the final PyInstaller executable and the all-in-one Inno Setup script. Test the installation process on a clean, factory-reset laptop to verify the automated Ollama installation and model pulling works flawlessly.
