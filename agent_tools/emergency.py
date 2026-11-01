"""
Zenith Universal Emergency Motor Killswitch (100% Free)
======================================================
Provides an atomic, zero-latency emergency killswitch for all motor,
automation, visual, web, shell, and background audio systems.
"""

import logging
import asyncio
from typing import List, Dict, Any
from livekit.agents import function_tool, RunContext
import ui_state

logger = logging.getLogger("emergency_stop")

async def execute_emergency_stop() -> Dict[str, Any]:
    """
    Executes a comprehensive, non-blocking emergency halt across all subsystems.
    """
    cancelled_items: List[str] = []
    
    # 1. Update UI HUD immediately
    ui_state.set_text("🛑 EMERGENCY STOP")

    # 2. Cancel visual screen control (computer_use)
    try:
        from computer_use import cancel_active_computer_task
        cu_res = await cancel_active_computer_task()
        if cu_res:
            cancelled_items.append("visual screen control")
    except Exception as e:
        logger.debug(f"Computer use cancellation: {e}")

    # 3. Cancel Windows UI Automation (uia_control)
    try:
        from uia_control import cancel_active_uia_task
        uia_res = cancel_active_uia_task()
        if uia_res:
            cancelled_items.append("UI automation loop")
    except Exception as e:
        logger.debug(f"UIA cancellation: {e}")

    # 4. Cancel Autonomous Web Browsing (web.py)
    try:
        from agent_tools.web import cancel_active_web_task
        web_res = await cancel_active_web_task()
        if web_res:
            cancelled_items.append("autonomous web agent")
    except Exception as e:
        logger.debug(f"Web task cancellation: {e}")

    # 5. Cancel all background swarm tasks
    try:
        from agent_tools.task_manager import task_manager
        swarm_count = task_manager.cancel_all()
        if swarm_count > 0:
            cancelled_items.append(f"{swarm_count} background worker task(s)")
    except Exception as e:
        logger.debug(f"Task manager cancellation: {e}")

    # 6. Reset persistent shell (terminates runaway commands)
    try:
        from agent_tools.persistent_shell import persistent_shell
        persistent_shell.reset()
        cancelled_items.append("terminal execution session")
    except Exception as e:
        logger.debug(f"Persistent shell reset: {e}")

    # 7. Release stuck hardware keys & mouse buttons via PyAutoGUI
    try:
        import pyautogui
        pyautogui.mouseUp(button='left')
        pyautogui.mouseUp(button='right')
        pyautogui.mouseUp(button='middle')
        for mod in ['ctrl', 'alt', 'shift', 'win']:
            try:
                pyautogui.keyUp(mod)
            except Exception:
                pass
        cancelled_items.append("hardware input locks released")
    except Exception as e:
        logger.debug(f"PyAutoGUI key release: {e}")

    # 8. Stop narration & audio mixers
    try:
        from agent_tools.smart_tts import _get_mixer
        mixer = _get_mixer()
        if mixer and mixer.music.get_busy():
            mixer.music.stop()
            cancelled_items.append("script narration audio")
    except Exception as e:
        logger.debug(f"Audio stop: {e}")

    # 9. Record in working memory
    try:
        from agent_tools.working_memory import working_memory
        working_memory.record_ambient_signal("emergency_stop", "All motor actions and background swarms forcibly halted.")
        working_memory.add_note("Emergency Killswitch triggered. All operations frozen.")
    except Exception as e:
        logger.debug(f"Working memory update: {e}")

    return {
        "status": "frozen",
        "cancelled_subsystems": cancelled_items
    }

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOL
# ==============================================================================

@function_tool()
async def emergency_stop_all(
    context: RunContext  # type: ignore
) -> str:
    """
    EMERGENCY MOTOR KILLSWITCH. Immediately aborts, terminates, and freezes ALL
    active operations, including:
    - Screen automation & mouse movements (computer_use)
    - Windows UI automation clicks and keystrokes (uia_control)
    - Autonomous web browser sessions (browser-use)
    - Running PowerShell/terminal commands
    - Background task worker swarms
    - Audio narration and playback
    - Releases any stuck mouse buttons or modifier keys.

    Use this IMMEDIATELY whenever the user says:
    - "Stop everything", "Emergency stop", "Abort mission", "Freeze", "Halt"
    - "Ruk jao sab", "Sab band karo", "Stop right now", "Cancel everything"
    NEVER hesitate or ask for verbal confirmation.
    """
    res = await execute_emergency_stop()
    items = res.get("cancelled_subsystems", [])
    if items:
        return f"All motor systems disengaged, Sir. Complete system freeze initiated. Terminated: {', '.join(items)}."
    return "All motor systems disengaged, Sir. Complete system freeze initiated. All channels are idle."
