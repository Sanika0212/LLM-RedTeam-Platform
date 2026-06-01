from openai import OpenAI

from integrations.base import BaseLLMClient, LLMResponse


class OpenAIClient(BaseLLMClient):
    provider_name = "openai"

    def __init__(self, api_key: str, model_id: str, base_url: str = ""):
        super().__init__(api_key=api_key, model_id=model_id)
        self.base_url = base_url or None  # None → SDK uses the default OpenAI endpoint

    def is_available(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-...")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                text="",
                model=self.model_id,
                provider="openai",
                error="OpenAI API key not configured",
            )
        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            choice = response.choices[0]
            return LLMResponse(
                text=choice.message.content or "",
                model=self.model_id,
                provider="openai",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                },
                raw=response.model_dump(),
            )
        except Exception as e:
            return LLMResponse(
                text="",
                model=self.model_id,
                provider="openai",
                error=str(e),
            )
