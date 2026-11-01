"""
Zenith Local Semantic Graph Memory & Vector RAG (Phase 6)
=========================================================
Implements:
1. Dual-Engine Vector Embeddings (Gemini gemini-embedding-001 with local TF-IDF n-gram fallback).
2. SQLite-backed binary vector storage & fast NumPy cosine similarity search.
3. Local Knowledge Graph (entities, typed relations, 1-hop and 2-hop subgraph traversal).
4. Hybrid Reciprocal Rank Fusion (RRF) combining vector similarity, lexical matching, and graph proximity.
"""

import os
import re
import json
import time
import math
import sqlite3
import logging
import asyncio
from typing import List, Dict, Tuple, Any, Optional
import numpy as np

logger = logging.getLogger("semantic_memory")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zenith_memory.db")

# -----------------------------------------------------------------------------
# Local Fallback Vectorizer (Zero-Cost, Offline, No External Dependencies)
# -----------------------------------------------------------------------------
class LocalHashingVectorizer:
    """
    Deterministic subword character n-gram + word hashing vectorizer.
    Produces dense 256-dimensional L2-normalized embeddings without any external API or weights.
    Used automatically if offline, missing API key, or during rate limits.
    """
    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        clean = text.lower().strip()
        words = re.findall(r'\b\w+\b', clean)

        for w in words:
            # Word hash
            h_word = abs(hash(w)) % self.dim
            vec[h_word] += 1.5

            # 3-gram and 4-gram character hashes
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    tri = w[i:i+3]
                    h_tri = abs(hash(tri)) % self.dim
                    vec[h_tri] += 0.8
            if len(w) >= 4:
                for i in range(len(w) - 3):
                    quad = w[i:i+4]
                    h_quad = abs(hash(quad)) % self.dim
                    vec[h_quad] += 0.5

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec


local_vectorizer = LocalHashingVectorizer(dim=256)


