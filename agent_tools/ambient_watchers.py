"""
Proactive Ambient Watchers for Zenith AI
Monitors clipboard, active developer processes, and system metrics in the background.
Enables Zenith to proactively alert the user when builds finish, errors are copied,
or resources become constrained, moving beyond purely reactive voice interactions.
"""

import re
import time
import ctypes
from ctypes import wintypes
import logging
import asyncio
from typing import Optional, Dict, Set, List, Callable, Any
import psutil
from livekit.agents import function_tool, RunContext
import ui_state
from .working_memory import working_memory

logger = logging.getLogger("zenith.ambient")

# Win32 Clipboard APIs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

CF_UNICODETEXT = 13

# Regex patterns matching code errors, exceptions, and stack traces
ERROR_PATTERNS = [
    (r"Traceback \(most recent call last\):", "Python Traceback"),
    (r"panic: .+", "Go/Rust Panic"),
    (r"fatal error: .+", "Compiler Fatal Error"),
    (r"npm ERR! .+", "NPM Build Error"),
    (r"error\[E[0-9]+\]: .+", "Rustc Error"),
    (r"(?:NullPointerException|ClassNotFoundException)", "Java Runtime Exception"),
    (r"CONFLICT \(content\): Merge conflict in .+", "Git Merge Conflict"),
    (r"FAILED \(failures=[0-9]+\)", "Test Suite Failure"),
    (r"SyntaxError: .+", "Syntax Error"),
    (r"(?:[A-Za-z]+Error|Exception): .+", "Unhandled Exception")
]


def read_win32_clipboard() -> Optional[str]:
    """Reads current clipboard text in microseconds using direct Win32 memory handles."""
    if not user32.OpenClipboard(None):
        return None
    try:
        h_data = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_data:
            return None
        ptr = kernel32.GlobalLock(h_data)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h_data)
    except Exception:
        return None
    finally:
        user32.CloseClipboard()


def detect_error_in_text(text: str) -> Optional[str]:
    """Detects if text contains a programming error or stack trace."""
    if not text or len(text) < 15 or len(text) > 15000:
        return None
    for pattern, label in ERROR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None


class AmbientWatcherManager:
    """Manages background ambient watchers for clipboard events, process life cycles, and battery."""
    def __init__(self):
        self.enabled: bool = True
        self.clipboard_enabled: bool = True
        self.process_enabled: bool = True
        self.voice_alerts_enabled: bool = True

        self._notifier: Optional[Callable[[str], Any]] = None
        self._last_seq_num: int = 0
        self._last_error_text: Optional[str] = None
        self._last_error_type: Optional[str] = None
        self._last_voice_alert_time: float = 0
        self._alert_cooldown_seconds: float = 40.0

        self._monitored_pids: Dict[int, str] = {}  # pid -> name
        self._running_tasks: List[asyncio.Task] = []

    def set_notifier(self, callback: Callable[[str], Any]) -> None:
        self._notifier = callback

    def start(self) -> None:
        """Starts all ambient watcher background coroutines."""
        self._running_tasks.append(asyncio.create_task(self._clipboard_watcher_loop()))
        self._running_tasks.append(asyncio.create_task(self._process_watcher_loop()))
        self._running_tasks.append(asyncio.create_task(self._system_metrics_loop()))
        logger.info("Zenith Proactive Ambient Watchers started.")

    def stop(self) -> None:
        """Stops all watcher coroutines."""
        for t in self._running_tasks:
            if not t.done():
                t.cancel()
        self._running_tasks.clear()
        logger.info("Zenith Proactive Ambient Watchers stopped.")

    def watch_process(self, query: str) -> str:
        """Finds and monitors a running process by name or PID."""
        query_clean = query.strip().lower()
        matched = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                name = p.info['name'].lower()
                pid = p.info['pid']
                if query_clean in name or query_clean == str(pid):
                    self._monitored_pids[pid] = p.info['name']
                    matched.append(f"{p.info['name']} (PID {pid})")
            except Exception:
                continue

        if matched:
            return f"Now monitoring {len(matched)} process(es): {', '.join(matched[:3])}. I will notify Sir the moment it completes."
        return f"Could not find any running process matching '{query}'."

    async def _clipboard_watcher_loop(self) -> None:
        """Checks clipboard sequence number every 1.2 seconds with ~0% CPU."""
        await asyncio.sleep(2)
        try:
            self._last_seq_num = user32.GetClipboardSequenceNumber()
        except Exception:
            pass

        while True:
            await asyncio.sleep(1.2)
            if not self.clipboard_enabled:
                continue

            try:
                current_seq = user32.GetClipboardSequenceNumber()
                if current_seq != self._last_seq_num:
                    self._last_seq_num = current_seq
                    text = read_win32_clipboard()
                    if not text:
                        continue

                    # Check for programming error or crash
                    error_type = detect_error_in_text(text)
                    if error_type:
                        self._last_error_text = text
                        self._last_error_type = error_type
                        ui_state.set_text(f"💡 Copied: {error_type[:15]}")
                        working_memory.record_ambient_signal("clipboard_error", f"{error_type}: {text[:150]}")
                        logger.info(f"Proactive Ambient Trigger: Copied {error_type}")

                        now = time.time()
                        if self.voice_alerts_enabled and (now - self._last_voice_alert_time) > self._alert_cooldown_seconds:
                            self._last_voice_alert_time = now
                            if self._notifier:
                                announcement = f"Sir, I noticed a {error_type} in your clipboard. Say 'explain error' if you would like me to diagnose the fix."
                                try:
                                    res = self._notifier(announcement)
                                    if asyncio.iscoroutine(res):
                                        await res
                                except Exception as notify_err:
                                    logger.error(f"Vocal ambient notification error: {notify_err}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Clipboard watcher exception: {e}")

    async def _process_watcher_loop(self) -> None:
        """Monitors designated background build/compiler processes for completion."""
        await asyncio.sleep(0.5)
        while True:
            await asyncio.sleep(0.8)
            if not self.process_enabled or not self._monitored_pids:
                continue

            try:
                finished_pids = []
                for pid, name in list(self._monitored_pids.items()):
                    if not psutil.pid_exists(pid):
                        finished_pids.append((pid, name))

                for pid, name in finished_pids:
                    del self._monitored_pids[pid]
                    ui_state.set_text(f"✅ Process Done: {name}")
                    working_memory.record_ambient_signal("process_done", f"{name} (PID {pid}) finished")
                    logger.info(f"Monitored process '{name}' (PID {pid}) finished.")

                    if self.voice_alerts_enabled and self._notifier:
                        announcement = f"Sir, your monitored process '{name}' has completed."
                        try:
                            res = self._notifier(announcement)
                            if asyncio.iscoroutine(res):
                                await res
                        except Exception:
                            pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Process watcher exception: {e}")

    async def _system_metrics_loop(self) -> None:
        """Monitors battery levels and critical hardware bottlenecks."""
        await asyncio.sleep(10)
        battery_alerted = False

        while True:
            await asyncio.sleep(30.0)
            try:
                # Battery check
                battery = psutil.sensors_battery()
                if battery is not None:
                    if battery.percent <= 15 and not battery.power_plugged and not battery_alerted:
                        battery_alerted = True
                        ui_state.set_text("⚠️ Battery < 15%")
                        if self.voice_alerts_enabled and self._notifier:
                            res = self._notifier(f"Sir, your laptop battery is at {battery.percent}%. Please connect your charger.")
                            if asyncio.iscoroutine(res):
                                await res
                    elif battery.power_plugged or battery.percent > 20:
                        battery_alerted = False
            except asyncio.CancelledError:
                break
            except Exception:
                pass


