#!/usr/bin/env python3
"""Performance test for coverage impact analysis with detailed timing"""

import sys
import time
import traceback
from pathlib import Path
from typing import Dict

# Add project to path before other imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Import all dependencies at top
# JUSTIFICATION: Configures system path before import
from rich.console import Console  # noqa: E402 # pylint: disable=wrong-import-position

# JUSTIFICATION: Configures system path before import
from rich.table import Table  # noqa: E402 # pylint: disable=wrong-import-position

# JUSTIFICATION: Configures system path before import
from pytest_coverage_impact.logic.analyzer import CoverageImpactAnalyzer  # noqa: E402 # pylint: disable=wrong-import-position

# JUSTIFICATION: Configures system path before import
from pytest_coverage_impact.gateways.call_graph import build_call_graph  # noqa: E402 # pylint: disable=wrong-import-position

# JUSTIFICATION: Configures system path before import
from pytest_coverage_impact.core.impact_calculator import (  # noqa: E402 # pylint: disable=wrong-import-position
    ImpactCalculator,
    load_coverage_data,
)

# JUSTIFICATION: Configures system path before import
from pytest_coverage_impact.core.prioritizer import Prioritizer  # noqa: E402 # pylint: disable=wrong-import-position

# JUSTIFICATION: Configures system path before import
from pytest_coverage_impact.gateways.progress import ProgressMonitor  # noqa: E402 # pylint: disable=wrong-import-position

console = Console()


