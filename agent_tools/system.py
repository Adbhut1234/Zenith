import logging
import os
import subprocess
import asyncio
import sys
import pyautogui
from livekit.agents import function_tool, RunContext
import ui_state

@function_tool()
async def open_file(
    context: RunContext,  # type: ignore
    filename_or_path: str
) -> str:
    """
    Open any existing file (PDF, document, image, report, spreadsheet, video) on the user's PC using its default application.
    Automatically searches common locations like Desktop, Downloads, and Documents if a relative filename is provided.
    Use this IMMEDIATELY whenever the user asks to open a specific file (e.g., 'open resume.pdf', 'open the PDF file on my desktop', 'open report.docx').
    NEVER ask for verbal confirmation to open a file.
    """
    try:
        ui_state.set_text(f"File | Opening '{os.path.basename(filename_or_path)}'")
        target_input = filename_or_path.strip().strip('"').strip("'")
        target_path = os.path.expanduser(target_input)

        # 1. Direct path check
        if os.path.exists(target_path) and os.path.isfile(target_path):
            os.startfile(os.path.abspath(target_path))
            return f"Successfully opened file: '{target_path}'"

        # 2. Search common user directories (Desktop, Downloads, Documents)
        user_home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Pictures"),
            user_home
        ]

        clean_name = os.path.basename(target_path).lower()

        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for entry in os.listdir(d):
                full_entry_path = os.path.join(d, entry)
                if os.path.isfile(full_entry_path):
                    if entry.lower() == clean_name or clean_name in entry.lower():
                        os.startfile(full_entry_path)
                        return f"Found and opened file: '{full_entry_path}'"

        # 3. System launcher fallback
        res = subprocess.run(f'start "" "{target_input}"', shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return f"Opened file '{target_input}' via system launcher."

        return f"Could not locate file '{filename_or_path}' on Desktop, Downloads, or Documents. Please verify the filename."
    except Exception as e:
        return f"Failed to open file '{filename_or_path}': {e}"

@function_tool()
async def execute_pc_command(
    context: RunContext,  # type: ignore
    command: str,
    reasoning: str,
    user_confirmed: bool = False
) -> str:
    """
    Execute a Windows system command on the user's PC. 
    Can be used to open apps, manage files, or change system settings.
    Use this when the user asks you to control their computer or open an application.
    """
    try:
        allowed_commands_str = os.getenv("ALLOWED_COMMANDS", "*")
        allowed_commands = [c.strip().lower() for c in allowed_commands_str.split(",")]
        require_confirmation = os.getenv("REQUIRE_CMD_CONFIRMATION", "false").lower() == "true"
        
        is_allowed = "*" in allowed_commands or any(command.lower().startswith(cmd) for cmd in allowed_commands)
        
        if (require_confirmation and not is_allowed) and not user_confirmed:
            logging.info(f"Command execution requires confirmation: {command}")
            return f"Action requires user confirmation. Command '{command}' was NOT executed. Please verbally ask the user to confirm. If they say yes, call this tool again with user_confirmed=True."

        ui_state.set_text(f"System | Command: {command[:25]}")
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
        ui_state.set_text(f"File | Writing '{os.path.basename(filename)}'")
        filename = os.path.expanduser(filename)
        filename = os.path.abspath(filename)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
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
        ui_state.set_text(f"File | Launching '{app_name}'")
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

import datetime
import ctypes

@function_tool()
async def change_volume(
    context: RunContext,  # type: ignore
    action: str,
    steps: int = 5
) -> str:
    """
    Adjust or control the system audio volume instantly.
    Use this whenever the user asks to increase, decrease, mute, or unmute volume.
    Never ask for confirmation to change volume.
    action: 'increase' | 'decrease' | 'mute' | 'unmute'
    steps: Number of volume increments (default 5, max 25)
    """
    try:
        ui_state.set_text(f"System | Volume {action.title()}")
        action_lower = action.lower().strip()
        num_steps = max(1, min(steps, 25))

        if action_lower in ["increase", "up", "raise"]:
            for _ in range(num_steps):
                await asyncio.to_thread(pyautogui.press, 'volumeup')
                await asyncio.sleep(0.02)
            return f"Successfully increased master volume by {num_steps * 2}%."
        elif action_lower in ["decrease", "down", "lower"]:
            for _ in range(num_steps):
                await asyncio.to_thread(pyautogui.press, 'volumedown')
                await asyncio.sleep(0.02)
            return f"Successfully decreased master volume by {num_steps * 2}%."
        elif action_lower in ["mute", "unmute", "toggle_mute"]:
            await asyncio.to_thread(pyautogui.press, 'volumemute')
            return "Successfully toggled master volume mute state."
        else:
            return f"Unknown volume action: '{action}'. Use increase, decrease, or mute."
    except Exception as e:
        return f"Failed to change volume: {e}"

@function_tool()
async def control_media(
    context: RunContext,  # type: ignore
    action: str
) -> str:
    """
    Control media playback (Spotify, YouTube Music, browser, video player).
    action: 'play_pause' | 'next' | 'previous' | 'stop'
    Use this instantly whenever the user asks to play, pause, skip, or go to previous track.
    Never ask for confirmation.
    """
    try:
        ui_state.set_text(f"System | Media {action.title()}")
        act = action.lower().strip()
        if act in ["play_pause", "play", "pause", "toggle"]:
            await asyncio.to_thread(pyautogui.press, 'playpause')
            return "Media play/pause toggled."
        elif act in ["next", "skip", "next_track"]:
            await asyncio.to_thread(pyautogui.press, 'nexttrack')
            return "Skipped to next media track."
        elif act in ["previous", "prev", "prev_track", "back"]:
            await asyncio.to_thread(pyautogui.press, 'prevtrack')
            return "Returned to previous media track."
        elif act in ["stop"]:
            await asyncio.to_thread(pyautogui.press, 'stop')
            return "Media playback stopped."
        else:
            return f"Unknown media action '{action}'."
    except Exception as e:
        return f"Failed to control media: {e}"

@function_tool()
async def change_brightness(
    context: RunContext,  # type: ignore
    action: str,
    percentage: int = 20
) -> str:
    """
    Adjust screen brightness.
    action: 'increase' | 'decrease' | 'set'
    percentage: Target percentage or step amount (1-100)
    """
    try:
        ui_state.set_text(f"🔆 Brightness {action}...")
        act = action.lower().strip()
        target_pct = max(0, min(100, percentage))
        
        ps_script = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target_pct})"
        res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"Successfully set screen brightness to {target_pct}%."
        else:
            return "Could not adjust screen brightness on this monitor."
    except Exception as e:
        return f"Failed to change brightness: {e}"

