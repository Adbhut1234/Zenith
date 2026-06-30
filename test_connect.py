from dotenv import load_dotenv
import asyncio
from google import genai
load_dotenv()
async def run():
    client = genai.Client()
    try:
        async with client.aio.live.connect(model='gemini-3.1-flash-live-preview', config={"response_modalities": ["AUDIO"]}) as session:
            print('Connected to gemini-3.1-flash-live-preview')
            await session.send(input={"text": "hello"}, end_of_turn=True)
            async for msg in session.receive():
                print(msg)
                break
    except Exception as e:
        print(f"Error: {e}")
asyncio.run(run())
