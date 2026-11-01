import os
import sqlite3
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from livekit.agents import function_tool, RunContext
from agent_tools.semantic_memory import hybrid_rag, knowledge_graph

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zenith_memory.db")

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

def init_memory_db() -> None:
    """Initialize SQLite tables for persistent facts and conversation history."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    topic TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, topic)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_user ON zenith_facts(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON zenith_history(user_id)")
            conn.commit()
            logging.info(f"Zenith persistent memory database initialized at {DB_PATH}")
    except Exception as e:
        logging.error(f"Failed to initialize memory database: {e}")

# Ensure DB is created on load
init_memory_db()

def save_fact(topic: str, fact: str, category: str = "general", user_id: str = "Admin") -> bool:
    """
    Save or update a persistent fact about the user.
    """
    topic_clean = topic.strip().lower()
    fact_clean = fact.strip()
    category_clean = category.strip().lower()
    now = datetime.now().isoformat()
    
    if not topic_clean or not fact_clean:
        return False
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO zenith_facts (user_id, category, topic, fact, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, topic) DO UPDATE SET
                    fact = excluded.fact,
                    category = excluded.category,
                    updated_at = excluded.updated_at
            """, (user_id, category_clean, topic_clean, fact_clean, now, now))
            conn.commit()
            
            # Index vector embedding and graph triples
            cursor.execute("SELECT id FROM zenith_facts WHERE user_id = ? AND topic = ?", (user_id, topic_clean))
            row = cursor.fetchone()
            if row:
                try:
                    hybrid_rag.index_fact(row[0], topic_clean, fact_clean, category_clean)
                except Exception as ex:
                    logging.warning(f"Vector indexing deferred: {ex}")
                    
            logging.info(f"Stored fact [{category_clean}] {topic_clean}: {fact_clean}")
            return True
    except Exception as e:
        logging.error(f"Error saving fact '{topic_clean}': {e}")
        return False

def delete_fact(topic: str, user_id: str = "Admin") -> bool:
    """Delete a specific stored fact by topic and its vector embedding."""
    topic_clean = topic.strip().lower()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM zenith_embeddings 
                WHERE ref_type = 'fact' AND ref_id IN (
                    SELECT id FROM zenith_facts WHERE user_id = ? AND topic = ?
                )
            """, (user_id, topic_clean))
            cursor.execute("DELETE FROM zenith_facts WHERE user_id = ? AND topic = ?", (user_id, topic_clean))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Error deleting fact '{topic_clean}': {e}")
        return False

def get_all_facts(user_id: str = "Admin") -> List[Dict[str, Any]]:
    """Retrieve all stored facts for the specified user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, topic, fact, updated_at FROM zenith_facts WHERE user_id = ? AND (is_active IS NULL OR is_active = 1) ORDER BY category, topic", (user_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logging.error(f"Error fetching facts: {e}")
        return []