@function_tool()
async def system_power_control(
    context: RunContext,  # type: ignore
    action: str,
    user_confirmed: bool = False
) -> str:
    """
    System power management: lock screen, sleep, shutdown, or restart PC.
    action: 'lock' | 'sleep' | 'shutdown' | 'restart'
    Lock workstation requires ZERO confirmation.
    Shutdown and restart require verbal confirmation (user_confirmed=True).
    """
    try:
        act = action.lower().strip()
        if act == "lock":
            ui_state.set_text("🔒 Locking workstation...")
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked successfully."
        elif act == "sleep":
            ui_state.set_text("🌙 Putting PC to sleep...")
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "System sleep initiated."
        elif act in ["shutdown", "restart"]:
            if not user_confirmed:
                return f"Action '{act}' requires user verbal confirmation. Please ask the user to confirm. If they agree, call system_power_control with user_confirmed=True."
            if act == "shutdown":
                ui_state.set_text("⚠️ Shutting down PC...")
                subprocess.run("shutdown /s /t 5", shell=True)
                return "Initiating PC shutdown in 5 seconds."
            else:
                ui_state.set_text("⚠️ Restarting PC...")
                subprocess.run("shutdown /r /t 5", shell=True)
                return "Initiating PC restart in 5 seconds."
        else:
            return f"Unknown power action '{action}'."
    except Exception as e:
        return f"Power command failed: {e}"

