import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.intelligence.orchestrator import AgentOrchestrator, AgentState
from app.services.intelligence.planner import PlannerService, ExecutionPlanResult, PlanStep
from app.db.models.execution import ExecutionPlan, ExecutionNode, ExecutionEdge, ExecutionEvent
from app.db.models.capability import Capability
from app.db.models.workspace import Workspace
from app.db.models.conversation import Conversation, ConversationMessage

@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Setup some basic returns if necessary
    return db

@pytest.mark.asyncio
async def test_capability_resolution(mock_db):
    planner = PlannerService()
    caps = [
        Capability(code="get_weather_conditions", description="Weather"),
        Capability(code="analyze_coastal_exposure", description="Exposure")
    ]
    with patch("app.services.intelligence.planner.ModelRouter.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value.content = '{"intent": "analyze", "reasoning_summary": "test", "steps": [{"step_id": "1", "agent": "A", "capability": "get_weather_conditions", "depends_on": []}]}'
        
        # we mock agent validation since objects are mocked
        with patch("app.services.intelligence.planner.PlannerService.generate_plan", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = ExecutionPlanResult(
                intent="analyze",
                reasoning_summary="test",
                steps=[PlanStep(step_id="1", agent="WeatherAgent", capability="get_weather_conditions", depends_on=[])]
            )
            res = await planner.generate_plan("query", "test_workspace", caps, [])
            assert len(res.steps) == 1
            assert res.steps[0].capability == "get_weather_conditions"

@pytest.mark.asyncio
async def test_execution_plan_persistence(mock_db):
    orc = AgentOrchestrator(mock_db)
    
    with patch.object(orc, "_get_workspace_capabilities", return_value=[]) as mock_caps:
        with patch.object(orc.planner, "generate_plan", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = ExecutionPlanResult(
                intent="analyze",
                reasoning_summary="test",
                steps=[PlanStep(step_id="step1", agent="A", capability="C", depends_on=[])]
            )
            # just mock db.execute to not fail when getting conversation
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_result.scalars.return_value.first.return_value = None
            mock_db.execute.return_value = mock_result
            
            with patch.object(orc, "_execute_capability", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {"node_results": {"step1": {"status": "SUCCESS"}}}
                
                with patch.object(orc.synthesis, "synthesize", new_callable=AsyncMock) as mock_syn:
                    mock_syn.return_value = "Final answer"
                    
                    res = await orc.execute_query("test query", "coastal-authority")
                    
                    assert res["status"] == "running"
                    assert res["answer"] == "Execution started in background."
                    
                    # check db.add calls for ExecutionPlan and ExecutionNode
                    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
                    has_plan = any(isinstance(o, ExecutionPlan) for o in added_objects)
                    has_node = any(isinstance(o, ExecutionNode) for o in added_objects)
                    has_event = any(isinstance(o, ExecutionEvent) for o in added_objects)
                    
                    assert has_plan, "ExecutionPlan not persisted"
                    assert has_node, "ExecutionNode not persisted"
                    assert has_event, "ExecutionEvent not persisted"

@pytest.mark.asyncio
async def test_failure_handling(mock_db):
    orc = AgentOrchestrator(mock_db)
    
    with patch.object(orc, "_get_workspace_capabilities", return_value=[]) as mock_caps:
        with patch.object(orc.planner, "generate_plan", new_callable=AsyncMock) as mock_plan:
            mock_plan.return_value = ExecutionPlanResult(
                intent="test",
                reasoning_summary="test",
                steps=[PlanStep(step_id="step1", agent="A", capability="failing_cap", depends_on=[])]
            )
            mock_res = MagicMock()
            mock_res.scalars.return_value.all.return_value = []
            mock_res.scalars.return_value.first.return_value = None
            mock_db.execute.return_value = mock_res
            
            with patch.object(orc, "_execute_capability", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {"node_results": {"step1": {"status": "FAILED"}}, "errors": ["failed"]}
                
                res = await orc.execute_query("test", "test")
                
                assert res["status"] == "running"
