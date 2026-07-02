import os, io, json, time, base64, logging, asyncio
import pyautogui
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
_pc_lock = asyncio.Lock()

ACTION_SCHEMA = """
Respond ONLY with JSON in this exact shape, no other text:
{
  "reasoning": "what you see and why you're choosing this action",
  "action": "left_click | double_click | right_click | mouse_move | type | key | scroll | wait | done",
  "coordinate": [x, y],          // required for click/move actions
  "text": "string to type",      // required for "type"
  "keys": "ctrl+s",              // required for "key" (use '+' to join)
  "scroll_direction": "up|down", // required for "scroll"
  "scroll_amount": 3,            // required for "scroll"
  "seconds": 1,                  // required for "wait"
  "done_summary": "what was accomplished" // required for "done"
}
"""

def _screenshot_part():
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"), img.size

def _execute(action: dict):
    a = action["action"]
    if a == "left_click":
        x, y = action["coordinate"]; pyautogui.click(x, y)
    elif a == "double_click":
        x, y = action["coordinate"]; pyautogui.doubleClick(x, y)
    elif a == "right_click":
        x, y = action["coordinate"]; pyautogui.rightClick(x, y)
    elif a == "mouse_move":
        x, y = action["coordinate"]; pyautogui.moveTo(x, y, duration=0.3)
    elif a == "type":
        pyautogui.write(action["text"], interval=0.03)
    elif a == "key":
        pyautogui.hotkey(*action["keys"].split("+"))
    elif a == "scroll":
        amt = action.get("scroll_amount", 3)
        clicks = amt if action.get("scroll_direction") == "up" else -amt
        pyautogui.scroll(clicks)
    elif a == "wait":
        time.sleep(action.get("seconds", 1))

async def computer_use_loop(task: str, max_steps: int = 15) -> str:
    if _pc_lock.locked():
        return "I'm still working on the previous screen task — please wait for it to finish first."
    async with _pc_lock:
        history = []
        for step in range(max_steps):
            screenshot_part, (w, h) = await asyncio.to_thread(_screenshot_part)
            prompt = (
                f"You are controlling a desktop to accomplish this task: {task}\n"
                f"Screen resolution: {w}x{h}. Coordinates must be within this range.\n"
                f"Actions taken so far: {json.dumps(history[-5:])}\n"
                f"Look at the screenshot. Decide the SINGLE next action.\n{ACTION_SCHEMA}"
            )
            try:
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, screenshot_part],
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logging.warning("API rate limit hit during computer_use_loop.")
                    return "Task aborted due to API rate limits (429 Quota Exceeded). Please wait a minute before trying again or upgrade your API tier."
                raise e
            try:
                action = json.loads(response.text)
            except json.JSONDecodeError:
                logging.error(f"Bad JSON from model: {response.text}")
                continue

            logging.info(f"Step {step}: {action}")
            history.append({"action": action.get("action"), "reasoning": action.get("reasoning", "")})

            if action["action"] == "done":
                return action.get("done_summary", "Task completed.")

            await asyncio.to_thread(_execute, action)
            await asyncio.sleep(0.6)  # let UI settle before next screenshot

        return "Reached max steps without confirming task completion. Stopped for safety."
