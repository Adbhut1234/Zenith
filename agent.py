from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext
from livekit.plugins import noise_cancellation
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import get_weather, search_web, send_email, execute_pc_command, open_website, write_and_open_file, move_and_click_mouse, type_keyboard_text, press_keyboard_shortcut
from mem0 import AsyncMemoryClient

import os
import json
import logging
load_dotenv()


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
                press_keyboard_shortcut
            ],
            chat_ctx=chat_ctx

        )
        


async def entrypoint(ctx: agents.JobContext):

    async def shutdown_hook(chat_ctx: ChatContext, mem0: AsyncMemoryClient, memory_str: str):
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
        await mem0.add(messages_formatted, user_id="Adi")
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

    ctx.add_shutdown_callback(lambda: shutdown_hook(session._agent.chat_ctx, mem0, memory_str))

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))