from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class OllamaClient:
    base_url: str
    model: str
    timeout_seconds: float = 120.0

    def generate(self, prompt: str) -> str:
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

        payload = response.json()
        return str(payload["response"]).strip()