@function_tool()
async def take_screenshot(
    context: RunContext,  # type: ignore
    filename: str = ""
) -> str:
    """
    Take a full-screen screenshot, save it to the user's Pictures folder, and open it.
    Use this when the user asks you to capture or take a screenshot of their screen.
    """
    try:
        ui_state.set_text(f"File | Screenshot Captured")
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        os.makedirs(pictures_dir, exist_ok=True)

        if not filename:
            filename = f"Zenith_Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if not filename.endswith('.png'):
            filename += '.png'

        filepath = os.path.join(pictures_dir, filename)
        screenshot = await asyncio.to_thread(pyautogui.screenshot)
        await asyncio.to_thread(screenshot.save, filepath)

        if sys.platform == "win32":
            os.startfile(filepath)

        return f"Screenshot captured and saved to {filepath}"
    except Exception as e:
        return f"Failed to capture screenshot: {e}"

@function_tool()
async def get_system_stats(
    context: RunContext  # type: ignore
) -> str:
    """
    Get current PC performance metrics: CPU load, RAM usage, battery status, and disk space.
    Use this when the user asks 'how is my PC running', 'check CPU', 'check battery', etc.
    """
    try:
        ui_state.set_text("System Stats | CPU & RAM Audit")
        ps_cmd = """
        $cpu = (Get-CimInstance Win32_Processor).LoadPercentage
        $os = Get-CimInstance Win32_OperatingSystem
        $freeMem = [math]::Round($os.FreePhysicalMemory / 1024 / 1024, 2)
        $totalMem = [math]::Round($os.TotalVisibleMemorySize / 1024 / 1024, 2)
        $usedMem = [math]::Round($totalMem - $freeMem, 2)
        $battery = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
        $batPct = if ($battery) { "$($battery.EstimatedChargeRemaining)%" } else { "N/A (Desktop/AC)" }
        "CPU Load: $cpu% | Memory Used: $usedMem GB / $totalMem GB | Battery: $batPct"
        """
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
        output = res.stdout.strip()
        if output:
            return f"System Stats: {output}"
        return "Could not retrieve system stats."
    except Exception as e:
        return f"Failed to get system stats: {e}"

@function_tool()
async def empty_recycle_bin(
    context: RunContext  # type: ignore
) -> str:
    """Empty the Windows Recycle Bin to free up disk space."""
    try:
        ui_state.set_text("🗑️ Emptying Recycle Bin...")
        subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], capture_output=True, text=True, timeout=10)
        return "Recycle Bin emptied successfully."
    except Exception as e:
        return f"Failed to empty Recycle Bin: {e}"

@function_tool()
async def get_clipboard(
    context: RunContext  # type: ignore
) -> str:
    """
    Read text currently copied to the Windows clipboard.
    Use this when the user asks 'what is in my clipboard' or 'read my copied text'.
    """
    try:
        ui_state.set_text("📋 Reading clipboard...")
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        text = r.clipboard_get()
        r.destroy()
        if text:
            return f"Clipboard Content: {text}"
        return "Clipboard is empty."
    except Exception:
        return "Clipboard is empty or does not contain plain text."

@function_tool()
async def set_clipboard(
    context: RunContext,  # type: ignore
    text: str
) -> str:
    """
    Copy text to the Windows clipboard.
    Use this when the user asks you to copy text, code, or links to their clipboard.
    """
    try:
        ui_state.set_text("📋 Copying to clipboard...")
        process = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
        process.communicate(input=text.encode('utf-8'))
        return f"Successfully copied text to clipboard: '{text[:60]}...'"
    except Exception as e:
        return f"Failed to copy to clipboard: {e}"

