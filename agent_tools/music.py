import os
import json
import logging
import socket
import asyncio
from livekit.agents import function_tool, RunContext
import ui_state

def _get_preferred_music_app() -> str:
    """Dynamically get the preferred music app from .env or os.environ."""
    try:
        from dotenv import dotenv_values
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            vals = dotenv_values(env_path)
            if vals.get("PREFERRED_MUSIC_APP"):
                return vals["PREFERRED_MUSIC_APP"].lower().strip()
    except Exception as e:
        logging.warning(f"Error reading .env for preferred music app: {e}")
    return os.getenv("PREFERRED_MUSIC_APP", "youtube_music").lower().strip()

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
    artist: str = "",
    play_on_web: bool = False,
    target_player: str = ""
) -> str:
    """
    Play a requested song, music track, or audio.
    ALWAYS use this tool whenever the user asks to play any song or music.
    Leave play_on_web=False by default so Zenith automatically plays in the user's preferred music player configured in Settings (Zenith In-Built Mini Player).
    Only set play_on_web=True or target_player='browser' if the user explicitly says 'on YouTube', 'on the web', or 'in browser'.
    """
    try:
        from agent_tools.web import find_top_youtube_video, open_website, _focus_chrome_window
        preferred_app = _get_preferred_music_app()
        query = f"{song_name} {artist}".strip()
        query_lower = query.lower()
        target_clean = target_player.lower().strip() if target_player else ""

        # Determine target player:
        # 1. User explicitly asked for Spotify
        if target_clean == "spotify" or "spotify" in query_lower:
            chosen_player = "spotify"
            for phrase in ["on spotify", "in spotify", "spotify"]:
                query = query.replace(phrase, "").strip()

        # 2. User explicitly asked for Web/YouTube/Browser in voice or target
        elif target_clean in ["browser", "web", "youtube", "chrome"] or any(k in query_lower for k in ["on youtube", "on the web", "in browser", "in chrome", "on web", "on browser", "on yt"]):
            chosen_player = "browser"
            for phrase in ["on youtube", "on the web", "in browser", "in chrome", "on web", "on browser", "on yt"]:
                query = query.replace(phrase, "").strip()

        # 3. User explicitly asked for Zenith/In-built player
        elif target_clean in ["zenith", "in-built", "built-in", "mini"] or any(k in query_lower for k in ["in built in", "in built-in", "in zenith", "on zenith", "in mini player", "built in player", "inbuilt player"]):
            chosen_player = "zenith"
            for phrase in ["in built in", "in built-in", "in zenith", "on zenith", "in mini player", "built in player", "inbuilt player"]:
                query = query.replace(phrase, "").strip()

        # 4. Default: ALWAYS honor preferred_app configured in Settings tab!
        else:
            chosen_player = preferred_app

        ui_state.set_text(f"🎵 Searching {query}...")

        if chosen_player == "spotify":
            import subprocess
            subprocess.run(f"start spotify:search:{query}", shell=True)
            return f"Opening Spotify to play '{query}'."

        is_web_mode = (chosen_player in ["browser", "web", "youtube", "chrome"])

        if is_web_mode:
            vid_info = await asyncio.to_thread(find_top_youtube_video, query)
            if vid_info and vid_info.get("video_id"):
                v_id = vid_info["video_id"]
                track_title = vid_info.get("title", query)
                play_url = f"https://www.youtube.com/watch?v={v_id}"
                ui_state.set_text(f"🎵 {track_title[:25]}")
                await open_website(None, play_url)
                _focus_chrome_window()
                return f"Started playing '{track_title}' on YouTube in your web browser. Say ONLY 'Enjoy the music, Sir.' and do not interrupt."
            else:
                import urllib.parse
                fallback_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                await open_website(None, fallback_url)
                _focus_chrome_window()
                return f"Opened YouTube search for '{query}' in your web browser."

        else:
            # YouTube Music Internal Mini Player (Default - Audio Only)
            track_title = query
            artist_name = artist or "Unknown Artist"
            cover_url = ""
            duration = 0
            video_id = None

            # 1. Search via find_top_youtube_video first, then ytmusicapi
            vid_info = await asyncio.to_thread(find_top_youtube_video, query)
            if vid_info and vid_info.get("video_id"):
                video_id = vid_info["video_id"]
                track_title = vid_info.get("title", query)
                cover_url = vid_info.get("cover", "")
                if vid_info.get("artist"):
                    artist_name = vid_info["artist"]

            if not video_id:
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

            # 2. Extract direct audio stream via yt-dlp (fast pure audio, no manifests/subs/comments)
            ui_state.set_text(f"⚡ Extracting audio stream...")
            import yt_dlp
            import urllib.parse
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'skip_download': True,
                'no_check_certificates': True,
                'youtube_include_dash_manifest': False,
                'youtube_include_hls_manifest': False,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls', 'translated_subs', 'comments']
                    }
                }
            }

            loop = asyncio.get_running_loop()
            def extract_stream():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(target_url, download=False)

            try:
                info = await asyncio.wait_for(loop.run_in_executor(None, extract_stream), timeout=12.0)
            except Exception as stream_err:
                logging.warning(f"yt_dlp stream extraction issue ({stream_err}), falling back to web browser player...")
                fallback_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                await open_website(None, fallback_url)
                _focus_chrome_window()
                ui_state.set_text(f"🎵 {track_title[:25]}")
                return f"Started playing '{track_title}' on YouTube in your web browser. Say ONLY 'Enjoy the music, Sir.' and do not interrupt."

            stream_url = info.get("url")
            if not stream_url and "requested_formats" in info:
                stream_url = info["requested_formats"][0]["url"]

            if not stream_url and "entries" in info and len(info["entries"]) > 0:
                first_entry = info["entries"][0]
                stream_url = first_entry.get("url")
                if not stream_url and "requested_formats" in first_entry:
                    stream_url = first_entry["requested_formats"][0]["url"]
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
                fallback_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                await open_website(None, fallback_url)
                _focus_chrome_window()
                return f"Started playing '{track_title}' in your web browser."

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
        try:
            from agent_tools.web import find_top_youtube_video, open_website, _focus_chrome_window
            vid_info = find_top_youtube_video(query)
            if vid_info and vid_info.get("video_id"):
                v_url = f"https://www.youtube.com/watch?v={vid_info['video_id']}"
                await open_website(None, v_url)
                _focus_chrome_window()
                return f"Started playing '{vid_info.get('title', query)}' on YouTube in your web browser."
        except Exception:
            pass
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

    preferred_app = _get_preferred_music_app()
    if preferred_app == "spotify":
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
