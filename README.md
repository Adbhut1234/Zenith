<div align="center">
  <h1>🤖 J.A.R.V.I.S.</h1>
  <p><i>Just A Rather Very Intelligent System</i></p>
  <p>A highly capable, multimodal desktop assistant powered by LiveKit and Google's Gemini Multimodal Live API.</p>
</div>

---

## ⚡ What's New
- **Gemini 3.1 Flash Live API:** Fully migrated to `gemini-3.1-flash-live-preview` for ultra-low latency, bidirectional native audio streams, utilizing the Charon voice.
- **Native Windows UIA Control:** Completely replaced the legacy vision-based screen control with a high-speed, text-based Windows UI Automation (UIA) engine via `pywinauto`. It reads the actual UI element tree and uses `gemini-2.5-flash` to execute native interactions (focus, click, type), entirely eliminating screenshots and coordinate guessing.
- **Apple-Style Liquid UI Pill:** Introduced a sleek, always-on-top, transparent overlay built with PyQtWebEngine. It seamlessly syncs with JARVIS's internal states (listening, waiting, speaking) to provide a premium, non-blocking visual experience.
- **Electron Dashboard Integration:** A robust, single-instance background daemon architecture built into a new Electron Dashboard. This setup launches the Python agent silently without console flicker, prevents process duplication, and enforces a strict lifecycle link ensuring the agent engine terminates reliably when the dashboard closes.
- **Dynamic User Memory:** `Mem0` integration now dynamically isolates and persists memory based on the active user identity (`user_name`) rather than a hardcoded bucket.

---

## ⚙️ Core Capabilities

J.A.R.V.I.S. operates as an autonomous desktop agent with deep system access, offering the following capabilities:

- **🧠 Smart Memory (Mem0):** Persistent context tracking across sessions. J.A.R.V.I.S. remembers you and retrieves prior context natively on boot.
- **👁️ Native UI Automation (UIA):** Instead of guessing coordinates or using vision models, JARVIS reads the exact accessibility tree of your Windows applications to drive UI interactions precisely and reliably.
- **💻 System Override:** Full command-line control over your Windows PC (execute commands, manage files, write code).
- **🚀 Universal App Launching:** Launches installed applications dynamically via Windows Search, without relying on hardcoded shell paths.
- **🖱️ & ⌨️ Motor Functions:** Precision mouse movement, clicking, and keyboard shortcuts via `PyAutoGUI`.
- **🗣️ Vocal Interface:** High-speed, natural, and sarcastic speech interaction reflecting the classic JARVIS persona.
- **🌐 Global Network Access:** Real-time web search (DuckDuckGo), weather data (`wttr.in`), and direct URL navigation.
- **📨 Communications Protocol:** Automated email dispatch via Gmail SMTP.
- **🎧 Spotify Integration:** Native workflows for searching tracks and controlling Spotify playback.
- **🔌 External Nodes (MCP):** Expandable via MCP Server connections for automated workflows.

---

## 🚀 System Initialization Sequence (Setup)

To bring J.A.R.V.I.S. online, follow these exact initialization steps:

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

## 🔑 Obtaining Your API Keys

To run J.A.R.V.I.S., you need a few external services. Here is how to get the required keys:

**1. Google Gemini API Key (`GOOGLE_API_KEY`)**
- Go to [Google AI Studio](https://aistudio.google.com/).
- Sign in with your Google account.
- Click **"Get API key"** in the left sidebar and create a new key.

**2. LiveKit Cloud (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`)**
- Go to [LiveKit Cloud](https://cloud.livekit.io/).
- Sign up and create a new Project.
- Navigate to **Settings > Keys** in your project dashboard.
- Generate a new key pair. You will get the API Key, API Secret, and your project's WebSocket URL.

**3. Gmail App Password (For Email Automation)**
- Go to your [Google Account Security page](https://myaccount.google.com/security).
- Ensure **2-Step Verification** is turned on.
- Search for "App Passwords" in the top search bar (or find it under 2-Step Verification settings).
- Create a new App Password (select "Other" and name it "JARVIS").
- Use this 16-character password as your `GMAIL_APP_PASSWORD`, and your email address as `GMAIL_USER`.

---

## 👨‍💻 Author

Built and maintained by **Adi Pandey**.
