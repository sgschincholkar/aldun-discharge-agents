import os
from opentelemetry import trace as otel_trace
from arize.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation import TraceConfig

_instrumented = False


def init_tracing():
    """Initialise Arize AX tracing. Call once at app startup."""
    global _instrumented

    if _instrumented:
        return

    if not os.environ.get("ARIZE_API_KEY"):
        raise EnvironmentError("ARIZE_API_KEY is not set. Add it to your .env file.")

    if not os.environ.get("ARIZE_SPACE_ID"):
        raise EnvironmentError("ARIZE_SPACE_ID is not set. Add it to your .env file.")

    # register() sends traces to Arize AX — reads ARIZE_API_KEY and ARIZE_SPACE_ID from env
    tracer_provider = register(
        space_id=os.environ["ARIZE_SPACE_ID"],
        api_key=os.environ["ARIZE_API_KEY"],
        project_name="Aldun_Discharge_Agents",
        set_global_tracer_provider=True,
    )

    # Instrument OpenAI SDK with full input/output/message capture
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
