import logging
import os
import subprocess
import asyncio
import sys
import pyautogui
from livekit.agents import function_tool, RunContext
import ui_state

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
