"""
Stellar Engineering Command: User Interface
Handles CLI output, branding, and status messages.
"""

import os
from typing import Any
from rich.console import Console
from pytest_coverage_impact.constants import SENSORIA_BANNER


class SystemUI:
    """Handles visual telemetry and system announcements for Sensoria."""

    @staticmethod
    def announce_initialization(config: Any) -> None:
        """
        Prints the Sensoria status.
        - Banner: If Interactive TTY and Color enabled.
        - Colored Text: If Non-Interactive but Color enabled (CI/Logs).
        - Plain Text: If Color disabled (NO_COLOR) or fallback.
        - Silent: If quiet flags are set.
        """
        # 1. Check Silence
        is_quiet = config.option.quiet if hasattr(config.option, "quiet") else False
        is_verbose = config.option.verbose if hasattr(config.option, "verbose") else 0

        if not config.getoption("--coverage-impact") or (is_quiet or is_verbose == -1):
            return

        # 2. Check Color Capability
        use_color = not os.getenv("NO_COLOR")

        # 3. Determine Output
        try:
            console = Console()
            # JUSTIFICATION: Console wrapper is an implementation detail of UI
            if console.is_terminal and use_color:  # pylint: disable=clean-arch-delegation
                console.print(SENSORIA_BANNER)
            elif use_color:
                # User requested colored text instead of emoji icon
                console.print("[blue][SENSORIA] Calibrating impact sensors and telemetry...[/blue]")
            else:
                console.print("[SENSORIA] Calibrating impact sensors and telemetry...")

        # JUSTIFICATION: Fallback if console/rich fails early, prevent crash during startup
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    @staticmethod
    def announce_section(title: str) -> None:
        """Prints a section header."""
        console = Console()
        console.print(f"\n[bold blue]{title}[/bold blue]")
        console.print("=" * 60)

    @staticmethod
    def announce_progress(message: str) -> None:
        """Prints a progress message."""
        console = Console()
        console.print(f"[dim]{message}[/dim]")

    @staticmethod
    def announce_warning(message: str) -> None:
        """Prints a warning message."""
        console = Console()
        console.print(f"[yellow]⚠ Warning: {message}[/yellow]")

    @staticmethod
    def announce_error(message: str) -> None:
        """Prints an error message."""
        console = Console()
        console.print(f"\n[red]✗ Error: {message}[/red]")

    @staticmethod
    def announce_success(message: str) -> None:
        """Prints a success message."""
        console = Console()
        console.print(f"[green]✓[/green] {message}")
