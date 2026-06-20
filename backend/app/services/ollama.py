from dataclasses import dataclass

import httpx


class OllamaServiceError(Exception):
    pass


@dataclass(frozen=True)
class OllamaClient:
    base_url: str
    model: str
    timeout_seconds: float = 120.0

    def generate(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise OllamaServiceError("LLM service is unavailable") from error

        payload = response.json()
        return str(payload["response"]).strip()
