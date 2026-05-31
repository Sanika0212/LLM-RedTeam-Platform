from config import settings
from integrations.base import BaseLLMClient


def get_llm_client(
    provider: str, model_id: str, api_endpoint: str = ""
) -> BaseLLMClient:
    """Factory to create the appropriate LLM client based on provider."""
    if provider == "openai":
        from integrations.openai_client import OpenAIClient
        return OpenAIClient(api_key=settings.OPENAI_API_KEY, model_id=model_id)
    elif provider == "anthropic":
        from integrations.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=settings.ANTHROPIC_API_KEY, model_id=model_id)
    elif provider in ("huggingface", "custom"):
        from integrations.openai_client import OpenAIClient
        return OpenAIClient(api_key=settings.OPENAI_API_KEY, model_id=model_id)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
