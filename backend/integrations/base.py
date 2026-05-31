from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    error: str | None = None


class BaseLLMClient(ABC):
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a prompt to the LLM and return the response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the client has a valid API key configured."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