# -----------------------------------------------------------------------------
# Dual-Engine Embedding Generator
# -----------------------------------------------------------------------------
def generate_embedding(text: str) -> Tuple[np.ndarray, str]:
    """
    Generates embedding for text.
    First attempts Gemini gemini-embedding-001 (dim=3072).
    Falls back to local_vectorizer (dim=256) if unconfigured or on failure.
    Returns: (vector_np, model_name)
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            res = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text
            )
            if res and res.embeddings and len(res.embeddings) > 0:
                values = res.embeddings[0].values
                vec = np.array(values, dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 1e-6:
                    vec /= norm
                return vec, "gemini-embedding-001"
        except Exception as e:
            logger.debug(f"Gemini embedding fallback to local vectorizer: {e}")

    # Local fallback
    vec = local_vectorizer.embed(text)
    return vec, "local-hashing-v1"


# -----------------------------------------------------------------------------
# Database Schema Initialization
# -----------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_semantic_tables():
    """Initializes tables for embeddings, entities, and knowledge graph relations."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Vector embeddings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ref_type TEXT NOT NULL,       -- 'fact', 'history', 'custom'
                    ref_id INTEGER,
                    text_content TEXT NOT NULL,
                    vector BLOB NOT NULL,
                    model TEXT NOT NULL,
                    dimension INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Knowledge Graph Entities
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,    -- lowercase normalized identifier
                    display_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'concept', -- 'tech', 'person', 'project', 'preference'
                    description TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Knowledge Graph Relations (Directed Triples)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zenith_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_entity TEXT NOT NULL,
                    relation TEXT NOT NULL,        -- 'USES', 'PREFERS', 'WORKS_ON', 'PART_OF', 'REQUIRES'
                    target_entity TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    context TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_entity, relation, target_entity)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emb_ref ON zenith_embeddings(ref_type, ref_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_src ON zenith_relations(source_entity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_tgt ON zenith_relations(target_entity)")
            conn.commit()
            logger.info("Semantic vector & knowledge graph tables verified.")
    except Exception as e:
        logger.error(f"Error initializing semantic tables: {e}")


init_semantic_tables()


# -----------------------------------------------------------------------------
# Knowledge Graph Operations
# -----------------------------------------------------------------------------
class KnowledgeGraphEngine:
    """Manages nodes (entities) and directed edges (relations) in SQLite."""

    COMMON_RELATIONS = {
        "uses": "USES",
        "prefers": "PREFERS",
        "likes": "PREFERS",
        "works on": "WORKS_ON",
        "building": "WORKS_ON",
        "part of": "PART_OF",
        "belongs to": "PART_OF",
        "requires": "REQUIRES",
        "depends on": "DEPENDS_ON",
        "written in": "WRITTEN_IN",
        "created by": "CREATED_BY",
        "associated with": "ASSOCIATED_WITH"
    }

    @staticmethod
    def normalize_entity(name: str) -> str:
        return re.sub(r'[^\w\s-]', '', name).strip().lower()

    def add_entity(self, display_name: str, entity_type: str = "concept", description: str = "") -> int:
        norm = self.normalize_entity(display_name)
        if not norm:
            return 0
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO zenith_entities (name, display_name, entity_type, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        display_name = excluded.display_name,
                        entity_type = excluded.entity_type,
                        description = COALESCE(excluded.description, zenith_entities.description)
                """, (norm, display_name.strip(), entity_type, description, now))
                conn.commit()
                return cursor.lastrowid or 0
        except Exception as e:
            logger.error(f"Failed to upsert entity '{display_name}': {e}")
            return 0

    def add_relation(self, source: str, relation: str, target: str, weight: float = 1.0, context: str = "") -> bool:
        src_norm = self.normalize_entity(source)
        tgt_norm = self.normalize_entity(target)
        rel_clean = relation.strip().upper().replace(" ", "_")
        if not src_norm or not tgt_norm or not rel_clean:
            return False

        # Ensure both entities exist in entities table
        self.add_entity(source, "concept")
        self.add_entity(target, "concept")

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO zenith_relations (source_entity, relation, target_entity, weight, context, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_entity, relation, target_entity) DO UPDATE SET
                        weight = excluded.weight,
                        context = excluded.context
                """, (src_norm, rel_clean, tgt_norm, weight, context, now))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add relation {source} -[{rel_clean}]-> {target}: {e}")
            return False

    def extract_and_ingest_triples(self, text: str, default_subject: str = "Sir"):
        """
        Lightweight heuristic triple extractor for instant zero-shot graph ingestion.
        """
        lower = text.lower()
        extracted = []

        # Pattern 1: Subject uses/prefers/works on Object
        patterns = [
            (r'([\w\s]+?)\s+(?:uses|is using|built with)\s+([\w\s]+)', "USES"),
            (r'([\w\s]+?)\s+(?:prefers|favorite|likes)\s+([\w\s]+)', "PREFERS"),
            (r'([\w\s]+?)\s+(?:works on|is developing|is building)\s+([\w\s]+)', "WORKS_ON"),
            (r'([\w\s]+?)\s+(?:part of|belongs to|component of)\s+([\w\s]+)', "PART_OF"),
            (r'([\w\s]+?)\s+(?:depends on|requires)\s+([\w\s]+)', "DEPENDS_ON"),
        ]

        for pat, rel in patterns:
            matches = re.finditer(pat, lower)
            for m in matches:
                src = m.group(1).strip()
                tgt = m.group(2).strip()
                if len(src) < 40 and len(tgt) < 40 and len(src) > 1 and len(tgt) > 1:
                    self.add_relation(src, rel, tgt, context=text[:100])
                    extracted.append((src, rel, tgt))

        # Default subject attachment if personal preference
        if not extracted and ("i prefer" in lower or "my favorite" in lower or "i use" in lower):
            parts = re.split(r'i prefer|my favorite|i use', lower, maxsplit=1)
            if len(parts) > 1:
                obj = parts[1].strip(" :-,.").split(".")[0]
                if obj and len(obj) < 40:
                    self.add_relation(default_subject, "PREFERS", obj, context=text[:100])
                    extracted.append((default_subject, "PREFERS", obj))

        return extracted

    def get_subgraph(self, entity_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Retrieves 1-hop or 2-hop connected relations for a given entity.
        """
        norm = self.normalize_entity(entity_name)
        results = []
        visited_nodes = {norm}
        current_layer = [norm]

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                for _ in range(depth):
                    if not current_layer:
                        break
                    next_layer = []
                    placeholders = ",".join(["?"] * len(current_layer))
                    query = f"""
                        SELECT source_entity, relation, target_entity, weight, context
                        FROM zenith_relations
                        WHERE source_entity IN ({placeholders}) OR target_entity IN ({placeholders})
                    """
                    cursor.execute(query, current_layer + current_layer)
                    rows = cursor.fetchall()

                    for r in rows:
                        item = dict(r)
                        results.append(item)
                        for node in [item["source_entity"], item["target_entity"]]:
                            if node not in visited_nodes:
                                visited_nodes.add(node)
                                next_layer.append(node)
                    current_layer = next_layer

            # Deduplicate results
            seen = set()
            deduped = []
            for item in results:
                key = (item["source_entity"], item["relation"], item["target_entity"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(item)
            return deduped
        except Exception as e:
            logger.error(f"Error querying subgraph for '{entity_name}': {e}")
            return []


knowledge_graph = KnowledgeGraphEngine()


# -----------------------------------------------------------------------------
# Vector Index & Hybrid RAG Engine
# -----------------------------------------------------------------------------
class HybridSemanticRAG:
    """
    Blends lexical keyword search, dense cosine vector similarity,
    and knowledge graph traversal via Reciprocal Rank Fusion (RRF).
    """

    @staticmethod
    def index_fact(fact_id: int, topic: str, fact_text: str, category: str = "general"):
        """
        Computes and saves vector embedding for a fact, and ingests graph relations.
        """
        full_text = f"[{category}] {topic}: {fact_text}"
        vec, model_name = generate_embedding(full_text)
        vec_blob = vec.astype(np.float32).tobytes()
        dim = len(vec)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM zenith_embeddings WHERE ref_type = 'fact' AND ref_id = ?
                """, (fact_id,))
                cursor.execute("""
                    INSERT INTO zenith_embeddings (ref_type, ref_id, text_content, vector, model, dimension, created_at)
                    VALUES ('fact', ?, ?, ?, ?, ?, ?)
                """, (fact_id, full_text, vec_blob, model_name, dim, now))
                conn.commit()

            # Ingest graph triples
            knowledge_graph.extract_and_ingest_triples(fact_text)
            knowledge_graph.add_entity(topic, "topic", description=fact_text[:80])
        except Exception as e:
            logger.error(f"Failed to index fact #{fact_id}: {e}")

    @staticmethod
    def search_hybrid(
        query: str,
        user_id: str = "Admin",
        top_k: int = 5,
        vector_weight: float = 1.0,
        lexical_weight: float = 0.8,
        graph_weight: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes multi-stage hybrid search across SQLite facts and relations.
        """
        query_clean = query.strip()
        if not query_clean:
            return {"facts": [], "graph_context": []}

        # 1. Fetch all candidate facts from SQLite
        all_facts = []
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, category, topic, fact, updated_at
                    FROM zenith_facts
                    WHERE user_id = ?
                """, (user_id,))
                all_facts = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error loading facts for hybrid search: {e}")
            return {"facts": [], "graph_context": []}

        if not all_facts:
            return {"facts": [], "graph_context": []}

        fact_ids = [f["id"] for f in all_facts]
        fact_map = {f["id"]: f for f in all_facts}

        # 2. Stage 1: Lexical scoring (Substring & Token overlap)
        query_tokens = set(re.findall(r'\b\w+\b', query_clean.lower()))
        lexical_scores: Dict[int, float] = {}
        for f in all_facts:
            content = f"{f['topic']} {f['fact']} {f['category']}".lower()
            tokens = set(re.findall(r'\b\w+\b', content))
            overlap = len(query_tokens.intersection(tokens))
            sub_boost = 1.5 if query_clean.lower() in content else 0.0
            lexical_scores[f["id"]] = overlap + sub_boost

        # Sort lexical ranks
        lexical_ranked = sorted(fact_ids, key=lambda fid: lexical_scores.get(fid, 0), reverse=True)

        # 3. Stage 2: Vector Semantic Scoring
        query_vec, q_model = generate_embedding(query_clean)
        vector_scores: Dict[int, float] = {}

        # Fetch embeddings from DB
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                placeholders = ",".join(["?"] * len(fact_ids))
                cursor.execute(f"""
                    SELECT ref_id, vector, dimension, model
                    FROM zenith_embeddings
                    WHERE ref_type = 'fact' AND ref_id IN ({placeholders})
                """, fact_ids)
                emb_rows = cursor.fetchall()

                for r in emb_rows:
                    fid = r["ref_id"]
                    blob = r["vector"]
                    dim = r["dimension"]
                    f_model = r["model"]

                    # Only compare if model dimensions match
                    if dim == len(query_vec) and f_model == q_model:
                        f_vec = np.frombuffer(blob, dtype=np.float32)
                        cosine = float(np.dot(query_vec, f_vec))
                        vector_scores[fid] = max(0.0, cosine)
                    else:
                        # Fallback to local vector comparison on the fly
                        f_text = f"{fact_map[fid]['topic']}: {fact_map[fid]['fact']}"
                        loc_q = local_vectorizer.embed(query_clean)
                        loc_f = local_vectorizer.embed(f_text)
                        vector_scores[fid] = max(0.0, float(np.dot(loc_q, loc_f)))
        except Exception as e:
            logger.error(f"Vector search computation error: {e}")

        vector_ranked = sorted(fact_ids, key=lambda fid: vector_scores.get(fid, 0), reverse=True)

        # 4. Stage 3: Knowledge Graph Proximity Scoring
        graph_boost: Dict[int, float] = {fid: 0.0 for fid in fact_ids}
        connected_triples = []

        for token in query_tokens:
            if len(token) > 2:
                triples = knowledge_graph.get_subgraph(token, depth=1)
                if triples:
                    connected_triples.extend(triples)
                    for tr in triples:
                        nodes = [tr["source_entity"], tr["target_entity"]]
                        for fid, f in fact_map.items():
                            f_text = f"{f['topic']} {f['fact']}".lower()
                            if any(n in f_text for n in nodes):
                                graph_boost[fid] += tr.get("weight", 1.0) * 0.5

        graph_ranked = sorted(fact_ids, key=lambda fid: graph_boost.get(fid, 0), reverse=True)

        # 5. Reciprocal Rank Fusion (RRF)
        # RRF(d) = sum( w / (60 + rank) )
        rrf_scores: Dict[int, float] = {}
        k_const = 60.0

        for fid in fact_ids:
            score = 0.0
            # Lexical RRF component
            if fid in lexical_ranked and lexical_scores[fid] > 0:
                rank_lex = lexical_ranked.index(fid) + 1
                score += lexical_weight * (1.0 / (k_const + rank_lex))

            # Vector RRF component
            if fid in vector_ranked and vector_scores.get(fid, 0) > 0.15:
                rank_vec = vector_ranked.index(fid) + 1
                score += vector_weight * (1.0 / (k_const + rank_vec))

            # Graph RRF component
            if fid in graph_ranked and graph_boost.get(fid, 0) > 0:
                rank_graph = graph_ranked.index(fid) + 1
                score += graph_weight * (1.0 / (k_const + rank_graph))

            rrf_scores[fid] = score

        # Top K selection
        top_fids = sorted(rrf_scores.keys(), key=lambda fid: rrf_scores[fid], reverse=True)[:top_k]
        final_facts = []
        for fid in top_fids:
            if rrf_scores[fid] > 0 or len(top_fids) == 1:
                item = dict(fact_map[fid])
                item["rrf_score"] = round(rrf_scores[fid], 4)
                item["vector_similarity"] = round(vector_scores.get(fid, 0.0), 3)
                final_facts.append(item)

        # Deduplicate graph triples
        seen_triples = set()
        unique_graph = []
        for tr in connected_triples:
            key = (tr["source_entity"], tr["relation"], tr["target_entity"])
            if key not in seen_triples:
                seen_triples.add(key)
                unique_graph.append(tr)

        return {
            "facts": final_facts,
            "graph_context": unique_graph[:6]
        }


hybrid_rag = HybridSemanticRAG()
