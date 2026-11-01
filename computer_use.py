import os
import io
import json
import time
import logging
import asyncio
from typing import Optional, Dict
from PIL import Image
import pyautogui
from google import genai
from google.genai import types
from dotenv import load_dotenv
import ui_state
from agent_tools.procedural_memory import reflect_on_outcome
from agent_tools.som_grounding import (
    generate_set_of_marks,
    format_marks_for_prompt,
    resolve_action_target,
    MarkInfo
)

load_dotenv()
_pc_lock = asyncio.Lock()

ACTION_SCHEMA = """
Respond ONLY with a valid JSON object in this exact shape, no markdown formatting or extra text:
{
  "reasoning": "Brief explanation of what you see on the screen and why you are taking this action",
  "action": "left_click | double_click | right_click | mouse_move | type | key | scroll | wait | done",
  "mark_id": 14,                 // PREFERRED: Exact numbered Set-of-Marks badge [N] visible on target element
  "coordinate": [x, y],          // fallback pixel coordinates if no mark_id applies
  "text": "string to type",        // string to type when action is "type"
  "press_enter": true,           // whether to press Enter after typing
  "keys": "ctrl+t",              // hotkey when action is "key" (use '+' to join, e.g. 'ctrl+w', 'enter')
  "scroll_direction": "up|down", // when action is "scroll"
  "scroll_amount": 3,            // when action is "scroll"
  "seconds": 1,                  // when action is "wait" (max 3)
  "done_summary": "Summary of what was achieved" // when action is "done"
}
"""

def _screenshot_with_som():
    """Captures desktop screen and enriches it with Set-of-Marks (SoM) visual badges."""
    raw_img = None
    try:
        raw_img = pyautogui.screenshot()
    except Exception:
        # Fallback to latest frame from screen stream receiver if desktop session is backgrounded
        try:
            from agent_tools.screen_stream import screen_video_input
            if screen_video_input._latest_frame:
                f = screen_video_input._latest_frame
                raw_img = Image.frombytes("RGBA", (f.width, f.height), bytes(f.data)).convert("RGB")
        except Exception:
            pass

    if raw_img is None:
        raw_img = Image.new("RGB", (1920, 1080), color=(30, 30, 40))

    annotated_img, mark_map = generate_set_of_marks(raw_img, max_marks=45)
    
    buf = io.BytesIO()
    annotated_img.save(buf, format="JPEG", quality=75)
    part = types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")
    return part, raw_img.size, mark_map


def _execute(action: dict, mark_map: Optional[Dict[int, MarkInfo]] = None):
    """Executes a computer use action, resolving targets via Set-of-Marks for near-100% precision."""
    a = action.get("action", "")
    target_coord = None

    if mark_map and a in ["left_click", "double_click", "right_click", "mouse_move"]:
        target_coord = resolve_action_target(action, mark_map, snap_distance=45)

    if not target_coord and action.get("coordinate"):
        target_coord = tuple(action["coordinate"])

    if a == "left_click":
        if target_coord:
            pyautogui.click(int(target_coord[0]), int(target_coord[1]))
    elif a == "double_click":
        if target_coord:
            pyautogui.doubleClick(int(target_coord[0]), int(target_coord[1]))
    elif a == "right_click":
        if target_coord:
            pyautogui.rightClick(int(target_coord[0]), int(target_coord[1]))
    elif a == "mouse_move":
        if target_coord:
            pyautogui.moveTo(int(target_coord[0]), int(target_coord[1]), duration=0.25)
    elif a == "type":
        text = action.get("text", "")
        pyautogui.write(text, interval=0.03)
        if action.get("press_enter", False):
            pyautogui.press("enter")
    elif a == "key":
        raw_keys = action.get("keys", "")
        keys = [k.strip().lower() for k in raw_keys.split("+") if k.strip()]
        if keys:
            pyautogui.hotkey(*keys)
    elif a == "scroll":
        amt = action.get("scroll_amount", 3)
        clicks = int(amt) * 120 if action.get("scroll_direction") == "up" else -(int(amt) * 120)
        pyautogui.scroll(clicks)
    elif a == "wait":
        secs = min(max(1, int(action.get("seconds", 1))), 3)
        time.sleep(secs)


_active_computer_task: Optional[asyncio.Task] = None
_current_computer_task_desc: Optional[str] = None

