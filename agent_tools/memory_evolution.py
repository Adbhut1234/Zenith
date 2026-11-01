"""
Zenith "Ship of Theseus" Memory Evolution & Contradiction Engine (100% Free)
==========================================================================
Inspired by Vision's inquiry into the Ship of Theseus:
"If the planks of a ship are replaced one by one until none of the original
material remains, is it still the same ship?"
As the user's life, career, projects, and habits change over time,
this engine reconciles semantic contradictions, archives superseded facts,
and maintains an evolving continuum of truth without data corruption.
"""

import os
import re
import json
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from livekit.agents import function_tool, RunContext
import ui_state

logger = logging.getLogger("memory_evolution")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zenith_memory.db")

_genai_client = None

def get_genai_client(api_key: str):
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_evolution_schema():
    """Ensure zenith_facts supports temporal versioning & evolution tracking."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check existing columns
            cursor.execute("PRAGMA table_info(zenith_facts)")
            cols = [r["name"] for r in cursor.fetchall()]
            
            if "is_active" not in cols:
                cursor.execute("ALTER TABLE zenith_facts ADD COLUMN is_active INTEGER DEFAULT 1")
            if "superseded_by" not in cols:
                cursor.execute("ALTER TABLE zenith_facts ADD COLUMN superseded_by INTEGER DEFAULT NULL")
            if "superseded_reason" not in cols:
                cursor.execute("ALTER TABLE zenith_facts ADD COLUMN superseded_reason TEXT DEFAULT NULL")
                
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_memory_evolution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    old_fact_id INTEGER,
                    old_fact TEXT,
                    new_fact_id INTEGER,
                    new_fact TEXT,
                    reason TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.info("Ship of Theseus evolution schema verified.")
    except Exception as e:
        logger.error(f"Error initializing memory evolution schema: {e}")

init_evolution_schema()

# ==============================================================================
# CONTRADICTION & EVOLUTION RECONCILIATION
# ==============================================================================

RECONCILE_PROMPT = """
You are the Epistemic Truth Arbiter of Zenith's memory (inspired by the Ship of Theseus).
Evaluate whether a newly learned user fact conflicts with, updates, or supersedes an existing active fact.

Existing Fact: "{existing_fact}" (Topic: {existing_topic}, Category: {existing_category})
New Incoming Fact: "{new_fact}" (Topic: {new_topic}, Category: {new_category})

Determine:
1. RELATION:
   - "update": The new fact describes a state change, job change, preference update, or newer status that replaces the old one (e.g. switched company, moved cities, changed primary IDE).
   - "supplement": Both facts can happily coexist as concurrent truths (e.g. user knows Python AND also learned Rust).
   - "no_conflict": The two facts refer to separate orthogonal subjects.
2. REASON: A brief 1-sentence explanation of why the fact evolved.

Return valid JSON strictly matching:
{{
  "relation": "update" | "supplement" | "no_conflict",
  "reason": "string"
}}
"""

def _offline_heuristic_reconciliation(old_fact: str, new_fact: str) -> Dict[str, Any]:
    old_l = old_fact.lower()
    new_l = new_fact.lower()
    
    # Check for direct antonyms or temporal transition words
    transition_words = ["now", "switched", "changed", "moved", "quit", "joined", "instead", "no longer"]
    has_transition = any(w in new_l for w in transition_words)
    
    # Check for workplace/job shift
    if any(k in old_l for k in ["work", "company", "employed", "job", "office"]) and any(k in new_l for k in ["work", "company", "employed", "job", "office"]):
        return {
            "relation": "update",
            "reason": "Career/employment update replaces previous workplace fact."
        }
    # Check for city/residence shift
    if any(k in old_l for k in ["live", "located", "city", "house", "reside"]) and any(k in new_l for k in ["live", "located", "city", "house", "reside"]):
        return {
            "relation": "update",
            "reason": "Location/residence update supersedes previous living address."
        }
    if has_transition:
        return {
            "relation": "update",
            "reason": "Temporal transition detected in statement."
        }
        
    return {
        "relation": "supplement",
        "reason": "Both facts are treated as concurrent factual details."
    }

async def evaluate_evolution(
    existing: Dict[str, Any],
    new_topic: str,
    new_fact: str,
    new_category: str
) -> Dict[str, Any]:
    """Uses free-tier Gemini or offline heuristics to evaluate memory evolution."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _offline_heuristic_reconciliation(existing["fact"], new_fact)

    try:
        from google.genai import types
        client = await asyncio.to_thread(get_genai_client, api_key)
        
        prompt = RECONCILE_PROMPT.format(
            existing_fact=existing["fact"],
            existing_topic=existing["topic"],
            existing_category=existing.get("category", "general"),
            new_fact=new_fact,
            new_topic=new_topic,
            new_category=new_category
        )
        
        models = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
        for m in models:
            try:
                response = await client.aio.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                if response and response.text:
                    parsed = json.loads(response.text.strip())
                    if "relation" in parsed:
                        return parsed
            except Exception:
                continue
                
        return _offline_heuristic_reconciliation(existing["fact"], new_fact)
    except Exception as e:
        logger.warning(f"Error evaluating memory evolution: {e}")
        return _offline_heuristic_reconciliation(existing["fact"], new_fact)

