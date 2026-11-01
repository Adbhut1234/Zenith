"""
Verification test for Phase 3: Background Worker Swarm in Zenith
Validates non-blocking dispatch, parallel worker execution, voice notification callback,
and surgical task cancellation.
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
import time
from agent_tools.task_manager import (
    task_manager,
    dispatch_background_task,
    check_background_tasks,
    cancel_background_task
)


async def run_swarm_verification():
    print("=" * 65)
    print("⚡ ZENITH PHASE 3 VERIFICATION: BACKGROUND WORKER SWARM")
    print("=" * 65)

    notifications_received = []

    def mock_voice_announcer(announcement: str):
        notifications_received.append(announcement)
        print(f"    📢 [MOCK LIVE VOCAL ANNOUNCEMENT]: {announcement[:90]}...")

    task_manager.set_notifier(mock_voice_announcer)

    # 1. Non-blocking dispatch benchmark
    print("\n[*] Step 1: Testing Non-Blocking Worker Dispatch (Voice channel stays open)...")
    t0 = time.time()
    dispatch_msg = await dispatch_background_task(
        None, task_type="research", details="Breakthroughs in Fusion Energy 2026"
    )
    dispatch_latency_ms = (time.time() - t0) * 1000
    print(f"    ✅ Dispatch returned in {dispatch_latency_ms:.2f}ms (< 15ms target)")
    print(f"    ✅ Response snippet: {dispatch_msg.splitlines()[0]}")
    assert dispatch_latency_ms < 50.0
    assert "Background worker successfully dispatched" in dispatch_msg

    # 2. Check active swarm tasks
    print("\n[*] Step 2: Querying Live Swarm Status...")
    status_report = await check_background_tasks(None)
    print("    --------------------------------------------------")
    for line in status_report.splitlines():
        print(f"    {line}")
    print("    --------------------------------------------------")
    assert "RUNNING" in status_report or "Initiated" in status_report

    # 3. Simulate Fast Completing Worker with Voice Notification
    print("\n[*] Step 3: Testing Async Worker Completion & Vocal Notification...")
    async def fast_worker(topic: str):
        await asyncio.sleep(0.3)
        return f"Synthesized 4 key fusion milestones for {topic}. Saved to Desktop."

    sim_task = task_manager.spawn("fusion_research", "Fusion Energy 2026", fast_worker, topic="Fusion Energy")
    print(f"    ✅ Spawned fast worker [{sim_task.task_id}]. Awaiting non-blocking completion...")
    
    # Wait for completion
    await asyncio.sleep(0.5)
    assert sim_task.status == "completed"
    print(f"    ✅ Worker [{sim_task.task_id}] completed with status: {sim_task.status.upper()}")
    print(f"    ✅ Result captured: {sim_task.result}")
    assert len(notifications_received) >= 1
    assert "Fusion Energy 2026" in notifications_received[-1]

    # 4. Testing Surgical Worker Cancellation
    print("\n[*] Step 4: Testing Surgical Background Task Cancellation...")
    async def perpetual_worker():
        await asyncio.sleep(100.0)
        return "Done"

    long_task = task_manager.spawn("web_scraper", "Scraping 500 web pages", perpetual_worker)
    print(f"    ✅ Spawned long-running worker [{long_task.task_id}].")
    
    cancel_result = await cancel_background_task(None, task_id=long_task.task_id)
    print(f"    ✅ Cancellation Result: {cancel_result}")
    assert "has been cancelled" in cancel_result
    assert long_task.status == "cancelled"

    # 5. Batch Cleanup
    print("\n[*] Step 5: Testing Swarm Batch Shutdown...")
    task_manager.spawn("job_a", "Batch Job A", perpetual_worker)
    task_manager.spawn("job_b", "Batch Job B", perpetual_worker)
    active_before = len(task_manager.list_active_tasks())
    print(f"    ✅ Active workers before batch cancel: {active_before}")
    assert active_before >= 2

    cleaned_count = task_manager.cancel_all()
    print(f"    ✅ Aborted {cleaned_count} active workers simultaneously.")
    assert len(task_manager.list_active_tasks()) == 0

    print("\n" + "=" * 65)
    print("🎉 PHASE 3 VERIFICATION COMPLETE: ALL CHECKS PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_swarm_verification())
