"""Report generators for coverage impact analysis"""

from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table


class TerminalReporter:
    """Generate terminal output for coverage impact analysis"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def generate_report(self, impact_scores: List[Dict], top_n: int = 20) -> None:
        """Generate terminal report

        Args:
            impact_scores: List of function impact score dictionaries
            top_n: Number of top functions to display
        """
        if not impact_scores:
            self.console.print("[yellow]No functions found for analysis[/yellow]")
            return

        # Create table
        table = Table(title="Top Functions by Priority (Impact / Complexity)")
        table.add_column("Priority", justify="right", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Impact", justify="right", style="green")
        table.add_column("Complexity", justify="right", style="yellow")
        table.add_column("Coverage %", justify="right", style="yellow")
        table.add_column("File", style="blue")
        table.add_column("Function", style="magenta")

        for i, item in enumerate(impact_scores[:top_n], 1):
            priority = f"{i}"
            priority_score = f"{item.get('priority', item.get('impact_score', 0)):.2f}"
            impact = f"{item['impact']:.1f}"

            # Complexity with confidence interval if available
            complexity = item.get("complexity_score", 0.5)
            if "confidence" in item and item["confidence"] < 1.0:
                complexity_str = f"{complexity:.2f} [±{1-item['confidence']:.2f}]"
            else:
                complexity_str = f"{complexity:.2f}"

            coverage_pct = f"{item['coverage_percentage']*100:.1f}%" if item.get("coverage_percentage") else "N/A"

            # Truncate file path
            file_path = item["file"]
            if len(file_path) > 35:
                file_path = "..." + file_path[-32:]

            # Get function name
            func_name = item["function"]
            if "::" in func_name:
                func_name = func_name.split("::")[-1]
            if len(func_name) > 25:
                func_name = func_name[:22] + "..."

            table.add_row(priority, priority_score, impact, complexity_str, coverage_pct, file_path, func_name)

        self.console.print("\n")
        self.console.print(table)
        self.console.print(
            f"\n[dim]Showing top {min(top_n, len(impact_scores))} of {len(impact_scores)} functions[/dim]"
        )


class JSONReporter:
    """Generate JSON report for coverage impact analysis"""

    @staticmethod
    def generate_report(impact_scores: List[Dict], output_path: Path) -> None:
        """Generate JSON report

        Args:
            impact_scores: List of function impact score dictionaries
            output_path: Path to write JSON file
        """
        import json

        report = {
            "version": "1.0",
            "total_functions": len(impact_scores),
            "functions": impact_scores,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
