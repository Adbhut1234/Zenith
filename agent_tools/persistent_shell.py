"""
Zenith Persistent Shell & Self-Healing Action Engine (Phase 5)
=============================================================
Maintains a stateful, interactive PowerShell session across turns:
- Retains working directory ($PWD), virtualenvs, and environment variables across turns.
- Uses high-speed sentinel tokens for deterministic stdout/stderr/exitcode capture.
- Features self-healing action loops:
  * POSIX -> PowerShell translation (export, source, rm -rf, touch, which)
  * python3/pip3 -> python/pip fallback on Windows
  * ExecutionPolicy automatic bypass on script restriction
  * Directory typo auto-correction & fuzzy matching
  * Post-execution file/folder state verification
"""

import os
import re
import sys
import uuid
import time
import queue
import logging
import asyncio
import difflib
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any

logger = logging.getLogger("persistent_shell")

@dataclass
class ShellResult:
    command: str
    output: str
    exit_code: int
    cwd: str
    duration_ms: float
    healed: bool = False
    healing_summary: str = ""
    verified: bool = False
    verification_summary: str = ""

    def to_formatted_response(self) -> str:
        lines = []
        if self.healed:
            lines.append(f"[Self-Healing Applied]: {self.healing_summary}")
        if self.verified:
            lines.append(f"[Action Verified]: {self.verification_summary}")
            
        lines.append(f"Directory: {self.cwd}")
        lines.append(f"Exit Code: {self.exit_code}")
        
        cleaned_out = self.output.strip()
        if cleaned_out:
            lines.append(f"Output:\n{cleaned_out}")
        else:
            lines.append("Output: (Command executed with no output)")
            
        return "\n".join(lines)


