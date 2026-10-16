"""Check the retry helper with fake functions (no Gemini calls).

Run:  python -m scripts.check_retry
"""
from google.genai import errors

from backend.utils.retry import call_with_retry


def make_flaky(code: int, failures: int):
    """Return a function that fails `failures` times with the given error code, then succeeds."""
    state = {"calls": 0}

    def flaky() -> str:
        state["calls"] += 1
        if state["calls"] <= failures:
            raise errors.APIError(code, {"error": {"message": "fake error"}})
        return "success"

    return flaky, state


def main() -> None:
    print("Case 1: 503 twice, then success (should retry and succeed)")
    flaky, state = make_flaky(503, 2)
    print(f"  result: {call_with_retry(flaky)} after {state['calls']} calls\n")

    print("Case 2: 400 error (should NOT retry)")
    flaky, state = make_flaky(400, 1)
    try:
        call_with_retry(flaky)
    except errors.APIError as error:
        print(f"  raised error {error.code} after {state['calls']} call\n")

    print("Case 3: 503 every time (should give up after all attempts)")
    flaky, state = make_flaky(503, 99)
    try:
        call_with_retry(flaky)
    except errors.APIError as error:
        print(f"  gave up with error {error.code} after {state['calls']} calls")


if __name__ == "__main__":
    main()
