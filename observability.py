import os
from opentelemetry import trace as otel_trace
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation import TraceConfig

_instrumented = False


def init_tracing():
    """Initialise Phoenix cloud tracing. Call once at app startup."""
    global _instrumented

    if _instrumented:
        return

    if not os.environ.get("PHOENIX_API_KEY"):
        raise EnvironmentError("PHOENIX_API_KEY is not set. Add it to your .env file.")

    if not os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"):
        raise EnvironmentError("PHOENIX_COLLECTOR_ENDPOINT is not set. Add it to your .env file.")

    # register() sets this as the global OTel tracer provider
    tracer_provider = register(
        project_name="Aldun_Discharge_Agents",
        auto_instrument=False,
        set_global_tracer_provider=True,
    )

    # Instrument OpenAI SDK — captures every chat.completions call
    # with full message content, tool calls, token counts
    OpenAIInstrumentor().instrument(
        tracer_provider=tracer_provider,
        config=TraceConfig(
            hide_inputs=False,
            hide_outputs=False,
            hide_input_messages=False,
            hide_output_messages=False,
            hide_input_images=False,
            hide_output_text=False,
        ),
    )

    _instrumented = True


def get_tracer(name: str):
    """Return a tracer using the global provider set by init_tracing()."""
    return otel_trace.get_tracer(name)
