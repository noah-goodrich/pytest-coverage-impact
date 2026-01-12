"""Progress monitoring with Rich formatting for coverage impact analysis"""

from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    TaskID,
)


class ProgressMonitor:
    """Progress monitor for coverage impact analysis steps"""

    def __init__(self, console: Optional[Console] = None, enabled: bool = True):
        """Initialize progress monitor

        Args:
            console: Rich Console instance (creates new if None)
            enabled: Whether to show progress (can be disabled for testing)
        """
        self.console = console or Console()
        self.enabled = enabled
        self.progress: Optional[Progress] = None

    def __enter__(self):
        """Context manager entry"""
        if self.enabled:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TextColumn("•"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
                console=self.console,
                transient=False,  # Keep progress visible after completion
            )
            self.progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.progress:
            self.progress.stop()

    def add_task(self, description: str, total: int = 0) -> Optional[TaskID]:
        """Add a new progress task

        Args:
            description: Description of the task
            total: Total number of items (0 for indeterminate)

        Returns:
            TaskID for updating progress, or None if disabled
        """
        if not self.enabled or not self.progress:
            return None
        return self.progress.add_task(description, total=total)

    def update(self, task_id: Optional[TaskID], advance: int = 1, description: Optional[str] = None):
        """Update progress for a task

        Args:
            task_id: Task ID from add_task
            advance: Amount to advance by
            description: Optional new description
        """
        if not self.enabled or not self.progress or task_id is None:
            return
        self.progress.update(task_id, advance=advance, description=description)

    def update_description(self, task_id: Optional[TaskID], description: str):
        """Update task description

        Args:
            task_id: Task ID from add_task
            description: New description
        """
        if not self.enabled or not self.progress or task_id is None:
            return
        self.progress.update(task_id, description=description)

    def complete_task(self, task_id: Optional[TaskID]):
        """Mark a task as complete

        Args:
            task_id: Task ID to complete
        """
        if not self.enabled or not self.progress or task_id is None:
            return
        self.progress.update(task_id, completed=self.progress.tasks[task_id].total)