def format_time(seconds: float) -> str:
    """Format time in human-readable format"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"

    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.1f}s"


def _print_performance_summary(timings: Dict[str, float]) -> None:
    """Print performance summary table"""
    console.print("\n" + "=" * 80)
    console.print("[bold green]Performance Summary[/bold green]")
    console.print("=" * 80)

    table = Table(title="Execution Times", show_header=True, header_style="bold magenta")
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Time", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")

    total_time = timings.get("Total Time", 0)
    for step_name, step_time in timings.items():
        if step_name == "Total Time":
            continue
        percentage = (step_time / total_time * 100) if total_time > 0 else 0
        table.add_row(step_name, format_time(step_time), f"{percentage:.1f}%")

    table.add_section()
    table.add_row("[bold]TOTAL[/bold]", format_time(total_time), "100.0%", style="bold green")

    console.print(table)


def _analyze_bottlenecks(timings: Dict[str, float]) -> None:
    """Identify and print bottlenecks"""
    total_time = timings.get("Total Time", 0)
    console.print("\n[bold yellow]Bottleneck Analysis:[/bold yellow]")

    sorted_steps = sorted(
        [(k, v) for k, v in timings.items() if k != "Total Time"],
        key=lambda x: x[1],
        reverse=True,
    )

    if sorted_steps:
        slowest = sorted_steps[0]
        percentage = (slowest[1] / total_time * 100) if total_time > 0 else 0
        console.print(f"  • Slowest step: [red]{slowest[0]}[/red] ({format_time(slowest[1])}, {percentage:.1f}%)")

        if len(sorted_steps) > 1:
            second_slowest = sorted_steps[1]
            percentage2 = (second_slowest[1] / total_time * 100) if total_time > 0 else 0
            console.print(
                f"  • Second slowest: [yellow]{second_slowest[0]}[/yellow] "
                f"({format_time(second_slowest[1])}, {percentage2:.1f}%)"
            )


def _print_verdict(total_time: float) -> None:
    """Print final verdict based on total execution time"""
    console.print("\n[bold green]✓ Analysis completed successfully![/bold green]")
    # JUSTIFICATION: Simple threshold logic, strategy pattern not required
    # pylint: disable=clean-arch-delegation,W9005
    if total_time > 300:  # 5 minutes
        console.print(f"[red]⚠ Total time ({format_time(total_time)}) exceeds 5 minutes - consider optimizations[/red]")
    elif total_time > 120:  # 2 minutes
        console.print(
            f"[yellow]⚠ Total time ({format_time(total_time)}) exceeds 2 minutes "
            "- acceptable but could be improved[/yellow]"
        )
    else:
        console.print(f"[green]✓ Total time ({format_time(total_time)}) is reasonable[/green]")


def run_analysis(project_path: Path, coverage_file: Path) -> int:
    """Run the analysis and track timings"""
    timings = {}
    start_total = time.time()

    try:
        # Step 1: Initialize analyzer
        step_start = time.time()
        analyzer = CoverageImpactAnalyzer(project_path)
        timings["Initialize Analyzer"] = time.time() - step_start

        # Step 2: Build call graph
        console.print("\n[bold cyan]Step 1: Building Call Graph[/bold cyan]")
        step_start = time.time()
        with ProgressMonitor(console, enabled=True) as progress:
            call_graph = build_call_graph(analyzer.source_dir, progress_monitor=progress)
        timings["Build Call Graph"] = time.time() - step_start
        console.print(f"[green]✓[/green] Found {len(call_graph.graph)} functions")

        # Step 3: Load coverage data
        console.print("\n[bold cyan]Step 2: Loading Coverage Data[/bold cyan]")
        step_start = time.time()
        coverage_data = load_coverage_data(coverage_file)
        timings["Load Coverage Data"] = time.time() - step_start
        # Removed num_files variable to reduce locals
        console.print(f"[green]✓[/green] Loaded coverage for {len(coverage_data.get('files', {}))} files")

        # Step 4: Calculate impact scores
        console.print("\n[bold cyan]Step 3: Calculating Impact Scores[/bold cyan]")
        step_start = time.time()
        with ProgressMonitor(console, enabled=True) as progress:
            calculator = ImpactCalculator(call_graph, coverage_data)
            impact_scores = calculator.calculate_impact_scores(progress_monitor=progress)
        timings["Calculate Impact Scores"] = time.time() - step_start
        console.print(f"[green]✓[/green] Calculated scores for {len(impact_scores)} functions")

        # Step 5: Estimate complexity
        console.print("\n[bold cyan]Step 4: Estimating Complexity[/bold cyan]")
        step_start = time.time()
        model_path = analyzer.get_model_path()
        complexity_scores = {}
        confidence_scores = {}

        if model_path and model_path.exists():
            with ProgressMonitor(console, enabled=True) as progress:
                # JUSTIFICATION: Benchmarking internal method directly for performance analysis
                # pylint: disable=protected-access,clean-arch-visibility
                complexity_scores, confidence_scores = analyzer._estimate_complexities(
                    impact_scores, model_path=model_path, progress_monitor=progress
                )
            timings["Estimate Complexity"] = time.time() - step_start
            console.print(f"[green]✓[/green] Estimated complexity for {len(complexity_scores)} functions")
        else:
            timings["Estimate Complexity"] = 0.0
            console.print("[yellow]⚠ No ML model found, skipping complexity estimation[/yellow]")

        # Step 6: Prioritize functions
        step_start = time.time()
        Prioritizer.prioritize_functions(
            impact_scores,
            complexity_scores if model_path and model_path.exists() else {},
            confidence_scores if model_path and model_path.exists() else {},
        )
        timings["Prioritize Functions"] = time.time() - step_start

        timings["Total Time"] = time.time() - start_total

        _print_performance_summary(timings)
        _analyze_bottlenecks(timings)
        _print_verdict(timings["Total Time"])

        return 0

        # JUSTIFICATION: Catch-all to ensure performance test reporting completes
    except Exception as e:  # pylint: disable=broad-exception-caught
        console.print(f"\n[red]✗ Error during analysis: {e}[/red]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


def main() -> int:
    """Main entry point"""
    console.print("[bold blue]Performance Test: Coverage Impact Analysis[/bold blue]")
    console.print("=" * 80)

    if len(sys.argv) < 2:
        console.print("[red]Usage: python scripts/test_performance.py <project_path>[/red]")
        console.print("Example: python scripts/test_performance.py /path/to/snowfort")
        return 1

    project_path = Path(sys.argv[1])
    if not project_path.exists():
        console.print(f"[red]Error: Project path does not exist: {project_path}[/red]")
        return 1

    coverage_file = project_path / "coverage.json"
    if not coverage_file.exists():
        console.print(f"[yellow]Warning: coverage.json not found at {coverage_file}[/yellow]")
        console.print("[yellow]Run pytest with --cov first to generate coverage data[/yellow]")
        return 1

    console.print(f"\n[bold]Project:[/bold] {project_path}")
    console.print(f"[bold]Coverage file:[/bold] {coverage_file}\n")

    return run_analysis(project_path, coverage_file)


if __name__ == "__main__":
    sys.exit(main())