@function_tool()
async def manage_windows(
    context: RunContext,  # type: ignore
    action: str
) -> str:
    """
    Manage open desktop windows instantly.
    action: 'show_desktop' | 'close_active_window' | 'switch_app'
    Use this when the user says 'show my desktop', 'minimize everything', 'close this window', or 'switch window'.
    """
    try:
        ui_state.set_text(f"🪟 Window {action}...")
        act = action.lower().strip()
        if act in ["show_desktop", "minimize_all", "toggle_desktop"]:
            await asyncio.to_thread(pyautogui.hotkey, 'win', 'd')
            return "Toggled desktop view (minimized/restored windows)."
        elif act in ["close_active_window", "close_window", "close_app"]:
            await asyncio.to_thread(pyautogui.hotkey, 'alt', 'f4')
            return "Closed active window."
        elif act in ["switch_app", "next_window", "alt_tab"]:
            await asyncio.to_thread(pyautogui.hotkey, 'alt', 'tab')
            return "Switched active window."
        else:
            return f"Unknown window management action: {action}"
    except Exception as e:
        return f"Failed to manage windows: {e}"

@function_tool()
async def open_user_folder(
    context: RunContext,  # type: ignore
    folder_name: str
) -> str:
    """
    Open common user folders directly in File Explorer.
    folder_name: 'downloads' | 'documents' | 'desktop' | 'pictures' | 'videos' | 'music' | 'home'
    Use this when the user asks 'open my downloads', 'open my documents', 'open desktop', etc.
    """
    try:
        ui_state.set_text(f"📁 Opening {folder_name}...")
        f = folder_name.lower().strip()
        user_home = os.path.expanduser("~")
        folder_map = {
            "downloads": os.path.join(user_home, "Downloads"),
            "documents": os.path.join(user_home, "Documents"),
            "desktop": os.path.join(user_home, "Desktop"),
            "pictures": os.path.join(user_home, "Pictures"),
            "videos": os.path.join(user_home, "Videos"),
            "music": os.path.join(user_home, "Music"),
            "home": user_home
        }
        target_path = folder_map.get(f, user_home)
        os.startfile(target_path)
        return f"Opened '{folder_name}' folder ({target_path}) in File Explorer."
    except Exception as e:
        return f"Failed to open folder: {e}"

@function_tool()
async def manage_notes(
    context: RunContext,  # type: ignore
    action: str,
    note_text: str = ""
) -> str:
    """
    Save or read quick voice notes / to-do items.
    action: 'save' | 'read' | 'clear'
    note_text: text of the note to save (when action='save')
    """
    try:
        ui_state.set_text(f"📌 Notes {action}...")
        notes_file = os.path.join(os.path.expanduser("~"), "Zenith_Notes.txt")
        act = action.lower().strip()
        if act == "save":
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {note_text}\n")
            return f"Saved note: '{note_text}'"
        elif act == "read":
            if os.path.exists(notes_file):
                with open(notes_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    return f"Your saved notes:\n{content}"
            return "You have no saved notes."
        elif act == "clear":
            if os.path.exists(notes_file):
                os.remove(notes_file)
            return "Cleared all quick notes."
        else:
            return f"Unknown note action '{action}'."
    except Exception as e:
        return f"Failed to manage notes: {e}"

@function_tool()
async def search_files_on_pc(
    context: RunContext,  # type: ignore
    query: str,
    file_extension: str = ""
) -> str:
    """
    Search for files across Desktop, Downloads, Documents, Pictures, and Home directory by name or extension.
    Use this when the user asks 'find my PDF', 'where is my report file', 'search for files named X', etc.
    """
    try:
        ui_state.set_text(f"File Search | Finding '{query}'")
        user_home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Pictures"),
            os.path.join(user_home, "Videos"),
            user_home
        ]

        q = query.lower().strip()
        ext = file_extension.lower().strip().lstrip('.')
        matches = []

        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    f_lower = f.lower()
                    if q in f_lower:
                        if not ext or f_lower.endswith(f".{ext}"):
                            full_path = os.path.join(root, f)
                            matches.append(full_path)
                            if len(matches) >= 10:
                                break
                if len(matches) >= 10:
                    break
            if len(matches) >= 10:
                break

        if matches:
            formatted = "\n".join([f"- {m}" for m in matches[:8]])
            return f"Found {len(matches)} matching file(s):\n{formatted}"
        return f"No files matching '{query}' found in user directories."
    except Exception as e:
        return f"File search failed: {e}"

