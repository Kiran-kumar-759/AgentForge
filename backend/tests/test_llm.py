import pytest
from app.services.llm.providers import GroqProvider, GeminiProvider, OpenRouterProvider
from app.services.llm.router import ModelRouter
from app.schemas.llm import LLMResponse
from app.core.exceptions import ProviderAuthenticationFailure, ProviderError

@pytest.mark.asyncio
async def test_groq_primary(mocker):
    router = ModelRouter()
    
    mock_response = LLMResponse(
        provider="groq", model="llama3", content="Test", latency_ms=100
    )
    mocker.patch.object(router.providers[0], 'generate', return_value=mock_response)
    
    response = await router.generate("Hello")
    assert response.provider == "groq"
    assert response.fallback_used is False

@pytest.mark.asyncio
async def test_gemini_fallback(mocker):
    router = ModelRouter()
    
    mocker.patch.object(router.providers[0], 'generate', side_effect=ProviderAuthenticationFailure("Auth failed"))
    mock_response = LLMResponse(
        provider="gemini", model="gemini-pro", content="Test", latency_ms=100
    )
    mocker.patch.object(router.providers[1], 'generate', return_value=mock_response)
    
    response = await router.generate("Hello")
    assert response.provider == "gemini"
    assert response.fallback_used is True
    assert response.fallback_from_provider == "groq"

@pytest.mark.asyncio
async def test_openrouter_fallback(mocker):
    router = ModelRouter()
    
    mocker.patch.object(router.providers[0], 'generate', side_effect=ProviderAuthenticationFailure("Auth failed"))
    mocker.patch.object(router.providers[1], 'generate', side_effect=ProviderError("Rate limit"))
    mock_response = LLMResponse(
        provider="openrouter", model="claude", content="Test", latency_ms=100
    )
    mocker.patch.object(router.providers[2], 'generate', return_value=mock_response)
    
    response = await router.generate("Hello")
    assert response.provider == "openrouter"
    assert response.fallback_used is True
    assert response.fallback_from_provider == "gemini"

@pytest.mark.asyncio
async def test_all_fail(mocker):
    router = ModelRouter()
    
    mocker.patch.object(router.providers[0], 'generate', side_effect=ProviderError("Fail 1"))
    mocker.patch.object(router.providers[1], 'generate', side_effect=ProviderError("Fail 2"))
    mocker.patch.object(router.providers[2], 'generate', side_effect=ProviderError("Fail 3"))
    
    with pytest.raises(ProviderError):
        await router.generate("Hello")
