import os
from phoenix.otel import register

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

    register(
        project_name="Aldun_Discharge_Agents",
        auto_instrument=True,
    )
    _instrumented = True