def search_facts(query: str, user_id: str = "Admin") -> List[Dict[str, Any]]:
    """Search stored facts by keyword matching in topic or fact content."""
    query_clean = f"%{query.strip().lower()}%"
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, topic, fact, updated_at 
                FROM zenith_facts 
                WHERE user_id = ? AND (is_active IS NULL OR is_active = 1) AND (topic LIKE ? OR fact LIKE ? OR category LIKE ?)
                ORDER BY updated_at DESC
            """, (user_id, query_clean, query_clean, query_clean))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logging.error(f"Error searching facts with query '{query}': {e}")
        return []

def get_memory_prompt_injection(user_id: str = "Admin") -> str:
    """
    Produces a formatted string of known facts and preferences to inject into
    Zenith's system prompt instructions upon startup.
    """
    facts = get_all_facts(user_id)
    if not facts:
        return ""
    
    lines = ["\n### PERSISTENT LONG-TERM MEMORY (Facts Zenith knows about the User):"]
    categorized: Dict[str, List[str]] = {}
    for f in facts:
        cat = f.get("category", "general").capitalize()
        item = f"- **{f['topic'].title()}**: {f['fact']}"
        categorized.setdefault(cat, []).append(item)
        
    for cat, items in categorized.items():
        lines.append(f"**[{cat}]**")
        lines.extend(items)
        
    # Append top knowledge graph relations
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_entity, relation, target_entity FROM zenith_relations ORDER BY weight DESC LIMIT 8")
            rel_rows = cursor.fetchall()
            if rel_rows:
                lines.append("\n**[Knowledge Graph Relationships]**")
                for r in rel_rows:
                    lines.append(f"- ({r['source_entity']}) -[{r['relation']}]-> ({r['target_entity']})")
    except Exception:
        pass

    lines.append("Use these known facts naturally to personalize responses without unnecessarily repeating that you read them from memory.")
    return "\n".join(lines)

def record_chat_turn(role: str, content: str, user_id: str = "Admin") -> None:
    """Records a single conversation turn in SQLite history."""
    if not content or not content.strip():
        return
    now = datetime.now().isoformat()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO zenith_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, content.strip(), now)
            )
            conn.commit()
    except Exception as e:
        logging.error(f"Error recording chat turn: {e}")

_memory_quota_exhausted = False

async def extract_and_learn_facts(user_id: str, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Background worker that sends recent conversation messages to Gemini
    to extract facts and save them to SQLite.
    """
    global _memory_quota_exhausted
    if _memory_quota_exhausted:
        return []

    if not messages:
        return []
        
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []

    convo_text = ""
    for m in messages:
        r = m.get("role", "user")
        c = m.get("content", "")
        if "please greet me" in c:
            continue
        convo_text += f"{r.upper()}: {c}\n"

    if not convo_text.strip():
        return []

    try:
        from google.genai import types
        
        client = await asyncio.to_thread(get_genai_client, api_key)
        prompt = (
            "You are Zenith's memory extraction engine. Analyze the following conversation transcript.\n"
            "Identify any persistent facts, personal details, preferences, workflows, project context, or user instructions.\n"
            "Extract ONLY permanent/long-term facts about the USER (e.g. user's name, hobbies, stack, likes/dislikes, goals).\n"
            "Do NOT include temporary conversational chit-chat or tool commands.\n\n"
            "Return a strictly valid JSON array of objects with keys:\n"
            "- 'topic': concise label (e.g. 'favorite_music', 'job_title', 'preferred_editor', 'name')\n"
            "- 'fact': clear declarative statement of the fact\n"
            "- 'category': one of ['personal', 'preference', 'project', 'routine', 'general']\n\n"
            "If no persistent facts are found, return an empty array [].\n\n"
            f"Transcript:\n{convo_text}"
        )
        
        response = None
        last_mem_err = None
        for m in ["gemini-3.5-flash-lite", "gemini-2.5-flash"]:
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
                    break
            except Exception as m_err:
                last_mem_err = m_err
                logging.warning(f"Memory extraction model {m} failed: {m_err}, trying fallback...")
                continue

        if not response or not response.text:
            raise last_mem_err or RuntimeError("All memory extraction models failed.")
        
        raw_json = response.text.strip()
        if not raw_json:
            return []
            
        extracted = json.loads(raw_json)
        saved = []
        if isinstance(extracted, list):
            for item in extracted:
                t = item.get("topic")
                f = item.get("fact")
                c = item.get("category", "general")
                if t and f:
                    ok = await asyncio.to_thread(save_fact, topic=t, fact=f, category=c, user_id=user_id)
                    if ok:
                        saved.append(item)
                        
        if saved:
            logging.info(f"Learned and saved {len(saved)} new memories for {user_id}: {saved}")
        return saved
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            _memory_quota_exhausted = True
            logging.warning("Gemini 2.5 Flash free-tier quota exhausted. Pausing background fact extraction until next session to preserve system speed.")
        else:
            logging.error(f"Error during memory extraction: {e}")
        return []


# ==============================================================================
# LIVEKIT AGENT FUNCTION TOOLS (Exposed to Zenith Live)
# ==============================================================================

