"""
Stateful, process-safe rate limiter for controlling requests to external APIs.

This rate limiter is designed to be robust for script-based execution by:
1. Persisting its state to a file, ensuring limits are respected across
   multiple script runs within the same day.
2. Using a file-based lock to prevent race conditions if multiple processes
   access the same state file.
3. Correctly handling timezones and Daylight Saving Time for daily resets.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Use zoneinfo for modern timezone handling (Python 3.9+)
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    # Fallback for Python < 3.9, though project likely uses newer versions.
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # type: ignore

from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Custom exception for when a rate limit is exceeded."""


class RateLimiter:
    """
    A stateful rate limiter that persists its state to disk.

    Attributes:
        rpm_limit (int): Requests per minute limit.
        rpd_limit (int): Requests per day limit.
        state_file (Path): File to store the rate limiter's state.
        lock_file (Path): File to use for process synchronization.
        timezone (ZoneInfo): The timezone for daily limit resets.
    """

    def __init__(
        self,
        rpm_limit: int,
        rpd_limit: int,
        state_file: Path,
        timezone_str: str = "America/Los_Angeles",
    ):
        if rpm_limit <= 0 and rpd_limit <= 0:
            raise ValueError("At least one rate limit (RPM or RPD) must be positive.")

        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.state_file = state_file
        self.lock_file = self.state_file.with_suffix(".lock")
        self.state: dict[str, Any] = {"timestamps": [], "daily_count": 0, "day_str": ""}

        try:
            self.timezone = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError:
            logger.error(f"Invalid timezone '{timezone_str}'. Defaulting to UTC.")
            self.timezone = ZoneInfo("UTC")

    def _load_state(self) -> None:
        """Load the rate limiter state from the JSON file."""
        if not self.state_file.exists():
            self._save_state()
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)
                # Basic validation
                if "timestamps" in loaded_state and "daily_count" in loaded_state:
                    self.state = loaded_state
                else:
                    logger.warning("Invalid state file format. Resetting state.")
                    self._reset_state()
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load state file, resetting. Error: {e}")
            self._reset_state()

    def _save_state(self) -> None:
        """Save the current state to the JSON file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f)
        except OSError as e:
            logger.error(f"Failed to save rate limiter state to {self.state_file}: {e}")

    def _reset_state(self) -> None:
        """Resets the state to its initial values."""
        self.state = {"timestamps": [], "daily_count": 0, "day_str": ""}

    def wait_if_needed(self) -> None:
        """
        Checks rate limits and waits if necessary before allowing the request.

        This method is process-safe using a file lock.

        Raises:
            RateLimitError: If the daily request quota has been exhausted.
        """
        if self.rpm_limit <= 0 and self.rpd_limit <= 0:
            return  # Both limits are disabled, do nothing.

        try:
            with FileLock(self.lock_file, timeout=10):
                self._load_state()
                now = datetime.now(self.timezone)
                now_utc_ts = now.timestamp()

                # --- Daily Limit Check and Reset ---
                if self.rpd_limit > 0:
                    current_day_str = now.strftime("%Y-%m-%d")
                    if self.state.get("day_str") != current_day_str:
                        logger.info(
                            f"New day ({current_day_str}). Resetting daily request count."
                        )
                        self.state["daily_count"] = 0
                        self.state["day_str"] = current_day_str

                    if self.state["daily_count"] >= self.rpd_limit:
                        msg = f"Daily rate limit of {self.rpd_limit} requests exhausted."
                        logger.error(msg)
                        raise RateLimitError(msg)

                # --- Per-Minute Limit Check ---
                if self.rpm_limit > 0:
                    # Prune timestamps older than 1 minute
                    one_minute_ago = now_utc_ts - 60
                    self.state["timestamps"] = [
                        t for t in self.state["timestamps"] if t > one_minute_ago
                    ]

                    if len(self.state["timestamps"]) >= self.rpm_limit:
                        oldest_request_ts = self.state["timestamps"][0]
                        wait_time = oldest_request_ts - one_minute_ago
                        if wait_time > 0:
                            logger.info(
                                f"RPM limit reached. Waiting {wait_time:.2f}s."
                            )
                            time.sleep(wait_time)
                            now_utc_ts = datetime.now(self.timezone).timestamp()

                # --- Record the new request ---
                self.state["timestamps"].append(now_utc_ts)
                if self.rpd_limit > 0:
                    self.state["daily_count"] += 1

                self._save_state()

        except Timeout:
            logger.error(
                "Could not acquire lock on rate limiter state file. "
                "Skipping rate limit check to avoid deadlock."
            )
