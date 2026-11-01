"""
Test script for Zenith's Autonomous Browser Agent (browser-use + Chrome/Edge executable)
Supports --login mode to log into your Google account.
"""
import asyncio
import os
import sys
import subprocess
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from agent_tools.web import autonomous_web_task, _get_chrome_path

async def run_test():
    print("=" * 60)
    print("Zenith Browser Agent Test")
    print("=" * 60)

    chrome_path = _get_chrome_path()

    print(f"[*] Detected Browser Executable: {chrome_path}")
    print(f"[*] Using Default Chrome Profile")
    if not chrome_path:
        print("[!] Error: No Chrome or Edge executable found.")
        return

    # Check for --login mode
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("--login", "-login", "login"):
        print("\n" + "=" * 60)
        print("🔑 Google Account Login Mode")
        print("=" * 60)
        print("[*] Launching Chrome with Zenith's dedicated persistent profile...")
        print("[*] Please log in to your Google account in the opened window.")
        print("[*] Once logged in, close the Chrome window to save your session.\n")
        
        proc = subprocess.Popen([
            chrome_path,
            "https://accounts.google.com"
        ])
        proc.wait()
        print("\n✅ Chrome closed. Your Google session and cookies are saved for Zenith!")
        return

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Error: GOOGLE_API_KEY is not set in .env.")
        return
    print(f"[*] Google API Key loaded: {api_key[:6]}...{api_key[-4:]}")

    # Access unwrapped function from LiveKit function_tool decorator
    func = getattr(autonomous_web_task, "__wrapped__", getattr(autonomous_web_task, "_func", autonomous_web_task))

    task_desc = sys.argv[1] if len(sys.argv) > 1 else "Go to https://news.ycombinator.com and extract the title of the top trending story."
    print(f"\n[*] Starting task: \"{task_desc}\"")
    print("[*] Launching visible browser with persistent profile... Watch the Chrome window!\n")

    result = await func(None, task=task_desc, max_steps=5)
    print("\n" + "=" * 60)
    print("Result:")
    print("=" * 60)
    print(result)

if __name__ == "__main__":
    asyncio.run(run_test())