@function_tool()
async def remember_user_fact(
    context: RunContext,  # type: ignore
    topic: str,
    detail: str,
    category: str = "general"
) -> str:
    """
    Save a persistent piece of information, preference, habit, or rule about the user into Zenith's long-term memory.
    Use this when the user says "remember that...", "note down that I...", "keep in mind that...", or shares an important personal fact.
    
    Args:
        topic: A concise topic identifier (e.g. 'favorite_genre', 'programming_language', 'birthday', 'wake_up_time').
        detail: The full factual detail to remember permanently.
        category: Category of fact: 'preference', 'personal', 'project', 'routine', or 'general'.
    """
    user_id = os.getenv("Zenith_USER_ID") or "Admin"
    success = save_fact(topic=topic, fact=detail, category=category, user_id=user_id)
    if success:
        return f"Successfully saved to long-term memory: [{topic}] {detail}."
    else:
        return f"Could not save [{topic}] to memory due to a storage error."

@function_tool()
async def recall_user_memory(
    context: RunContext,  # type: ignore
    query: str
) -> str:
    """
    Search and retrieve facts, preferences, workflows, or project details stored in Zenith's long-term memory
    using hybrid semantic vector search and knowledge graph relations.
    Use this whenever Sir asks "What do you remember about...", "What are my preferences for...", or when you need past context.
    
    Args:
        query: Subject, concept, or natural language question to search for in memory.
    """
    user_id = os.getenv("Zenith_USER_ID") or "Admin"
    hybrid_res = await asyncio.to_thread(hybrid_rag.search_hybrid, query=query, user_id=user_id, top_k=5)
    facts = hybrid_res.get("facts", [])
    graph = hybrid_res.get("graph_context", [])

    if not facts and not graph:
        all_facts = get_all_facts(user_id)
        if all_facts:
            summary = "\n".join([f"- [{f['category']}] {f['topic']}: {f['fact']}" for f in all_facts[:6]])
            return f"No direct semantic match for '{query}'. Recent active facts:\n{summary}"
        return f"I don't have any saved memories related to '{query}' yet, Sir."

    lines = []
    if facts:
        lines.append(f"Retrieved {len(facts)} memory record(s):")
        for f in facts:
            lines.append(f"- [{f['category']}] {f['topic']}: {f['fact']} (Relevance: {f['rrf_score']:.3f})")

    if graph:
        lines.append("\nConnected Knowledge Graph Relations:")
        for rel in graph:
            lines.append(f"  • ({rel['source_entity']}) -[{rel['relation']}]-> ({rel['target_entity']})")

    return "\n".join(lines)

@function_tool()
async def explore_knowledge_graph(
    context: RunContext,  # type: ignore
    entity: str,
    depth: int = 1
) -> str:
    """
    Explore the semantic knowledge graph around an entity or topic to discover connections, dependencies, and preferences.
    Use this when Sir asks about relationships or dependencies between technologies, people, or preferences.
    
    Args:
        entity: The entity or keyword to traverse (e.g. 'Python', 'Electron', 'Sir', 'Zenith').
        depth: Graph traversal depth (1 for immediate relations, 2 for multi-hop graph neighborhood).
    """
    triples = await asyncio.to_thread(knowledge_graph.get_subgraph, entity_name=entity, depth=min(depth, 2))
    if not triples:
        return f"No knowledge graph relations recorded for '{entity}' yet, Sir."

    lines = [f"Knowledge Graph Subgraph for '{entity}' ({len(triples)} edges):"]
    for tr in triples:
        lines.append(f"  • ({tr['source_entity']}) -[{tr['relation']}]-> ({tr['target_entity']})")
    return "\n".join(lines)

@function_tool()
async def forget_user_fact(
    context: RunContext,  # type: ignore
    topic: str
) -> str:
    """
    Remove or forget a specific topic or fact from Zenith's long-term memory.
    Use when the user explicitly requests to remove, forget, or delete a saved fact.
    
    Args:
        topic: The topic name or key to remove from memory (e.g. 'favorite_food', 'old_project').
    """
    user_id = os.getenv("Zenith_USER_ID") or "Admin"
    deleted = delete_fact(topic=topic, user_id=user_id)
    if deleted:
        return f"I have forgotten and deleted [{topic}] from memory."
    else:
        return f"I could not find [{topic}] in saved memory to forget."
