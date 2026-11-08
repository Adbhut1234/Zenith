<div align="center">
  <h1>🤖 Zenith</h1>
  <p><i>Just A Rather Very Intelligent System — Vision-Grade Cognitive Desktop Agent</i></p>
  <p>A multimodal, autonomous desktop assistant powered by LiveKit WebRTC and Google's Gemini Multimodal Live API, featuring Vision-grade cognitive reasoning, neuroplastic self-healing, and a sovereign local memory matrix.</p>
</div>

---

## ⚡ What's New (Vision Cognitive Architecture)

- **🧠 Subconscious Deep Thinker (System 2 Reasoning):** When faced with complex coding bugs, multi-step system tasks, or strategic trade-offs, Zenith engages its deliberative subconscious matrix (`deep_reasoning_matrix`) to simulate failure modes, evaluate counterfactuals, and formulate optimal execution plans.
- **⚡ Neuroplasticity & Self-Healing Playbooks:** Powered by an automated post-mortem reflection engine (`procedural_memory.py`). Whenever a terminal command, UI automation action, or screen click encounters an error, Zenith diagnoses the root cause and records a permanent procedural playbook into SQLite so it never repeats the mistake.
- **📝 Stream of Consciousness (Working Memory Scratchpad):** Maintains an active cognitive scratchpad (`working_memory.py`) across conversation turns, tracking the active mission goal, subtask completion checklists, intermediate hypotheses, and ambient sensory signals. Restores unfinished tasks automatically upon boot.
- **⚖️ The Council of Overlays (Dialectical Debate):** Inspired by Vision's multi-layered mind (J.A.R.V.I.S., Stark, Banner, and Ultron). When evaluating high-stakes architectural choices or competing approaches, Zenith convenes The Architect, The Skeptic, and The Pragmatist to debate trade-offs and synthesize a unified consensus.
- **🌙 The Dream Cycle (Proactive Idle Cognition):** While you work, Zenith's background dream cycle quietly reconciles unresolved ambient signals (copied compiler errors, completed processes) and pre-computes fixes before you even ask.
- **⚛️ Code Phasing & Molecular Inspection:** Inspired by Vision's phasing abilities. Uses native Python AST parsing (`code_phasing.py`) to dissect and map classes, functions, signatures, and docstrings across entire codebases in milliseconds with **zero token cost**.
- **🚨 Universal Emergency Motor Killswitch:** A zero-latency atomic killswitch (`emergency_stop_all`) triggered verbally ("Stop everything", "Abort", "Freeze", "Ruk jao") to instantly disengage screen automation, UI clicks, web browsing, and terminal processes in < 5ms while releasing all hardware key locks.
- **🏛️ "The Ship of Theseus" Memory Evolution:** Temporal contradiction reconciliation that prevents factual drift as your habits, career, and tools evolve over time, automatically archiving superseded beliefs while preserving historical provenance.
- **🩺 Stark-Style Automated System Diagnostics:** An instant 5-point self-diagnostic inspection (`diagnose_system_health`) reporting live neural latency, SQLite integrity (`PRAGMA integrity_check`), persistent shell readiness, hardware resource load, and background cognitive loops.
- **🔒 100% Free & Sovereign Local Memory:** Completely retired third-party cloud memory platforms (Mem0) in favor of an embedded SQLite database (`zenith_memory.db`) with local vector embeddings, Knowledge Graph traversal, and a dedicated CLI manager (`manage_local_memory.py`).

---

## ⚙️ Core System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                 Frontal Voice Interface (J.A.R.V.I.S.)                 │
│              LiveKit Real-Time Audio Streaming (Ultra-Fast)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
┌────────────────────────┐ ┌────────────────────────┐ ┌─────────────────────┐
│ Subconscious Reasoner  │ │ Council of Overlays    │ │ The Dream Cycle     │
│ Deliberative System 2  │ │ Multi-Perspective      │ │ Idle Proactive      │
│ (The Mind Stone)       │ │ Dialectical Synthesis  │ │ Synthesis Engine    │
│ deep_thinker.py        │ │ council_of_overlays.py │ │ dream_cycle.py      │
└───────────┬────────────┘ └───────────┬────────────┘ └──────────┬──────────┘
            │                          │                         │
            ▼                          ▼                         ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Working Memory Scratchpad (Stream of Consciousness)                   │
