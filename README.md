<div align="center">
  <h1>🤖 Zenith</h1>
  <p><i>Just A Rather Very Intelligent System</i></p>
  <p>A highly capable, multimodal desktop assistant powered by LiveKit and Google's Gemini Multimodal Live API.</p>
</div>

---

## ⚡ What's New
- **Gemini 3.1 Flash Live API:** Fully migrated to `gemini-3.1-flash-live-preview` for ultra-low latency, bidirectional native audio streams, utilizing the Charon voice.
- **Native Windows UIA Control:** Completely replaced the legacy vision-based screen control with a high-speed, text-based Windows UI Automation (UIA) engine via `pywinauto`. It reads the actual UI element tree and uses `gemini-2.5-flash` to execute native interactions (focus, click, type), entirely eliminating screenshots and coordinate guessing.
- **Apple-Style Liquid UI Pill:** Introduced a sleek, always-on-top, transparent overlay built with PyQtWebEngine. It seamlessly syncs with Zenith's internal states (listening, waiting, speaking) to provide a premium, non-blocking visual experience.
- **Electron Dashboard Integration:** A robust, single-instance background daemon architecture built into a new Electron Dashboard. This setup launches the Python agent silently without console flicker, prevents process duplication, and enforces a strict lifecycle link ensuring the agent engine terminates reliably when the dashboard closes.
- **Dynamic User Memory:** `Mem0` integration now dynamically isolates and persists memory based on the active user identity (`user_name`) rather than a hardcoded bucket.

---

## ⚙️ Core Capabilities

Zenith operates as an autonomous desktop agent with deep system access, offering the following capabilities:

- **🧠 Smart Memory (Mem0):** Persistent context tracking across sessions. Zenith remembers you and retrieves prior context natively on boot.
- **👁️ Native UI Automation (UIA):** Instead of guessing coordinates or using vision models, Zenith reads the exact accessibility tree of your Windows applications to drive UI interactions precisely and reliably.
- **💻 System Override:** Full command-line control over your Windows PC (execute commands, manage files, write code).
- **🚀 Universal App Launching:** Launches installed applications dynamically via Windows Search, without relying on hardcoded shell paths.
- **🖱️ & ⌨️ Motor Functions:** Precision mouse movement, clicking, and keyboard shortcuts via `PyAutoGUI`.
- **🗣️ Vocal Interface:** High-speed, natural, and sarcastic speech interaction reflecting the classic Zenith persona.
- **🌐 Global Network Access:** Real-time web search (DuckDuckGo), weather data (`wttr.in`), and direct URL navigation.
- **📨 Communications Protocol:** Automated email dispatch via Gmail SMTP.
- **🎧 Spotify Integration:** Native workflows for searching tracks and controlling Spotify playback.
- **🔌 External Nodes (MCP):** Expandable via MCP Server connections for automated workflows.

---

## 🚀 System Initialization Sequence (Setup)

To bring Zenith online, follow these exact initialization steps:

1. **Construct Environment:** Create a new Python virtual environment (`python -m venv venv`).
2. **Engage Environment:** Activate the virtual environment (`.\venv\Scripts\activate` on Windows).
3. **Install Dependencies:** Execute `pip install -r requirements.txt`.
4. **Configure Core Constants:** 
   - Create a `.env` file from `.env.example`.
   - Populate it with your `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.
   - Add your `GOOGLE_API_KEY` to authenticate the Gemini API.
   - For email capabilities, input your `GMAIL_USER` and `GMAIL_APP_PASSWORD`.
5. **Install Dashboard Dependencies:** Navigate to the `electron_dashboard` directory and run `npm install`.
6. **Verify Services:** Ensure your LiveKit and Mem0 accounts are active and configured.
7. **Deploy:** 
   - **Launch Dashboard (Recommended):** Navigate to `electron_dashboard` and run `npm start`. The dashboard will automatically manage the background Python agent.
   - **Build Executable:** Run `npm run dist` inside `electron_dashboard` to create a standalone Windows installer.
   - **Standalone Console Mode:** Run `python agent.py console` in the root directory.

---

## 🔑 API Keys Guide

To bring Zenith online, you will need to acquire API keys from a few services. You can enter these directly into the Settings menu in the Electron Dashboard or add them to your `.env` file.

### 1. Google Gemini API (Required for the AI Brain)
- Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
- Sign in with your Google account.
- Click **Create API key** and copy it. This is your `GOOGLE_API_KEY`.

### 2. LiveKit Cloud (Required for Voice & Audio Streaming)
- Go to [LiveKit Cloud](https://cloud.livekit.io/) and sign up.
- Create a new project.
- Navigate to **Settings** > **Keys** in your project dashboard.
- Generate a new API Key. You will be provided with three essential values:
  - `LIVEKIT_URL` (The WebSocket URL)
  - `LIVEKIT_API_KEY`
  - `LIVEKIT_API_SECRET`

### 3. Mem0 Platform (Required for Long-Term Memory)
- Go to [Mem0 Platform](https://app.mem0.ai/).
- Sign in and navigate to the API Keys section in your dashboard.
- Generate a new key. This is your `MEM0_API_KEY`.

### 4. Gmail App Passwords (Optional, for sending emails)
- Go to your Google Account -> **Security**.
- Ensure **2-Step Verification** is enabled.
- Search for **App Passwords** in the search bar.
- Create a new App Password (e.g., named "Zenith").
- Copy the 16-character code. This is your `GMAIL_APP_PASSWORD`. Use your regular Gmail address for `GMAIL_USER`.

---

## 👨‍💻 Author

Built and maintained by **Adi Pandey**.