async def reconcile_and_save_fact(
    topic: str,
    fact: str,
    category: str = "general",
    user_id: str = "Admin"
) -> Tuple[bool, str]:
    """
    Saves a fact while detecting and archiving any superseded historical facts.
    Returns (success, message_summary).
    """
    topic_clean = topic.strip().lower()
    fact_clean = fact.strip()
    category_clean = category.strip().lower()
    now = datetime.now().isoformat()
    
    if not topic_clean or not fact_clean:
        return False, "Empty topic or fact."

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Fetch active facts that might conflict
            cursor.execute("""
                SELECT id, category, topic, fact 
                FROM zenith_facts 
                WHERE user_id = ? AND (is_active IS NULL OR is_active = 1)
            """, (user_id,))
            active_facts = [dict(r) for r in cursor.fetchall()]
            
            # Look for candidate conflicts: same topic OR semantic word overlap
            candidate_conflicts = []
            new_words = set(re.findall(r'\b\w+\b', f"{topic_clean} {fact_clean}".lower()))
            
            for af in active_facts:
                if af["topic"] == topic_clean:
                    candidate_conflicts.append(af)
                    continue
                old_words = set(re.findall(r'\b\w+\b', f"{af['topic']} {af['fact']}".lower()))
                overlap = new_words.intersection(old_words)
                # Significant topic/context intersection
                if len(overlap) >= 2 or af["category"] == category_clean and len(overlap) >= 1:
                    candidate_conflicts.append(af)

            superseded_summaries = []
            for candidate in candidate_conflicts:
                res = await evaluate_evolution(candidate, topic_clean, fact_clean, category_clean)
                if res.get("relation") == "update":
                    reason = res.get("reason", "Superseded by newer factual update.")
                    # Mark old fact as superseded
                    cursor.execute("""
                        UPDATE zenith_facts 
                        SET is_active = 0, superseded_reason = ?, updated_at = ?
                        WHERE id = ?
                    """, (reason, now, candidate["id"]))
                    
                    # Log evolution event
                    cursor.execute("""
                        INSERT INTO zenith_memory_evolution_log (user_id, old_fact_id, old_fact, new_fact, reason, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, candidate["id"], candidate["fact"], fact_clean, reason, now))
                    
                    superseded_summaries.append(f"Archived prior belief: '{candidate['fact']}' ({reason})")

            # Insert or update the new fact as active
            cursor.execute("""
                INSERT INTO zenith_facts (user_id, category, topic, fact, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(user_id, topic) DO UPDATE SET
                    fact = excluded.fact,
                    category = excluded.category,
                    is_active = 1,
                    superseded_reason = NULL,
                    updated_at = excluded.updated_at
            """, (user_id, category_clean, topic_clean, fact_clean, now, now))
            conn.commit()

            ui_state.set_text(f"🧠 Truth Evolved: {topic_clean[:15]}")
            
            msg = f"Stored fact: [{topic_clean}] {fact_clean}."
            if superseded_summaries:
                msg += " " + " ".join(superseded_summaries)
            logger.info(f"Memory evolution complete for user {user_id}: {msg}")
            return True, msg

    except Exception as e:
        logger.error(f"Error in reconcile_and_save_fact: {e}")
        return False, str(e)

async def audit_all_memory_contradictions(user_id: str = "Admin") -> List[str]:
    """Scans and resolves any latent contradictions across active user memories."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, category, topic, fact 
                FROM zenith_facts 
                WHERE user_id = ? AND (is_active IS NULL OR is_active = 1)
                ORDER BY updated_at ASC
            """, (user_id,))
            facts = [dict(r) for r in cursor.fetchall()]

        if len(facts) < 2:
            return []

        resolved = []
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                f1 = facts[i]
                f2 = facts[j]
                
                # Check for topic match or high overlap
                words1 = set(re.findall(r'\b\w+\b', f"{f1['topic']} {f1['fact']}".lower()))
                words2 = set(re.findall(r'\b\w+\b', f"{f2['topic']} {f2['fact']}".lower()))
                if len(words1.intersection(words2)) >= 3:
                    eval_res = await evaluate_evolution(f1, f2["topic"], f2["fact"], f2["category"])
                    if eval_res.get("relation") == "update":
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("UPDATE zenith_facts SET is_active = 0, superseded_reason = ? WHERE id = ?", (eval_res.get("reason"), f1["id"]))
                            conn.commit()
                        resolved.append(f"Resolved contradiction: archived '{f1['fact']}' in favor of newer '{f2['fact']}'.")
                        break
        return resolved
    except Exception as e:
        logger.error(f"Error auditing memory contradictions: {e}")
        return []

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOL
# ==============================================================================

@function_tool()
async def reconcile_memory_evolution(
    context: RunContext,  # type: ignore
    topic: str,
    updated_fact: str,
    category: str = "general"
) -> str:
    """
    Updates or evolves a fact about Sir in long-term memory while automatically
    archiving any older, conflicting historical beliefs (The Ship of Theseus Principle).
    Use this when Sir updates his preferences, changes jobs, switches tools/stacks,
    or corrects past assumptions.

    Args:
        topic: The conceptual identifier (e.g. 'workplace', 'primary_ide', 'living_city').
        updated_fact: The new current ground truth to record permanently.
        category: Category: 'personal', 'preference', 'project', 'routine', or 'general'.
    """
    user_id = os.getenv("Zenith_USER_ID") or "Admin"
    success, msg = await reconcile_and_save_fact(topic, updated_fact, category, user_id)
    if success:
        return f"Epistemic memory evolution confirmed, Sir: {msg}"
    return f"Failed to evolve memory record due to: {msg}"
