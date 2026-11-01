"""
Zenith Procedural Memory & Self-Reflection Engine (100% Free)
============================================================
Enables Neuroplasticity: Zenith reflects on action results,
diagnoses tool & command failures, and persists procedural playbooks
into SQLite so it continuously learns from experience without repeating mistakes.
"""

import os
import re
import json
import sqlite3
import logging
import ui_state
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from livekit.agents import function_tool, RunContext

logger = logging.getLogger("procedural_memory")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zenith_memory.db")

_genai_client = None
_genai_client_key = None

def get_genai_client(api_key: str):
    global _genai_client, _genai_client_key
    if _genai_client is None or _genai_client_key != api_key:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
        _genai_client_key = api_key
    return _genai_client

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_procedural_db() -> None:
    """Initialize SQLite tables for procedural playbooks and post-mortem reflections."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_playbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_pattern TEXT NOT NULL,
                    context_domain TEXT NOT NULL DEFAULT 'system',
                    lesson_learned TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    failure_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(task_pattern)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_event TEXT NOT NULL,
                    raw_input TEXT NOT NULL,
                    raw_output TEXT NOT NULL,
                    reflection_analysis TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_playbooks_domain ON zenith_playbooks(context_domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_playbooks_pattern ON zenith_playbooks(task_pattern)")
            conn.commit()
            logger.info("Zenith procedural memory tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize procedural memory database: {e}")

init_procedural_db()

# ==============================================================================
# PROCEDURAL STORAGE & RETRIEVAL
# ==============================================================================

def save_playbook(
    task_pattern: str,
    lesson_learned: str,
    recommended_action: str,
    context_domain: str = "system"
) -> bool:
    """Saves or updates a procedural playbook in SQLite."""
    pattern_clean = task_pattern.strip().lower()
    lesson_clean = lesson_learned.strip()
    action_clean = recommended_action.strip()
    domain_clean = context_domain.strip().lower()
    now = datetime.now().isoformat()

    if not pattern_clean or not action_clean:
        return False

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO zenith_playbooks (
                    task_pattern, context_domain, lesson_learned, recommended_action,
                    success_count, failure_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, 0, ?, ?)
                ON CONFLICT(task_pattern) DO UPDATE SET
                    lesson_learned = excluded.lesson_learned,
                    recommended_action = excluded.recommended_action,
                    context_domain = excluded.context_domain,
                    success_count = zenith_playbooks.success_count + 1,
                    updated_at = excluded.updated_at
            """, (pattern_clean, domain_clean, lesson_clean, action_clean, now, now))
            conn.commit()
            logger.info(f"Saved procedural playbook [{domain_clean}] {pattern_clean}")
            return True
    except Exception as e:
        logger.error(f"Error saving procedural playbook: {e}")
        return False

def find_playbooks(query: str, domain: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
    """Retrieves relevant procedural playbooks using keyword & token overlap."""
    query_clean = query.strip().lower()
    words = [w for w in re.findall(r'\b\w+\b', query_clean) if len(w) > 2]
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if domain:
                cursor.execute("SELECT * FROM zenith_playbooks WHERE context_domain = ?", (domain.lower(),))
            else:
                cursor.execute("SELECT * FROM zenith_playbooks")
            rows = cursor.fetchall()

        results = []
        for r in rows:
            pattern = r["task_pattern"].lower()
            lesson = r["lesson_learned"].lower()
            action = r["recommended_action"].lower()
            score = 0
            
            # Pattern exact match
            if pattern in query_clean or query_clean in pattern:
                score += 5.0
            
            # Word overlap
            for w in words:
                if w in pattern:
                    score += 2.0
                if w in lesson:
                    score += 1.0
                if w in action:
                    score += 0.5
                    
            if score > 0:
                results.append((score, dict(r)))
                
        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:limit]]
    except Exception as e:
        logger.error(f"Error finding procedural playbooks: {e}")
        return []

# ==============================================================================
# POST-MORTEM SELF-REFLECTION (Neuroplasticity Loop)
# ==============================================================================

REFLECTION_PROMPT = """
You are Zenith's Post-Mortem Reflection Engine. Your job is to extract durable lessons from actions.
Analyze this attempted task, the action taken, and the resulting output or error.

Determine:
1. ROOT CAUSE: Why did the action fail (or what made it succeed)?
2. PATTERN: A concise label for this recurring scenario (e.g. 'powershell_unquoted_space', 'node_module_missing', 'git_remote_rejected').
3. HEURISTIC RULE: The permanent procedural lesson learned.
4. RECOMMENDED ACTION: The exact proven command, workaround, or workflow to follow in the future.
5. DOMAIN: One of ['system', 'coding', 'web', 'uia', 'general'].

Return a strictly valid JSON object with keys:
{
  "task_pattern": "string",
  "domain": "string",
  "root_cause": "string",
  "lesson_learned": "string",
  "recommended_action": "string"
}
"""

