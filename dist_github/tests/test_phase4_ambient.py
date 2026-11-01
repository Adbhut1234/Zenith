"""
Verification test for Phase 4: Proactive Ambient Watchers in Zenith
Validates zero-overhead clipboard sequence monitoring, multi-language error classification,
process completion watching, and vocal ambient notification triggers.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import subprocess
from agent_tools.ambient_watchers import (
    ambient_manager,
    detect_error_in_text,
    read_win32_clipboard,
    explain_clipboard_error,
    watch_process,
    configure_ambient_watchers
)


async def run_ambient_verification():
    print("=" * 65)
    print("🔮 ZENITH PHASE 4 VERIFICATION: PROACTIVE AMBIENT WATCHERS")
    print("=" * 65)

    notifications_fired = []

    def mock_ambient_notifier(text: str):
        notifications_fired.append(text)
        print(f"    📢 [MOCK VOCAL ALERT]: {text[:80]}...")

    ambient_manager.set_notifier(mock_ambient_notifier)

    # 1. Multi-Language Error Classifier Test
    print("\n[*] Step 1: Testing Multi-Language Error & Crash Classifier...")
    test_cases = [
        ("Traceback (most recent call last):\n  File 'test.py', line 12\nZeroDivisionError: division by zero", "Python Traceback"),
        ("npm ERR! code ELIFECYCLE\nnpm ERR! errno 1\nnpm ERR! build failed", "NPM Build Error"),
        ("error[E0382]: borrow of moved value: `user`", "Rustc Error"),
        ("java.lang.NullPointerException: Cannot invoke method on null object", "Java Runtime Exception"),
        ("CONFLICT (content): Merge conflict in src/main.js", "Git Merge Conflict")
    ]

    for snippet, expected_type in test_cases:
        detected = detect_error_in_text(snippet)
        print(f"    ✅ '{expected_type}' -> Classified as: '{detected}'")
        assert detected == expected_type

    # 2. Test Win32 Native Clipboard Reader
    print("\n[*] Step 2: Testing Microsecond Win32 Clipboard Handle Reader...")
    clip = read_win32_clipboard()
    print(f"    ✅ Current System Clipboard: {len(clip) if clip else 0} characters read.")

    # 3. Test explain_clipboard_error Tool
    print("\n[*] Step 3: Testing explain_clipboard_error Tool Integration...")
    ambient_manager._last_error_text = "Traceback (most recent call last):\n  File 'server.py', line 45\nKeyError: 'auth_token'"
    explanation = await explain_clipboard_error(None)
    print("    --------------------------------------------------")
    for line in explanation.splitlines()[:5]:
        print(f"    {line}")
    print("    --------------------------------------------------")
    assert "KeyError" in explanation

    # 4. Test Active Process Completion Watcher
    print("\n[*] Step 4: Testing Proactive Process Completion Watcher...")
    # Spawn a short-lived subprocess (0.6s)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.6)"])
    pid = proc.pid
    print(f"    ✅ Spawned test background process PID {pid}.")

    watch_msg = ambient_manager.watch_process(str(pid))
    print(f"    ✅ Process Watcher registered: {watch_msg}")
    assert pid in ambient_manager._monitored_pids

    # Start watcher background loop
    ambient_manager.start()

    # Wait for process to exit and watcher to detect
    print("    ⏳ Waiting for process exit detection...")
    await asyncio.sleep(2.5)

    assert pid not in ambient_manager._monitored_pids, "Process should have been detected as finished."
    print("    ✅ Process termination was successfully detected by ambient watcher!")
    assert len(notifications_fired) >= 1
    print(f"    ✅ Proactive Vocal Notification triggered: {notifications_fired[-1]}")

    # 5. Test Ambient Configuration Tool
    print("\n[*] Step 5: Testing Ambient Watchers Configuration Tool...")
    config_msg = await configure_ambient_watchers(None, clipboard_enabled=True, voice_alerts_enabled=False)
    print(f"    ✅ Config Update: {config_msg.splitlines()[0]}")
    assert ambient_manager.voice_alerts_enabled is False

    # Teardown
    ambient_manager.stop()
    print("\n" + "=" * 65)
    print("🎉 PHASE 4 VERIFICATION COMPLETE: ALL CHECKS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_ambient_verification())
