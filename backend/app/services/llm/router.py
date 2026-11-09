from app.services.llm.providers import GroqProvider, GeminiProvider, OpenRouterProvider
from app.schemas.llm import LLMResponse
from app.core.exceptions import ProviderError, ProviderAuthenticationFailure
from app.core.logging import logger

class ModelRouter:
    def __init__(self):
        self.providers = [
            GroqProvider(),
            GeminiProvider(),
            OpenRouterProvider()
        ]

    async def generate(self, prompt: str) -> LLMResponse:
        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                response = await provider.generate(prompt)
                if i > 0:
                    response.fallback_used = True
                    response.fallback_from_provider = self.providers[i-1].name
                return response
            except ProviderAuthenticationFailure as e:
                logger.warning(f"Provider {provider.name} auth failed: {e}. Falling back.")
                last_error = e
            except ProviderError as e:
                logger.warning(f"Provider {provider.name} failed: {e}. Falling back.")
                last_error = e
            except Exception as e:
                logger.warning(f"Provider {provider.name} unexpected error: {e}. Falling back.")
                last_error = e

        raise ProviderError(f"All providers failed. Last error: {last_error}")
