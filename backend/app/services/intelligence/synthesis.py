import json
import logging
from typing import List, Dict, Any
from app.services.llm.router import ModelRouter

logger = logging.getLogger(__name__)

class SynthesisService:
    def __init__(self):
        self.router = ModelRouter()

    async def synthesize(self, user_query: str, execution_results: Dict[str, Any], context_messages: List[Dict[str, str]] = None) -> str:
        """
        Synthesize the final answer based on capability results.
        """
        context_str = ""
        if context_messages:
            context_str = "Conversation Context:\n"
            for m in context_messages:
                context_str += f"{m['role'].upper()}: {m['content']}\n"
                
        results_str = json.dumps(execution_results, indent=2, default=str)
        
        prompt = f"""
You are the ORCA Synthesis Agent. Your task is to provide a comprehensive, accurate, and evidence-grounded answer to the user's query based ONLY on the provided capability results.

{context_str}

User Query: "{user_query}"

Capability Results:
{results_str}

Rules:
1. Use ONLY the supplied evidence. Do not invent scientific measurements, coordinates, provider results, or citations.
2. If the data is unavailable or a capability failed, explicitly state that limitation (e.g. "Weather data was unavailable from the configured provider, so the assessment does not include current weather conditions").
3. Include important measurements and units.
4. Use evidence-grounded language (e.g., "Based on the retrieved data..."). Do not make absolute claims like "Definitely safe."
5. Provide a concise explanation of which agents/capabilities contributed.
"""

        response = await self.router.generate(prompt)
        return response.content.strip()
