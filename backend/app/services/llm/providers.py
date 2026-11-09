from typing import Dict, Any, List
import time
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.schemas.llm import LLMResponse
from app.core.exceptions import (
    ProviderAuthenticationFailure, ProviderRateLimit,
    ProviderTimeout, ProviderUnavailable, ProviderError
)

class LLMProvider:
    def __init__(self, name: str, api_key: str | None, model: str):
        self.name = name
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError

class GroqProvider(LLMProvider):
    def __init__(self):
        super().__init__("groq", settings.GROQ_API_KEY, settings.GROQ_MODEL)
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate(self, prompt: str) -> LLMResponse:
        if not self.api_key:
            raise ProviderAuthenticationFailure("Groq API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        start_time = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise ProviderTimeout("Groq request timed out")
            except httpx.RequestError as e:
                raise ProviderUnavailable(f"Groq request failed: {e}")
                
        latency = int((time.time() - start_time) * 1000)
        
        if response.status_code == 401:
            raise ProviderAuthenticationFailure("Groq authentication failed")
        elif response.status_code == 429:
            raise ProviderRateLimit("Groq rate limit exceeded")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"Groq server error: {response.status_code}")
        elif response.status_code != 200:
            raise ProviderError(f"Groq error: {response.text}")
            
        data = response.json()
        return LLMResponse(
            provider=self.name,
            model=self.model,
            content=data["choices"][0]["message"]["content"],
            input_tokens=data.get("usage", {}).get("prompt_tokens"),
            output_tokens=data.get("usage", {}).get("completion_tokens"),
            total_tokens=data.get("usage", {}).get("total_tokens"),
            latency_ms=latency,
            request_id=data.get("id"),
            fallback_used=False
        )

class GeminiProvider(LLMProvider):
    def __init__(self):
        super().__init__("gemini", settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate(self, prompt: str) -> LLMResponse:
        if not self.api_key:
            raise ProviderAuthenticationFailure("Gemini API key not configured")
            
        params = {"key": self.api_key}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        start_time = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.base_url, params=params, json=payload)
            except httpx.TimeoutException:
                raise ProviderTimeout("Gemini request timed out")
            except httpx.RequestError as e:
                raise ProviderUnavailable(f"Gemini request failed: {e}")
                
        latency = int((time.time() - start_time) * 1000)
        
        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthenticationFailure("Gemini authentication failed")
        elif response.status_code == 429:
            raise ProviderRateLimit("Gemini rate limit exceeded")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"Gemini server error: {response.status_code}")
        elif response.status_code != 200:
            raise ProviderError(f"Gemini error: {response.text}")
            
        data = response.json()
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            content = ""
            
        return LLMResponse(
            provider=self.name,
            model=self.model,
            content=content,
            latency_ms=latency,
            fallback_used=False
        )

class OpenRouterProvider(LLMProvider):
    def __init__(self):
        super().__init__("openrouter", settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL)
        self.base_url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"

    async def generate(self, prompt: str) -> LLMResponse:
        if not self.api_key:
            raise ProviderAuthenticationFailure("OpenRouter API key not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        start_time = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise ProviderTimeout("OpenRouter request timed out")
            except httpx.RequestError as e:
                raise ProviderUnavailable(f"OpenRouter request failed: {e}")
                
        latency = int((time.time() - start_time) * 1000)
        
        if response.status_code == 401:
            raise ProviderAuthenticationFailure("OpenRouter authentication failed")
        elif response.status_code == 429:
            raise ProviderRateLimit("OpenRouter rate limit exceeded")
        elif response.status_code >= 500:
            raise ProviderUnavailable(f"OpenRouter server error: {response.status_code}")
        elif response.status_code != 200:
            raise ProviderError(f"OpenRouter error: {response.text}")
            
        data = response.json()
        return LLMResponse(
            provider=self.name,
            model=self.model,
            content=data["choices"][0]["message"]["content"],
            input_tokens=data.get("usage", {}).get("prompt_tokens"),
            output_tokens=data.get("usage", {}).get("completion_tokens"),
            total_tokens=data.get("usage", {}).get("total_tokens"),
            latency_ms=latency,
            request_id=data.get("id"),
            fallback_used=False
        )
