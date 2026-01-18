# FLEET SYNC: This file is managed by stellar-ui-kit. Do not edit directly.
import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

__stellar_version__ = "1.1.1"


@runtime_checkable
class TelemetryPort(Protocol):
    """Unified telemetry protocol for the fleet."""

    def handshake(self) -> None: ...

    def step(self, msg: str) -> None: ...

    def error(self, msg: str) -> None: ...

    def ask(self, prompt: str, default: str | None = None, password: bool = False) -> str: ...

    def confirm(self, prompt: str, default: bool = True) -> bool: ...

    def warning(self, msg: str) -> None: ...

    def debug(self, msg: str) -> None: ...


class ProjectTelemetry(TelemetryPort):
    """Unified telemetry for use cases."""

    __fleet_component__ = True

    def __init__(self, project_name: str, color: str, welcome_msg: str):
        self.project_name = project_name
        self.color = color
        self.welcome_msg = welcome_msg
        self.console = Console()
        self.log_file = Path(f"/tmp/{project_name.lower().replace('-', '_')}.log")

        # Setup logger
        self.logger = logging.getLogger(project_name)
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.log_file)
        # JUSTIFICATION: Logging configuration requires direct object manipulation
        fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))  # pylint: disable=clean-arch-demeter
        self.logger.addHandler(fh)

    def handshake(self):
        """Initial welcome banner."""
        self.console.print(
            Panel(
                Text(self.welcome_msg, style=f"bold {self.color}"),
                title=f"[bold {self.color}]{self.project_name}[/]",
                border_style=self.color,
            )
        )
        self.logger.info(f"Session started for {self.project_name}")

    def step(self, msg: str):
        """Log a successful step."""
        self.console.print(f"[{self.color}]•[/] {msg}")
        self.logger.info(msg)

    def error(self, msg: str):
        """Log an error."""
        self.console.print(f"[red]✖[/] [bold red]Error:[/] {msg}")
        self.logger.error(msg)

    def ask(self, prompt: str, default: str | None = None, password: bool = False) -> str:
        """Prompt user for input."""
        if password:
            return self.console.input(f"[{self.color}]?[/] {prompt}: ", password=True)
        resp = self.console.input(f"[{self.color}]?[/] {prompt} {f'({default})' if default else ''}: ")
        return resp.strip() or (default if default else "")

    def confirm(self, prompt: str, default: bool = True) -> bool:
        """Prompt user for confirmation."""
        return Confirm.ask(f"[{self.color}]?[/] {prompt}", default=default, console=self.console)

    def warning(self, msg: str):
        """Log a warning."""
        self.console.print(f"[yellow]![/] [bold yellow]Warning:[/] {msg}")
        self.logger.warning(msg)

    def debug(self, msg: str):
        """Log a debug message."""
        self.logger.debug(msg)
