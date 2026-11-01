"""
Verification test for Phase 1: Native Desktop Screen Streaming in Zenith
Simulates Electron's DesktopCapturer feeding high-resolution desktop frames
into Zenith's native LiveKit Agents Gemini Live Session.
"""

import asyncio
import io
import time
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import aiohttp
from PIL import Image
from livekit import agents, rtc
from agent_tools.screen_stream import (
    start_screen_receiver, stop_screen_receiver,
    screen_video_input, DesktopScreenVideoInput
)


async def run_verification():
    print("=" * 65)
    print("🚀 ZENITH PHASE 1 VERIFICATION: NATIVE DESKTOP SCREEN STREAMING")
    print("=" * 65)

    # 1. Attach to AgentSession
    print("\n[*] Step 1: Initializing AgentSession with VideoInput...")
    session = agents.AgentSession()
    session.input.video = screen_video_input
    print(f"    ✅ Attached stream label: '{session.input.video.label}'")
    assert session.input.video.label == "desktop_screen_stream"

    # 2. Start Receiver Server
    print("\n[*] Step 2: Starting Native Screen Receiver on 127.0.0.1:49153...")
    runner = await start_screen_receiver(host="127.0.0.1", port=49153)
    print("    ✅ Screen Receiver listening on http://127.0.0.1:49153")

    # 3. Simulate Electron DesktopCapturer output (1024x576 JPEG @ 65% quality)
    print("\n[*] Step 3: Generating Simulated 1024x576 Desktop Frame...")
    img = Image.new("RGB", (1024, 576), color=(30, 30, 45))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=65)
    jpeg_payload = buf.getvalue()
    print(f"    ✅ Frame Size: {len(jpeg_payload)} bytes (1024x576)")

    # 4. Transmit frame over local bridge
    print("\n[*] Step 4: Transmitting frame from Electron Capturer to Zenith Engine...")
    t_start = time.time()
    async with aiohttp.ClientSession() as client:
        async with client.post("http://127.0.0.1:49153/screen_frame", data=jpeg_payload) as resp:
            status = resp.status
            body = await resp.text()
            print(f"    ✅ Bridge Response: HTTP {status} ({body})")
            assert status == 200

        async with client.get("http://127.0.0.1:49153/vision_status") as resp:
            info = await resp.json()
            print(f"    ✅ Vision Status Report: {info}")
            assert info["status"] == "active"
            assert info["frames_received"] >= 1

    # 5. Retrieve from VideoInput queue
    print("\n[*] Step 5: Pulling frame from Zenith VideoInput Queue...")
    frame: rtc.VideoFrame = await asyncio.wait_for(session.input.video.__anext__(), timeout=2.0)
    latency_ms = (time.time() - t_start) * 1000
    print(f"    ✅ Received rtc.VideoFrame: {frame.width}x{frame.height} format={frame.type}")
    print(f"    ✅ End-to-End Latency: {latency_ms:.2f}ms")
    assert frame.width == 1024
    assert frame.height == 576

    # 6. Teardown
    print("\n[*] Step 6: Cleaning up receiver...")
    await stop_screen_receiver()
    print("    ✅ Receiver cleanly stopped.")

    print("\n" + "=" * 65)
    print("🎉 PHASE 1 VERIFICATION COMPLETE: ALL CHECKS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_verification())
