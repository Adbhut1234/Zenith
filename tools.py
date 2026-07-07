import logging
from computer_use import computer_use_loop
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
import subprocess
import webbrowser
import pyautogui
import asyncio
import ui_state

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        ui_state.set_text(f"🌤️ Checking weather for {city}...")
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()   
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}." 

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using DuckDuckGo.
    """
    try:
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
async def execute_pc_command(
    context: RunContext,  # type: ignore
    command: str,
    reasoning: str,
    user_confirmed: bool = False
) -> str:
    """
    Execute a Windows system command on the user's PC. 
    Can be used to open apps (e.g. 'start calc', 'start notepad', 'start spotify'), manage files, or change system settings.
    Use this when the user asks you to control their computer or open an application.
    If the command requires confirmation, ask the user verbally and call this tool again with user_confirmed=True.
    """
    try:
        allowed_commands_str = os.getenv("ALLOWED_COMMANDS", "start calc,start notepad,explorer")
        allowed_commands = [c.strip().lower() for c in allowed_commands_str.split(",")]
        require_confirmation = os.getenv("REQUIRE_CMD_CONFIRMATION", "true").lower() == "true"
        
        is_allowed = any(command.lower().startswith(cmd) for cmd in allowed_commands)
        
        if (require_confirmation or not is_allowed) and not user_confirmed:
            logging.info(f"Command execution requires confirmation: {command}")
            return f"Action requires user confirmation. Command '{command}' was NOT executed. Please verbally ask the user to confirm. If they say yes, call this tool again with user_confirmed=True."

        ui_state.set_text(f"💻 Executing command...")
        logging.info(f"Executing PC command: {command} (Reasoning: {reasoning}, Confirmed: {user_confirmed})")
        # Run the command using powershell/cmd
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return f"Command executed successfully. Output: {output}"
        else:
            return f"Command failed with error: {error}"
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error executing command: {str(e)}"

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
async def write_and_open_file(
    context: RunContext,  # type: ignore
    filename: str,
    content: str
) -> str:
    """
    Write text or code to a file and then instantly open it with the default application (like Notepad).
    Use this when the user asks you to write an application, script, or document and show it to them.
    """
    try:
        ui_state.set_text(f"📝 Writing to file...")
        logging.info(f"Writing to file: {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Open the file using the default application (cross-platform fallback)
        import sys
        if sys.platform == "win32":
            os.startfile(filename)
        elif sys.platform == "darwin":
            subprocess.call(["open", filename])
        else:
            subprocess.call(["xdg-open", filename])
            
        return f"Successfully wrote {len(content)} characters to {filename} and opened it."
    except Exception as e:
        return f"Failed to write or open file: {str(e)}"

@function_tool()
async def move_and_click_mouse(
    context: RunContext,  # type: ignore
    x: int,
    y: int,
    click: bool = True
) -> str:
    """
    Move the mouse to a known (x, y) coordinate and optionally click.
    ONLY use this when exact coordinates are explicitly given (e.g. the user
    says "click at 500, 300", or you just ran control_computer and it reported
    the coordinate). Do NOT use this to click something you haven't confirmed
    the location of — use control_computer for that instead.
    """
    try:
        logging.info(f"Moving mouse to ({x}, {y})")
        await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.5)
        if click:
            await asyncio.to_thread(pyautogui.click)
            return f"Successfully moved to ({x}, {y}) and clicked."
        return f"Successfully moved to ({x}, {y})."
    except Exception as e:
        return f"Failed to control mouse: {str(e)}"

@function_tool()
async def type_keyboard_text(
    context: RunContext,  # type: ignore
    text: str,
    press_enter: bool = True
) -> str:
    """
    Type text wherever the cursor is currently focused. Use this for quick
    follow-up text entry right after a click you already made (e.g. via
    control_computer), not as the primary way to fill out a form from scratch
    — for that, use control_computer so each field can be visually verified.
    """
    try:
        logging.info(f"Typing text: {text}")
        await asyncio.to_thread(pyautogui.write, text, interval=0.05)
        if press_enter:
            await asyncio.to_thread(pyautogui.press, 'enter')
            return f"Successfully typed text and pressed Enter."
        return f"Successfully typed text."
    except Exception as e:
        return f"Failed to type on keyboard: {str(e)}"

@function_tool()
async def press_keyboard_shortcut(
    context: RunContext,  # type: ignore
    keys: str
) -> str:
    """
    Press a keyboard shortcut (e.g. 'ctrl,c', 'win,d', 'alt,tab', 'enter', 'esc').
    Separate multiple keys with commas if they should be pressed simultaneously.
    """
    try:
        logging.info(f"Pressing shortcut: {keys}")
        key_list = [k.strip() for k in keys.split(',')]
        await asyncio.to_thread(pyautogui.hotkey, *key_list)
        return f"Successfully pressed {keys}."
    except Exception as e:
        return f"Failed to press shortcut: {str(e)}"

@function_tool()
async def control_computer(context: RunContext, task: str) -> str:
    """
    Take control of the screen to complete a multi-step visual task — looking at screenshots,
    clicking, typing, and verifying each step before moving on. Use this instead of
    move_and_click_mouse/type_keyboard_text when the task needs precise visual grounding
    (e.g. "open Spotify and play my workout playlist", "fill out this form").
    """
    try:
        ui_state.set_text(f"👁️ Controlling screen for '{task}'...")
        return await computer_use_loop(task)
    except Exception as e:
        logging.error(f"control_computer failed: {e}")
        return f"Computer control task failed: {str(e)}"

@function_tool()
async def open_application(context: RunContext, app_name: str) -> str:
    """
    Open any installed application by its display name, using Windows Search —
    works for any app in the Start Menu, regardless of whether it has a registered
    system command or URI protocol. Use this as the default way to open apps,
    instead of guessing 'start <name>' in execute_pc_command.
    """
    try:
        ui_state.set_text(f"🚀 Opening {app_name}...")
        logging.info(f"Opening application via Windows Search: {app_name}")
        await asyncio.to_thread(pyautogui.press, 'win')
        await asyncio.sleep(0.5)
        await asyncio.to_thread(pyautogui.write, app_name, interval=0.05)
        await asyncio.sleep(1.2)  # let search results populate before confirming
        await asyncio.to_thread(pyautogui.press, 'enter')
        return f"Opened '{app_name}' via Windows Search."
    except Exception as e:
        return f"Failed to open '{app_name}': {str(e)}"

@function_tool()
async def get_now_playing(context: RunContext) -> str:
    """Get the name of the song currently playing in YouTube Music Desktop App."""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        w = desktop.window(title_re=".*YouTube Music.*")
        title = w.window_text()
        # Title format: "Song Name - Artist | YouTube Music Desktop App"
        if " | " in title:
            return f"Currently playing: {title.split(' | ')[0]}"
        return f"Window title: {title}"
    except Exception as e:
        return f"Could not read now playing: {e}"