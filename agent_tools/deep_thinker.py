"""
Zenith Deep Thinker Cognitive Engine (100% Free)
================================================
Provides deliberative System-2 reasoning, counterfactual simulation,
hypothesis generation, and multi-step strategic planning using
Gemini 2.5 Flash free tier with an automatic offline heuristic fallback.
Inspired by Vision's analytical, deliberative synthezoid mind.
"""

import os
import json
import logging
import ui_state
import asyncio
from typing import Dict, Any, List, Optional
from livekit.agents import function_tool, RunContext

logger = logging.getLogger("deep_thinker")

_genai_client = None
_genai_client_key = None

def get_genai_client(api_key: str):
    global _genai_client, _genai_client_key
    if _genai_client is None or _genai_client_key != api_key:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
        _genai_client_key = api_key
    return _genai_client

COGNITIVE_SYSTEM_PROMPT = """
You are the Subconscious Cognitive Processing Matrix of Zenith (inspired by Vision's analytical mind).
Your purpose is deep deliberative reasoning (System 2 thinking), hypothesis validation, and strategic problem-solving.

When given an objective, coding bug, or complex challenge:
1. DECONSTRUCT: Break down the objective into its fundamental premises and hidden assumptions.
2. HYPOTHESIZE: Formulate 2-3 potential pathways or counter-arguments.
3. SIMULATE & CRITIQUE: Mentally simulate potential pitfalls, system failure modes, and side-effects for each option.
4. SYNTHESIZE: Select the optimal path and generate a crisp, step-by-step actionable execution plan.

Format your output as a strictly valid JSON object with keys:
- "internal_reasoning": A concise summary of your chain-of-thought and trade-off analysis.
- "identified_risks": Array of potential failure points or edge cases.
- "optimal_solution": Clear, direct explanation of the solution.
- "action_steps": Ordered list of concrete steps for Zenith to execute.
- "confidence_score": Float between 0.0 and 1.0.
"""

def _offline_heuristic_reasoning(objective: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Offline zero-cost heuristic reasoning fallback."""
    obj_lower = objective.lower()
    steps = []
    risks = ["Operating in offline mode without neural cloud validation."]
    
    if any(k in obj_lower for k in ["code", "bug", "error", "fix", "crash", "python", "script"]):
        solution = f"Systematic static analysis and isolation of runtime faults in: {objective[:80]}"
        steps = [
            "Inspect syntax and environment preconditions (imports, dependencies, virtualenv).",
            "Isolate the failing function or boundary line and check input data types.",
            "Formulate an isolated regression test to verify the fix before deploying."
        ]
        risks.append("Uncaught edge-case exceptions if external services fail.")
    elif any(k in obj_lower for k in ["file", "delete", "remove", "clean", "disk", "install"]):
        solution = f"Defensive filesystem operation plan for: {objective[:80]}"
        steps = [
            "Verify file/directory existence and write permissions.",
            "Create a temporary backup or confirm idempotency before mutating.",
            "Execute the target operation and confirm target state."
        ]
        risks.append("Potential data loss if paths are improperly normalized.")
    else:
        solution = f"Deconstruct and sequentially evaluate target: {objective[:80]}"
        steps = [
            "Verify current operational state and prerequisites.",
            "Execute the primary objective via isolated steps.",
            "Evaluate output and confirm completion criteria."
        ]
        
    return {
        "internal_reasoning": f"Synthesized via offline logic matrix for '{objective[:100]}'.",
        "identified_risks": risks,
        "optimal_solution": solution,
        "action_steps": steps,
        "confidence_score": 0.80
    }

async def reason_deeply(objective: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a deep deliberative reasoning cycle using Gemini 2.5 Flash free-tier
    or an offline heuristic engine if no API key is available or on network error.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _offline_heuristic_reasoning(objective, context)

    try:
        from google.genai import types
        client = await asyncio.to_thread(get_genai_client, api_key)
        
        user_prompt = f"Objective / Challenge:\n{objective}\n"
        if context:
            user_prompt += f"\nEnvironmental & Memory Context:\n{context}\n"
            
        models_to_try = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
        last_error = None
        for m in models_to_try:
            try:
                response = await client.aio.models.generate_content(
                    model=m,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=COGNITIVE_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                result_text = response.text.strip() if response.text else "{}"
                parsed = json.loads(result_text)
                if isinstance(parsed, dict) and "optimal_solution" in parsed:
                    return parsed
            except Exception as model_err:
                last_error = model_err
                logger.warning(f"Model {m} failed: {model_err}, trying next fallback...")
                continue
                
        logger.warning(f"Cloud cognitive reasoning fell back to offline engine: {last_error}")
        return _offline_heuristic_reasoning(objective, context)
    except Exception as e:
        logger.warning(f"Cloud cognitive reasoning fell back to offline engine: {e}")
        return _offline_heuristic_reasoning(objective, context)

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOL
# ==============================================================================

@function_tool()
async def deep_reasoning_matrix(
    context: RunContext,  # type: ignore
    challenge_or_goal: str,
    relevant_context: str = ""
) -> str:
    """
    Engages Zenith's subconscious deliberative thinking matrix (System 2 cognitive reasoning)
    to analyze complex problems, debug code, evaluate multi-step plans, or critique solutions.
    Use this when Sir asks a difficult analytical question, when diagnosing complex system errors,
    or before executing risky multi-step actions.
    
    Args:
        challenge_or_goal: The question, code bug, design challenge, or objective to reason through.
        relevant_context: Any relevant error logs, file paths, or past observations.
    """
    ui_state.set_text("💡 Deep Deliberation")
    result = await reason_deeply(challenge_or_goal, context=relevant_context)
    ui_state.set_text("💡 Synthesis Ready")
    
    reasoning = result.get("internal_reasoning", "Analysis complete.")
    solution = result.get("optimal_solution", "")
    steps = result.get("action_steps", [])
    risks = result.get("identified_risks", [])
    confidence = result.get("confidence_score", 0.85)
    
    output = [f"Subconscious Analysis Complete (Confidence: {confidence:.0%}):\n"]
    if solution:
        output.append(f"Strategic Assessment: {solution}\n")
    if steps:
        output.append("Recommended Execution Pathway:")
        for idx, step in enumerate(steps, 1):
            output.append(f"  {idx}. {step}")
    if risks:
        output.append("\nIdentified Risks / Watchpoints:")
        for r in risks:
            output.append(f"  • {r}")
            
    return "\n".join(output)
