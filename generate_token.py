import os
from livekit import api
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Load credentials from .env
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        print("Error: LIVEKIT_API_KEY or LIVEKIT_API_SECRET not found in .env")
        return

    # Create a token for the user to join the "my-room" room
    token = api.AccessToken(api_key, api_secret) \
        .with_identity("User") \
        .with_name("David") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room="my-room",
            can_publish=True,
            can_publish_data=True,
            can_subscribe=True,
        ))
    
    print("\n" + "="*50)
    print("YOUR CONNECTION TOKEN:")
    print("="*50)
    print(token.to_jwt())
    print("="*50 + "\n")
    print("1. Copy the token above.")
    print("2. Go to: https://agents-playground.livekit.io/")
    print(f"3. Select 'Custom' as your LiveKit Server.")
    print(f"4. Enter URL: {os.getenv('LIVEKIT_URL')}")
    print("5. Paste your token and Connect!")
    print("6. Click the 'Share Screen' button (monitor icon) to stream your screen to Zenith.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
