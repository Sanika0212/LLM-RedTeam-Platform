from config import settings
from integrations.base import BaseLLMClient


def get_llm_client(
    provider: str, model_id: str, api_endpoint: str = ""
) -> BaseLLMClient:
    """Factory to create the appropriate LLM client based on provider.

    For 'huggingface' and 'custom' providers the caller MUST supply a non-empty
    api_endpoint that points to an OpenAI-compatible inference server.
    Silently falling back to the OpenAI endpoint with the OpenAI key would
    produce metrics attributed to the wrong model entirely.
    """
    if provider == "openai":
        from integrations.openai_client import OpenAIClient
        return OpenAIClient(api_key=settings.OPENAI_API_KEY, model_id=model_id)
    elif provider == "anthropic":
        from integrations.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=settings.ANTHROPIC_API_KEY, model_id=model_id)
    elif provider in ("huggingface", "custom"):
        if not api_endpoint:
            raise ValueError(
                f"Provider '{provider}' requires a non-empty api_endpoint "
                "(e.g. an OpenAI-compatible HuggingFace Inference endpoint URL). "
                "Refusing to route to the OpenAI API with a different model name."
            )
        from integrations.openai_client import OpenAIClient
        api_key = getattr(settings, "HUGGINGFACE_API_KEY", "") or settings.OPENAI_API_KEY
        return OpenAIClient(
            api_key=api_key,
            model_id=model_id,
            base_url=api_endpoint,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