│ Active Mission Goal • Subtask Checklist • Sensory Signals              │
│ working_memory.py  [SQLite: zenith_working_memory]                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Neuroplasticity & Procedural Playbooks (Experience Engine)            │
│ Post-Mortem Error Reflection • Self-Healing Playbooks                  │
│ procedural_memory.py [SQLite: zenith_playbooks, zenith_reflections]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Sovereign Memory Matrix & Epistemic Evolution                         │
│ Facts • Knowledge Graph • Ship of Theseus Temporal Versioning          │
│ zenith_memory.db [SQLite + NumPy Vector Cosine Similarity]            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Core Capabilities

- **🧠 Sovereign Local Memory (SQLite + Vector RAG):** 100% private on-device memory with knowledge graph entity traversal and procedural playbooks.
- **👁️ Native UI Automation (UIA) & Set-of-Marks (SoM):** Combines headless Windows UI Automation (`pywinauto`) with Set-of-Marks visual badges for precision desktop navigation without coordinate guessing.
- **💻 Stateful Persistent PowerShell:** Maintains `$PWD`, environment variables, and active virtual environments across turns with self-healing POSIX-to-PowerShell translation.
- **🌐 Autonomous Web Agent:** End-to-end web automation via `browser-use` and Playwright for form-filling, product comparisons, and research.
- **🚨 Atomic Safety Controls:** Universal emergency motor killswitch halts runaway tasks and releases hardware inputs in < 5ms.
- **👁️ Enhanced Multimodal Sight:** Cascading dual-model vision (`gemini-3.5-flash-lite` ➔ `gemini-2.5-flash`) for real-time screen inspection.
- **🗣️ Low-Latency Spoken Persona:** Human-like, loyal, and technically brilliant persona reflecting J.A.R.V.I.S. with English, Hindi, and Hinglish fluency.
- **🎨 Stark Dynamic Island HUD:** Sleek, always-on-top glassmorphic overlay reflecting cognitive states (`💡 Deep Deliberation`, `🧠 Overlays Debating`, `⚛️ Phasing Codebase`, `🛑 EMERGENCY STOP`).

---

## 🚀 System Initialization Sequence (Setup)

To bring Zenith online, follow these initialization steps:

1. **Construct Environment:** Create a new Python virtual environment:
   ```powershell
   python -m venv venv
   ```
2. **Engage Environment:** Activate the virtual environment:
   ```powershell
   .\venv\Scripts\activate
   ```
3. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Configure Constants:** 
   - Create a `.env` file from `.env.example`.
   - Add your `GOOGLE_API_KEY` (from Google AI Studio — free tier).
   - Add your `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` (from LiveKit Cloud).
   - *(Optional)* Add `GMAIL_USER` and `GMAIL_APP_PASSWORD` for automated email dispatch.
5. **Install Dashboard Dependencies:**
   ```powershell
   cd electron_dashboard
   npm install
   cd ..
   ```
6. **Deploy:** 
   - **Launch Dashboard (Recommended):**
     ```powershell
     cd electron_dashboard
     npm start
     ```
   - **Standalone Console Mode:**
     ```powershell
     python agent.py console
     ```

---

## 📊 Managing Local Memory

Zenith includes a dedicated CLI utility to inspect, export, and manage your sovereign local SQLite memory:

```powershell
# View summary of active facts, playbooks, and knowledge graph
python manage_local_memory.py

# Export memory matrix snapshot to JSON
python manage_local_memory.py --export backup.json

# Clear active facts for a specific user
python manage_local_memory.py --user Admin --clear
```

---

## 🧪 Testing the Cognitive Suite

To run the complete 6-point verification test suite covering deliberative reasoning, neuroplasticity, working memory, emergency stop, Ship of Theseus evolution, and automated diagnostics:

```powershell
python tests/test_vision_cognitive_suite.py
```

---

## 🔑 API Keys Guide

Zenith requires only **two** free services:

### 1. Google Gemini API (Neural Brain — 100% Free Tier)
- Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
- Sign in with your Google account and click **Create API key**.
- Paste it as `GOOGLE_API_KEY` in your `.env` file.

### 2. LiveKit Cloud (Real-Time Audio Transport)
- Sign up at [LiveKit Cloud](https://cloud.livekit.io/) (free tier includes ample monthly minutes).
- Go to **Settings** > **Keys** and copy:
  - `LIVEKIT_URL` (WebSocket URL)
  - `LIVEKIT_API_KEY`
  - `LIVEKIT_API_SECRET`

*(No third-party memory subscriptions or credit cards needed!)*

---

## 📜 License

Distributed under the **Apache 2.0 License**. See [LICENSE](LICENSE) for more information.

Copyright (c) 2026 Enc0deX.

---

## 👨‍💻 Author

Built and maintained by **Enc0deX**.