async def cancel_active_computer_task() -> bool:
    """Cancels any currently running visual computer-use screen task."""
    global _active_computer_task, _pc_lock, _current_computer_task_desc
    was_active = False
    task_to_cancel = _active_computer_task
    if task_to_cancel and not task_to_cancel.done():
        was_active = True
        logging.info(f"Cancelling active computer screen task: {_current_computer_task_desc}")
        task_to_cancel.cancel()
        for _ in range(10):
            if not _pc_lock.locked() and (task_to_cancel is None or task_to_cancel.done()):
                break
            await asyncio.sleep(0.1)

    if _pc_lock.locked():
        _pc_lock = asyncio.Lock()

    return was_active


async def computer_use_loop(task: str, max_steps: int = 10) -> str:
    """
    Take control of the screen to complete visual tasks on Windows using Set-of-Marks (SoM).
    Uses visual badges and exact coordinate resolution for 100% click precision.
    """
    global _active_computer_task, _pc_lock, _current_computer_task_desc

    if _pc_lock.locked() or (_active_computer_task and not _active_computer_task.done()):
        logging.info(f"Preempting active computer task '{_current_computer_task_desc}' for new task: '{task}'")
        await cancel_active_computer_task()

    async with _pc_lock:
        current_coro = asyncio.current_task()
        _active_computer_task = current_coro
        _current_computer_task_desc = task
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Google API key is not configured for vision control."

        client = genai.Client(api_key=api_key)
        history = []
        ui_state.set_text(f"👁️ SoM Task | {task[:20]}")

        try:
            for step in range(max_steps):
                try:
                    screenshot_part, (w, h), mark_map = await asyncio.to_thread(_screenshot_with_som)
                    marks_text = format_marks_for_prompt(mark_map)

                    prompt = (
                        f"You are Zenith, an AI assistant controlling the user's Windows computer.\n"
                        f"Task to accomplish: {task}\n"
                        f"Screen resolution: {w}x{h}.\n\n"
                        f"{marks_text}\n\n"
                        f"Previous actions taken: {json.dumps(history[-4:])}\n\n"
                        f"GROUNDING INSTRUCTION: The screenshot is annotated with numbered Set-of-Marks badges [N].\n"
                        f"To interact with an element (click/type), supply its 'mark_id' (e.g. mark_id: 4) for exact targeting.\n"
                        f"Choose the SINGLE next action to progress the task, or return 'done' if the task is complete.\n"
                        f"{ACTION_SCHEMA}"
                    )

                    response = None
                    last_model_err = None
                    for m in ["gemini-3.5-flash-lite", "gemini-2.5-flash"]:
                        try:
                            response = await client.aio.models.generate_content(
                                model=m,
                                contents=[prompt, screenshot_part],
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json"
                                )
                            )
                            if response and response.text:
                                break
                        except Exception as m_err:
                            last_model_err = m_err
                            logging.warning(f"Computer use model {m} failed: {m_err}, attempting fallback...")
                            continue

                    if not response or not response.text:
                        raise last_model_err or RuntimeError("All vision models failed to respond.")

                    resp_text = response.text.strip()
                    if resp_text.startswith("```json"):
                        resp_text = resp_text[7:]
                    if resp_text.endswith("```"):
                        resp_text = resp_text[:-3]

                    action = json.loads(resp_text.strip())
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logging.error(f"Error in computer_use_loop at step {step}: {e}")
                    asyncio.create_task(reflect_on_outcome(
                        task_desc=f"Screen control for: {task}",
                        action_taken=f"Step {step} visual interaction",
                        raw_output=str(e),
                        is_error=True
                    ))
                    if "429" in str(e) or "quota" in str(e).lower():
                        return "Task paused due to API quota limits. Please try again in a few moments."
                    return f"Computer control encountered an error: {str(e)}"

                logging.info(f"Computer control step {step}: {action}")
                history.append({
                    "action": action.get("action"),
                    "mark_id": action.get("mark_id"),
                    "reasoning": action.get("reasoning", "")
                })

                if action.get("action") == "done":
                    summary = action.get("done_summary", "Task completed.")
                    ui_state.set_text(f"✅ {summary[:25]}")
                    return summary

                await asyncio.to_thread(_execute, action, mark_map)
                await asyncio.sleep(0.7)

            return "Finished screen task sequence."
        except asyncio.CancelledError:
            logging.info(f"computer_use_loop cancelled: '{task}'")
            ui_state.set_text("⏹️ Screen Task Cancelled")
            raise
        finally:
            if _active_computer_task is current_coro:
                _active_computer_task = None
                _current_computer_task_desc = None