@function_tool()
async def kill_process(
    context: RunContext,  # type: ignore
    process_name: str
) -> str:
    """
    Terminate or force-close any running application or process on PC (e.g. 'chrome', 'spotify', 'notepad', 'python', 'vlc').
    Use this when the user asks to 'kill app', 'close chrome', 'force quit app', 'close stuck program'.
    """
    try:
        ui_state.set_text(f"System | Terminating '{process_name}'")
        proc_clean = process_name.lower().strip().replace(".exe", "")
        cmd = f"taskkill /IM {proc_clean}.exe /F /T"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return f"Successfully terminated process '{proc_clean}.exe'."
        else:
            return f"Could not find or terminate process '{proc_clean}.exe'. Message: {res.stderr.strip()}"
    except Exception as e:
        return f"Failed to kill process '{process_name}': {e}"

@function_tool()
async def read_file_content(
    context: RunContext,  # type: ignore
    filepath: str,
    max_lines: int = 50
) -> str:
    """
    Read text or code from a file on the user's PC (e.g., .txt, .py, .json, .md, .csv, .log).
    Use this when the user asks you to 'read my notes', 'check log file', 'read code in file X', etc.
    """
    try:
        ui_state.set_text(f"File | Reading '{os.path.basename(filepath)}'")
        target_path = os.path.expanduser(filepath.strip().strip('"').strip("'"))
        if not os.path.exists(target_path):
            # Try searching in Desktop/Downloads/Documents
            user_home = os.path.expanduser("~")
            for d in [os.path.join(user_home, "Desktop"), os.path.join(user_home, "Downloads"), os.path.join(user_home, "Documents")]:
                candidate = os.path.join(d, os.path.basename(target_path))
                if os.path.exists(candidate):
                    target_path = candidate
                    break

        if not os.path.exists(target_path):
            return f"File '{filepath}' not found."

        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline() for _ in range(max_lines)]
            content = "".join([l for l in lines if l])

        return f"Content of '{os.path.basename(target_path)}' (first {len(lines)} lines):\n\n{content}"
    except Exception as e:
        return f"Failed to read file '{filepath}': {e}"

@function_tool()
async def zip_manage_archive(
    context: RunContext,  # type: ignore
    action: str,
    target_path: str,
    output_path: str = ""
) -> str:
    """
    Compress files/folders into a ZIP archive or extract an existing ZIP file.
    action: 'compress' | 'extract'
    target_path: file or folder to compress, or zip file to extract
    """
    import shutil
    import zipfile
    try:
        ui_state.set_text(f"📦 ZIP {action}...")
        act = action.lower().strip()
        src = os.path.expanduser(target_path.strip().strip('"').strip("'"))
        
        if act in ["compress", "zip"]:
            if not os.path.exists(src):
                return f"Path '{target_path}' does not exist."
            out_zip = os.path.expanduser(output_path.strip().strip('"').strip("'")) if output_path else f"{src}.zip"
            if not out_zip.endswith('.zip'):
                out_zip += '.zip'
            
            if os.path.isdir(src):
                shutil.make_archive(out_zip.replace('.zip', ''), 'zip', src)
            else:
                with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(src, os.path.basename(src))
            return f"Successfully created ZIP archive: '{out_zip}'"

        elif act in ["extract", "unzip"]:
            if not os.path.exists(src) or not src.endswith('.zip'):
                return f"ZIP file '{target_path}' not found."
            dest_dir = os.path.expanduser(output_path.strip().strip('"').strip("'")) if output_path else src.replace('.zip', '_extracted')
            os.makedirs(dest_dir, exist_ok=True)
            with zipfile.ZipFile(src, 'r') as zf:
                zf.extractall(dest_dir)
            return f"Successfully extracted archive to: '{dest_dir}'"
        else:
            return f"Unknown ZIP action '{action}'."
    except Exception as e:
        return f"ZIP operation failed: {e}"

