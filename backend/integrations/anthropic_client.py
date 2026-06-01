import anthropic

from integrations.base import BaseLLMClient, LLMResponse


class AnthropicClient(BaseLLMClient):
    provider_name = "anthropic"

    def is_available(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-ant-...")

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
                provider="anthropic",
                error="Anthropic API key not configured",
            )
        try:
            client = anthropic.Anthropic(api_key=self.api_key, timeout=60.0, max_retries=2)
            kwargs = {
                "model": self.model_id,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)
            text = response.content[0].text if response.content else ""
            return LLMResponse(
                text=text,
                model=self.model_id,
                provider="anthropic",
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw=response.model_dump(),
            )
        except Exception as e:
            return LLMResponse(
                text="",
                model=self.model_id,
                provider="anthropic",
                error=str(e),
            )
