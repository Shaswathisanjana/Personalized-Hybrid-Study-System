from unittest.mock import Mock

from google.genai import errors

from app.learning_agent.reassessment_generator import (
    ReassessmentGenerator,
)


# ============================================================
# CREATE GENERATOR WITHOUT CALLING REAL GEMINI
# ============================================================

generator = object.__new__(
    ReassessmentGenerator
)

generator.model_name = (
    "gemini-3.1-flash-lite-preview"
)

generator.MAX_API_RETRIES = 3

# No waiting during this test.
generator.RETRY_DELAY_SECONDS = 0


# ============================================================
# CREATE FAKE GEMINI CLIENT
# ============================================================

fake_client = Mock()

generator.client = fake_client


# ============================================================
# SIMULATE GEMINI 503
# ============================================================

server_error = errors.ServerError(
    503,
    {
        "error": {
            "code": 503,
            "message": (
                "This model is currently "
                "experiencing high demand."
            ),
            "status": "UNAVAILABLE",
        }
    },
    None,
)


fake_client.models.generate_content.side_effect = (
    server_error
)


# ============================================================
# RUN TEST
# ============================================================

print(
    "========== API FAILURE TEST =========="
)


try:

    generator._call_gemini_with_retry(
        "Generate a reassessment question."
    )

    raise AssertionError(
        "Expected RuntimeError was not raised."
    )


except RuntimeError as error:

    print(
        "\nControlled error caught:"
    )

    print(error)


# ============================================================
# VERIFY RETRIES
# ============================================================

call_count = (
    fake_client
    .models
    .generate_content
    .call_count
)


print(
    "\nGemini call attempts:",
    call_count,
)


assert call_count == 3


print(
    "\n========== API FAILURE TEST PASSED =========="
)