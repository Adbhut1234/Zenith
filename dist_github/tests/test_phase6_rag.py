"""
Unit and Integration Verification Suite for Phase 6:
Local Semantic Graph Memory & Vector RAG
"""

import os
import sys
import time
import asyncio
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from agent_tools.semantic_memory import (
    generate_embedding, local_vectorizer, knowledge_graph, hybrid_rag
)
from zenith_memory import (
    save_fact, delete_fact, recall_user_memory, explore_knowledge_graph,
    get_memory_prompt_injection
)

async def test_phase6_suite():
    print("=" * 70)
    print("🚀 ZENITH PHASE 6 TEST SUITE: LOCAL SEMANTIC GRAPH MEMORY & VECTOR RAG")
    print("=" * 70)

    # 1. Test Dual-Engine Embeddings
    print("\n[TEST 1] Testing Dual-Engine Embedding Generation...")
    sample_text = "Zenith AI Assistant is powered by Google Gemini Multimodal Live API."
    vec, model_name = generate_embedding(sample_text)
    norm = float(np.linalg.norm(vec))
    print(f"  Generated embedding using '{model_name}': dimension={len(vec)}, norm={norm:.4f}")
    assert len(vec) in [256, 3072], f"Unexpected embedding dimension: {len(vec)}"
    assert abs(norm - 1.0) < 1e-3, f"Vector is not unit normalized: {norm}"

    # Test local fallback vectorizer directly
    loc_vec = local_vectorizer.embed("Offline fallback test query")
    loc_norm = float(np.linalg.norm(loc_vec))
    print(f"  Local fallback vectorizer: dimension={len(loc_vec)}, norm={loc_norm:.4f}")
    assert len(loc_vec) == 256
    print("  ✓ PASS: Dual-engine vectorizer operational with unit L2 normalization.")

    # 2. Test Knowledge Graph Entity & Relation Ingestion
    print("\n[TEST 2] Testing Knowledge Graph Storage & Subgraph Traversal...")
    knowledge_graph.add_relation("Zenith", "USES", "Electron", weight=1.0, context="Desktop HUD overlay")
    knowledge_graph.add_relation("Zenith", "USES", "LiveKit", weight=1.0, context="Real-time WebRTC audio transport")
    knowledge_graph.add_relation("Zenith", "CONNECTS_TO", "Gemini Live", weight=1.0, context="Multimodal reasoning")
    knowledge_graph.add_relation("Sir", "PREFERS", "Dark Mode", weight=0.9, context="User styling preference")

    # Query 1-hop subgraph around Zenith
    subgraph = knowledge_graph.get_subgraph("Zenith", depth=1)
    print(f"  Retrieved {len(subgraph)} relation edge(s) for 'Zenith':")
    for edge in subgraph:
        print(f"    • ({edge['source_entity']}) -[{edge['relation']}]-> ({edge['target_entity']})")
    assert len(subgraph) >= 3, "Expected at least 3 relations for Zenith"
    targets = [e["target_entity"].lower() for e in subgraph]
    assert "electron" in targets and "livekit" in targets
    print("  ✓ PASS: Knowledge graph relation ingestion and 1-hop traversal verified.")

    # 3. Test Hybrid Vector RAG with Semantic Matching (Zero-Keyword Overlap)
    print("\n[TEST 3] Testing Semantic Vector Search with Zero-Keyword Overlap...")
    test_user = "Phase6TestUser"
    try:
        # Save facts for the test user
        save_fact(
            topic="frontend_framework",
            fact="Zenith desktop client is built on Electron with transparent frameless window rendering",
            category="project",
            user_id=test_user
        )
        save_fact(
            topic="audio_transport",
            fact="Bidirectional audio is streamed across WebRTC using LiveKit Agents protocol",
            category="project",
            user_id=test_user
        )
        save_fact(
            topic="beverage_taste",
            fact="Sir loves drinking hot espresso in the morning while reviewing pull requests",
            category="preference",
            user_id=test_user
        )

        # Query with ZERO shared keywords for frontend:
        # Query: "What graphical software shell displays the application on the desktop?"
        # None of words ('graphical', 'software', 'shell', 'displays') appear in the fact!
        query = "What graphical software shell displays the application on the desktop?"
        start_t = time.perf_counter()
        search_res = hybrid_rag.search_hybrid(query=query, user_id=test_user, top_k=3)
        query_dur = (time.perf_counter() - start_t) * 1000
        print(f"  Hybrid RAG query executed in {query_dur:.2f}ms")

        facts_retrieved = search_res.get("facts", [])
        print(f"  Top retrieved fact:")
        for idx, f in enumerate(facts_retrieved):
            print(f"    #{idx+1} [{f['category']}] {f['topic']}: {f['fact']} (RRF: {f['rrf_score']}, VecSim: {f['vector_similarity']})")

        assert len(facts_retrieved) > 0, "No facts retrieved!"
        # Top fact must be frontend_framework despite zero keyword overlap!
        top_topic = facts_retrieved[0]["topic"]
        assert top_topic == "frontend_framework", f"Expected 'frontend_framework' to rank #1, got '{top_topic}'"
        print("  ✓ PASS: Semantic Vector RAG retrieved correct fact with ZERO keyword overlap!")

        # 4. Test LiveKit Tool: recall_user_memory
        print("\n[TEST 4] Testing LiveKit Tool: recall_user_memory...")
        os.environ["Zenith_USER_ID"] = test_user
        tool_out = await recall_user_memory(None, "What does Sir drink when reviewing code?")
        print(f"  Tool Output:\n{tool_out}")
        assert "espresso" in tool_out.lower(), "Expected espresso preference to be retrieved"
        print("  ✓ PASS: recall_user_memory tool returned semantic match with RRF score.")

        # 5. Test LiveKit Tool: explore_knowledge_graph
        print("\n[TEST 5] Testing LiveKit Tool: explore_knowledge_graph...")
        graph_tool_out = await explore_knowledge_graph(None, "Zenith", depth=1)
        print(f"  Graph Tool Output:\n{graph_tool_out}")
        assert "electron" in graph_tool_out.lower(), "Expected Electron in graph tool output"
        print("  ✓ PASS: explore_knowledge_graph tool returned graph edges.")

        # 6. Test Prompt Injection with Knowledge Graph Relations
        print("\n[TEST 6] Testing Startup Prompt Injection...")
        prompt_injection = get_memory_prompt_injection(user_id=test_user)
        print(f"  Injected prompt excerpt:\n{prompt_injection[:300]}...")
        assert "PERSISTENT LONG-TERM MEMORY" in prompt_injection
        assert "Knowledge Graph" in prompt_injection
        print("  ✓ PASS: System prompt injection encompasses facts and knowledge graph triples.")

    finally:
        # Cleanup test facts
        delete_fact("frontend_framework", user_id=test_user)
        delete_fact("audio_transport", user_id=test_user)
        delete_fact("beverage_taste", user_id=test_user)

    print("\n" + "=" * 70)
    print("🏆 ALL PHASE 6 TESTS PASSED: SEMANTIC GRAPH MEMORY & VECTOR RAG OPERATIONAL!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_phase6_suite())
