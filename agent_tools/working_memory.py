"""
Zenith Working Memory & Cognitive Scratchpad (100% Free)
=======================================================
Implements an active cognitive scratchpad (Working Memory) inspired by
Vision's stream of consciousness. Tracks the active mission goal,
subtask progress, working hypotheses, and ambient sensory signals
across conversation turns and background watcher alerts.
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from livekit.agents import function_tool, RunContext

logger = logging.getLogger("working_memory")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zenith_memory.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

class WorkingMemoryBuffer:
    """Thread-safe active cognitive buffer with SQLite backup."""
    def __init__(self):
        self._lock = asyncio.Lock()
        self.active_goal: str = ""
        self.subtasks: List[Dict[str, str]] = []
        self.scratchpad_notes: List[str] = []
        self.ambient_signals: List[Dict[str, Any]] = []
        self._init_db()
        self._load_from_db()

    def _init_db(self):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS zenith_working_memory (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        active_goal TEXT NOT NULL DEFAULT '',
                        subtasks_json TEXT NOT NULL DEFAULT '[]',
                        notes_json TEXT NOT NULL DEFAULT '[]',
                        ambient_json TEXT NOT NULL DEFAULT '[]',
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing working memory DB: {e}")

    def _load_from_db(self):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM zenith_working_memory WHERE id = 1")
                row = cursor.fetchone()
                if row:
                    self.active_goal = row["active_goal"] or ""
                    self.subtasks = json.loads(row["subtasks_json"] or "[]")
                    self.scratchpad_notes = json.loads(row["notes_json"] or "[]")
                    self.ambient_signals = json.loads(row["ambient_json"] or "[]")
        except Exception as e:
            logger.warning(f"Could not load previous working memory: {e}")

    def _persist(self):
        try:
            now = datetime.now().isoformat()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO zenith_working_memory (id, active_goal, subtasks_json, notes_json, ambient_json, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        active_goal = excluded.active_goal,
                        subtasks_json = excluded.subtasks_json,
                        notes_json = excluded.notes_json,
                        ambient_json = excluded.ambient_json,
                        updated_at = excluded.updated_at
                """, (
                    self.active_goal,
                    json.dumps(self.subtasks),
                    json.dumps(self.scratchpad_notes),
                    json.dumps(self.ambient_signals),
                    now
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error persisting working memory: {e}")

    def set_goal(self, goal: str, subtasks: Optional[List[str]] = None):
        self.active_goal = goal.strip()
        if subtasks is not None:
            self.subtasks = [{"title": s.strip(), "status": "pending"} for s in subtasks if s.strip()]
        self._persist()

    def update_subtask(self, title: str, status: str = "completed"):
        for st in self.subtasks:
            if title.lower() in st["title"].lower():
                st["status"] = status
        self._persist()

    def add_note(self, note: str):
        if note.strip() and note.strip() not in self.scratchpad_notes:
            self.scratchpad_notes.append(note.strip())
            if len(self.scratchpad_notes) > 10:
                self.scratchpad_notes.pop(0)
            self._persist()

    def record_ambient_signal(self, signal_type: str, details: str):
        sig = {
            "type": signal_type,
            "details": details[:300],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self.ambient_signals.append(sig)
        if len(self.ambient_signals) > 8:
            self.ambient_signals.pop(0)
        self._persist()

    def clear(self):
        self.active_goal = ""
        self.subtasks = []
        self.scratchpad_notes = []
        self.ambient_signals = []
        self._persist()

    def get_summary(self) -> str:
        lines = []
        if self.active_goal:
            lines.append(f"Active Mission Goal: {self.active_goal}")
        if self.subtasks:
            lines.append("Subtasks:")
            for st in self.subtasks:
                mark = "[X]" if st["status"] == "completed" else "[-]" if st["status"] == "in_progress" else "[ ]"
                lines.append(f"  {mark} {st['title']}")
        if self.scratchpad_notes:
            lines.append("Scratchpad Notes:")
            for n in self.scratchpad_notes[-5:]:
                lines.append(f"  • {n}")
        if self.ambient_signals:
            lines.append("Recent Ambient Sensory Signals:")
            for s in self.ambient_signals[-3:]:
                lines.append(f"  [{s['timestamp']}] ({s['type']}): {s['details']}")
                
        if not lines:
            return "Working memory scratchpad is currently empty. No active multi-step mission."
            
        return "\n".join(lines)

working_memory = WorkingMemoryBuffer()

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOLS
# ==============================================================================

@function_tool()
async def inspect_scratchpad(
    context: RunContext  # type: ignore
) -> str:
    """
    Inspect Zenith's active working memory scratchpad.
    Returns the current high-level goal, subtask checklist, scratchpad thoughts,
    and recent ambient signals. Use this to maintain context across long operations.
    """
    return working_memory.get_summary()

@function_tool()
async def update_scratchpad(
    context: RunContext,  # type: ignore
    active_goal: str = "",
    subtask_to_add: str = "",
    complete_subtask: str = "",
    thought_or_note: str = ""
) -> str:
    """
    Updates Zenith's working memory scratchpad during complex multi-step missions.
    Use this to record working hypotheses, mark progress, or update the main objective.
    
    Args:
        active_goal: Set or update the primary multi-step mission goal.
        subtask_to_add: A new sub-step to add to the active checklist.
        complete_subtask: Title or keyword of a subtask you just finished.
        thought_or_note: A working hypothesis, diagnostic finding, or intermediate result to keep in mind.
    """
    updates = []
    if active_goal:
        working_memory.set_goal(active_goal)
        updates.append(f"Set goal: '{active_goal}'")
    if subtask_to_add:
        working_memory.subtasks.append({"title": subtask_to_add.strip(), "status": "pending"})
        working_memory._persist()
        updates.append(f"Added subtask: '{subtask_to_add}'")
    if complete_subtask:
        working_memory.update_subtask(complete_subtask, "completed")
        updates.append(f"Completed subtask matching '{complete_subtask}'")
    if thought_or_note:
        working_memory.add_note(thought_or_note)
        updates.append(f"Logged thought: '{thought_or_note}'")

    if not updates:
        return "No updates specified for working memory."
    return f"Working memory updated successfully: {'; '.join(updates)}."

@function_tool()
async def clear_scratchpad(
    context: RunContext  # type: ignore
) -> str:
    """
    Clears the working memory scratchpad when a mission or complex task is fully completed.
    """
    working_memory.clear()
    return "Working memory scratchpad has been cleared for the next mission, Sir."
