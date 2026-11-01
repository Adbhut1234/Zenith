import asyncio
import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from agent_tools.deep_thinker import reason_deeply
from agent_tools.procedural_memory import save_playbook, find_playbooks, reflect_on_outcome
from agent_tools.working_memory import working_memory
from agent_tools.emergency import execute_emergency_stop
from agent_tools.memory_evolution import reconcile_and_save_fact, get_db_connection
from agent_tools.system_diagnostics import run_full_diagnostics

async def run_full_suite():
    print("=" * 65)
    print("ZENITH VISION COGNITIVE ARCHITECTURE COMPLETE TEST SUITE")
    print("=" * 65)
    
    # -------------------------------------------------------------
    # Test 1: Subconscious Deliberative Reasoning (System 2 Thinking)
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing Subconscious Deliberative Reasoning (System 2)...")
    thought = await reason_deeply(
        objective="Design a fail-safe backup strategy for a local SQLite database that is actively being written to."
    )
    print(f"-> Confidence: {thought.get('confidence_score')}")
    print(f"-> Optimal Solution: {thought.get('optimal_solution')[:100]}...")
    assert "optimal_solution" in thought
    print("PASS: System 2 Cognitive Reasoning operational.")

    # -------------------------------------------------------------
    # Test 2: Procedural Learning & Self-Reflection (Neuroplasticity)
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Procedural Memory & Self-Reflection...")
    save_playbook(
        task_pattern="git_detached_head_commit",
        lesson_learned="Commits made in detached HEAD state will be orphaned unless a branch is created.",
        recommended_action="git switch -c recovery-branch before committing.",
        context_domain="coding"
    )
    pb_matches = find_playbooks("how to fix detached head in git")
    assert len(pb_matches) > 0
    print(f"-> Retrieved {len(pb_matches)} relevant playbook(s). Best match: '{pb_matches[0]['task_pattern']}'")
    print("PASS: Procedural Neuroplasticity Engine operational.")

    # -------------------------------------------------------------
    # Test 3: Working Memory Scratchpad & Ambient Integration
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Working Memory & Cognitive Scratchpad...")
    working_memory.set_goal(
        goal="Refactor Zenith Core for Vision-like Deliberative Cognition",
        subtasks=["Build Deep Thinker", "Build Neuroplasticity Engine", "Build Working Memory"]
    )
    working_memory.update_subtask("Build Deep Thinker", "completed")
    summary = working_memory.get_summary()
    assert "Active Mission Goal:" in summary
    assert "[X] Build Deep Thinker" in summary
    print("PASS: Working Memory Scratchpad operational.")

    # -------------------------------------------------------------
    # Test 4: Universal Emergency Motor Killswitch
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Universal Emergency Motor Killswitch...")
    emergency_res = await execute_emergency_stop()
    assert emergency_res.get("status") == "frozen"
    print(f"-> Subsystems frozen: {emergency_res.get('cancelled_subsystems')}")
    print("PASS: Emergency Killswitch disengaged all motor loops.")

    # -------------------------------------------------------------
    # Test 5: The Ship of Theseus Memory Evolution Engine
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Ship of Theseus Memory Evolution Engine...")
    test_user = "TestVisionUser"
    ok1, _ = await reconcile_and_save_fact(
        topic="work_station",
        fact="Sir codes on a dual-monitor desktop in Delhi",
        category="personal",
        user_id=test_user
    )
    ok2, msg2 = await reconcile_and_save_fact(
        topic="work_station",
        fact="Sir moved and now works on a mobile workstation setup in Bangalore",
        category="personal",
        user_id=test_user
    )
    assert ok1 and ok2
    print(f"-> Evolution result: {msg2[:100]}...")
    # Cleanup test user
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM zenith_facts WHERE user_id = ?", (test_user,))
        c.execute("DELETE FROM zenith_memory_evolution_log WHERE user_id = ?", (test_user,))
        conn.commit()
    print("PASS: Ship of Theseus Memory Evolution operational.")

    # -------------------------------------------------------------
    # Test 6: Stark-Style Automated System Diagnostics
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing Automated System Diagnostics...")
    diag_res = await run_full_diagnostics()
    assert "database" in diag_res
    assert "hardware" in diag_res
    print(f"-> Database Status: {diag_res['database']['status']}")
    print(f"-> Hardware Stats:  CPU: {diag_res['hardware']['cpu_usage']} | RAM: {diag_res['hardware']['ram_used_pct']}")
    print("PASS: Stark-Style System Diagnostics operational.")

    print("\n" + "=" * 65)
    print("ALL 6 TESTS PASSED: Zenith is 100% Operational & Vision-Ready!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_full_suite())
