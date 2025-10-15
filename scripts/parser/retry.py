"""Retry utilities with exponential backoff."""

import functools
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        # Final attempt failed, raise the exception
                        raise

                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** (attempt - 1))

                    # Log retry attempt (in production, use proper logging)
                    print(
                        f"Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )

                    time.sleep(delay)

            # Should never reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            return None  # pragma: no cover

        return wrapper  # type: ignore

    return decorator
