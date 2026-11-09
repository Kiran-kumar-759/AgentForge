from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LLMProviderStatus(BaseModel):
    provider: str
    role: str
    configured: bool
    available: bool

class ProvidersResponse(BaseModel):
    providers: List[LLMProviderStatus]

class LLMTestRequest(BaseModel):
    prompt: str

class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: int
    request_id: Optional[str] = None
    fallback_used: bool = False
    fallback_from_provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
