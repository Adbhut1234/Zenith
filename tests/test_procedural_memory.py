import asyncio
import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from agent_tools.procedural_memory import (
    save_playbook, find_playbooks, reflect_on_outcome
)

async def main():
    print("Testing Zenith Procedural Memory & Self-Reflection Engine...")
    
    # 1. Test saving a playbook
    ok = save_playbook(
        task_pattern="windows_powershell_spaces_in_path",
        lesson_learned="Paths with spaces like 'C:\\Users\\Adi Pandey' must be escaped with double quotes in PowerShell.",
        recommended_action="Wrap path with `\"...\"` or use `cmd /c`.",
        context_domain="system"
    )
    print(f"Playbook saved: {ok}")
    
    # 2. Test searching playbooks
    results = find_playbooks("powershell script with spaces in user directory")
    print(f"Found playbooks: {len(results)}")
    for r in results:
        print(f"  - Pattern: {r['task_pattern']} | Action: {r['recommended_action']}")

    # 3. Test self-reflection on a simulated error
    print("\nRunning post-mortem reflection on simulated tool failure...")
    reflection = await reflect_on_outcome(
        task_desc="Run python script with spaces in path",
        action_taken="node C:\\Users\\Adi Pandey\\script.js",
        raw_output="Error: Cannot find module 'C:\\Users\\Adi'",
        is_error=True
    )
    print("Reflection outcome:")
    print(f"  Pattern: {reflection.get('task_pattern')}")
    print(f"  Lesson: {reflection.get('lesson_learned')}")
    print(f"  Action: {reflection.get('recommended_action')}")
    
    print("\nSUCCESS: Procedural memory and reflection verified.")

if __name__ == "__main__":
    asyncio.run(main())
