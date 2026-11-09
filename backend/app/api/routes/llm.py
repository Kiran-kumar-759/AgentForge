from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.llm import ProvidersResponse, LLMProviderStatus, LLMTestRequest, LLMResponse
from app.services.llm.providers import GroqProvider, GeminiProvider, OpenRouterProvider
from app.services.llm.router import ModelRouter
from app.db.session import get_db
from app.db.repositories.llm_request import LLMRequestRepository
from app.core.config import settings
from app.core.exceptions import ProviderError

router = APIRouter(tags=["llm"])

@router.get("/providers", response_model=ProvidersResponse)
async def get_providers():
    providers = []
    
    groq = GroqProvider()
    providers.append(LLMProviderStatus(
        provider=groq.name,
        role="primary",
        configured=bool(groq.api_key),
        available=bool(groq.api_key)
    ))
    
    gemini = GeminiProvider()
    providers.append(LLMProviderStatus(
        provider=gemini.name,
        role="fallback_1",
        configured=bool(gemini.api_key),
        available=bool(gemini.api_key)
    ))
    
    openrouter = OpenRouterProvider()
    providers.append(LLMProviderStatus(
        provider=openrouter.name,
        role="fallback_2",
        configured=bool(openrouter.api_key),
        available=bool(openrouter.api_key)
    ))
    
    return ProvidersResponse(providers=providers)

@router.post("/test", response_model=LLMResponse)
async def test_llm(request: LLMTestRequest, db: AsyncSession = Depends(get_db)):
    model_router = ModelRouter()
    repo = LLMRequestRepository(db)
    
    try:
        response = await model_router.generate(request.prompt)
        await repo.create(
            provider=response.provider,
            model=response.model,
            request_id=response.request_id,
            status="success",
            latency_ms=response.latency_ms,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
            fallback_used=response.fallback_used,
            fallback_from_provider=response.fallback_from_provider
        )
        return response
    except ProviderError as e:
        await repo.create(
            provider="unknown",
            model="unknown",
            status="error",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise
