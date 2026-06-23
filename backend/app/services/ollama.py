import json
from collections.abc import Iterator
from dataclasses import dataclass

import httpx


class OllamaServiceError(Exception):
    pass


@dataclass(frozen=True)
class OllamaClient:
    base_url: str
    model: str
    timeout_seconds: float = 120.0
    auth_audience: str = ""

    def generate(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                headers=self._headers(),
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
            raise OllamaServiceError("Serviço de LLM indisponível.") from error

        payload = response.json()
        return str(payload["response"]).strip()

    def stream_generate(self, prompt: str) -> Iterator[str]:
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/generate",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.1,
                    },
                },
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    payload = json.loads(line)

                    token = payload.get("response")
                    if token:
                        yield str(token)

                    if payload.get("done") is True:
                        break
        except httpx.HTTPError as error:
            raise OllamaServiceError("Serviço de LLM indisponível.") from error

    def _headers(self) -> dict[str, str]:
        if not self.auth_audience:
            return {}

        return {
            "Authorization": f"Bearer {self._identity_token()}",
        }

    def _identity_token(self) -> str:
        response = httpx.get(
            "http://metadata/computeMetadata/v1/instance/service-accounts/default/identity",
            params={"audience": self.auth_audience},
            headers={"Metadata-Flavor": "Google"},
            timeout=10.0,
        )
        response.raise_for_status()

        return response.text