@function_tool()
async def get_top_running_apps(
    context: RunContext  # type: ignore
) -> str:
    """
    List top active desktop apps and background processes sorted by RAM memory usage.
    Use this when the user asks 'what app is using the most RAM/CPU', 'check active processes', etc.
    """
    try:
        ui_state.set_text("📊 Auditing running processes...")
        ps_cmd = """
        Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 7 | ForEach-Object {
            "{0} (PID {1}): {2:N2} MB" -f $_.ProcessName, $_.Id, ($_.WorkingSet64 / 1MB)
        }
        """
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=8)
        out = res.stdout.strip()
        if out:
            return f"Top Processes by Memory Usage:\n{out}"
        return "Could not retrieve process memory audit."
    except Exception as e:
        return f"Process audit failed: {e}"

@function_tool()
async def find_large_files(
    context: RunContext,  # type: ignore
    min_size_mb: int = 100,
    search_location: str = "downloads"
) -> str:
    """
    Scan user directories (Downloads, Desktop, Documents) for large files (>100MB) to help free up disk space.
    Use this when the user asks 'what is taking up disk space', 'find big files', 'find large downloads'.
    """
    try:
        ui_state.set_text("🔍 Scanning for large files...")
        user_home = os.path.expanduser("~")
        loc_map = {
            "downloads": os.path.join(user_home, "Downloads"),
            "desktop": os.path.join(user_home, "Desktop"),
            "documents": os.path.join(user_home, "Documents"),
            "home": user_home
        }
        target_dir = loc_map.get(search_location.lower().strip(), os.path.join(user_home, "Downloads"))
        min_bytes = min_size_mb * 1024 * 1024
        large_files = []

        if os.path.exists(target_dir):
            for root, _, files in os.walk(target_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        if sz >= min_bytes:
                            sz_mb = round(sz / (1024 * 1024), 1)
                            large_files.append((fp, sz_mb))
                    except Exception:
                        pass
                if len(large_files) >= 10:
                    break

        if large_files:
            large_files.sort(key=lambda x: x[1], reverse=True)
            formatted = "\n".join([f"- {os.path.basename(path)} ({size} MB) -> {path}" for path, size in large_files[:7]])
            return f"Found {len(large_files)} large file(s) (>={min_size_mb}MB) in {search_location}:\n{formatted}"
        return f"No files larger than {min_size_mb}MB found in {search_location}."
    except Exception as e:
        return f"Large file scan failed: {e}"

@function_tool()
async def manage_file_system(
    context: RunContext,  # type: ignore
    action: str,
    source_path: str,
    destination_path: str = ""
) -> str:
    """
    File system management: create folder, copy file/folder, move file/folder, rename, or delete file.
    action: 'mkdir' | 'copy' | 'move' | 'rename' | 'delete'
    """
    import shutil
    try:
        ui_state.set_text(f"📁 File System {action}...")
        act = action.lower().strip()
        src = os.path.expanduser(source_path.strip().strip('"').strip("'"))

        if act in ["mkdir", "create_folder"]:
            os.makedirs(src, exist_ok=True)
            return f"Created directory: '{src}'"

        elif act in ["copy"]:
            dest = os.path.expanduser(destination_path.strip().strip('"').strip("'"))
            if os.path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)
            return f"Copied '{src}' to '{dest}'"

        elif act in ["move", "rename"]:
            dest = os.path.expanduser(destination_path.strip().strip('"').strip("'"))
            shutil.move(src, dest)
            return f"Moved/renamed '{src}' to '{dest}'"

        elif act in ["delete", "remove"]:
            if os.path.isdir(src):
                shutil.rmtree(src)
            else:
                os.remove(src)
            return f"Deleted: '{src}'"

        return f"Unknown action: {action}"
    except Exception as e:
        return f"File operation failed: {e}"

