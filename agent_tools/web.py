import logging
import os
import requests
import asyncio
import webbrowser
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional, Any, List, Dict
from livekit.agents import function_tool, RunContext
import ui_state

WEATHER_CODES = {
    0: "☀️ Clear Sky", 1: "🌤️ Mainly Clear", 2: "⛅ Partly Cloudy", 3: "☁️ Overcast",
    45: "🌫️ Foggy", 48: "🌫️ Rime Fog", 51: "🌦️ Light Drizzle", 53: "🌦️ Moderate Drizzle",
    55: "🌦️ Dense Drizzle", 61: "🌧️ Slight Rain", 63: "🌧️ Moderate Rain", 65: "🌧️ Heavy Rain",
    71: "🌨️ Light Snow", 73: "🌨️ Moderate Snow", 75: "🌨️ Heavy Snow", 80: "🌧️ Rain Showers",
    81: "🌧️ Moderate Rain Showers", 82: "🌧️ Violent Rain Showers", 95: "🌩️ Thunderstorm", 96: "🌩️ Thunderstorm with Hail"
}

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get current weather and whole day forecast for a given city.
    """
    city_clean = city.strip().title()
    ui_state.set_text(f"Weather | Checking {city_clean}...")
    
    def fetch_weather():
        headers = {'User-Agent': 'ZenithWeather/1.0'}
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_clean}&count=1"
            geo_res = requests.get(geo_url, headers=headers, timeout=8)
            if geo_res.status_code == 200:
                results = geo_res.json().get("results")
                if results:
                    lat = results[0]["latitude"]
                    lon = results[0]["longitude"]
                    country = results[0].get("country", "")
                    name = results[0].get("name", city_clean)
                    
                    w_url = (
                        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                        f"&current_weather=true"
                        f"&hourly=temperature_2m,weathercode,relativehumidity_2m,apparent_temperature,precipitation_probability,windspeed_10m"
                        f"&daily=weathercode,temperature_2m_max,temperature_2m_min,uv_index_max"
                        f"&timezone=auto"
                    )
                    w_res = requests.get(w_url, headers=headers, timeout=8)
                    if w_res.status_code == 200:
                        w_json = w_res.json()
                        cw = w_json.get("current_weather", {})
                        temp = round(cw.get("temperature", 0))
                        code = cw.get("weathercode", 0)
                        condition = WEATHER_CODES.get(code, "🌤️ Clear")
                        
                        # Hourly forecast for whole day (first 24h, sampled every 3h)
                        h = w_json.get("hourly", {})
                        times = h.get("time", [])[:24]
                        temps = h.get("temperature_2m", [])[:24]
                        codes = h.get("weathercode", [])[:24]
                        rains = h.get("precipitation_probability", [])[:24]
                        humidities = h.get("relativehumidity_2m", [])[:24]
                        winds = h.get("windspeed_10m", [])[:24]
                        
                        hourly_data = []
                        for i in range(len(times)):
                            if i % 3 == 0:
                                t_str = times[i].split("T")[1] if "T" in times[i] else str(times[i])
                                hourly_data.append({
                                    "time": t_str,
                                    "temp": round(temps[i]) if i < len(temps) else temp,
                                    "code": codes[i] if i < len(codes) else code,
                                    "rain": rains[i] if i < len(rains) else 0,
                                    "humidity": humidities[i] if i < len(humidities) else 0,
                                    "wind": round(winds[i]) if i < len(winds) else 0
                                })
                        
                        daily = w_json.get("daily", {})
                        max_temp = round(daily.get("temperature_2m_max", [temp])[0])
                        min_temp = round(daily.get("temperature_2m_min", [temp])[0])
                        uv_max = round(daily.get("uv_index_max", [0])[0])
                        
                        # Send rich weather payload to Dynamic Island UI
                        weather_payload = {
                            "type": "weather",
                            "city": name,
                            "country": country,
                            "temp": temp,
                            "condition": condition,
                            "code": code,
                            "max_temp": max_temp,
                            "min_temp": min_temp,
                            "humidity": humidities[0] if humidities else 50,
                            "rain": rains[0] if rains else 0,
                            "uv": uv_max,
                            "wind": round(cw.get("windspeed", 0)),
                            "hourly": hourly_data
                        }
                        ui_state.send_json(weather_payload)
                        
                        return f"{name}, {country} | {condition}, {temp}°C (High: {max_temp}° / Low: {min_temp}°)"
        except Exception as e:
            logging.warning(f"Open-Meteo failed for {city}: {e}")

        # Fallback to wttr.in format=j1
        try:
            w_res = requests.get(f"https://wttr.in/{city_clean}?format=j1", headers=headers, timeout=6)
            if w_res.status_code == 200:
                j = w_res.json()
                cc = j.get("current_condition", [{}])[0]
                temp = round(float(cc.get("temp_C", 0)))
                cond = cc.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
                w0 = j.get("weather", [{}])[0]
                max_t = round(float(w0.get("maxtempC", temp)))
                min_t = round(float(w0.get("mintempC", temp)))
                uv = round(float(w0.get("uvIndex", 0)))
                humidity = round(float(cc.get("humidity", 50)))
                wind = round(float(cc.get("windspeedKmph", 0)))

                hourly_data = []
                for h in w0.get("hourly", []):
                    raw_time = int(h.get("time", "0"))
                    t_str = f"{raw_time // 100:02d}:00"
                    hourly_data.append({
                        "time": t_str,
                        "temp": round(float(h.get("tempC", temp))),
                        "code": 1,
                        "rain": int(h.get("chanceofrain", 0)),
                        "humidity": int(h.get("humidity", 50)),
                        "wind": int(h.get("windspeedKmph", 0))
                    })

                weather_payload = {
                    "type": "weather",
                    "city": city_clean,
                    "country": "",
                    "temp": temp,
                    "condition": f"🌤️ {cond}",
                    "code": 1,
                    "max_temp": max_t,
                    "min_temp": min_t,
                    "humidity": humidity,
                    "rain": hourly_data[0]["rain"] if hourly_data else 0,
                    "uv": uv,
                    "wind": wind,
                    "hourly": hourly_data
                }
                ui_state.send_json(weather_payload)
                return f"{city_clean} | 🌤️ {cond}, {temp}°C (High: {max_t}° / Low: {min_t}°)"
        except Exception as e:
            logging.warning(f"wttr.in j1 failed for {city}: {e}")

        # Fallback to wttr.in format=3
        try:
            w_res = requests.get(f"https://wttr.in/{city_clean}?format=3", headers=headers, timeout=5)
            if w_res.status_code == 200 and w_res.text.strip():
                return w_res.text.strip()
        except Exception as e:
            logging.warning(f"wttr.in failed for {city}: {e}")

        return None

    try:
        result_str = await asyncio.to_thread(fetch_weather)
        if result_str:
            out = f"Weather | {result_str}"
            ui_state.set_text(out)
            logging.info(f"Weather retrieved for {city}: {result_str}")
            return f"Weather report for {result_str}."
        else:
            ui_state.set_text(f"Weather | {city_clean}: Data Unavailable")
            return f"Unable to fetch current weather for {city_clean} right now."
    except Exception as e:
        logging.error(f"Weather tool exception for {city}: {e}")
        ui_state.set_text(f"Weather | {city_clean}: Error")
        return f"Error retrieving weather for {city_clean}: {e}" 

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web for real-time information, news, current events, facts, and websites.
    Uses multi-source search combining DuckDuckGo and Wikipedia encyclopedic lookup.
    """
    ui_state.set_text(f"🔍 Searching web for '{query}'...")

    def _perform_search():
        prefix_wiki = ""
        # Quick Wikipedia encyclopedic check for entity queries
        try:
            import urllib.request
            import urllib.parse
            slug = urllib.parse.quote(query.strip().replace(" ", "_"))
            w_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
            req = urllib.request.Request(w_url, headers={"User-Agent": "ZenithAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                w_data = json.loads(resp.read().decode("utf-8"))
                if w_data and w_data.get("extract"):
                    w_title = w_data.get("title", query)
                    w_extract = w_data.get("extract")
                    w_link = w_data.get("content_urls", {}).get("desktop", {}).get("page", "")
                    prefix_wiki = f"--- WIKIPEDIA FACT CHECK ({w_title}) ---\n{w_extract}\nSource: {w_link}\n\n--- WEB RESULTS ---\n"
        except Exception:
            pass

        # 1. Try modern direct ddgs library (fast, lightweight, no langchain import stalls)
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if results:
                    web_part = "\n\n".join([
                        f"Title: {r.get('title', 'No Title')}\nSnippet: {r.get('body', '')}\nURL: {r.get('href', '')}"
                        for r in results
                    ])
                    return prefix_wiki + web_part
        except Exception as e_ddgs:
            logging.warning(f"Direct ddgs search failed for '{query}': {e_ddgs}")

        # 2. Try DuckDuckGoSearchRun from langchain_community
        try:
            from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchRun
            res = DuckDuckGoSearchRun().run(tool_input=query)
            if res:
                return prefix_wiki + res
        except Exception as e_lc:
            logging.warning(f"DuckDuckGoSearchRun failed for '{query}': {e_lc}")

        # 3. Try legacy duckduckgo_search library directly
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if results:
                    web_part = "\n\n".join([
                        f"Title: {r.get('title', 'No Title')}\nSnippet: {r.get('body', '')}\nURL: {r.get('href', '')}"
                        for r in results
                    ])
                    return prefix_wiki + web_part
        except Exception as e_old:
            logging.warning(f"Legacy duckduckgo_search failed for '{query}': {e_old}")

        return prefix_wiki.strip() or None

    try:
        results = await asyncio.to_thread(_perform_search)
        if results:
            logging.info(f"Search results for '{query}': {results[:250]}...")
            return results
        else:
            logging.error(f"All search backends returned empty or failed for '{query}'")
            return f"I was unable to retrieve search results for '{query}' right now."
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."    

@function_tool()    
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    try:
        ui_state.set_text(f"📧 Sending email to {to_email}...")
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Email sending failed: Gmail credentials not configured."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Attach message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(gmail_user, gmail_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()
        
        logging.info(f"Email sent successfully to {to_email}")
        return f"Email sent successfully to {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "Email sending failed: Authentication error. Please check your Gmail credentials."
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"An error occurred while sending email: {str(e)}"

def _focus_chrome_window() -> bool:
    """Brings Google Chrome main window to the foreground."""
    try:
        import win32gui
        import win32con
        import win32process
        import ctypes
        
        target = None
        def enum_cb(hwnd, _):
            nonlocal target
            if target:
                return
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                cls = win32gui.GetClassName(hwnd).lower()
                # Must have a non-empty window title to ensure it's an actual browser window, not background/tray
                if title and ("chrome_widgetwin_1" in cls or "chrome" in cls or "chrome" in title.lower() or "google chrome" in title.lower()):
                    target = hwnd
                    
        win32gui.EnumWindows(enum_cb, None)
        if target:
            user32 = ctypes.windll.user32
            fore_hwnd = user32.GetForegroundWindow()
            fore_thread = win32process.GetWindowThreadProcessId(fore_hwnd)[0] if fore_hwnd else 0
            app_thread = ctypes.windll.kernel32.GetCurrentThreadId()
            if fore_thread and fore_thread != app_thread:
                user32.AttachThreadInput(fore_thread, app_thread, True)
                win32gui.ShowWindow(target, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target)
                win32gui.BringWindowToTop(target)
                user32.AttachThreadInput(fore_thread, app_thread, False)
            else:
                win32gui.ShowWindow(target, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target)
                win32gui.BringWindowToTop(target)
            return True
    except Exception as e:
        logging.debug(f"Focus Chrome failed: {e}")
    return False

def _cdp_get_tabs(port: int = 9222) -> list:
    try:
        import urllib.request
        import json
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=0.8) as resp:
            data = json.loads(resp.read().decode())
            return [t for t in data if t.get("type") == "page"]
    except Exception:
        return []

def _cdp_open_tab(url: str, port: int = 9222) -> bool:
    try:
        import urllib.request
        import urllib.parse
        import json
        target_url = urllib.parse.quote(url, safe=":/%?&=#@+-_.~")
        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?{target_url}", method="PUT")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                try:
                    tab_data = json.loads(resp.read().decode())
                    if "id" in tab_data:
                        _cdp_activate_tab(tab_data["id"], port)
                except Exception:
                    pass
                return True
    except Exception:
        return False

def _cdp_activate_tab(tab_id: str, port: int = 9222) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/activate/{tab_id}", timeout=0.6) as resp:
            return resp.status == 200
    except Exception:
        return False

def _cdp_close_tab(tab_id: str, port: int = 9222) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/close/{tab_id}", timeout=0.6) as resp:
            return resp.status == 200
    except Exception:
        return False

async def _cdp_eval_js(script: str, port: int = 9222, url_keyword: str = "") -> Optional[Any]:
    tabs = _cdp_get_tabs(port)
    if not tabs:
        return None
    target_tab = None
    if url_keyword:
        kw = url_keyword.lower()
        for t in tabs:
            if kw in t.get("url", "").lower() or kw in t.get("title", "").lower():
                target_tab = t
                break
    if not target_tab:
        target_tab = tabs[0]
    ws_url = target_tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return None
    try:
        import websockets
        import json
        async with websockets.connect(ws_url, close_timeout=1.0) as ws:
            msg = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {"expression": script, "returnByValue": True, "awaitPromise": True}
            }
            await ws.send(json.dumps(msg))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            val = resp.get("result", {}).get("result", {}).get("value")
            return val
    except Exception as e:
        logging.debug(f"CDP eval failed: {e}")
        return None

