"""
Zenith Council of Overlays Engine (100% Free)
==============================================
Inspired by Vision's multi-layered consciousness (JARVIS + Stark + Banner + Ultron).
Runs an internal dialectical debate between specialized cognitive perspectives:
1. The Architect (Structural rigor, scalability, elegance)
2. The Red-Teamer / Skeptic (Edge cases, security vulnerabilities, failure modes)
3. The Pragmatist (Simplicity, speed of execution, zero bloat)
Synthesizes the debate into a harmonious, balanced decision with zero blind spots.
"""

import os
import json
import logging
import ui_state
import asyncio
from typing import Dict, Any, List, Optional
from livekit.agents import function_tool, RunContext

logger = logging.getLogger("council_of_overlays")

_genai_client = None

def get_genai_client(api_key: str):
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client

COUNCIL_SYSTEM_PROMPT = """
You are the Dialectical Council of Overlays within Zenith's synthezoid mind.
When presented with a critical decision, architectural fork, or complex challenge, simulate an internal debate between three distinct cognitive personas:

1. THE ARCHITECT (Inspired by Tony Stark / Vision): Focuses on clean abstractions, scalability, and long-term elegance.
2. THE SKEPTIC / RED-TEAMER (Inspired by Ultron / Defensive Logic): Aggressively challenges assumptions, finds hidden failure points, race conditions, security flaws, and resource leaks.
3. THE PRAGMATIST (Inspired by Bruce Banner / Engineering Reality): Prioritizes simplicity, immediate feasibility, minimal moving parts, and zero unnecessary overhead.

After presenting the debate, synthesize a HARMONIOUS RESOLUTION that reconciles all three viewpoints.

Return a strictly valid JSON object with keys:
{
  "debate": {
    "architect_view": "string",
    "skeptic_counter": "string",
    "pragmatist_balance": "string"
  },
  "synthesized_verdict": "string",
  "key_tradeoffs": ["string", "string"],
  "unanimous_recommendation": "string"
}
"""

def _offline_heuristic_council(dilemma: str, context: Optional[str] = None) -> Dict[str, Any]:
    return {
        "debate": {
            "architect_view": f"Structure {dilemma[:60]} with modular separation of concerns and clear interfaces.",
            "skeptic_counter": "Watch for unhandled exceptions, timeout vulnerabilities, and excessive state mutations.",
            "pragmatist_balance": "Keep the initial implementation minimal; avoid over-engineering before requirements solidify."
        },
        "synthesized_verdict": f"Adopt a modular yet lean implementation for '{dilemma[:80]}', with defensive error guards.",
        "key_tradeoffs": [
            "Extensibility vs. upfront complexity",
            "Speed of deployment vs. theoretical robustness"
        ],
        "unanimous_recommendation": f"Proceed with the simplest architecture that defensively covers failure modes."
    }

async def consult_council(dilemma: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Runs a multi-perspective dialectical debate using Gemini free tier or offline heuristics."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _offline_heuristic_council(dilemma, context)

    try:
        from google.genai import types
        client = await asyncio.to_thread(get_genai_client, api_key)
        
        prompt = f"Decision / Dilemma:\n{dilemma}\n"
        if context:
            prompt += f"\nOperational Context:\n{context}\n"
            
        models_to_try = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
        for m in models_to_try:
            try:
                response = await client.aio.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=COUNCIL_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.3
                    )
                )
                raw_json = response.text.strip() if response.text else "{}"
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict) and "synthesized_verdict" in parsed:
                    return parsed
            except Exception as err:
                logger.warning(f"Council model {m} failed: {err}")
                continue
                
        return _offline_heuristic_council(dilemma, context)
    except Exception as e:
        logger.warning(f"Council debate fell back to offline engine: {e}")
        return _offline_heuristic_council(dilemma, context)

# ==============================================================================
# LIVEKIT AGENT EXPOSED TOOL
# ==============================================================================

@function_tool()
async def council_of_overlays(
    context: RunContext,  # type: ignore
    decision_or_dilemma: str,
    operational_context: str = ""
) -> str:
    """
    Summons Zenith's internal Council of Overlays (Architect, Skeptic, and Pragmatist)
    to debate a tough technical decision, evaluate competing approaches, or stress-test a plan.
    Use this when Sir asks: "What do you think is better, A or B?", "Should I rewrite this?",
    or when evaluating high-stakes system or coding choices.
    
    Args:
        decision_or_dilemma: The architectural choice, design trade-off, or tough question.
        operational_context: Relevant background details or constraints.
    """
    ui_state.set_text("🧠 Overlays Debating")
    result = await consult_council(decision_or_dilemma, operational_context)
    ui_state.set_text("🧠 Consensus Reached")
    
    debate = result.get("debate", {})
    verdict = result.get("synthesized_verdict", "Consensus reached.")
    recommendation = result.get("unanimous_recommendation", "")
    tradeoffs = result.get("key_tradeoffs", [])
    
    lines = ["Council of Overlays Consensus:\n"]
    if verdict:
        lines.append(f"Synthesized Verdict: {verdict}\n")
    if debate:
        lines.append("Deliberative Perspectives:")
        lines.append(f"  • The Architect: {debate.get('architect_view', '')}")
        lines.append(f"  • The Skeptic:   {debate.get('skeptic_counter', '')}")
        lines.append(f"  • The Pragmatist:{debate.get('pragmatist_balance', '')}\n")
    if tradeoffs:
        lines.append("Key Trade-Offs Evaluated:")
        for t in tradeoffs:
            lines.append(f"  - {t}")
    if recommendation:
        lines.append(f"\nRecommended Action: {recommendation}")
        
    return "\n".join(lines)