@function_tool()
async def clean_disk_temp_junk(
    context: RunContext  # type: ignore
) -> str:
    """
    Clean Windows temporary junk files, cache files, and prefetch items to free up disk space.
    Use this when the user asks to 'clean temp files', 'clean junk', 'free up space', 'clean my PC'.
    """
    try:
        ui_state.set_text("System | Cleaned Temp Junk Files")
        ps_cmd = """
        $tempDirs = @($env:TEMP, "C:\\Windows\\Temp")
        $deleted = 0
        foreach ($d in $tempDirs) {
            if (Test-Path $d) {
                Get-ChildItem -Path $d -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
                $deleted++
            }
        }
        "Cleaned temporary directories successfully."
        """
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=12)
        return "Cleaned Windows temporary junk files and system cache successfully."
    except Exception as e:
        return f"Temp clean failed: {e}"

@function_tool()
async def generate_qr_code(
    context: RunContext,  # type: ignore
    text_or_url: str
) -> str:
    """
    Generate a QR code PNG image for any URL, text, or link, save it to Pictures, and open it.
    Use this when the user asks 'generate QR code for X', 'create QR link', 'make QR code'.
    """
    try:
        ui_state.set_text(f"File | Generated QR Code")
        import urllib.parse
        target = text_or_url.strip()
        encoded = urllib.parse.quote(target)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}"
        
        import urllib.request
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        os.makedirs(pictures_dir, exist_ok=True)
        filename = f"Zenith_QR_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(pictures_dir, filename)

        urllib.request.urlretrieve(qr_url, filepath)

        if sys.platform == "win32":
            os.startfile(filepath)

        return f"Successfully generated QR code for '{target}' and saved to Pictures ({filepath})."
    except Exception as e:
        return f"Failed to generate QR code: {e}"

@function_tool()
async def set_timer_or_alarm(
    context: RunContext,  # type: ignore
    duration_seconds: int,
    timer_label: str = "Timer"
) -> str:
    """
    Set a voice countdown timer (in seconds) that alerts the user when finished.
    Use this when the user asks 'set a timer for X minutes/seconds', 'remind me in X minutes'.
    duration_seconds: time in seconds (e.g. 5 minutes = 300 seconds)
    """
    try:
        sec = max(1, duration_seconds)
        ui_state.set_text(f"Timer | {sec}s Active ({timer_label})")
        
        async def timer_task():
            await asyncio.sleep(sec)
            ui_state.set_text(f"Timer | EXPIRED: {timer_label}")
            try:
                import pyautogui
                pyautogui.press('volumemute')
                await asyncio.sleep(0.1)
                pyautogui.press('volumemute')
            except Exception:
                pass

        asyncio.create_task(timer_task())
        mins = sec // 60
        rem_sec = sec % 60
        time_str = f"{mins} min {rem_sec} sec" if mins > 0 else f"{sec} seconds"
        return f"Countdown timer for '{timer_label}' set for {time_str}. I will alert you when it expires."
    except Exception as e:
        return f"Failed to set timer: {e}"

