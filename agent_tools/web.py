import logging
import os
import requests
import asyncio
import webbrowser
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
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
    Search the web using DuckDuckGo.
    """
    try:
        from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchRun
        ui_state.set_text(f"🔍 Searching web for '{query}'...")
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
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

@function_tool()
async def open_website(
    context: RunContext,  # type: ignore
    url: str
) -> str:
    """
    Open a website in the user's default web browser.
    Make sure the URL starts with http:// or https://.
    """
    try:
        ui_state.set_text(f"🌐 Opening website...")
        logging.info(f"Opening website: {url}")
        webbrowser.open(url)
        return f"Successfully opened {url} in the browser."
    except Exception as e:
        return f"Failed to open website: {str(e)}"

@function_tool()
async def control_browser(
    context: RunContext,  # type: ignore
    action: str,
    query: str = "",
    url: str = ""
) -> str:
    """
    Control Google Chrome / default web browser actions directly.
    Supported actions:
    - 'search_youtube': Search and open YouTube with results for query (e.g. query='lofi hip hop')
    - 'search_google': Search Google for query (e.g. query='latest space missions')
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
    - 'play_pause': Toggle video/audio playback on active webpage (space/k)
    - 'fullscreen': Toggle fullscreen in browser (f11)
    """
    import urllib.parse
    import pyautogui
    act = action.lower().strip()
    ui_state.set_text(f"🌐 Browser | {act.replace('_', ' ').title()}")
    try:
        if act == "search_youtube":
            q = query.strip()
            target = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
            await asyncio.to_thread(webbrowser.open, target)
            return f"Searched YouTube for '{q}' in browser."

        elif act == "search_google":
            q = query.strip()
            target = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
            await asyncio.to_thread(webbrowser.open, target)
            return f"Searched Google for '{q}' in browser."

        elif act == "new_tab":
            if url and url.strip():
                u = url.strip()
                if not u.startswith("http"):
                    u = "https://" + u
                await asyncio.to_thread(webbrowser.open_new_tab, u)
                return f"Opened new browser tab for {u}."
            else:
                await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 't')
                return "Opened new browser tab."

        elif act in ["close_tab", "close"]:
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'w')
            return "Closed active browser tab."

        elif act in ["reopen_tab", "restore_tab"]:
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'shift', 't')
            return "Reopened previously closed browser tab."

        elif act in ["next_tab", "switch_tab"]:
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'tab')
            return "Switched to next browser tab."

        elif act in ["prev_tab", "previous_tab"]:
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'shift', 'tab')
            return "Switched to previous browser tab."

        elif act in ["refresh", "reload"]:
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'r')
            return "Reloaded active webpage."

        elif act in ["go_back", "back"]:
            await asyncio.to_thread(pyautogui.hotkey, 'alt', 'left')
            return "Navigated back in browser history."

        elif act in ["go_forward", "forward"]:
            await asyncio.to_thread(pyautogui.hotkey, 'alt', 'right')
            return "Navigated forward in browser history."

        elif act in ["scroll_down", "down"]:
            await asyncio.to_thread(pyautogui.press, 'pagedown')
            return "Scrolled down on webpage."

        elif act in ["scroll_up", "up"]:
            await asyncio.to_thread(pyautogui.press, 'pageup')
            return "Scrolled up on webpage."

        elif act in ["play_pause", "toggle_video", "pause", "resume"]:
            await asyncio.to_thread(pyautogui.press, 'space')
            return "Toggled video/audio playback on webpage."

        elif act in ["fullscreen", "toggle_fullscreen"]:
            await asyncio.to_thread(pyautogui.press, 'f11')
            return "Toggled browser fullscreen mode."

        else:
            return f"Unknown browser action: '{action}'. Available: search_youtube, search_google, new_tab, close_tab, reopen_tab, next_tab, prev_tab, refresh, go_back, go_forward, scroll_down, scroll_up, play_pause, fullscreen."
    except Exception as e:
        return f"Browser control failed: {str(e)}"
