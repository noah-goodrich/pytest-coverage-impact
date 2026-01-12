"""Report generators for coverage impact analysis"""

from pathlib import Path
from typing import Dict, List, Optional
import json
from rich.console import Console
from rich.table import Table


class TerminalReporter:
    """Generate terminal output for coverage impact analysis"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def generate_report(
        self, impact_scores: List[Dict], top_n: int = 20, totals: Optional[Dict] = None, files: Optional[Dict] = None
    ) -> None:
        """Generate terminal report

        Args:
            impact_scores: List of function impact score dictionaries
            top_n: Number of top functions to display
            totals: Optional dictionary with overall coverage totals
            files: Optional dictionary with per-file coverage data
        """
        if totals:
            self._print_summary(totals)

        if files:
            self._print_package_coverage(files)

        if not impact_scores:
            self.console.print("[yellow]No functions found for analysis[/yellow]")
            return

        self._print_impact_scores(impact_scores, top_n)

    def print_timings(self, timings: Dict) -> None:
        """Print timing summary

        Args:
            timings: Dictionary of timing metrics
        """
        if not timings:
            return

        timing_table = Table(title="Performance Summary", show_header=True, header_style="bold magenta")
        timing_table.add_column("Step", style="cyan", no_wrap=True)
        timing_table.add_column("Time", justify="right", style="green")
        timing_table.add_column("Percentage", justify="right", style="yellow")

        total = timings.get("total", 0)
        step_names = {
            "build_call_graph": "Build Call Graph",
            "load_coverage_data": "Load Coverage Data",
            "calculate_impact_scores": "Calculate Impact Scores",
            "estimate_complexity": "Estimate Complexity",
            "prioritize_functions": "Prioritize Functions",
        }

        for step_key, step_display in step_names.items():
            if step_key in timings:
                step_time = timings[step_key]
                if step_time > 0:
                    pct = (step_time / total * 100) if total > 0 else 0
                    timing_table.add_row(step_display, f"{step_time:.2f}s", f"{pct:.1f}%")

        if total > 0:
            self._add_table_section(timing_table)
            timing_table.add_row("[bold]TOTAL[/bold]", f"[bold]{total:.2f}s[/bold]", "100.0%", style="bold green")
            self.console.print("\n")
            self.console.print(timing_table)

    def _print_summary(self, totals: Dict) -> None:
        """Print overall coverage summary table."""
        summary = Table(title="Overall Coverage Summary", show_header=True, header_style="bold green")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", justify="right", style="magenta")

        cov_pct = totals.get("percent_covered", 0)
        summary.add_row("Total Statements", str(totals.get("num_statements", 0)))
        summary.add_row("Covered Statements", str(totals.get("covered_lines", 0)))
        summary.add_row("Missing Lines", str(totals.get("missing_lines", 0)))
        summary.add_row("Overall Coverage", f"{cov_pct:.1f}%")

        self.console.print(summary)
        self.console.print("\n")

    def _print_package_coverage(self, files: Dict) -> None:
        """Print coverage per package."""
        # Group by package
        package_cov: Dict[str, Dict] = {}
        for file_path, data in files.items():
            # Extract package name (e.g. packages/snowarch-core)
            parts = file_path.split("/")
            package_name = parts[0]
            if package_name == "packages" and len(parts) > 1:
                package_name = parts[1]

            if package_name not in package_cov:
                package_cov[package_name] = {"statements": 0, "covered": 0}

            f_summary = data.get("summary", {})
            package_cov[package_name]["statements"] += f_summary.get("num_statements", 0)
            package_cov[package_name]["covered"] += f_summary.get("covered_lines", 0)

        if package_cov:
            pkg_table = Table(title="Package Coverage Summary", show_header=True, header_style="bold cyan")
            pkg_table.add_column("Package", style="blue")
            pkg_table.add_column("Coverage", justify="right", style="green")
            pkg_table.add_column("Stats", justify="right", style="dim")

            for pkg, stats in sorted(package_cov.items()):
                if stats["statements"] > 0:
                    pct = (stats["covered"] / stats["statements"]) * 100
                    pkg_table.add_row(pkg, f"{pct:.1f}%", f"{stats['covered']}/{stats['statements']}")

            self.console.print(pkg_table)
            self.console.print("\n")

    def _print_impact_scores(self, impact_scores: List[Dict], top_n: int) -> None:
        """Print table of top impact functions."""
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
                complexity_str = f"{complexity:.2f} [±{1 - item['confidence']:.2f}]"
            else:
                complexity_str = f"{complexity:.2f}"

            coverage_pct = f"{item['coverage_percentage'] * 100:.1f}%" if item.get("coverage_percentage") else "N/A"

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

    @staticmethod
    def _add_table_section(table: Table) -> None:
        """Helper to add section to table (Friend/Stranger boundary)"""
        table.add_section()


class JSONReporter:
    """Generate JSON report for coverage impact analysis"""

    @staticmethod
    def generate_report(impact_scores: List[Dict], output_path: Path) -> None:
        """Generate JSON report

        Args:
            impact_scores: List of function impact score dictionaries
            output_path: Path to write JSON file
        """
        report = JSONReporter.get_report_data(impact_scores)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    @staticmethod
    def get_report_data(impact_scores: List[Dict]) -> Dict:
        """Get report data as a dictionary"""
        return {
            "version": "1.0",
            "total_functions": len(impact_scores),
            "functions": impact_scores,
        }
