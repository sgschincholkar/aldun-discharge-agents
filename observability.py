import os
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

    # Register tracer provider — do NOT use auto_instrument so we control config
    tracer_provider = register(
        project_name="Aldun_Discharge_Agents",
        auto_instrument=False,
    )

    # Explicitly instrument OpenAI with full input/output capture
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