@function_tool()
async def manage_bluetooth(
    context: RunContext,  # type: ignore
    action: str,
    device_name: str = ""
) -> str:
    """
    Manage Bluetooth hardware and device connections on PC.
    action: 'toggle' | 'on' | 'off' | 'settings' | 'connect'
    device_name: optional Bluetooth device name (e.g. 'Headphones', 'AirPods', 'Controller')
    Use this when the user asks to 'connect Bluetooth headphones', 'turn on Bluetooth', 'open Bluetooth settings', etc.
    """
    try:
        ui_state.set_text(f"Bluetooth | {action.title()} {device_name}".strip())
        act = action.lower().strip()
        
        if act in ["on", "enable"]:
            ps_cmd = "Start-Service bthserv -ErrorAction SilentlyContinue"
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
            subprocess.run("start ms-settings:bluetooth", shell=True)
            return "Bluetooth service enabled and Bluetooth settings opened."

        elif act in ["off", "disable"]:
            ps_cmd = "Stop-Service bthserv -Force -ErrorAction SilentlyContinue"
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
            return "Bluetooth service turned off."

        elif act in ["settings", "open", "pair", "connect"]:
            subprocess.run("start ms-settings:bluetooth", shell=True)
            if device_name:
                return f"Opened Bluetooth settings to connect '{device_name}'."
            return "Opened Windows Bluetooth settings."

        else:
            subprocess.run("start ms-settings:bluetooth", shell=True)
            return f"Opened Bluetooth manager for action '{action}'."
    except Exception as e:
        return f"Bluetooth command failed: {e}"

@function_tool()
async def register_voice_macro(
    context: RunContext,  # type: ignore
    action: str,
    macro_name: str,
    commands: str = ""
) -> str:
    """
    Register, run, or list custom voice macro shortcuts.
    action: 'save' | 'run' | 'list' | 'delete'
    macro_name: custom trigger phrase (e.g. 'demo time', 'coding setup', 'clean workspace')
    commands: comma-separated list of app names, URLs, or commands to execute sequentially when action='save'
    Use this when the user asks 'save macro X', 'run macro X', 'create shortcut when I say X'.
    """
    try:
        macro_file = os.path.join(os.path.expanduser("~"), "Zenith_Macros.json")
        macros = {}
        if os.path.exists(macro_file):
            try:
                with open(macro_file, "r", encoding="utf-8") as f:
                    macros = json.load(f)
            except Exception:
                macros = {}

        act = action.lower().strip()
        m_name = macro_name.lower().strip()

        if act == "save":
            ui_state.set_text(f"⚡ Saving macro '{m_name}'...")
            cmd_list = [c.strip() for c in commands.split(",") if c.strip()]
            if not cmd_list:
                return f"Please provide commands to associate with macro '{macro_name}'."
            macros[m_name] = cmd_list
            with open(macro_file, "w", encoding="utf-8") as f:
                json.dump(macros, f, indent=2)
            return f"Successfully saved custom macro '{m_name}' with {len(cmd_list)} action(s): {cmd_list}"

        elif act == "run":
            ui_state.set_text(f"⚡ Running macro '{m_name}'...")
            if m_name not in macros:
                return f"Macro '{macro_name}' not found. Saved macros: {list(macros.keys())}"
            cmd_list = macros[m_name]
            executed = []
            for cmd in cmd_list:
                if cmd.startswith("http://") or cmd.startswith("https://"):
                    import webbrowser
                    webbrowser.open(cmd)
                elif "." in cmd and os.path.exists(os.path.expanduser(cmd)):
                    os.startfile(os.path.expanduser(cmd))
                else:
                    subprocess.run(f"start {cmd}", shell=True)
                executed.append(cmd)
                await asyncio.sleep(0.5)
            return f"Executed macro '{m_name}' ({len(executed)} actions)."

        elif act == "list":
            if macros:
                items = [f"- '{k}': {v}" for k, v in macros.items()]
                return f"Saved Voice Macros:\n" + "\n".join(items)
            return "No voice macros saved yet."

        elif act == "delete":
            if m_name in macros:
                del macros[m_name]
                with open(macro_file, "w", encoding="utf-8") as f:
                    json.dump(macros, f, indent=2)
                return f"Deleted macro '{m_name}'."
            return f"Macro '{macro_name}' not found."

        else:
            return f"Unknown macro action '{action}'."
    except Exception as e:
        return f"Macro manager error: {e}"







