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
    artist: str = "",
    play_on_web: bool = False
) -> str:
    """
    Play a requested song, music track, or video.
    Use this tool whenever the user asks to play music, a song, playlist, artist track, or play on web/YouTube/browser.
    If play_on_web is True or PREFERRED_MUSIC_APP is set to browser/web/youtube, it immediately resolves the direct video and begins playing on YouTube in the web browser.
    Otherwise, plays in the Zenith Mini Player (or Spotify if preferred).
    """
    try:
        from agent_tools.web import find_top_youtube_video, open_website, _focus_chrome_window
        preferred_app = os.getenv("PREFERRED_MUSIC_APP", "youtube_music").lower().strip()
        query = f"{song_name} {artist}".strip()
        ui_state.set_text(f"🎵 Searching {query}...")

        if preferred_app == "spotify":
            import subprocess
            subprocess.run(f"start spotify:search:{query}", shell=True)
            return f"Opening Spotify to play '{query}'."

        is_web_mode = play_on_web or (preferred_app in ["browser", "web", "youtube", "chrome"])

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
