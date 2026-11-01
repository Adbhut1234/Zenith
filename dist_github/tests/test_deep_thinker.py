import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure root directory is on python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from agent_tools.deep_thinker import reason_deeply

async def main():
    print("Testing Zenith Deep Thinker Cognitive Engine...")
    result = await reason_deeply(
        objective="Analyze how to optimize memory usage when parsing large 10GB log files in Python without hitting Out-Of-Memory errors."
    )
    print("\n--- Deep Thinker Output ---")
    print(f"Confidence: {result.get('confidence_score')}")
    print(f"Optimal Solution:\n{result.get('optimal_solution')}")
    print("\nAction Steps:")
    for i, s in enumerate(result.get('action_steps', []), 1):
        print(f"  {i}. {s}")
    print("\nIdentified Risks:")
    for r in result.get('identified_risks', []):
        print(f"  - {r}")
    print("\nSUCCESS: Deep Thinker operational.")

if __name__ == "__main__":
    asyncio.run(main())