# Global singleton manager
ambient_manager = AmbientWatcherManager()


# --- Function Tools for Gemini ---

@function_tool()
async def explain_clipboard_error(context: RunContext) -> str:  # type: ignore
    """
    Diagnose and provide a direct solution for any error, exception, or traceback currently in the user's clipboard.
    Use this when the user says "explain this error", "what is wrong with this traceback", or "fix the error I just copied".
    """
    raw_text = ambient_manager._last_error_text or read_win32_clipboard()
    if not raw_text or len(raw_text.strip()) < 10:
        return "Sir, I do not see an error or stack trace in your clipboard. Please copy the error message or terminal output and ask again."

    error_type = detect_error_in_text(raw_text) or "Error"
    return (
        f"Detected {error_type} in clipboard:\n\n"
        f"```text\n{raw_text[:1200]}\n```\n\n"
        f"Please explain clearly to Sir why this error occurred and provide the exact, corrected code or command to fix it."
    )


@function_tool()
async def watch_process(
    context: RunContext,  # type: ignore
    process_name: str
) -> str:
    """
    Monitor an ongoing background program, compilation, build, download, or script (e.g. 'node', 'python', 'npm', 'cargo', 'pytest').
    Zenith will automatically watch the process and proactively alert the user the second it completes.
    
    Args:
        process_name: Name or PID of the process to track (e.g. 'python.exe', 'node', 'build').
    """
    return ambient_manager.watch_process(process_name)


@function_tool()
async def configure_ambient_watchers(
    context: RunContext,  # type: ignore
    clipboard_enabled: Optional[bool] = None,
    process_enabled: Optional[bool] = None,
    voice_alerts_enabled: Optional[bool] = None
) -> str:
    """
    Configure Zenith's proactive ambient monitoring preferences (clipboard error detection, process watcher, vocal alerts).
    """
    if clipboard_enabled is not None:
        ambient_manager.clipboard_enabled = clipboard_enabled
    if process_enabled is not None:
        ambient_manager.process_enabled = process_enabled
    if voice_alerts_enabled is not None:
        ambient_manager.voice_alerts_enabled = voice_alerts_enabled

    status = (
        f"Ambient Watcher Settings Updated:\n"
        f"- Clipboard Error Watcher: {'ON' if ambient_manager.clipboard_enabled else 'OFF'}\n"
        f"- Process Completion Watcher: {'ON' if ambient_manager.process_enabled else 'OFF'}\n"
        f"- Proactive Voice Alerts: {'ON' if ambient_manager.voice_alerts_enabled else 'OFF'}"
    )
    return status
