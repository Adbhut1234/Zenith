<div align="center">
  <img src="./web/logo.png" alt="Zenith Logo" width="90" />
  <h1>Zenith</h1>
  <p><strong>Autonomous Multimodal Desktop Agent</strong></p>
  <p>Real-time bidirectional voice & vision assistant powered by LiveKit WebRTC, Gemini Live API, and on-device SQLite vector memory.</p>

  <p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" /></a>
    <a href="https://livekit.io"><img src="https://img.shields.io/badge/LiveKit-WebRTC-0070F3?style=flat-square&logo=webrtc&logoColor=white" alt="LiveKit WebRTC" /></a>
    <a href="https://ai.google.dev"><img src="https://img.shields.io/badge/Gemini-Live_API-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini Live API" /></a>
    <a href="https://www.sqlite.org"><img src="https://img.shields.io/badge/Memory-SQLite_Vector-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite Memory" /></a>
  </p>

  <br />

  <img src="./web/images/zenith-dashboard.png" alt="Zenith Desktop Dashboard" width="90%" style="border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);" />
</div>

---

## Highlights

- ⚡ **Sub-Second Voice:** Full-duplex conversational audio streaming over LiveKit WebRTC with live interruption support.
- 👁️ **Desktop Vision & Grounding:** Continuous screen inspection using Set-of-Marks (SoM) and Windows UI Automation (`pywinauto`).
- 🧠 **Sovereign Local Memory:** 100% on-device SQLite vector storage with NumPy cosine similarity — zero external cloud memory lock-in.
- 🛠️ **Self-Healing Shell:** Persistent PowerShell subprocess with automated error reflection that saves procedural recovery playbooks.
- 🛑 **Atomic Safety Killswitch:** Hardware-level freeze and automation abort in `< 5ms` via voice command or hotkey.

---

## Architecture

```
[ Microphone / Screen ] ──(WebRTC)──> [ LiveKit Engine ] ──> [ Gemini Live API ]
                                                                     │
                                                                     ▼
[ Desktop Automation ] <── [ Persistent Shell ] <── [ System 2 Reasoning ]
(UIA + Set-of-Marks)       (Stateful PowerShell)              │
                                                              ▼
                                                   [ SQLite Vector Store ]
                                                   (Local Facts & Playbooks)
```

---

## Quickstart

### 1. Setup Environment
```powershell
git clone https://github.com/Adbhut1234/Zenith.git
cd Zenith

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Keys
Create a `.env` file from `.env.example`:
```env
GOOGLE_API_KEY=your_gemini_api_key
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

### 3. Launch
```powershell
# Option A: Full Electron Dashboard
cd electron_dashboard && npm start

# Option B: Lightweight Console Mode
python agent.py console
```

---

## Memory Management

Zenith includes a CLI to inspect and manage your local SQLite memory matrix:

```powershell
# View stored facts and procedural playbooks
python manage_local_memory.py

# Export memory to JSON
python manage_local_memory.py --export backup.json
```

---

## Verification

To run the verification test suite covering cognitive loops, memory, and safety stops:

```powershell
python tests/test_vision_cognitive_suite.py
```

---

## License

Copyright (c) 2026 **Enc0deX**. All Rights Reserved.
