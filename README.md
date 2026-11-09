<div align="center">
  <img src="./web/zenith_logo.svg" alt="Zenith Logo" width="120" />
  <h1>Zenith</h1>
  <p><strong>Autonomous Multimodal Desktop Agent</strong></p>
  <p>Real-time bidirectional voice & vision assistant powered by LiveKit WebRTC, Google Gemini Live API, and on-device SQLite vector memory.</p>

  <p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" /></a>
    <a href="https://livekit.io"><img src="https://img.shields.io/badge/Transport-LiveKit_WebRTC-0070F3?style=flat-square&logo=webrtc&logoColor=white" alt="LiveKit WebRTC" /></a>
    <a href="https://ai.google.dev"><img src="https://img.shields.io/badge/Brain-Gemini_Live_API-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini Live API" /></a>
    <a href="https://www.sqlite.org"><img src="https://img.shields.io/badge/Memory-On--Device_SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite Memory" /></a>
    <img src="https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows" />
    <img src="https://img.shields.io/badge/License-All_Rights_Reserved-red?style=flat-square" alt="License" />
  </p>

  <p>
    <a href="#-architecture">Architecture</a> •
    <a href="#-visual-interface-tour">Interface Tour</a> •
    <a href="#-core-capabilities">Capabilities</a> •
    <a href="#-why-zenith-comparison">Comparison</a> •
    <a href="#-quickstart">Quickstart</a> •
    <a href="#-memory-cli">Memory CLI</a>
  </p>

  <br />

  <img src="./web/images/zenith-dashboard-active.png" alt="Zenith Desktop Dashboard" width="95%" style="border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);" />
</div>

---

## 🏗️ Architecture

Zenith couples a **sub-second real-time streaming pipeline** with **deliberative cognitive planning** and **sovereign local persistence**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Real-Time Audio Transport (LiveKit WebRTC)           │
│                   Sub-Second Duplex Voice & Video Frame Transport      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
┌────────────────────────┐ ┌────────────────────────┐ ┌─────────────────────┐
│ Deliberative Reasoner  │ │ Dialectical Synthesis  │ │ Proactive Idle Loop │
│ System 2 Plan Matrix   │ │ Multi-Perspective      │ │ Background Ambient  │
│ deep_thinker.py        │ │ council_of_overlays.py │ │ dream_cycle.py      │
└────────────────────────┘ └────────────────────────┘ └─────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Automation & Perception Execution Layer                                │
│ UI Automation (UIA) • Set-of-Marks (SoM) • Persistent PowerShell Shell │
│ Python AST Parsing (code_phasing.py) • Emergency Motor Killswitch       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Sovereign Local Memory Matrix & Epistemic Versioning                   │
│ SQLite + NumPy Vector Embeddings • Entity Graph • Temporal Conflict Fix│
│ zenith_memory.db • manage_local_memory.py                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📸 Visual Interface Tour

<table align="center" width="100%">
  <tr>
    <td width="50%" align="center">
      <img src="./web/images/zenith-voice-overlay.png" alt="Zenith Voice Overlay" width="100%" />
      <br />
      <strong>Real-Time Spoken Persona & Floating HUD</strong>
      <br />
      <em>Sub-second duplex voice interaction with dynamic state indicators.</em>
    </td>
    <td width="50%" align="center">
      <img src="./web/images/zenith-screen-vision.png" alt="Zenith Screen Vision" width="100%" />
      <br />
      <strong>Multimodal Screen Inspection & Grounding</strong>
      <br />
      <em>Continuous desktop sight powered by Set-of-Marks coordinate mapping.</em>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="./web/images/app-dashboard.png" alt="Control Center Dashboard" width="100%" />
      <br />
      <strong>Mission Control & System Diagnostics</strong>
      <br />
      <em>Live monitoring of neural latency, memory integrity, and active processes.</em>
    </td>
    <td width="50%" align="center">
      <img src="./web/images/zenith-settings-view.png" alt="Settings & API Configuration" width="100%" />
      <br />
      <strong>Local Security & Hardware Settings</strong>
      <br />
      <em>On-device configuration for emergency stop triggers, audio feeds, and credentials.</em>
    </td>
  </tr>
</table>

---

## ⚡ Core Capabilities

