from app.services.tracing import LangSmithTracer, TraceConfig


def test_tracer_runs_function_when_disabled() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=False,
            project_name="test-project",
            endpoint=None,
            api_key=None,
        )
    )

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={"input": "value"},
        metadata={"env": "test"},
        function=lambda: "ok",
    )

    assert result == "ok"


def test_tracer_runs_function_when_enabled_without_api_key() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=True,
            project_name="test-project",
            endpoint=None,
            api_key=None,
        )
    )

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={"input": "value"},
        metadata={"env": "test"},
        function=lambda: "ok",
    )

    assert result == "ok"


def test_tracer_propagates_function_error_when_disabled() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=False,
            project_name="test-project",
            endpoint=None,
            api_key=None,
        )
    )

    def fail() -> str:
        raise ValueError("boom")

    try:
        tracer.trace(
            name="test",
            run_type="chain",
            inputs={},
            metadata={},
            function=fail,
        )
    except ValueError as error:
        assert str(error) == "boom"
    else:
        raise AssertionError("Expected ValueError")


def test_tracer_continues_when_create_run_returns_none() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=True,
            project_name="test-project",
            endpoint=None,
            api_key="fake-key",
        )
    )

    class FakeClient:
        def create_run(self, *args: object, **kwargs: object) -> None:
            return None

    tracer.client = FakeClient()  # type: ignore[assignment]

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={},
        metadata={},
        function=lambda: "ok",
    )

    assert result == "ok"


def test_tracer_continues_when_create_run_fails() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=True,
            project_name="test-project",
            endpoint=None,
            api_key="fake-key",
        )
    )

    class FakeClient:
        def create_run(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("langsmith unavailable")

    tracer.client = FakeClient()  # type: ignore[assignment]

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={},
        metadata={},
        function=lambda: "ok",
    )

    assert result == "ok"
