import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.llm.router import ModelRouter
from app.db.models.capability import Capability
from app.db.models.workspace import Workspace

logger = logging.getLogger(__name__)

class PlanStep(BaseModel):
    step_id: str
    agent: str
    capability: str
    depends_on: List[str] = []

class ExecutionPlanResult(BaseModel):
    intent: str
    reasoning_summary: str
    steps: List[PlanStep]

class PlannerService:
    def __init__(self):
        self.router = ModelRouter()

    async def generate_plan(
        self, 
        user_query: str, 
        workspace_code: str,
        available_capabilities: List[Capability],
        context_messages: List[Dict[str, str]] = None
    ) -> ExecutionPlanResult:
        
        # Build capability list text
        caps_text = ""
        for c in available_capabilities:
            agent_codes = [m.agent.code for m in c.agent_mappings]
            agent_str = ", ".join(agent_codes)
            caps_text += f"- Capability: {c.code}\n  Agent: {agent_str}\n  Description: {c.description}\n\n"
            
        context_str = ""
        if context_messages:
            context_str = "Conversation Context:\n"
            for m in context_messages:
                context_str += f"{m['role'].upper()}: {m['content']}\n"
            
        prompt = f"""
You are the ORCA Planner Agent. Your task is to interpret a user query within the '{workspace_code}' workspace and create an execution plan using ONLY the provided capabilities.

{context_str}

User Query: "{user_query}"

Available Capabilities:
{caps_text}

Rules:
1. You must output valid JSON only.
2. The JSON must match this structure exactly:
{{
  "intent": "<short intent name>",
  "reasoning_summary": "<brief reasoning>",
  "steps": [
    {{
      "step_id": "<unique_step_id>",
      "agent": "<agent_code from the capability>",
      "capability": "<capability_code>",
      "depends_on": ["<step_id of dependency>"]
    }}
  ]
}}
3. DO NOT invent capabilities or agents. Only use those listed above.
4. If steps can run in parallel (no data dependency), their `depends_on` array should be empty.
5. If a step relies on the output of another, list the parent step_id in `depends_on`.
6. DO NOT include markdown formatting like ```json ... ```, just output the raw JSON string.
"""

        response = await self.router.generate(prompt)
        content = response.content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        try:
            plan_dict = json.loads(content)
            result = ExecutionPlanResult(**plan_dict)
        except Exception as e:
            logger.error(f"Failed to parse planner output: {e}\nOutput: {content}")
            raise ValueError("Planner generated invalid JSON structure")
            
        # Validate plan against provided capabilities
        valid_cap_codes = {c.code for c in available_capabilities}
        for step in result.steps:
            step.capability = step.capability.lower()
            if step.capability not in valid_cap_codes:
                raise ValueError(f"Planner hallucinated capability: {step.capability}")
                
            # Verify agent is mapped
            cap_obj = next((c for c in available_capabilities if c.code == step.capability), None)
            if cap_obj:
                valid_agents = {m.agent.code for m in cap_obj.agent_mappings}
                if step.agent not in valid_agents:
                    raise ValueError(f"Planner assigned wrong agent '{step.agent}' for capability '{step.capability}'")
                    
        return result

    async def generate_replan(
        self,
        user_query: str,
        workspace_code: str,
        available_capabilities: List[Capability],
        completed_nodes: List[Dict[str, str]],
        failed_nodes: List[Dict[str, str]],
        context_messages: List[Dict[str, str]] = None
    ) -> ExecutionPlanResult:
        caps_text = ""
        for c in available_capabilities:
            agent_codes = [m.agent.code for m in c.agent_mappings]
            agent_str = ", ".join(agent_codes)
            caps_text += f"- Capability: {c.code}\n  Agent: {agent_str}\n  Description: {c.description}\n\n"
            
        context_str = ""
        if context_messages:
            context_str = "Conversation Context:\n"
            for m in context_messages:
                context_str += f"{m['role'].upper()}: {m['content']}\n"

        completed_str = json.dumps(completed_nodes, indent=2)
        failed_str = json.dumps(failed_nodes, indent=2)

        prompt = f"""
You are the ORCA Planner Agent. Your task is to REPLAN an execution that has partially failed.
You must interpret the user query within the '{workspace_code}' workspace and create a replacement execution plan using ONLY the provided capabilities.

{context_str}

User Query: "{user_query}"

The previous plan failed. Here is the execution summary:
Completed Nodes:
{completed_str}

Failed Nodes:
{failed_str}

Available Capabilities:
{caps_text}

Rules:
1. Output valid JSON exactly matching the structure below.
2. DO NOT invent capabilities or agents. Only use those listed above.
3. If a capability failed, DO NOT try to use it again. Find an alternative path if possible, or omit it if the intent can still be partially fulfilled.
4. If a previously completed capability is still needed in the new plan, you MUST include it again. The system will reuse its previous output automatically.
5. If steps can run in parallel, their `depends_on` array should be empty.
6. JSON Structure:
{{
  "intent": "<short intent name>",
  "reasoning_summary": "<brief reasoning for replan>",
  "steps": [
    {{
      "step_id": "<unique_step_id>",
      "agent": "<agent_code from the capability>",
      "capability": "<capability_code>",
      "depends_on": ["<step_id of dependency>"]
    }}
  ]
}}
"""
        response = await self.router.generate(prompt)
        content = response.content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        try:
            plan_dict = json.loads(content)
            result = ExecutionPlanResult(**plan_dict)
        except Exception as e:
            logger.error(f"Failed to parse replanner output: {e}\nOutput: {content}")
            raise ValueError("Replanner generated invalid JSON structure")
            
        valid_cap_codes = {c.code for c in available_capabilities}
        for step in result.steps:
            step.capability = step.capability.lower()
            if step.capability not in valid_cap_codes:
                raise ValueError(f"Replanner hallucinated capability: {step.capability}")
                
            cap_obj = next((c for c in available_capabilities if c.code == step.capability), None)
            if cap_obj:
                valid_agents = {m.agent.code for m in cap_obj.agent_mappings}
                if step.agent not in valid_agents:
                    raise ValueError(f"Replanner assigned wrong agent '{step.agent}' for capability '{step.capability}'")
                    
        return result
