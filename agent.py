import asyncio
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext
from livekit.plugins import noise_cancellation
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from agent_tools.web import get_weather, search_web, send_email, open_website
from agent_tools.system import execute_pc_command, write_and_open_file, open_application, get_now_playing
from agent_tools.os_control import move_and_click_mouse, type_keyboard_text, press_keyboard_shortcut, control_computer
from mem0 import AsyncMemoryClient

import os
import json
import logging
import subprocess
import atexit
import sys

load_dotenv()

# --- UI UDP Management ---
import socket

def start_ui():
    pass

def update_ui(state):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(state.encode(), ("127.0.0.1", 49152))
        sock.close()
    except:
        pass

def stop_ui():
    pass
# --------------------------------



class Assistant(Agent):
    def __init__(self, chat_ctx=None, custom_instructions=None) -> None:
        final_instructions = custom_instructions if custom_instructions else AGENT_INSTRUCTION
        super().__init__(
            instructions=final_instructions,
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
        


def extract_role_and_content(item):
    role = getattr(item, 'role', None)
    if not role and isinstance(item, dict):
        role = item.get('role')
    if hasattr(role, 'value'):
        role = role.value
    role = str(role).lower() if role else ''

    if role not in ['user', 'assistant']:
        return None, None

    content = getattr(item, 'content', None)
    if content is None and isinstance(item, dict):
        content = item.get('content')

    text_parts = []
    if isinstance(content, list):
        for c in content:
            if isinstance(c, str):
                text_parts.append(c)
            elif hasattr(c, 'text') and getattr(c, 'text'):
                text_parts.append(str(getattr(c, 'text')))
            elif isinstance(c, dict) and c.get('text'):
                text_parts.append(str(c.get('text')))
            elif c is not None:
                text_parts.append(str(c))
    elif content is not None:
        text_parts.append(str(content))

    full_text = ' '.join(text_parts).strip()
    if not full_text or full_text == 'None':
        return None, None

    return role, full_text


async def entrypoint(ctx: agents.JobContext):

    async def shutdown_hook(chat_ctx: ChatContext, tracked: list, mem0: AsyncMemoryClient, memory_str: str, user_name: str):
        logging.info("Shutting down, saving chat context to memory...")

        messages_formatted = []
        seen_texts = set()

        all_items = []
        if chat_ctx:
            try:
                all_items.extend(chat_ctx.messages())
            except Exception as e:
                logging.error(f"Error fetching chat_ctx messages on shutdown: {e}")
        all_items.extend(tracked)

        for item in all_items:
            role, text = extract_role_and_content(item)
            if not role or not text:
                continue

            if "Hello J.A.R.V.I.S., please greet me" in text:
                continue

            if text in seen_texts:
                continue

            seen_texts.add(text)
            messages_formatted.append({
                "role": role,
                "content": text
            })

        logging.info(f"Formatted messages to add to memory on shutdown: {messages_formatted}")
        if messages_formatted:
            try:
                res = await mem0.add(messages_formatted, user_id=user_name)
                logging.info(f"Chat context saved to memory: {res}")
            except Exception as e:
                logging.error(f"Failed to save chat context to mem0: {e}")
        else:
            logging.info("No new chat context to save to memory.")

    session = AgentSession()

    mem0 = AsyncMemoryClient()
    raw_user_name = ctx.room.metadata if ctx.room.metadata else (os.getenv('Zenith_USER_ID') or os.getenv('J.A.R.V.I.S._USER_ID') or 'Admin')
    user_name = raw_user_name.strip() if raw_user_name and raw_user_name.strip() else 'Admin'

    raw_results = await mem0.get_all(filters={'user_id': user_name})
    results = raw_results.get('results', []) if isinstance(raw_results, dict) else raw_results

    initial_ctx = ChatContext()
    memory_str = ''
    dynamic_instructions = AGENT_INSTRUCTION

    # Always inject user identity override
    if user_name and user_name.lower() != 'admin':
        dynamic_instructions += f"\n\nUser Identity Override: The user's name/alias is '{user_name}'. Address the user as '{user_name}' or 'Sir {user_name}' (or 'Sir')."
    else:
        dynamic_instructions += f"\n\nThe user's name is '{user_name}'."

    if results:
        memories = [
            {
                "memory": result["memory"],
                "updated_at": result["updated_at"]
            }
            for result in results
        ]
        memory_str = json.dumps(memories)
        logging.info(f"Memories loaded for user {user_name}: {memory_str}")
        dynamic_instructions += f"\n\nRelevant context & memories about {user_name}: {memory_str}."

    # Inject personal info defined in the dashboard if available
    personal_info = os.getenv('USER_PERSONAL_INFO')
    if personal_info:
        dynamic_instructions += f"\n\nUser's Personal Background & Preferences: {personal_info}"

    # Append session instructions
    dynamic_instructions += f"\n\n{SESSION_INSTRUCTION}"

    initial_ctx.add_message(
        role="user",
        content="Hello J.A.R.V.I.S., please greet me."
    )

    agent = Assistant(chat_ctx=initial_ctx, custom_instructions=dynamic_instructions)
    
    # Start the overlay UI
    start_ui()

    interaction_state = {"last_active": asyncio.get_event_loop().time(), "state": "idle"}
    tracked_messages = []

    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        item = getattr(event, 'item', event)
        tracked_messages.append(item)

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

    # Watchdog: Monitors UI state timeouts to return to idle and save memories
    async def ui_watchdog():
        import ui_state
        await asyncio.sleep(4) # Let the 3-second startup animation play first!
        last_memory_save_len = 0
        
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
                # If inactive for 15 seconds from any active state, go idle
                if interaction_state["state"] in ["waiting", "custom", "speaking", "listening"] and now - interaction_state["last_active"] > 15.0:
                    update_ui("idle")
                    interaction_state["state"] = "idle"
                    
                # Dynamic Memory Save after inactivity or when idle
                try:
                    items = agent.chat_ctx.messages()
                except Exception as e:
                    items = []

                if len(items) > last_memory_save_len:
                    logging.info(f"Watchdog debug: len(items)={len(items)} last={last_memory_save_len} state={interaction_state['state']} inactive_time={now - interaction_state['last_active']}")
                
                if interaction_state["state"] == "idle" or (now - interaction_state["last_active"] > 10.0):
                    if len(items) > last_memory_save_len:
                        new_items = items[last_memory_save_len:]
                        messages_formatted = []
                        for item in new_items:
                            role, text = extract_role_and_content(item)
                            if role and text and "Hello J.A.R.V.I.S., please greet me" not in text:
                                messages_formatted.append({"role": role, "content": text})
                        
                        if messages_formatted:
                            try:
                                logging.info(f"Saving {len(messages_formatted)} new messages to mem0: {messages_formatted}")
                                asyncio.create_task(mem0.add(messages_formatted, user_id=user_name))
                            except Exception as e:
                                logging.error(f"Background mem save failed: {e}")
                        last_memory_save_len = len(items)

            except Exception as e:
                logging.error(f"Watchdog exception: {e}")

    asyncio.create_task(ui_watchdog())

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    
    update_ui("startup")
    interaction_state["state"] = "startup"
    interaction_state["last_active"] = asyncio.get_event_loop().time()

    async def on_shutdown():
        await shutdown_hook(agent.chat_ctx, tracked_messages, mem0, memory_str, user_name)
    ctx.add_shutdown_callback(on_shutdown)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))