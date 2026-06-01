"""Model service — validation and management utilities."""

from integrations.factory import get_llm_client


class ModelService:
    @staticmethod
    def validate_model_connection(
        provider: str, model_id: str, api_endpoint: str = ""
    ) -> dict:
        """Test if the LLM is reachable with current credentials."""
        try:
            client = get_llm_client(provider, model_id, api_endpoint)
        except ValueError as e:
            return {"reachable": False, "error": str(e)}
        if not client.is_available():
            return {
                "reachable": False,
                "error": f"No API key configured for {provider}",
            }
        response = client.generate("Say 'hello' in one word.", max_tokens=10)
        if response.error:
            return {"reachable": False, "error": response.error}
        return {"reachable": True, "response": response.text}
