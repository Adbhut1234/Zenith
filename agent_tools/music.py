import os
import json
import logging
import socket
import asyncio
from livekit.agents import function_tool, RunContext
import ui_state

def _send_ipc_message(payload: dict):
    """Send JSON payload via UDP socket to Electron main process (port 49152)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", 49152))
        sock.close()
    except Exception as e:
        logging.error(f"Error sending music IPC message: {e}")

@function_tool()
async def play_music(
    context: RunContext,  # type: ignore
    song_name: str,
    artist: str = ""
) -> str:
    """
    Play a requested song or music track.
    Use this tool whenever the user asks to play music, a song, playlist, or artist track.
    Supports YouTube Music internal mini player (ad-free direct streaming), Spotify Desktop app, or web browser depending on configuration.
    """
    try:
        preferred_app = os.getenv("PREFERRED_MUSIC_APP", "youtube_music").lower().strip()
        query = f"{song_name} {artist}".strip()
        ui_state.set_text(f"🎵 Searching {query}...")

        if preferred_app == "spotify":
            import subprocess
            subprocess.run(f"start spotify:search:{query}", shell=True)
            return f"Opening Spotify to play '{query}'."

        elif preferred_app == "browser" or preferred_app == "web":
            import webbrowser
            url = f"https://music.youtube.com/search?q={query}"
            webbrowser.open(url)
            return f"Opened YouTube Music in web browser for '{query}'."

        else:
            # YouTube Music Internal Mini Player (Default - Audio Only)
            track_title = query
            artist_name = artist or "Unknown Artist"
            cover_url = ""
            duration = 0
            video_id = None

            # 1. Search via ytmusicapi explicitly filtered for songs
            try:
                from ytmusicapi import YTMusic
                ytmusic = YTMusic()
                search_results = await asyncio.to_thread(ytmusic.search, query, filter="songs")
                if search_results and len(search_results) > 0:
                    top = search_results[0]
                    video_id = top.get("videoId")
                    track_title = top.get("title", query)
                    artists_list = [a.get("name") for a in top.get("artists", []) if a.get("name")]
                    if artists_list:
                        artist_name = ", ".join(artists_list)
                    duration = top.get("duration_seconds", 0)
                    thumbnails = top.get("thumbnails", [])
                    if thumbnails:
                        cover_url = thumbnails[-1].get("url", "")
            except Exception as e:
                logging.warning(f"ytmusicapi search warning: {e}")

            if video_id:
                target_url = f"https://www.youtube.com/watch?v={video_id}"
                if not cover_url:
                    cover_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            else:
                target_url = f"ytsearch1:{query} official audio"

            # 2. Extract direct audio stream via yt-dlp (audio only)
            ui_state.set_text(f"⚡ Extracting audio stream...")
            import yt_dlp
            import urllib.parse
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios']
                    }
                }
            }

            loop = asyncio.get_running_loop()
            def extract_stream():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(target_url, download=False)

            try:
                info = await loop.run_in_executor(None, extract_stream)
            except Exception as stream_err:
                logging.warning(f"yt_dlp stream extraction warning ({stream_err}), falling back to web browser player...")
                import webbrowser
                fallback_url = target_url if target_url.startswith("http") else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                webbrowser.open(fallback_url)
                ui_state.set_text(f"🎵 {track_title[:25]}")
                return f"Opened '{track_title}' on YouTube in your web browser. Say ONLY 'Enjoy the music, Sir.' and do not interrupt."

            stream_url = info.get("url")
            if not stream_url and "requested_formats" in info:
                stream_url = info["requested_formats"][0]["url"]

            if not stream_url and "entries" in info and len(info["entries"]) > 0:
                first_entry = info["entries"][0]
                stream_url = first_entry.get("url")
                if not video_id:
                    video_id = first_entry.get("id")
                if not track_title or track_title == query:
                    track_title = first_entry.get("title", query)

            if not video_id and info.get("id"):
                video_id = info.get("id")

            if not track_title or track_title == query:
                track_title = info.get("title", query)
            if not artist_name or artist_name == "Unknown Artist":
                artist_name = info.get("uploader", info.get("artist", "YouTube Music"))

            if not cover_url:
                if video_id:
                    cover_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                elif info.get("thumbnail"):
                    cover_url = info.get("thumbnail")

            if not stream_url:
                import webbrowser
                fallback_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                webbrowser.open(fallback_url)
                return f"Opened '{track_title}' in your web browser."

            # 3. Send IPC payload to Electron Mini Player
            payload = {
                "type": "play_music",
                "title": track_title,
                "artist": artist_name,
                "cover": cover_url,
                "video_id": video_id or "",
                "stream_url": stream_url,
                "duration": duration or info.get("duration", 0)
            }

            _send_ipc_message(payload)
            ui_state.set_text(f"🎵 {track_title}")
            return f"Started playing '{track_title}' by {artist_name}. Instructions for assistant: Say ONLY 'Enjoy the music, Sir.' (or brief 'Enjoy!') and do not speak further or interrupt unless explicitly called by name."

    except Exception as e:
        logging.error(f"Error in play_music: {e}", exc_info=True)
        import webbrowser
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}")
        return f"Opened YouTube search for '{query}' in your web browser."

@function_tool()
async def control_music(
    context: RunContext,  # type: ignore
    action: str,
    volume: int = -1
) -> str:
    """
    Control currently playing music playback in the Zenith Mini Player or system player.
    Supported actions: 'play', 'pause', 'resume', 'toggle', 'next', 'previous', 'stop', 'close', 'volume'.
    If action is 'volume', provide volume parameter (0 to 100).
    """
    action_clean = action.lower().strip()
    payload = {
        "type": "control_music",
        "action": action_clean,
        "volume": volume
    }
    _send_ipc_message(payload)

    try:
        import pyautogui
        if action_clean in ["pause", "play", "resume", "toggle"]:
            pyautogui.press("playpause")
        elif action_clean in ["next", "skip"]:
            pyautogui.press("nexttrack")
        elif action_clean in ["prev", "previous"]:
            pyautogui.press("prevtrack")
        elif action_clean in ["stop", "close"]:
            pyautogui.press("stop")
    except Exception:
        pass

    return f"Music control action '{action_clean}' sent."