def _offline_heuristic_reflection(task_desc: str, raw_output: str, is_error: bool) -> Dict[str, Any]:
    out_lower = raw_output.lower()
    domain = "system"
    if "cannot find module" in out_lower or "module_not_found" in out_lower:
        pattern = "node_module_path_space"
        lesson = "Node CLI fails when directory path contains spaces unless wrapped in double quotes."
        action = "Wrap directory paths in escaped double quotes or invoke via cmd /c."
    elif "command not found" in out_lower or "is not recognized" in out_lower:
        pattern = "unrecognized_cli_binary"
        lesson = "Binary is not on PATH or requires activation of local virtual environment."
        action = "Check venv/Scripts path or verify executable existence with Get-Command."
    elif "permission denied" in out_lower or "access is denied" in out_lower:
        pattern = "permission_elevation_required"
        lesson = "Operation target requires Administrator privileges or is locked by another process."
        action = "Run with elevated rights or inspect open file handles using handle.exe/Get-Process."
    else:
        pattern = "generic_execution_fault"
        lesson = "Target execution encountered non-zero status code."
        action = "Verify input arguments, inspect stack trace, and execute step-by-step."
        
    return {
        "task_pattern": pattern,
        "domain": domain,
        "root_cause": "Extracted via offline heuristics analyzer.",
        "lesson_learned": lesson,
        "recommended_action": action
    }

async def reflect_on_outcome(
    task_desc: str,
    action_taken: str,
    raw_output: str,
    is_error: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Background reflection loop. Analyzes execution outcomes and saves playbooks.
    100% Free: uses Gemini free tier with automatic offline heuristic fallback.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    reflection = None

    if api_key and is_error:
        try:
            from google.genai import types
            client = await asyncio.to_thread(get_genai_client, api_key)
            prompt = (
                f"Task Description: {task_desc}\n"
                f"Action Executed: {action_taken}\n"
                f"Result / Error Output:\n{raw_output[:2000]}\n"
                f"Execution Status: {'FAILED' if is_error else 'SUCCESS'}\n"
            )
            response = await client.aio.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=REFLECTION_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw_json = response.text.strip() if response.text else "{}"
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict) and "recommended_action" in parsed:
                reflection = parsed
        except Exception as e:
            logger.warning(f"Cloud reflection failed, using offline heuristics: {e}")

    if not reflection:
        reflection = _offline_heuristic_reflection(task_desc, raw_output, is_error)

    # Persist reflection log
    try:
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO zenith_reflections (trigger_event, raw_input, raw_output, reflection_analysis, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("tool_error" if is_error else "tool_success", f"{task_desc} | {action_taken}", raw_output[:1000], json.dumps(reflection), now))
            conn.commit()
    except Exception as ex:
        logger.warning(f"Could not persist reflection record: {ex}")

    # Save to playbooks
    pattern = reflection.get("task_pattern")
    lesson = reflection.get("lesson_learned")
    action = reflection.get("recommended_action")
    domain = reflection.get("domain", "system")
    if pattern and action:
        ui_state.set_text(f"⚡ Rule Learned: {pattern[:15]}")
        save_playbook(pattern, lesson or "Procedural guideline", action, domain)

    return reflection

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOLS
# ==============================================================================

@function_tool()
async def consult_playbooks(
    context: RunContext,  # type: ignore
    task_or_problem: str,
    domain: str = ""
) -> str:
    """
    Consults Zenith's learned procedural playbooks and past lessons before attempting a task.
    Use this to check if you have previously encountered errors or discovered best practices
    for a specific command, coding task, or system operation.
    
    Args:
        task_or_problem: The command, problem, or task you are about to perform.
        domain: Optional domain filter ('system', 'coding', 'web', 'uia').
    """
    playbooks = await asyncio.to_thread(find_playbooks, query=task_or_problem, domain=domain or None, limit=3)
    if not playbooks:
        return f"No prior procedural playbooks recorded for '{task_or_problem}', Sir. Proceeding with standard execution."

    lines = [f"Found {len(playbooks)} learned playbook(s) for '{task_or_problem}':"]
    for pb in playbooks:
        lines.append(f"\n• Scenario: {pb['task_pattern']} (Domain: {pb['context_domain']})")
        lines.append(f"  Lesson: {pb['lesson_learned']}")
        lines.append(f"  Proven Action: {pb['recommended_action']}")
        lines.append(f"  Reliability: {pb['success_count']} success(es)")

    return "\n".join(lines)

@function_tool()
async def record_learned_playbook(
    context: RunContext,  # type: ignore
    scenario_pattern: str,
    proven_solution: str,
    lesson: str = "",
    domain: str = "system"
) -> str:
    """
    Explicitly records a new procedural playbook or how-to guideline into Zenith's permanent memory.
    Use this when Sir teaches you a new technical rule, a preferred workaround, or when you discover a working solution.
    
    Args:
        scenario_pattern: Short key identifier (e.g. 'powershell_run_admin', 'git_rebase_conflict').
        proven_solution: The exact recommended command or step-by-step workaround.
        lesson: The conceptual reason or explanation behind this rule.
        domain: Domain of task ('system', 'coding', 'web', 'uia').
    """
    ok = await asyncio.to_thread(save_playbook, scenario_pattern, lesson or proven_solution, proven_solution, domain)
    if ok:
        return f"Understood, Sir. Recorded procedural playbook for '{scenario_pattern}' into permanent memory."
    return f"Failed to record playbook for '{scenario_pattern}' due to a local database error."