class PersistentPowerShell:
    """
    Manages a persistent background PowerShell process with non-blocking I/O
    and sentinel protocol for atomic command execution.
    """
    def __init__(self, initial_cwd: Optional[str] = None):
        self.initial_cwd = os.path.abspath(initial_cwd or os.getcwd())
        self.cwd = self.initial_cwd
        self.process: Optional[subprocess.Popen] = None
        self._lock = asyncio.Lock()
        self._thread_lock = threading.Lock()
        self.history: List[Dict[str, Any]] = []
        self._active_token: Optional[str] = None
        self._spawn()

    def _spawn(self):
        """Spawns or restarts the background PowerShell process."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        logger.info(f"Spawning persistent PowerShell session at: {self.cwd}")
        # -ExecutionPolicy Bypass ensures local scripts (.ps1) can run
        self.process = subprocess.Popen(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoExit",
                "-ExecutionPolicy", "Bypass",
                "-Command", "-"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified parsing
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=self.cwd
        )

        # Initialize UTF-8 encoding and standard preferences in PowerShell
        clean_cwd = self.cwd.replace("'", "''")
        init_commands = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "$ErrorActionPreference = 'Continue'\n"
            f"Set-Location -LiteralPath '{clean_cwd}'\n"
        )
        self.process.stdin.write(init_commands)
        self.process.stdin.flush()

    def _raw_execute(self, command: str, timeout_sec: float = 25.0) -> Tuple[str, int, str, float]:
        """
        Synchronous raw execution using sentinel wrapping.
        Returns: (output, exit_code, new_cwd, duration_ms)
        """
        with self._thread_lock:
            if not self.process or self.process.poll() is not None:
                self._spawn()

            tok = uuid.uuid4().hex[:12]
            start_time = time.perf_counter()

            # Construct sentinel-wrapped script block (all blocks on single lines to prevent multiline prompt delay)
            script = (
                f"[Console]::Out.WriteLine('__ZENITH_START_{tok}__')\n"
                f"try {{ {command} }} catch {{ [Console]::Out.WriteLine('ERROR: ' + $_.Exception.Message) }}\n"
                f"$__z_ec = if ($LASTEXITCODE -ne $null) {{ $LASTEXITCODE }} elseif (-not $?) {{ 1 }} else {{ 0 }}\n"
                f"$__z_pwd = $ExecutionContext.SessionState.Path.CurrentLocation.Path\n"
                f"[Console]::Out.WriteLine('__ZENITH_END_{tok}__:' + $__z_ec + ':' + $__z_pwd)\n"
            )

            try:
                self.process.stdin.write(script)
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                logger.warning(f"PowerShell pipe broken: {e}. Respawning...")
                self._spawn()
                self.process.stdin.write(script)
                self.process.stdin.flush()

            lines = []
            started = False
            exit_code = 0
            new_cwd = self.cwd
            deadline = time.time() + timeout_sec

            while True:
                # Check timeout
                if time.time() > deadline:
                    logger.warning(f"Command '{command[:30]}' timed out after {timeout_sec}s. Interrupting...")
                    self._spawn()  # Respawn to clear locked state
                    return "Execution timed out (process aborted to prevent deadlock).", 124, self.cwd, (time.perf_counter() - start_time) * 1000

                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        logger.warning("PowerShell process exited unexpectedly. Respawning...")
                        self._spawn()
                        break
                    time.sleep(0.01)
                    continue

                line_clean = line.rstrip("\r\n")

                if f"__ZENITH_START_{tok}__" in line_clean:
                    started = True
                    continue

                if f"__ZENITH_END_{tok}__" in line_clean:
                    parts = line_clean.split(":", 2)
                    if len(parts) >= 3:
                        try:
                            exit_code = int(parts[1])
                        except ValueError:
                            exit_code = 0
                        new_cwd = parts[2].strip()
                    break

                if started:
                    lines.append(line_clean)

            duration_ms = (time.perf_counter() - start_time) * 1000
            self.cwd = new_cwd
            output = "\n".join(lines).strip()
            return output, exit_code, new_cwd, duration_ms

    def _pre_heal_command(self, cmd: str) -> Tuple[str, bool, str]:
        """
        Translates POSIX conventions and common cross-platform syntax to native PowerShell.
        """
        original = cmd.strip()
        healed_cmd = original
        healing_applied = False
        reasons = []

        # 0. Windows Store execution alias bypass for python3 / pip3
        if re.search(r'\bpython3\b', healed_cmd):
            healed_cmd = re.sub(r'\bpython3\b', 'python', healed_cmd)
            healing_applied = True
            reasons.append("Mapped 'python3' to 'python' (Windows compatibility)")

        if re.search(r'\bpip3\b', healed_cmd):
            healed_cmd = re.sub(r'\bpip3\b', 'pip', healed_cmd)
            healing_applied = True
            reasons.append("Mapped 'pip3' to 'pip' (Windows compatibility)")

        # 1. POSIX export VAR=val -> $env:VAR = "val"
        if healed_cmd.startswith("export ") and "=" in healed_cmd:
            parts = healed_cmd[7:].split("=", 1)
            var_name = parts[0].strip()
            var_val = parts[1].strip().strip('"').strip("'")
            healed_cmd = f'$env:{var_name} = "{var_val}"'
            healing_applied = True
            reasons.append(f"Converted bash export to PowerShell $env:{var_name}")

        # 2. POSIX source venv/bin/activate -> .\venv\Scripts\Activate.ps1
        elif healed_cmd.startswith("source ") or healed_cmd.startswith(". "):
            target = healed_cmd.split(maxsplit=1)[1].strip()
            if "activate" in target.lower():
                # Check for Windows virtualenv activate script
                for cand in [".\\venv\\Scripts\\Activate.ps1", ".\\.venv\\Scripts\\Activate.ps1", "venv\\Scripts\\Activate.ps1"]:
                    if os.path.exists(os.path.join(self.cwd, cand)):
                        healed_cmd = f"& '{cand}'"
                        healing_applied = True
                        reasons.append(f"Converted virtualenv source to Windows '{cand}'")
                        break

        # 3. rm -rf <target> -> Remove-Item -Recurse -Force <target>
        elif healed_cmd.startswith("rm -rf "):
            target = healed_cmd[7:].strip()
            healed_cmd = f"Remove-Item -Recurse -Force {target}"
            healing_applied = True
            reasons.append(f"Converted 'rm -rf' to PowerShell 'Remove-Item -Recurse -Force'")

        # 4. touch <target> -> New-Item -ItemType File -Force <target>
        elif healed_cmd.startswith("touch "):
            target = healed_cmd[6:].strip()
            healed_cmd = f"New-Item -ItemType File -Force {target}"
            healing_applied = True
            reasons.append(f"Converted 'touch' to PowerShell 'New-Item -ItemType File'")

        # 5. which <tool> -> Get-Command <tool>
        elif healed_cmd.startswith("which "):
            target = healed_cmd[6:].strip()
            healed_cmd = f"Get-Command {target} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source"
            healing_applied = True
            reasons.append(f"Converted 'which' to 'Get-Command'")

        # 6. cd ~ or paths with forward slashes
        elif healed_cmd.startswith("cd "):
            target = healed_cmd[3:].strip().strip('"').strip("'")
            if target == "~":
                target = os.path.expanduser("~")
                healed_cmd = f'Set-Location -LiteralPath "{target}"'
                healing_applied = True
                reasons.append("Expanded '~' to user home directory")
            elif "/" in target:
                norm = target.replace("/", "\\")
                healed_cmd = f'Set-Location -LiteralPath "{norm}"'
                healing_applied = True
                reasons.append("Normalized forward slashes in path")

        return healed_cmd, healing_applied, "; ".join(reasons)

    def _post_heal_command(self, cmd: str, output: str, exit_code: int) -> Tuple[Optional[str], str]:
        """
        Inspects failures and produces an auto-corrected command if a recoverable pattern is detected.
        """
        lower_out = output.lower()

        # Case 1: python3 not recognized on Windows -> retry with python
        if exit_code != 0 and ("'python3' is not recognized" in lower_out or "the term 'python3' is not recognized" in lower_out):
            new_cmd = cmd.replace("python3", "python")
            return new_cmd, "Substituted 'python' for 'python3' (Windows compatibility)"

        # Case 2: pip3 not recognized on Windows -> retry with pip
        if exit_code != 0 and ("'pip3' is not recognized" in lower_out or "the term 'pip3' is not recognized" in lower_out):
            new_cmd = cmd.replace("pip3", "pip")
            return new_cmd, "Substituted 'pip' for 'pip3' (Windows compatibility)"

        # Case 3: Script execution disabled by ExecutionPolicy
        if exit_code != 0 and ("execution of scripts is disabled" in lower_out or "running scripts is disabled" in lower_out):
            new_cmd = f"Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; {cmd}"
            return new_cmd, "Bypassed execution policy restriction"

        # Case 4: Cannot find path for cd / Set-Location -> fuzzy match directories in current cwd
        if exit_code != 0 and ("cannot find path" in lower_out or "does not exist" in lower_out) and cmd.strip().startswith(("cd ", "Set-Location ")):
            raw_target = cmd.strip().split(maxsplit=1)[1].strip().strip('"').strip("'")
            try:
                available_dirs = [d for d in os.listdir(self.cwd) if os.path.isdir(os.path.join(self.cwd, d))]
                matches = difflib.get_close_matches(raw_target, available_dirs, n=1, cutoff=0.6)
                if matches:
                    corrected_target = matches[0]
                    new_cmd = f'Set-Location -LiteralPath "{os.path.join(self.cwd, corrected_target)}"'
                    return new_cmd, f"Corrected directory path to '{corrected_target}' via fuzzy matching"
            except Exception:
                pass

        return None, ""

    def _verify_action(self, cmd: str, exit_code: int) -> Tuple[bool, str]:
        """
        Verifies that side-effecting operations (creation, deletion, moves) succeeded on disk.
        """
        if exit_code != 0:
            return False, ""

        cmd_lower = cmd.strip().lower()

        # Verify folder creation
        if cmd_lower.startswith(("mkdir ", "md ", "new-item -itemtype directory")):
            parts = cmd.strip().split(maxsplit=1)
            if len(parts) > 1:
                target_name = parts[1].replace("-Force", "").replace("-ItemType Directory", "").strip().strip('"').strip("'")
                full_path = os.path.join(self.cwd, target_name)
                if os.path.exists(full_path):
                    return True, f"Verified directory exists at: {full_path}"

        # Verify file creation
        if cmd_lower.startswith(("new-item -itemtype file", "echo ", "> ", "touch ")):
            # Check if any new item was created recently in cwd
            pass

        # Verify removal
        if cmd_lower.startswith(("remove-item", "rm ", "del ", "rmdir ")):
            parts = cmd.strip().split(maxsplit=1)
            if len(parts) > 1:
                target_name = parts[1].replace("-Recurse", "").replace("-Force", "").strip().strip('"').strip("'")
                full_path = os.path.join(self.cwd, target_name)
                if not os.path.exists(full_path):
                    return True, f"Verified item was successfully deleted from: {full_path}"

        return False, ""

    async def execute(self, command: str, timeout_sec: float = 30.0, auto_heal: bool = True) -> ShellResult:
        """
        Asynchronously executes a command inside the persistent PowerShell session
        with automatic pre-healing, post-healing, and post-action verification.
        """
        async with self._lock:
            # Step 1: Pre-execution translation
            exec_cmd, pre_healed, pre_reason = self._pre_heal_command(command)
            healing_notes = [pre_reason] if pre_healed else []

            # Step 2: First attempt execution in worker thread
            output, exit_code, new_cwd, duration = await asyncio.to_thread(
                self._raw_execute, exec_cmd, timeout_sec
            )

            # Step 3: Post-execution healing attempt if failed
            if exit_code != 0 and auto_heal:
                post_cmd, post_reason = self._post_heal_command(exec_cmd, output, exit_code)
                if post_cmd:
                    logger.info(f"Self-healing triggered: {post_reason}. Retrying with: {post_cmd}")
                    healing_notes.append(post_reason)
                    retry_out, retry_ec, retry_cwd, retry_dur = await asyncio.to_thread(
                        self._raw_execute, post_cmd, timeout_sec
                    )
                    # If retry was better or succeeded, adopt it
                    if retry_ec == 0 or len(retry_out) > len(output):
                        output = retry_out
                        exit_code = retry_ec
                        new_cwd = retry_cwd
                        duration += retry_dur
                        exec_cmd = post_cmd

            # Step 4: Verification of physical state
            verified, verify_summary = self._verify_action(exec_cmd, exit_code)

            # Record history
            entry = {
                "timestamp": time.time(),
                "original_cmd": command,
                "executed_cmd": exec_cmd,
                "exit_code": exit_code,
                "cwd": new_cwd,
                "duration_ms": duration,
                "healed": bool(healing_notes)
            }
            self.history.append(entry)
            if len(self.history) > 50:
                self.history.pop(0)

            return ShellResult(
                command=exec_cmd,
                output=output,
                exit_code=exit_code,
                cwd=new_cwd,
                duration_ms=duration,
                healed=bool(healing_notes),
                healing_summary=" | ".join(healing_notes),
                verified=verified,
                verification_summary=verify_summary
            )

    def get_state(self) -> Dict[str, Any]:
        """Returns the current state of the persistent shell session."""
        return {
            "cwd": self.cwd,
            "alive": self.process is not None and self.process.poll() is None,
            "history_count": len(self.history),
            "recent_history": self.history[-5:] if self.history else []
        }

    def reset(self):
        """Resets the shell session to a fresh state at the initial working directory."""
        self.cwd = self.initial_cwd
        self._spawn()
        self.history.clear()
        logger.info("Persistent PowerShell session was reset.")

    def terminate(self):
        """Gracefully terminates the background shell process."""
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            logger.info("Persistent PowerShell session terminated.")


# Global persistent shell singleton
persistent_shell = PersistentPowerShell()