| Capability | Module | Description |
| :--- | :--- | :--- |
| **Deliberative System 2 Planning** | `deep_thinker.py` | Pauses immediate generation during complex tasks to simulate failure modes, evaluate counterfactuals, and generate validated execution sequences. |
| **Self-Healing Procedural Memory** | `procedural_memory.py` | Automated post-mortem reflection engine that diagnoses terminal error outputs and logs permanent procedural playbooks into SQLite to prevent repeated failures. |
| **Cross-Turn Working Memory** | `working_memory.py` | Active scratchpad tracking active mission goals, subtask checklists, and intermediate hypotheses; restores unfinished sessions across reboots. |
| **Multi-Perspective Strategy Synthesis** | `council_of_overlays.py` | Evaluates competing architectural and refactoring decisions across parallel heuristics (Architect, Skeptic, Pragmatist) to synthesize consensus. |
| **Zero-Token AST Codebase Indexing** | `code_phasing.py` | High-speed native Python AST parser that maps classes, functions, signatures, and docstrings across local codebases in milliseconds with 0 LLM token cost. |
| **Atomic Hardware & Process Killswitch** | `emergency.py` | Zero-latency atomic interrupt (`emergency_stop_all`) callable via voice or shortcut to abort automation, UI clicks, and subprocesses in < 5ms while releasing all hardware key locks. |
| **Temporal Knowledge Versioning** | `memory_evolution.py` | Automatically resolves factual contradictions over time (e.g., tool migrations, workflow updates) by archiving superseded records while keeping full historical provenance. |
| **100% Sovereign Local Vector Memory** | `zenith_memory.py` | Embeds user facts, entity graphs, and procedural knowledge into local SQLite with NumPy cosine similarity. Zero cloud memory lock-in. |
| **Desktop Perception & UI Automation** | `uia_control.py` / `som_grounding.py` | Headless Windows UI Automation (`pywinauto`) paired with Set-of-Marks (SoM) bounding visual badges for precise desktop interaction without blind pixel guesses. |
| **Persistent PowerShell Shell** | `persistent_shell.py` | Retains `$PWD`, environment variables, process handles, and active Python virtual environments across turns with automatic POSIX-to-PowerShell translation. |

---

## 📊 Why Zenith? (Comparison)

| Feature | Traditional Voice Assistants (Siri / Alexa) | Cloud AI Agent Platforms | **Zenith** |
| :--- | :---: | :---: | :---: |
| **Interaction Latency** | High (Cloud request-response) | High (Multi-turn HTTP polling) | **Sub-Second (LiveKit WebRTC)** |
| **Data Privacy & Storage** | Proprietary cloud servers | Third-party cloud vector DBs | **100% Sovereign On-Device SQLite** |
| **Desktop Automation** | None (Sandboxed voice commands) | Browser-only or mocked | **Native Windows UIA + Persistent Shell** |
| **Visual Grounding** | None | Full-screen screenshot guesses | **Set-of-Marks (SoM) Coordinate Badges** |
| **Error Recovery** | Fails on error | Blind retries | **SQLite Procedural Playbook Cache** |
| **Code Inspection** | None | Full-file token upload ($$$) | **Static Python AST Parsing (0 Token Cost)** |

---

## 🚀 Quickstart

### Prerequisites
* **OS:** Windows 10 or 11
* **Runtime:** Python 3.10+ and Node.js 18+ (for Electron dashboard)
* **API Keys:** Google Gemini API (Free tier from [AI Studio](https://aistudio.google.com/app/apikey)) and LiveKit Cloud (Free tier from [LiveKit](https://cloud.livekit.io/))

### 1. Clone & Set Up Python Environment
```powershell
git clone https://github.com/Adbhut1234/Zenith.git
cd Zenith

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Populate your `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret

# Optional for automated email dispatch:
# GMAIL_USER=your_email@gmail.com
# GMAIL_APP_PASSWORD=your_app_password
```

### 3. Launch Dashboard & Agent
```powershell
# In Terminal 1: Launch Electron Mission Control
cd electron_dashboard
npm install
npm start

# In Terminal 2: Start Agent Runtime
python agent.py
```

*Or run standalone in lightweight console mode:*
```powershell
python agent.py console
```

---

## 🧠 Memory CLI

Zenith includes an administrative CLI to inspect, export, and manage your on-device vector memory matrix:

```powershell
# View summary of active facts, playbooks, and knowledge graph
python manage_local_memory.py

# Export local memory snapshot to JSON backup
python manage_local_memory.py --export backup.json

# Clear active memory facts for a user
python manage_local_memory.py --user Admin --clear
```

---

## 🧪 Verification & Test Suite

Verify all cognitive loops, procedural memory, deliberative reasoning, and emergency stops with the built-in test suite:

```powershell
python tests/test_vision_cognitive_suite.py
```

---

## 📜 License

Copyright (c) 2026 **Enc0deX**. All Rights Reserved.  
Commercial distribution, modification, or licensing without explicit written authorization is prohibited.

<div align="center">
  <br />
  <p>Built with precision by <strong>Enc0deX</strong>.</p>
</div>
