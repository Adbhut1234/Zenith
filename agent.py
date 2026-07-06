import asyncio
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext
from livekit.plugins import noise_cancellation
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import get_weather, search_web, send_email, execute_pc_command, open_website, write_and_open_file, move_and_click_mouse, type_keyboard_text, press_keyboard_shortcut, control_computer, open_application
from mem0 import AsyncMemoryClient

import os
import json
import logging
import subprocess
import atexit
import sys

load_dotenv()

# --- UI Subprocess Management ---
ui_process = None

def start_ui():
    global ui_process
    ui_process = subprocess.Popen([sys.executable, 'jarvis_overlay.py'], stdin=subprocess.PIPE, text=True)

def update_ui(state):
    global ui_process
    if ui_process and ui_process.poll() is None:
        try:
            ui_process.stdin.write(f"{state}\n")
            ui_process.stdin.flush()
        except:
            pass

def stop_ui():
    global ui_process
    if ui_process:
        ui_process.terminate()

atexit.register(stop_ui)
# --------------------------------



class Assistant(Agent):
    def __init__(self, chat_ctx=None) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                 model="gemini-3.1-flash-live-preview",
                 voice="Charon",
                 temperature=0.8,
                 modalities=["AUDIO"],
            ),
            tools=[
                get_weather,
                search_web,
                send_email,
                execute_pc_command,
                open_website,
                write_and_open_file,
                move_and_click_mouse,
                type_keyboard_text,
                press_keyboard_shortcut,
                control_computer,
                open_application
            ],
            chat_ctx=chat_ctx

        )
        


async def entrypoint(ctx: agents.JobContext):

    async def shutdown_hook(chat_ctx: ChatContext, mem0: AsyncMemoryClient, memory_str: str, user_name: str):
        logging.info("Shutting down, saving chat context to memory...")

        messages_formatted = [
        ]

        messages_attr = getattr(chat_ctx, 'messages', chat_ctx.items)
        items = messages_attr() if callable(messages_attr) else messages_attr
        logging.info(f"Chat context messages: {items}")

        for item in items:
            if not hasattr(item, 'content') or not hasattr(item, 'role'):
                continue

            content_str = ''.join(item.content) if isinstance(item.content, list) else str(item.content)

            if memory_str and memory_str in content_str:
                continue

            if item.role in ['user', 'assistant']:
                messages_formatted.append({
                    "role": item.role,
                    "content": content_str.strip()
                })

        logging.info(f"Formatted messages to add to memory: {messages_formatted}")
        await mem0.add(messages_formatted, user_id=user_name)
        logging.info("Chat context saved to memory.")


    session = AgentSession(
        
    )

    

    mem0 = AsyncMemoryClient()
    user_name = ctx.room.metadata if ctx.room.metadata else os.getenv('JARVIS_USER_ID', 'Admin')

    raw_results = await mem0.get_all(filters={'user_id': user_name})
    results = raw_results.get('results', []) if isinstance(raw_results, dict) else raw_results

    initial_ctx = ChatContext()
    memory_str = ''

    if results:
        memories = [
            {
                "memory": result["memory"],
                "updated_at": result["updated_at"]
            }
            for result in results
        ]
        memory_str = json.dumps(memories)
        logging.info(f"Memories: {memory_str}")
        initial_ctx.add_message(
            role="assistant",
            content=f"The user's name is {user_name}, and this is relvant context about him: {memory_str}."
        )

    # Prompt the assistant to greet the user
    initial_ctx.add_message(
        role="system",
        content=SESSION_INSTRUCTION
    )
    initial_ctx.add_message(
        role="user",
        content="Hello J.A.R.V.I.S, please greet me."
    )

    agent = Assistant(chat_ctx=initial_ctx)
    
    # Start the overlay UI
    start_ui()

    interaction_state = {"last_active": asyncio.get_event_loop().time(), "state": "idle"}

    @session.on("user_state_changed")
    def on_user_state_changed(event):
        if event.new_state == "speaking":
            print(">>> UI TRIGGER: USER SPEAKING (LISTENING) <<<")
            update_ui("listening")
            interaction_state["last_active"] = asyncio.get_event_loop().time()
            interaction_state["state"] = "listening"

    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        if event.new_state == "speaking":
            print(">>> UI TRIGGER: AGENT SPEAKING <<<")
            update_ui("speaking")
            interaction_state["last_active"] = asyncio.get_event_loop().time()
            interaction_state["state"] = "speaking"
        elif event.new_state == "thinking":
            print(">>> UI TRIGGER: AGENT COMMITTED (WAITING) <<<")
            update_ui("waiting")
            interaction_state["last_active"] = asyncio.get_event_loop().time()
            interaction_state["state"] = "waiting"

    # Watchdog: Monitors UI state timeouts to return to idle
    async def ui_watchdog():
        import ui_state
        await asyncio.sleep(4) # Let the 3-second startup animation play first!
        
        while True:
            await asyncio.sleep(0.5)
            try:
                if ui_state.current_custom_text:
                    custom_text = ui_state.current_custom_text
                    ui_state.current_custom_text = None
                    update_ui(f"custom:{custom_text}")
                    interaction_state["last_active"] = asyncio.get_event_loop().time()
                    interaction_state["state"] = "custom"
                
                now = asyncio.get_event_loop().time()
                # If waiting and inactive for 15 seconds, go idle
                if interaction_state["state"] in ["waiting", "custom"] and now - interaction_state["last_active"] > 15.0:
                    update_ui("idle")
                    interaction_state["state"] = "idle"
            except Exception as e:
                pass

    asyncio.create_task(ui_watchdog())

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    # generate_reply is incompatible with Gemini Realtime API and omitted here.

    ctx.add_shutdown_callback(lambda: shutdown_hook(session._agent.chat_ctx, mem0, memory_str, user_name))

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))