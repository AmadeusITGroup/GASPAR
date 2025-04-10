"""
Progress display for GASPAR CLI.
"""

import sys
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class ProgressState:
    """Progress state tracker."""
    total_steps: int = 0
    current_step: int = 0
    current_operation: str = ""
    start_time: float = 0.0


class ProgressDisplay:
    """CLI progress display."""

    def __init__(self, total_steps: int, show_spinner: bool = True):
        """
        Initialize progress display.

        Args:
            total_steps: Total number of steps
            show_spinner: Whether to show spinner animation
        """
        self.state = ProgressState(
            total_steps=total_steps,
            start_time=time.time()
        )
        self.show_spinner = show_spinner
        self._spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self._spinner_index = 0

    def update(self, operation: str, step: Optional[int] = None) -> None:
        """
        Update progress display.

        Args:
            operation: Current operation description
            step: Optional step number
        """
        if step is not None:
            self.state.current_step = step
        self.state.current_operation = operation
        self._render()

    def finish(self, success: bool = True) -> None:
        """
        Finish progress display.

        Args:
            success: Whether operation was successful
        """
        duration = time.time() - self.state.start_time
        status = "✓" if success else "✗"

        sys.stdout.write("\r" + " " * 80 + "\r")  # Clear line
        if success:
            print(f"{status} Completed in {duration:.1f}s")
        else:
            print(f"{status} Failed after {duration:.1f}s")

    def _render(self) -> None:
        """Render progress display."""
        # Calculate progress percentage
        progress = (self.state.current_step / self.state.total_steps) * 100

        # Create spinner animation
        if self.show_spinner:
            spinner = self._spinner_chars[self._spinner_index]
            self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        else:
            spinner = "•"

        # Format progress bar
        bar_width = 20
        filled = int((progress / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Format output
        output = f"\r{spinner} [{bar}] {progress:3.0f}% | {self.state.current_operation}"

        # Write to stdout
        sys.stdout.write(output)
        sys.stdout.flush()