@function_tool()
async def open_website(
    context: RunContext,  # type: ignore
    url: str
) -> str:
    """
    Open any website or web application in Google Chrome.
    """
    try:
        ui_state.set_text(f"🌐 Opening website...")
        logging.info(f"Opening website: {url}")
        target = url.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target = "https://" + target

        if _is_cdp_available(9222):
            if _cdp_open_tab(target, 9222):
                _focus_chrome_window()
                return f"Opened {target} in Chrome, Sir."

        chrome_path = _get_chrome_path()
        if chrome_path:
            import subprocess
            import sys
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
            subprocess.Popen(
                [chrome_path, target],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )
            await asyncio.sleep(0.5)
            _focus_chrome_window()
            return f"Opened {target} in Google Chrome, Sir."
        else:
            await asyncio.to_thread(webbrowser.open, target)
            return f"Successfully opened {target} in your browser, Sir."
    except Exception as e:
        return f"Failed to open website: {str(e)}"

def find_top_youtube_video(query: str) -> Optional[Dict[str, Any]]:
    """
    Quickly and reliably find the top YouTube video for a query.
    Returns dict with keys: video_id, title, artist, cover.
    """
    clean_q = query.strip()
    if not clean_q:
        return None

    # Step 1: Fast YouTube HTML search scrape via regex (< 1s)
    try:
        import urllib.request
        import urllib.parse
        import re
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            }
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            vr_match = re.search(r'\"videoRenderer\":\{\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
            if vr_match:
                vid = vr_match.group(1)
                title_match = re.search(r'\"title\":\{\"runs\":\[\{\"text\":\"([^\"]+)\"\}', html)
                title = title_match.group(1) if title_match else clean_q
                try:
                    import codecs
                    title = codecs.decode(title, 'unicode_escape')
                except Exception:
                    pass
                return {
                    "video_id": vid,
                    "title": title,
                    "artist": "",
                    "cover": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                }

            v_matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
            if v_matches:
                vid = v_matches[0]
                return {
                    "video_id": vid,
                    "title": clean_q,
                    "artist": "",
                    "cover": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                }
    except Exception as e:
        logging.warning(f"YouTube fast scrape warning for '{clean_q}': {e}")

    # Step 2: ytmusicapi fallback
    try:
        from ytmusicapi import YTMusic
        yt = YTMusic()
        res = yt.search(clean_q, filter="songs")
        if not res:
            res = yt.search(clean_q)
        if res and len(res) > 0:
            top = res[0]
            vid = top.get("videoId")
            if vid:
                title = top.get("title", clean_q)
                artists_list = [a.get("name") for a in top.get("artists", []) if a.get("name")]
                artist = ", ".join(artists_list) if artists_list else ""
                thumbnails = top.get("thumbnails", [])
                cover = thumbnails[-1].get("url") if thumbnails else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                return {
                    "video_id": vid,
                    "title": title,
                    "artist": artist,
                    "cover": cover
                }
    except Exception as e:
        logging.warning(f"ytmusicapi search warning for '{clean_q}': {e}")

    # Step 3: yt-dlp flat search fallback
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{clean_q}", download=False)
            if info and "entries" in info and len(info["entries"]) > 0:
                first = info["entries"][0]
                vid = first.get("id")
                if vid:
                    return {
                        "video_id": vid,
                        "title": first.get("title", clean_q),
                        "artist": first.get("uploader", ""),
                        "cover": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                    }
    except Exception as e:
        logging.warning(f"yt_dlp flat lookup warning for '{clean_q}': {e}")

    return None

@function_tool()
async def control_browser(
    context: RunContext,  # type: ignore
    action: str,
    query: str = "",
    url: str = ""
) -> str:
    """
    Control Google Chrome directly: search, play YouTube videos, click top results, control video playback, tabs, and navigation.
    Supported actions:
    - 'play_youtube' | 'play_video' | 'play_song': Search YouTube AND immediately play top video on the watch player (query='song or video name')
    - 'search_youtube': Search YouTube for query (query='topic')
    - 'search_amazon': Search Amazon for products (query='item')
    - 'search_flipkart': Search Flipkart for products (query='item')
    - 'search_google': Search Google for query (query='search terms')
    - 'play_first' | 'click_first': Play or click the top video or product on the current webpage
    - 'skip_ad': Skip YouTube advertisement if present
    - 'play_pause' | 'pause' | 'resume': Toggle video/audio playback on active webpage
    - 'mute' | 'unmute': Toggle mute on active video
    - 'next_video': Skip to next video on YouTube
    - 'prev_video': Go back to previous video on YouTube
    - 'seek_forward': Jump forward 10 seconds on video
    - 'seek_backward': Rewind 10 seconds on video
    - 'playback_speed': Set video playback speed (query='1.5x' | '2x' | 'normal')
    - 'fullscreen': Toggle fullscreen video / browser
    - 'theater_mode': Toggle YouTube theater mode
    - 'captions' | 'subtitles': Toggle closed captions
    - 'new_tab': Open a new tab (optionally at given url)
    - 'close_tab': Close the active browser tab
    - 'reopen_tab': Reopen the last closed tab
    - 'next_tab': Switch to the next tab
    - 'prev_tab': Switch to the previous tab
    - 'refresh': Reload the active tab
    - 'go_back': Navigate back in browser history
    - 'go_forward': Navigate forward in browser history
    - 'scroll_down': Scroll down on the active webpage
    - 'scroll_up': Scroll up on the active webpage
    - 'scroll_top': Scroll to top of webpage
    - 'scroll_bottom': Scroll to bottom of webpage
    - 'zoom_in': Zoom in webpage (Ctrl++)
    - 'zoom_out': Zoom out webpage (Ctrl+-)
    - 'zoom_reset': Reset zoom to 100% (Ctrl+0)
    - 'focus': Bring Google Chrome window to the foreground
    - 'status' | 'current_tab': Get title and URL of current active tab
    """
    import urllib.parse
    import pyautogui
    act = action.lower().strip()
    ui_state.set_text(f"🌐 Browser | {act.replace('_', ' ').title()}")
    try:
        if act in ["play_youtube", "play_video", "play_song", "play_music"]:
            q = query.strip()
            if q:
                # Fast direct video resolution so we open the actual video player and play immediately
                vid_info = await asyncio.to_thread(find_top_youtube_video, q)
                if vid_info and vid_info.get("video_id"):
                    v_id = vid_info["video_id"]
                    v_title = vid_info.get("title", q)
                    target = f"https://www.youtube.com/watch?v={v_id}"
                    await open_website(None, target)
                    ui_state.set_text(f"🎵 Playing {v_title[:25]}")
                    if _is_cdp_available(9222):
                        await asyncio.sleep(1.2)
                        await _cdp_eval_js("""
                        (() => {
                            const v = document.querySelector('video');
                            if (v && v.paused) { v.play(); }
                            return 'playing';
                        })()
                        """, url_keyword="youtube")
                    _focus_chrome_window()
                    return f"Playing '{v_title}' on YouTube in your browser, Sir."
                else:
                    target = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
                    await open_website(None, target)
                    await asyncio.sleep(1.8)
                    if _is_cdp_available(9222):
                        res = await _cdp_eval_js("""
                        (() => {
                            const yt = document.querySelector('ytd-video-renderer a#thumbnail, ytd-rich-item-renderer a#thumbnail, #contents ytd-video-renderer a#video-title');
                            if (yt) { yt.click(); return 'Started top YouTube video'; }
                            return null;
                        })()
                        """, url_keyword="youtube")
                        if res:
                            _focus_chrome_window()
                            return f"Playing '{q}' on YouTube, Sir."
                    _focus_chrome_window()
                    await asyncio.to_thread(pyautogui.press, 'enter')
                    return f"Playing top result for '{q}' on YouTube, Sir."
            else:
                _focus_chrome_window()
                return "Please provide a song or video title to play on YouTube, Sir."

        elif act in ["search_youtube", "youtube"]:
            q = query.strip()
            target = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            await open_website(None, target)
            return f"Searched YouTube for '{q}' in Chrome, Sir."

        elif act in ["search_flipkart", "flipkart"]:
            q = query.strip()
            target = f"https://www.flipkart.com/search?q={urllib.parse.quote_plus(q)}"
            await open_website(None, target)
            return f"Opened Flipkart search for '{q}' in your Chrome browser, Sir."

        elif act in ["search_amazon", "amazon"]:
            q = query.strip()
            target = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(q)}"
            await open_website(None, target)
            return f"Opened Amazon search for '{q}' in your Chrome browser, Sir."

        elif act == "search_google":
            q = query.strip()
            target = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
            await open_website(None, target)
            return f"Searched Google for '{q}' in your browser, Sir."

        elif act in ["play_first", "click_first", "open_first", "select_first"]:
            if _is_cdp_available(9222):
                js_click = """
                (() => {
                    const yt = document.querySelector('ytd-video-renderer a#thumbnail, ytd-rich-item-renderer a#thumbnail, ytd-compact-video-renderer a#thumbnail, #contents ytd-video-renderer a#video-title');
                    if (yt) { yt.click(); return 'Started top YouTube video'; }
                    const amz = document.querySelector('div[data-component-type="s-search-result"] h2 a, a.s-no-outline');
                    if (amz) { amz.click(); return 'Opened top Amazon product'; }
                    const fk = document.querySelector('div._1AtVbE a._1fQZEK, div._1AtVbE a.s1Q9rs, a.CG2cNx');
                    if (fk) { fk.click(); return 'Opened top Flipkart product'; }
                    const g = document.querySelector('#search a h3, #rso a');
                    if (g) { g.closest('a').click(); return 'Opened top search result'; }
                    const anyL = document.querySelector('main a, #content a, article a');
                    if (anyL) { anyL.click(); return 'Clicked first link on page'; }
                    return null;
                })()
                """
                res = await _cdp_eval_js(js_click)
                if res:
                    _focus_chrome_window()
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'enter')
            return "Selected first item in Chrome, Sir."

        elif act in ["skip_ad", "skip"]:
            if _is_cdp_available(9222):
                js_skip = """
                (() => {
                    const btn = document.querySelector('.ytp-skip-ad-button, .ytp-ad-skip-button-modern, .ytp-ad-skip-button, button[id^="skip-button"], .ytp-ad-overlay-close-button');
                    if (btn) { btn.click(); return 'Skipped advertisement'; }
                    const ad = document.querySelector('.ad-showing video, .ytp-ad-player-overlay');
                    if (ad) {
                        const v = document.querySelector('video');
                        if (v && !isNaN(v.duration) && isFinite(v.duration)) {
                            v.currentTime = v.duration;
                            return 'Fast-forwarded ad to completion';
                        }
                    }
                    return null;
                })()
                """
                res = await _cdp_eval_js(js_skip, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'tab')
            await asyncio.sleep(0.05)
            await asyncio.to_thread(pyautogui.press, 'enter')
            return "Attempted to skip advertisement, Sir."

        elif act in ["play_pause", "toggle_video", "pause", "resume", "play"]:
            if _is_cdp_available(9222):
                js_toggle = """
                (() => {
                    const v = document.querySelector('video');
                    if (v) {
                        if (v.paused) { v.play(); return 'Resumed playback'; }
                        else { v.pause(); return 'Paused playback'; }
                    }
                    return null;
                })()
                """
                res = await _cdp_eval_js(js_toggle, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'k')
            return "Toggled video playback, Sir."

        elif act in ["mute", "unmute", "toggle_mute"]:
            if _is_cdp_available(9222):
                js_mute = """
                (() => {
                    const v = document.querySelector('video');
                    if (v) { v.muted = !v.muted; return v.muted ? 'Muted video' : 'Unmuted video'; }
                    return null;
                })()
                """
                res = await _cdp_eval_js(js_mute, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'm')
            return "Toggled video mute, Sir."

        elif act in ["next_video", "skip_video"]:
            if _is_cdp_available(9222):
                res = await _cdp_eval_js("""
                (() => {
                    const nextBtn = document.querySelector('.ytp-next-button');
                    if (nextBtn) { nextBtn.click(); return 'Playing next video'; }
                    return null;
                })()
                """, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'shift', 'n')
            return "Playing next video on YouTube, Sir."

        elif act in ["prev_video", "previous_video"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'shift', 'p')
            return "Playing previous video on YouTube, Sir."

        elif act in ["seek_forward", "forward", "jump_forward", "fast_forward"]:
            if _is_cdp_available(9222):
                res = await _cdp_eval_js("""
                (() => {
                    const v = document.querySelector('video');
                    if (v) { v.currentTime = Math.min(v.duration || Infinity, v.currentTime + 10); return 'Jumped forward 10 seconds'; }
                    return null;
                })()
                """, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'l')
            return "Jumped forward 10 seconds, Sir."

        elif act in ["seek_backward", "backward", "rewind", "jump_backward"]:
            if _is_cdp_available(9222):
                res = await _cdp_eval_js("""
                (() => {
                    const v = document.querySelector('video');
                    if (v) { v.currentTime = Math.max(0, v.currentTime - 10); return 'Rewound 10 seconds'; }
                    return null;
                })()
                """, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'j')
            return "Rewound 10 seconds, Sir."

        elif act in ["playback_speed", "speed", "speed_up", "slow_down"]:
            speed_val = 1.0
            if "1.5" in query:
                speed_val = 1.5
            elif "2" in query:
                speed_val = 2.0
            elif "1.25" in query:
                speed_val = 1.25
            elif "0.75" in query:
                speed_val = 0.75
            elif "0.5" in query:
                speed_val = 0.5
            elif "normal" in query or "1x" in query or query == "1":
                speed_val = 1.0
            else:
                speed_val = 1.5
            if _is_cdp_available(9222):
                res = await _cdp_eval_js(f"""
                (() => {{
                    const v = document.querySelector('video');
                    if (v) {{ v.playbackRate = {speed_val}; return 'Set playback speed to {speed_val}x'; }}
                    return null;
                }})()
                """, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            return f"Set playback speed to {speed_val}x in Chrome, Sir."

        elif act in ["fullscreen", "toggle_fullscreen"]:
            if _is_cdp_available(9222):
                res = await _cdp_eval_js("""
                (() => {
                    const btn = document.querySelector('.ytp-fullscreen-button');
                    if (btn) { btn.click(); return 'Toggled fullscreen mode'; }
                    return null;
                })()
                """, url_keyword="youtube")
                if res:
                    return f"{res}, Sir."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'f')
            return "Toggled fullscreen mode, Sir."

        elif act in ["theater_mode", "theatre_mode"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 't')
            return "Toggled YouTube theater mode, Sir."

        elif act in ["captions", "subtitles", "toggle_captions"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'c')
            return "Toggled video subtitles/captions, Sir."

        elif act == "new_tab":
            if url and url.strip():
                return await open_website(None, url)
            else:
                if _is_cdp_available(9222):
                    _cdp_open_tab("chrome://newtab", 9222)
                    _focus_chrome_window()
                    return "Opened new browser tab."
                _focus_chrome_window()
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 't')
                return "Opened new browser tab."

        elif act in ["close_tab", "close"]:
            if _is_cdp_available(9222):
                tabs = _cdp_get_tabs(9222)
                if tabs:
                    _cdp_close_tab(tabs[0]["id"], 9222)
                    return "Closed active browser tab."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'w')
            return "Closed active browser tab."

        elif act in ["reopen_tab", "restore_tab"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'shift', 't')
            return "Reopened previously closed browser tab."

        elif act in ["next_tab", "switch_tab"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'tab')
            return "Switched to next browser tab."

        elif act in ["prev_tab", "previous_tab"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'shift', 'tab')
            return "Switched to previous browser tab."

        elif act in ["refresh", "reload"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'r')
            return "Reloaded active webpage."

        elif act in ["go_back", "back"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'alt', 'left')
            return "Navigated back in browser history."

        elif act in ["go_forward", "forward"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'alt', 'right')
            return "Navigated forward in browser history."

        elif act in ["scroll_down", "down"]:
            if _is_cdp_available(9222):
                await _cdp_eval_js('window.scrollBy({top: 600, behavior: "smooth"})')
                return "Scrolled down on webpage."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'pagedown')
            return "Scrolled down on webpage."

        elif act in ["scroll_up", "up"]:
            if _is_cdp_available(9222):
                await _cdp_eval_js('window.scrollBy({top: -600, behavior: "smooth"})')
                return "Scrolled up on webpage."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'pageup')
            return "Scrolled up on webpage."

        elif act in ["scroll_top", "top"]:
            if _is_cdp_available(9222):
                await _cdp_eval_js('window.scrollTo({top: 0, behavior: "smooth"})')
                return "Scrolled to top of webpage."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'home')
            return "Scrolled to top of webpage."

        elif act in ["scroll_bottom", "bottom"]:
            if _is_cdp_available(9222):
                await _cdp_eval_js('window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"})')
                return "Scrolled to bottom of webpage."
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.press, 'end')
            return "Scrolled to bottom of webpage."

        elif act in ["zoom_in"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', '+')
            return "Zoomed in webpage, Sir."

        elif act in ["zoom_out"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', '-')
            return "Zoomed out webpage, Sir."

        elif act in ["zoom_reset"]:
            _focus_chrome_window()
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', '0')
            return "Reset webpage zoom, Sir."

        elif act in ["focus", "bring_to_front"]:
            if _focus_chrome_window():
                return "Brought Google Chrome to front, Sir."
            return "Google Chrome window not found."

        elif act in ["status", "current_tab", "what_tab"]:
            if _is_cdp_available(9222):
                tabs = _cdp_get_tabs(9222)
                if tabs:
                    active = tabs[0]
                    return f"Active tab: '{active.get('title')}' ({active.get('url')}), Sir."
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if "chrome" in title.lower():
                return f"Current Chrome window: '{title}', Sir."
            return "No active Chrome tab detected, Sir."

        else:
            return f"Unknown browser action: '{action}'. Available: play_youtube, search_youtube, search_amazon, search_flipkart, search_google, play_first, skip_ad, play_pause, mute, next_video, prev_video, seek_forward, seek_backward, playback_speed, fullscreen, theater_mode, captions, new_tab, close_tab, reopen_tab, next_tab, prev_tab, refresh, go_back, go_forward, scroll_down, scroll_up, scroll_top, scroll_bottom, zoom_in, zoom_out, zoom_reset, focus, status."
    except Exception as e:
        return f"Browser control failed: {str(e)}"

@function_tool()
async def launch_chrome_with_control(
    context: RunContext,  # type: ignore
    url: Optional[str] = None,
    restart_if_running: bool = False
) -> str:
    """
    Launch or connect to Google Chrome with Zenith automation (CDP port 9222) enabled.
    This connects Zenith directly to Chrome, allowing full remote control of tabs,
    media, video playback, links, and search results.
    """
    chrome_path = _get_chrome_path()
    if not chrome_path:
        return "Could not locate a compatible Chrome installation on your system, Sir."

    if _is_cdp_available(9222):
        if url:
            target = url.strip()
            if not target.startswith("http"):
                target = "https://" + target
            _cdp_open_tab(target, 9222)
            _focus_chrome_window()
            return f"Opened {target} in your controlled Chrome browser, Sir."
        _focus_chrome_window()
        return "Google Chrome is already running with Zenith remote control active on port 9222, Sir. I am connected directly."

    import subprocess
    import sys
    args = [
        chrome_path,
        "--remote-debugging-port=9222",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    if url:
        target = url.strip()
        if not target.startswith("http"):
            target = "https://" + target
        args.append(target)

    try:
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
        subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
        for _ in range(6):
            await asyncio.sleep(0.5)
            if _is_cdp_available(9222):
                break

        if _is_cdp_available(9222):
            ui_state.set_text("🌐 Chrome Connected (CDP 9222)")
            _focus_chrome_window()
            return "Google Chrome is now connected with automation on port 9222, Sir. I can control your browser directly."
        else:
            _focus_chrome_window()
            return "Google Chrome was launched, Sir."
    except Exception as e:
        return f"Failed to launch Chrome with remote control: {str(e)}"


# ==============================================================================
# AUTONOMOUS AGENTIC WEB BROWSING (Powered by browser-use & Gemini 2.5 Flash)
# ==============================================================================

_web_agent_lock = asyncio.Lock()
_active_agent = None
_active_task_coro: Optional[asyncio.Task] = None
_current_web_task_desc: Optional[str] = None

async def cancel_active_web_task() -> bool:
    """
    Stops and cancels any currently executing autonomous web browsing agent.
    Returns True if an active task was found and stopped, False otherwise.
    """
    global _active_agent, _active_task_coro, _current_web_task_desc, _web_agent_lock
    was_active = False

    agent_to_stop = _active_agent
    task_to_cancel = _active_task_coro
    desc = _current_web_task_desc

    if agent_to_stop is not None:
        was_active = True
        logging.info(f"Signaling active web agent to stop (task: {desc})...")
        try:
            agent_to_stop.stop()
        except Exception as e:
            logging.warning(f"Error calling agent.stop(): {e}")

        try:
            if hasattr(agent_to_stop, 'browser_session') and agent_to_stop.browser_session:
                logging.info("Terminating active browser session...")
                await agent_to_stop.browser_session.kill()
        except Exception as e:
            logging.warning(f"Error killing browser session: {e}")

    if task_to_cancel is not None and not task_to_cancel.done():
        was_active = True
        try:
            task_to_cancel.cancel()
        except Exception as e:
            logging.warning(f"Error cancelling task coroutine: {e}")

    if was_active:
        for _ in range(15):
            if not _web_agent_lock.locked() and (task_to_cancel is None or task_to_cancel.done()):
                break
            await asyncio.sleep(0.1)

    if _web_agent_lock.locked():
        logging.warning("Web agent lock still held after cancel attempt; resetting lock.")
        _web_agent_lock = asyncio.Lock()

    return was_active

@function_tool()
async def stop_current_task(
    context: RunContext,  # type: ignore
    task_type: Optional[str] = "all"
) -> str:
    """
    Immediately stop, cancel, and abort any currently running autonomous task (web browsing, screen automation, or active long-running tool).
    Call this tool whenever:
    - The user says "stop", "cancel", "halt", "hold on", "wait", "ruk jao", "nahi ruko", "mat karo", "chhod do", or "abort".
    - The user indicates that an ongoing search or action is wrong, misheard, or no longer needed.
    - The user wants you to cease whatever task you are currently performing.

    Args:
        task_type: Specific type of task to stop ('web', 'computer', or 'all'). Defaults to 'all'.
    """
    stopped_items = []

    # 1. Stop web browsing agent if active
    try:
        web_stopped = await cancel_active_web_task()
        if web_stopped:
            stopped_items.append("web browsing task")
    except Exception as e:
        logging.error(f"Error stopping web task: {e}")

    # 2. Stop screen computer-use automation if active
    try:
        from computer_use import cancel_active_computer_task
        pc_stopped = await cancel_active_computer_task()
        if pc_stopped:
            stopped_items.append("screen automation task")
    except Exception as e:
        logging.debug(f"Computer task cancellation check: {e}")

    # 3. Stop smart TTS multi-voice narration if active
    try:
        from agent_tools.smart_tts import control_narration
        await control_narration(None, "stop")
    except Exception:
        pass

    ui_state.set_text("⏹️ Task Stopped")

    if stopped_items:
        joined = ", ".join(stopped_items)
        return f"Successfully stopped active {joined}, Sir."
    return "All active tasks have been stopped, Sir."

def _get_chrome_path() -> Optional[str]:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

import socket
import shutil

def _is_cdp_available(port: int = 9222) -> bool:
    """Check if the user's real Chrome is running with remote debugging port enabled."""
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.2):
            return True
    except Exception:
        return False

@function_tool()
async def autonomous_web_task(
    context: RunContext,  # type: ignore
    task: str,
    max_steps: int = 8
) -> str:
    """
    Execute an autonomous multi-step web agent task using browser-use and Gemini.
    Use this for tasks that require navigating websites, clicking elements, searching multiple pages,
    comparing products/prices, filling out web forms, interacting with dynamic web apps, or extracting structured data.
    
    Examples:
    - "Find the cheapest RTX 4080 Super on Amazon and report the top 3 options with price"
    - "Go to Wikipedia, find recent news about space exploration, and summarize the key facts"
    - "Look up flight schedules from Delhi to Mumbai on Google Flights"
    - "Fill out the contact inquiry form on example.com"
    
    Args:
        task: Clear natural language description of what the web agent should do or extract.
        max_steps: Maximum number of browsing interaction steps allowed (default 8).
    """
    global _web_agent_lock, _active_agent, _active_task_coro, _current_web_task_desc

    # If another web task is active or holding lock, PREEMPT IT!
    if _web_agent_lock.locked() or (_active_task_coro is not None and not _active_task_coro.done()):
        logging.info(f"Preempting active web task '{_current_web_task_desc}' for new incoming task: '{task}'")
        await cancel_active_web_task()

    async with _web_agent_lock:
        current_coro = asyncio.current_task()
        _active_task_coro = current_coro
        _current_web_task_desc = task
        ui_state.set_text(f"🌐 Web Agent | {task[:22]}...")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Google API key is not configured for autonomous web browsing."

        chrome_path = _get_chrome_path()
        if not chrome_path:
            return "Could not locate a compatible Chrome or Edge browser executable on the system."

        agent = None
        try:
            from browser_use import ChatGoogle, BrowserProfile, Agent
            
            # If user's real Chrome is running with remote debugging (CDP 9222), connect directly to it!
            if _is_cdp_available(9222):
                logging.info("Connecting directly to active Chrome instance on localhost:9222...")
                profile = BrowserProfile(cdp_url="http://localhost:9222", keep_alive=True)
            else:
                profile = BrowserProfile(
                    executable_path=chrome_path,
                    headless=False,
                    keep_alive=True
                )
            web_model = os.getenv("AUTONOMOUS_WEB_MODEL", "gemini-flash-latest")
            llm = ChatGoogle(model=web_model, api_key=api_key)
            agent = Agent(
                task=task,
                llm=llm,
                browser_profile=profile,
                use_thinking=False,
                use_judge=False,
                max_actions_per_step=4
            )
            _active_agent = agent

            history = await agent.run(max_steps=max(2, min(max_steps, 15)))
            res = history.final_result()
            if res:
                return f"Autonomous web task completed:\n{res}"
            else:
                return "Autonomous web task completed successfully."

        except asyncio.CancelledError:
            logging.info(f"autonomous_web_task cancelled: '{task}'")
            if agent:
                try:
                    agent.stop()
                    if hasattr(agent, 'browser_session') and agent.browser_session:
                        await agent.browser_session.kill()
                except Exception as clean_err:
                    logging.warning(f"Error during agent cancel cleanup: {clean_err}")
            ui_state.set_text("⏹️ Web task cancelled")
            raise

        except Exception as e:
            logging.error(f"Error executing autonomous_web_task: {e}", exc_info=True)
            return f"Autonomous web browsing encountered an error: {str(e)}"

        finally:
            if _active_agent is agent:
                _active_agent = None
            if _active_task_coro is current_coro:
                _active_task_coro = None
                _current_web_task_desc = None

