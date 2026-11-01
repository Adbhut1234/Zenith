import asyncio
import os
import sys
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from agent_tools.council_of_overlays import consult_council
from agent_tools.dream_cycle import dream_cycle, get_proactive_insights
from agent_tools.working_memory import working_memory

async def main():
    print("Testing Council of Overlays and Dream Cycle...")
    
    # 1. Test Council of Overlays
    print("\n[1] Testing Dialectical Council of Overlays...")
    decision = await consult_council(
        dilemma="Should we rewrite our backend from JavaScript to Rust for maximum performance, or keep Node.js with caching?"
    )
    print("Council Verdict:\n", decision.get("synthesized_verdict"))
    print("Debate summary:")
    debate = decision.get("debate", {})
    print("  Architect:", debate.get("architect_view")[:80] + "...")
    print("  Skeptic:  ", debate.get("skeptic_counter")[:80] + "...")
    print("  Pragmatist:", debate.get("pragmatist_balance")[:80] + "...")
    assert "synthesized_verdict" in decision
    print("PASS: Council of Overlays dialectic functional.")

    # 2. Test Dream Cycle
    print("\n[2] Testing Dream Cycle Proactive Ambient Synthesis...")
    # Simulate an unresolved clipboard error in working memory
    working_memory.record_ambient_signal("clipboard_error", "TypeError: Cannot read properties of undefined (reading 'map') at line 42")
    
    # Run a single synthesis cycle
    await dream_cycle._synthesize_unresolved_ambient()
    insights = get_proactive_insights()
    print(f"Generated proactive insights: {len(insights)}")
    if insights:
        print(f"  Issue: {insights[0]['issue']}")
        print(f"  Proactive Fix: {insights[0]['fix']}")
        
    summary = working_memory.get_summary()
    assert "Dream Cycle" in summary or len(insights) > 0
    print("PASS: Dream Cycle idle synthesis functional.")
    
    print("\nSUCCESS: Step 4 and Step 5 verified.")

if __name__ == "__main__":
    asyncio.run(main())
