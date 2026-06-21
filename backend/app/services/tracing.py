import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

from langsmith import Client
from pydantic import BaseModel

T = TypeVar("T")


@dataclass(frozen=True)
class TraceConfig:
    enabled: bool
    project_name: str
    endpoint: str | None
    api_key: str | None


class LangSmithTracer:
    def __init__(self, config: TraceConfig) -> None:
        self.config = config
        self.client = self._create_client()

    def trace(
        self,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any],
        function: Callable[[], T],
    ) -> T:
        if not self.config.enabled or self.client is None:
            return function()

        run_id = uuid4()
        start_time = datetime.now(UTC)
        start_perf = time.perf_counter()

        try:
            self.client.create_run(
                id=run_id,
                name=name,
                run_type=run_type,
                project_name=self.config.project_name,
                inputs=_json_safe(inputs),
                extra={
                    "metadata": _json_safe(metadata),
                },
                start_time=start_time,
            )
        except Exception:
            return function()

        try:
            output = function()
        except Exception as error:
            self._safe_update_run(
                run_id=run_id,
                error=str(error),
                end_time=datetime.now(UTC),
            )
            raise

        latency_ms = round((time.perf_counter() - start_perf) * 1000, 2)

        self._safe_update_run(
            run_id=run_id,
            outputs={
                "output": _json_safe(output),
                "latency_ms": latency_ms,
            },
            end_time=datetime.now(UTC),
        )

        return output

    def _safe_update_run(
        self,
        run_id: Any,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
        end_time: datetime | None = None,
    ) -> None:
        if self.client is None:
            return

        try:
            self.client.update_run(
                run_id,
                outputs=outputs,
                error=error,
                end_time=end_time,
            )
        except Exception:
            pass

    def _create_client(self) -> Client | None:
        if not self.config.enabled:
            return None

        if not self.config.api_key:
            return None

        try:
            return Client(
                api_key=self.config.api_key,
                api_url=self.config.endpoint,
            )
        except Exception:
            return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()

    if is_dataclass(value):
        return _json_safe(asdict(value))

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}

    if isinstance(value, list | tuple | set):
        return [_json_safe(item) for item in value]

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, str | int | float | bool) or value is None:
        return value

    return str(value)


def get_trace_config_from_env() -> TraceConfig:
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"

    return TraceConfig(
        enabled=tracing_enabled,
        project_name=os.getenv("LANGSMITH_PROJECT", "pipefy-rag-chat"),
        endpoint=os.getenv("LANGSMITH_ENDPOINT"),
        api_key=os.getenv("LANGSMITH_API_KEY"),
    )


def get_langsmith_tracer() -> LangSmithTracer:
    return LangSmithTracer(get_trace_config_from_env())
