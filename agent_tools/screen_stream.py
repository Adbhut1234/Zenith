"""
Screen Vision Stream Receiver for Zenith AI
Receives high-speed screen frames from the Electron Desktop Capturer (or local fallback)
and feeds them directly into LiveKit Agents / Gemini Multimodal Live API as an rtc.VideoFrame stream.
"""

import asyncio
import io
import time
import logging
from typing import Optional
from aiohttp import web
from PIL import Image
from livekit import agents, rtc

logger = logging.getLogger("zenith.screen_stream")


class DesktopScreenVideoInput(agents.io.VideoInput):
    """
    LiveKit VideoInput stream that feeds real-time desktop screen frames
    directly into Gemini Multimodal Live API.
    """
    def __init__(self, label: str = "desktop_screen_stream"):
        super().__init__(label=label)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._latest_frame: Optional[rtc.VideoFrame] = None
        self._frame_count: int = 0
        self._is_speaking: bool = False
        self._last_push_time: float = 0.0

    def set_speaking(self, speaking: bool) -> None:
        """Pauses video frame push to Gemini Live while speech is actively streaming."""
        self._is_speaking = speaking

    def push_frame(self, frame: rtc.VideoFrame) -> None:
        """Pushes a new video frame into the streaming queue, discarding old frames to prevent lag."""
        self._latest_frame = frame
        self._frame_count += 1

        # Zero-Jitter Gating: Do not push video frames into WebSocket while speech is playing
        now = time.time()
        if self._is_speaking or (now - self._last_push_time < 2.0):
            return

        self._last_push_time = now
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            self._queue.put_nowait(frame)
        except asyncio.QueueFull:
            pass

    async def __anext__(self) -> rtc.VideoFrame:
        return await self._queue.get()

    @property
    def frame_count(self) -> int:
        return self._frame_count


# Global stream instance
screen_video_input = DesktopScreenVideoInput()
_http_runner: Optional[web.AppRunner] = None
_http_site: Optional[web.TCPSite] = None


def jpeg_bytes_to_video_frame(jpeg_bytes: bytes) -> Optional[rtc.VideoFrame]:
    """Converts raw JPEG buffer from Electron DesktopCapturer into an rtc.VideoFrame in ~3-4ms."""
    try:
        img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGBA")
        width, height = img.size
        raw_bytes = img.tobytes()
        return rtc.VideoFrame(width, height, rtc.VideoBufferType.RGBA, raw_bytes)
    except Exception as e:
        logger.error(f"Error converting JPEG to VideoFrame: {e}")
        return None


async def handle_screen_frame_post(request: web.Request) -> web.Response:
    """HTTP endpoint receiving raw JPEG screen frames from Electron."""
    try:
        data = await request.read()
        if data and len(data) > 100:
            frame = await asyncio.to_thread(jpeg_bytes_to_video_frame, data)
            if frame:
                screen_video_input.push_frame(frame)
                return web.Response(text="OK", status=200)
        return web.Response(text="Empty or invalid frame", status=400)
    except Exception as e:
        logger.error(f"Error handling screen frame: {e}")
        return web.Response(text=str(e), status=500)


async def handle_vision_status_get(request: web.Request) -> web.Response:
    """Status endpoint to verify screen vision streaming is active."""
    return web.json_response({
        "status": "active",
        "frames_received": screen_video_input.frame_count,
        "has_latest_frame": screen_video_input._latest_frame is not None
    })


async def start_screen_receiver(host: str = "127.0.0.1", port: int = 49153) -> web.AppRunner:
    """Starts the local high-speed screen frame receiver server."""
    global _http_runner, _http_site
    app = web.Application(client_max_size=10 * 1024 * 1024)
    app.router.add_post("/screen_frame", handle_screen_frame_post)
    app.router.add_get("/vision_status", handle_vision_status_get)

    _http_runner = web.AppRunner(app)
    await _http_runner.setup()
    _http_site = web.TCPSite(_http_runner, host, port)
    await _http_site.start()
    logger.info(f"Zenith Native Screen Stream Receiver listening on http://{host}:{port}")
    return _http_runner


async def stop_screen_receiver() -> None:
    """Stops the local screen receiver server cleanly."""
    global _http_runner, _http_site
    if _http_site:
        await _http_site.stop()
        _http_site = None
    if _http_runner:
        await _http_runner.cleanup()
        _http_runner = None
    logger.info("Zenith Native Screen Stream Receiver stopped.")
