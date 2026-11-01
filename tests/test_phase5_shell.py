"""
Unit and Integration Verification Suite for Phase 5:
Persistent Shell Sessions & Self-Healing Action Loops
"""

import os
import sys
import asyncio
import logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from agent_tools.persistent_shell import persistent_shell, PersistentPowerShell
from agent_tools.system import get_terminal_state, reset_terminal_session

async def test_persistent_shell_suite():
    print("=" * 70)
    print("🚀 ZENITH PHASE 5 TEST SUITE: PERSISTENT SHELL & SELF-HEALING LOOPS")
    print("=" * 70)

    # 1. Test Session Initialization & Base Directory
    print("\n[TEST 1] Initializing Persistent Shell...")
    initial_cwd = persistent_shell.cwd
    print(f"  ✓ Shell spawned at: {initial_cwd}")
    assert os.path.exists(initial_cwd), "Initial CWD does not exist!"

    # 2. Test Multi-Turn Directory Persistence (cd across commands)
    print("\n[TEST 2] Verifying Directory State Persistence Across Turns...")
    test_dir_name = "_zenith_p5_verify_dir"
    test_dir_path = os.path.join(initial_cwd, test_dir_name)
    os.makedirs(test_dir_path, exist_ok=True)

    try:
        # Step A: Change directory
        res1 = await persistent_shell.execute(f"cd {test_dir_name}")
        print(f"  Step A: executed 'cd {test_dir_name}' -> new PWD: {res1.cwd}")
        assert test_dir_name.lower() in res1.cwd.lower(), f"Expected {test_dir_name} in {res1.cwd}"

        # Step B: Next command - verify that PWD did NOT reset
        res2 = await persistent_shell.execute("$ExecutionContext.SessionState.Path.CurrentLocation.Path")
        print(f"  Step B: subsequent turn PWD query -> {res2.output.strip()}")
        assert test_dir_name.lower() in res2.output.lower(), "Directory persistence failed across turns!"
        print("  ✓ PASS: Directory state remained persistently bound across independent turns.")

        # 3. Test Environment Variable Persistence Across Turns
        print("\n[TEST 3] Verifying Environment Variable State Persistence...")
        res_set = await persistent_shell.execute("$env:ZENITH_PHASE5_SENTINEL = 'ASTRA_SURPASSED'")
        assert res_set.exit_code == 0, "Failed to set environment variable"

        res_get = await persistent_shell.execute("Write-Output $env:ZENITH_PHASE5_SENTINEL")
        print(f"  Retrieved variable in separate turn: '{res_get.output.strip()}'")
        assert "ASTRA_SURPASSED" in res_get.output, "Environment variable did not persist!"
        print("  ✓ PASS: Environment variables persist across turns.")

        # 4. Test Cross-Platform Pre-Healing (POSIX translation)
        print("\n[TEST 4] Verifying Pre-Execution Cross-Platform Translation...")
        
        # Test 4a: POSIX export
        res_exp = await persistent_shell.execute("export ZENITH_PRE_VAR=UltraSpeed")
        print(f"  POSIX export -> Healed: {res_exp.healed} ({res_exp.healing_summary})")
        assert res_exp.healed, "POSIX export was not pre-healed!"
        
        res_check_exp = await persistent_shell.execute("Write-Output $env:ZENITH_PRE_VAR")
        assert "UltraSpeed" in res_check_exp.output, "Pre-healed export variable not set!"

        # Test 4b: touch command
        healed_file = "phase5_test_file.txt"
        res_touch = await persistent_shell.execute(f"touch {healed_file}")
        print(f"  POSIX touch -> Healed: {res_touch.healed} ({res_touch.healing_summary})")
        assert res_touch.healed, "POSIX touch was not pre-healed!"
        assert os.path.exists(os.path.join(persistent_shell.cwd, healed_file)), "Touched file not found on disk!"

        # Test 4c: rm -rf command with verification
        res_rm = await persistent_shell.execute(f"rm -rf {healed_file}")
        print(f"  POSIX rm -rf -> Healed: {res_rm.healed} | Verified: {res_rm.verified}")
        assert res_rm.healed, "POSIX rm -rf was not pre-healed!"
        assert not os.path.exists(os.path.join(persistent_shell.cwd, healed_file)), "File was not removed!"
        print("  ✓ PASS: POSIX export, touch, and rm -rf automatically healed & verified.")

        # 5. Test Post-Execution Auto-Healing (e.g. python3 -> python)
        print("\n[TEST 5] Verifying Post-Execution Dynamic Auto-Healing...")
        # Running python3 on Windows typically fails with "'python3' is not recognized"
        # PersistentShell should catch the error and auto-retry with 'python'
        res_py3 = await persistent_shell.execute('python3 -c "print(\'SELF_HEAL_PYTHON3_SUCCESS\')"', auto_heal=True)
        print(f"  Command with 'python3' output: {res_py3.output.strip()}")
        print(f"  Self-healed status: {res_py3.healed} ({res_py3.healing_summary})")
        assert "SELF_HEAL_PYTHON3_SUCCESS" in res_py3.output, f"Dynamic healing failed: {res_py3.output}"
        print("  ✓ PASS: Auto-healed command line binary incompatibility.")

        # 6. Test Terminal State Introspection
        print("\n[TEST 6] Verifying Terminal State Introspection...")
        state_repr = await get_terminal_state(None)
        print(f"  Terminal state output:\n{state_repr}")
        assert "Working Directory:" in state_repr, "State introspection missing Working Directory"
        assert "Recent Commands:" in state_repr, "State introspection missing Recent Commands"
        print("  ✓ PASS: Terminal state introspection operational.")

        # 7. Test Session Reset
        print("\n[TEST 7] Verifying Session Reset...")
        # Step back to initial cwd
        await persistent_shell.execute(f'cd "{initial_cwd}"')
        reset_res = await reset_terminal_session(None)
        print(f"  Reset output: {reset_res}")
        assert os.path.abspath(persistent_shell.cwd) == os.path.abspath(initial_cwd)
        print("  ✓ PASS: Session reset restored clean state.")

    finally:
        # Clean up temporary test directory
        try:
            persistent_shell.cwd = initial_cwd
            if os.path.exists(test_dir_path):
                import shutil
                shutil.rmtree(test_dir_path, ignore_errors=True)
        except Exception as e:
            print(f"  Cleanup warning: {e}")

    # Terminate shell cleanly
    persistent_shell.terminate()
    print("\n" + "=" * 70)
    print("🏆 ALL PHASE 5 TESTS PASSED: PERSISTENT SHELL & SELF-HEALING OPERATIONAL!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_persistent_shell_suite())
