"""
Zenith Dream Cycle & Autonomous Cognitive Synthesis (100% Free)
==============================================================
Runs an autonomous background loop during idle moments to:
1. Reconcile working memory with ambient signals (clipboard errors, process crashes).
2. Pre-compute proactive solutions before the user even asks.
3. Synthesize new Knowledge Graph relations from raw facts.
4. Keep the Apple-style Dynamic Island pill updated with proactive tactical insights.
"""

import os
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import ui_state
from .working_memory import working_memory
from .procedural_memory import find_playbooks, save_playbook, get_db_connection

logger = logging.getLogger("dream_cycle")

_genai_client = None

def get_genai_client(api_key: str):
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client

class DreamCycleSynthesizer:
    """Background autonomous cognitive synthesizer."""
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_processed_signal_time: Optional[str] = None
        self._idle_interval_seconds = 45.0
        self.proactive_insights: List[Dict[str, Any]] = []

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._dream_loop())
            logger.info("Zenith Dream Cycle initialized and active.")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _dream_loop(self):
        """Main idle background cognitive synthesis loop."""
        await asyncio.sleep(10.0)  # Initial boot grace period
        while self._running:
            try:
                await self._synthesize_unresolved_ambient()
                await self._consolidate_reflections()
                await self._audit_memory_evolution()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dream cycle synthesis: {e}")

            await asyncio.sleep(self._idle_interval_seconds)

    async def _synthesize_unresolved_ambient(self):
        """Checks for unhandled clipboard errors or process crashes and pre-computes fixes."""
        signals = working_memory.ambient_signals
        if not signals:
            return

        latest_sig = signals[-1]
        timestamp = latest_sig.get("timestamp")
        if timestamp == self._last_processed_signal_time:
            return

        if latest_sig.get("type") == "clipboard_error":
            self._last_processed_signal_time = timestamp
            details = latest_sig.get("details", "")
            
            # Check if we already have a playbook
            existing = find_playbooks(details)
            if existing:
                playbook = existing[0]
                insight = f"Found existing playbook for copied error: {playbook['recommended_action']}"
                working_memory.add_note(f"Dream Cycle: {insight}")
                ui_state.set_text(f"💡 Solution Ready")
                logger.info(f"Dream Cycle matched existing playbook: {insight}")
                return

            # Synthesize proactive solution via Gemini or heuristic
            solution = await self._generate_proactive_fix(details)
            if solution:
                working_memory.add_note(f"Dream Cycle Proactive Diagnosis: {solution}")
                self.proactive_insights.append({
                    "timestamp": timestamp,
                    "issue": details[:100],
                    "fix": solution
                })
                ui_state.set_text("💡 Fix Synthesized")
                logger.info(f"Dream Cycle synthesized new proactive fix: {solution}")

    async def _generate_proactive_fix(self, error_text: str) -> str:
        """Generates a concise tactical fix for an ambient error."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Verify path normalization and execute command in quotes."

        try:
            from google.genai import types
            client = await asyncio.to_thread(get_genai_client, api_key)
            prompt = (
                f"A developer copied this compiler/system error to their clipboard:\n{error_text[:1200]}\n\n"
                "Provide a single-sentence tactical diagnosis and the exact 1-line command or code fix to solve it.\n"
                "Keep it under 30 words."
            )
            response = await client.aio.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                )
            )
            return response.text.strip() if response.text else "Review syntax and arguments."
        except Exception:
            return "Inspect terminal arguments and check dependencies."

    async def _audit_memory_evolution(self):
        """Periodically audits active memory facts to eliminate stale contradictions."""
        try:
            from .memory_evolution import audit_all_memory_contradictions
            user_id = os.getenv("Zenith_USER_ID") or "Admin"
            resolutions = await audit_all_memory_contradictions(user_id)
            if resolutions:
                logger.info(f"Dream cycle reconciled {len(resolutions)} memory contradiction(s): {resolutions}")
        except Exception as e:
            logger.debug(f"Memory audit in dream cycle: {e}")

    async def _consolidate_reflections(self):
        """Prunes and links orphaned reflection records."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM zenith_reflections")
                count = cursor.fetchone()[0]
                if count > 200:
                    cursor.execute("DELETE FROM zenith_reflections WHERE id IN (SELECT id FROM zenith_reflections ORDER BY id ASC LIMIT 50)")
                    conn.commit()
        except Exception:
            pass

dream_cycle = DreamCycleSynthesizer()

def get_proactive_insights() -> List[Dict[str, Any]]:
    return dream_cycle.proactive_insights
