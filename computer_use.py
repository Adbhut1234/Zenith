import os
import io
import json
import time
import logging
import asyncio
import pyautogui
from google import genai
from google.genai import types
from dotenv import load_dotenv
import ui_state

load_dotenv()
_pc_lock = asyncio.Lock()

ACTION_SCHEMA = """
Respond ONLY with a valid JSON object in this exact shape, no markdown formatting or extra text:
{
  "reasoning": "Brief explanation of what you see on the screen and why you are taking this action",
  "action": "left_click | double_click | right_click | mouse_move | type | key | scroll | wait | done",
  "coordinate": [x, y],          // exact integer pixel coordinates on screen for clicks/moves
  "text": "string to type",        // string to type when action is "type"
  "press_enter": true,           // whether to press Enter after typing
  "keys": "ctrl+t",              // hotkey when action is "key" (use '+' to join, e.g. 'ctrl+w', 'enter')
  "scroll_direction": "up|down", // when action is "scroll"
  "scroll_amount": 3,            // when action is "scroll"
  "seconds": 1,                  // when action is "wait" (max 3)
  "done_summary": "Summary of what was achieved" // when action is "done"
}
"""

def _screenshot_part():
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"), img.size

def _execute(action: dict):
    a = action.get("action", "")
    if a == "left_click":
        coord = action.get("coordinate")
        if coord and len(coord) == 2:
            pyautogui.click(int(coord[0]), int(coord[1]))
    elif a == "double_click":
        coord = action.get("coordinate")
        if coord and len(coord) == 2:
            pyautogui.doubleClick(int(coord[0]), int(coord[1]))
    elif a == "right_click":
        coord = action.get("coordinate")
        if coord and len(coord) == 2:
            pyautogui.rightClick(int(coord[0]), int(coord[1]))
    elif a == "mouse_move":
        coord = action.get("coordinate")
        if coord and len(coord) == 2:
            pyautogui.moveTo(int(coord[0]), int(coord[1]), duration=0.25)
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

async def computer_use_loop(task: str, max_steps: int = 10) -> str:
    """
    Take control of the screen to complete visual tasks on Windows (Chrome, desktop apps, web).
    Uses Gemini Vision to see the screen and execute mouse clicks, typing, and shortcuts.
    """
    if _pc_lock.locked():
        return "I am currently executing another screen task. Please wait for it to finish."

    async with _pc_lock:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Google API key is not configured for vision control."

        client = genai.Client(api_key=api_key)
        history = []
        ui_state.set_text(f"👁️ Screen Task | {task[:20]}")

        for step in range(max_steps):
            try:
                screenshot_part, (w, h) = await asyncio.to_thread(_screenshot_part)
                prompt = (
                    f"You are Zenith, an AI assistant controlling the user's Windows computer.\n"
                    f"Task to accomplish: {task}\n"
                    f"Screen resolution: {w}x{h}. All click coordinates [x, y] must strictly be within [0, {w}] and [0, {h}].\n"
                    f"Previous actions taken: {json.dumps(history[-4:])}\n\n"
                    f"Look at the full-screen screenshot. Locate the exact UI elements (buttons, search inputs, tabs, links) to interact with.\n"
                    f"Choose the SINGLE next action to progress the task, or return 'done' if the task is complete.\n"
                    f"{ACTION_SCHEMA}"
                )

                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, screenshot_part],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )

                resp_text = response.text.strip()
                if resp_text.startswith("```json"):
                    resp_text = resp_text[7:]
                if resp_text.endswith("```"):
                    resp_text = resp_text[:-3]

                action = json.loads(resp_text.strip())
            except Exception as e:
                logging.error(f"Error in computer_use_loop at step {step}: {e}")
                if "429" in str(e) or "quota" in str(e).lower():
                    return "Task paused due to API quota limits. Please try again in a few moments."
                return f"Computer control encountered an error: {str(e)}"

            logging.info(f"Computer control step {step}: {action}")
            history.append({
                "action": action.get("action"),
                "reasoning": action.get("reasoning", "")
            })

            if action.get("action") == "done":
                summary = action.get("done_summary", "Task completed.")
                ui_state.set_text(f"✅ {summary[:25]}")
                return summary

            await asyncio.to_thread(_execute, action)
            await asyncio.sleep(0.7)

        return "Finished screen task sequence."
