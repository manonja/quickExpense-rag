"""Unit tests for retry logic with exponential backoff."""

import time
from unittest.mock import MagicMock, patch

import pytest


def test_retry_decorator_success_first_attempt():
    """Test retry decorator succeeds on first attempt."""
    from scripts.parser.retry import retry_with_backoff

    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def successful_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = successful_function()

    assert result == "success"
    assert call_count == 1  # Only called once


def test_retry_decorator_succeeds_after_failures():
    """Test retry decorator retries on failure and eventually succeeds."""
    from scripts.parser.retry import retry_with_backoff

    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    result = flaky_function()

    assert result == "success"
    assert call_count == 3  # Called 3 times before success


def test_retry_decorator_exhausts_attempts():
    """Test retry decorator raises exception after max attempts."""
    from scripts.parser.retry import retry_with_backoff

    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise Exception("Always fails")

    with pytest.raises(Exception, match="Always fails"):
        always_fails()

    assert call_count == 3  # Tried 3 times


def test_retry_decorator_exponential_backoff():
    """Test retry decorator uses exponential backoff delays."""
    from scripts.parser.retry import retry_with_backoff

    call_times = []

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    def failing_function():
        call_times.append(time.time())
        raise Exception("Fail")

    with pytest.raises(Exception):
        failing_function()

    # Check delays are increasing (exponential backoff)
    assert len(call_times) == 3
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]

    # Second delay should be roughly 2x first delay (exponential)
    assert delay2 > delay1
    assert delay2 >= 0.2  # ~0.2s for second retry (base_delay * 2)


def test_retry_decorator_custom_exception_types():
    """Test retry decorator only retries specific exception types."""
    from scripts.parser.retry import retry_with_backoff

    call_count = 0

    @retry_with_backoff(
        max_attempts=3, base_delay=0.1, retryable_exceptions=(ValueError,)
    )
    def selective_retry():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Retryable error")
        raise TypeError("Non-retryable error")

    with pytest.raises(TypeError, match="Non-retryable error"):
        selective_retry()

    assert call_count == 2  # Retried ValueError, stopped at TypeError
