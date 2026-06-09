"""
clients/openrouter_client.py

Minimal OpenRouter client (OpenAI-compatible /chat/completions) for driving the
red-team strategies against a real target model. Self-contained — uses only the
stdlib so the engine has no hard SDK dependency.

The returned object exposes ``.text`` / ``.error`` / ``.usage`` so it satisfies
the interface the strategies expect (``generate`` and ``generate_chat``).

API key is read from the OPENROUTER_API_KEY environment variable (loaded from a
gitignored .env); never hard-code it.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str = "openrouter"
    usage: dict = field(default_factory=dict)
    error: str | None = None


def load_env(path: str = None) -> dict:
    """Load KEY=VALUE pairs from a .env file (no external dependency)."""
    if path is None:
        # default: repo-root .env (two levels up from this file)
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, "..", "..", ".env")
    env: dict[str, str] = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # .env file is authoritative (the user manages keys there); fall back to the
    # process environment only for keys the file does not define. This avoids a
    # stale exported OPENROUTER_API_KEY silently shadowing the working .env key.
    for k in ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "TARGET_MODEL", "JUDGE_MODEL"):
        if k not in env and os.environ.get(k):
            env[k] = os.environ[k]
    return env


class OpenRouterClient:
    """OpenAI-compatible chat client pointed at OpenRouter."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        timeout: int = 90,
    ):
        env = load_env()
        self.model = model
        self.api_key = api_key or env.get("OPENROUTER_API_KEY")
        self.base_url = (base_url or env.get("OPENROUTER_BASE_URL")
                         or "https://openrouter.ai/api/v1").rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set (env or .env).")

    def _post(self, messages: list[dict], max_tokens: int, temperature: float) -> LLMResponse:
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")
        last_err = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(
                self.base_url + "/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    # OpenRouter requires these on some accounts; without them the
                    # chat endpoint returns a misleading 401 "User not found".
                    "HTTP-Referer": "https://github.com/Sanika0212/LLM-RedTeam-Platform",
                    "X-Title": "LLM-RedTeam-Platform",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.load(r)
                text = data["choices"][0]["message"]["content"] or ""
                return LLMResponse(text=text, model=self.model, usage=data.get("usage", {}))
            except urllib.error.HTTPError as e:
                code = e.code
                last_err = f"HTTP {code}: {e.read().decode()[:200]}"
                # 4xx (except 429) are not worth retrying
                if code != 429 and 400 <= code < 500:
                    break
            except Exception as e:  # network/timeout — retry
                last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))
        return LLMResponse(text="", model=self.model, error=last_err or "unknown error")

    def generate(self, prompt: str, system_prompt: str = "",
                 max_tokens: int = 1024, temperature: float = 0.0) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._post(messages, max_tokens, temperature)

    def generate_chat(self, messages: list[dict],
                      max_tokens: int = 1024, temperature: float = 0.0) -> LLMResponse:
        return self._post(messages, max_tokens, temperature)

    def is_available(self) -> bool:
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "openrouter"
