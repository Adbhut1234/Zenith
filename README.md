<div align="center">
  <h1>🤖 J.A.R.V.I.S.</h1>
  <p><i>Just A Rather Very Intelligent System</i></p>
  <p>A highly capable, multimodal desktop assistant powered by LiveKit and Google's Gemini Native Audio.</p>
</div>

---

## ⚙️ Core Directives (Capabilities)

J.A.R.V.I.S. operates as an autonomous desktop agent with deep system access, offering the following capabilities:

- **🧠 Smart Memory (Mem0):** Persistent context tracking across sessions. J.A.R.V.I.S. remembers you.
- **💻 System Override:** Full control over your Windows PC (run commands, open apps like Spotify, control files).
- **🖱️ Motor Functions:** Precision mouse movement and clicking via `PyAutoGUI`.
- **⌨️ Keyboard Override:** Direct text input and complex keyboard shortcut execution.
- **🗣️ Vocal Interface:** Low-latency, natural speech interaction using Gemini Native Audio (Voice: Charon).
- **👁️ Visual Processing:** Vision capabilities enabled through LiveKit camera feeds.
- **🌐 Global Network Access:** Real-time web search (DuckDuckGo), weather data (`wttr.in`), and direct URL navigation.
- **📨 Communications Protocol:** Automated email dispatch via SMTP.
- **🔌 External Nodes (MCP):** Expandable via n8n MCP Server connections for automated workflows.

---

## 🚀 System Initialization Sequence (Setup)

To bring J.A.R.V.I.S. online, follow these exact initialization steps:

1. **Construct Environment:** Create a new Python virtual environment.
2. **Engage Environment:** Activate the virtual environment.
3. **Install Dependencies:** Execute `pip install -r requirements.txt`.
4. **Configure Core Constants:** 
   - Create a `.env` file and populate it with your API Keys, LiveKit Secret, and LiveKit URL.
   - For email capabilities, input your `GMAIL_USER` and `GMAIL_APP_PASSWORD`.
5. **Verify LiveKit:** Ensure your LiveKit Account is correctly configured and operational.
6. **Verify Mem0:** Ensure your Mem0 Account is active for the memory subsystem.
7. **Verify MCP:** Set up your n8n MCP Server if utilizing external node workflows.

---

## 📡 Archives & Holo-Logs (Tutorials)

For detailed visual assistance in setting up the system architectures, consult the databanks:

- 🎥 **Phase 1 (Voice Agent Core Setup):** [Access Video Log](https://youtu.be/An4NwL8QSQ4?si=v1dNDDonmpCG1Els)
- 🎥 **Phase 2 (Memory System & MCP Server):** [Access Video Log](https://www.youtube.com/watch?v=gqmSKEUpRv8&ab_channel=Thanh-yDavidNguyen)

---

## 📜 Legal & Licensing

- **Proprietary Portions:** All files except `mcp_client` and portions of `agent.py` not authored by Thanh-Y Nguyen — Copyright © 2025 Thanh-Y Nguyen. Licensed for private/educational use only. Redistribution, publication, or commercial use is prohibited without written permission.  
- **Third-Party Components:**
  - `mcp_client` — Copyright © LiveKit, Inc., MIT License.  
  - Portions of `agent.py` not authored by Thanh-Y Nguyen — MIT or other applicable license.  
  - *See `thirdparty/LICENSE-LIVEKIT` for details.*
