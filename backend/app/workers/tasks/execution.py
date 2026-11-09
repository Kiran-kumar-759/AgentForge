import asyncio
import logging
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.intelligence.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

def run_async(coro):
    """Helper to run async functions in Celery task."""
    return asyncio.run(coro)

@celery_app.task(bind=True, name="agent.execution.run")
def run_agent_execution(self, execution_id: str):
    logger.info(f"Starting background execution for {execution_id}")
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            orchestrator = AgentOrchestrator(db)
            await orchestrator.run_execution(execution_id)
            
    try:
        run_async(_execute())
        logger.info(f"Finished background execution for {execution_id}")
    except Exception as e:
        logger.error(f"Error in background execution {execution_id}: {e}")
        raise e
