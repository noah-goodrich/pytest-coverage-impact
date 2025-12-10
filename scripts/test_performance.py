#!/usr/bin/env python3
"""Performance test for coverage impact analysis with detailed timing"""

import sys
import time
from pathlib import Path

# Add project to path before other imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from pytest_coverage_impact.analyzer import CoverageImpactAnalyzer  # noqa: E402
from pytest_coverage_impact.progress import ProgressMonitor  # noqa: E402

console = Console()


def format_time(seconds: float) -> str:
    """Format time in human-readable format"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"


def main():  # noqa: C901 - Orchestrates multi-step performance testing workflow
    """Run performance test with detailed timing"""
    console.print("[bold blue]Performance Test: Coverage Impact Analysis[/bold blue]")
    console.print("=" * 80)

    if len(sys.argv) < 2:
        console.print("[red]Usage: python scripts/test_performance.py <project_path>[/red]")
        console.print("Example: python scripts/test_performance.py /path/to/snowfort")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    if not project_path.exists():
        console.print(f"[red]Error: Project path does not exist: {project_path}[/red]")
        sys.exit(1)

    coverage_file = project_path / "coverage.json"
    if not coverage_file.exists():
        console.print(f"[yellow]Warning: coverage.json not found at {coverage_file}[/yellow]")
        console.print("[yellow]Run pytest with --cov first to generate coverage data[/yellow]")
        sys.exit(1)

    # Initialize analyzer
    start_total = time.time()
    console.print(f"\n[bold]Project:[/bold] {project_path}")
    console.print(f"[bold]Coverage file:[/bold] {coverage_file}\n")

    timings = {}

    try:
        # Step 1: Initialize analyzer and find source directory
        step_start = time.time()
        analyzer = CoverageImpactAnalyzer(project_path)
        timings["Initialize Analyzer"] = time.time() - step_start

        # Step 2: Build call graph
        console.print("\n[bold cyan]Step 1: Building Call Graph[/bold cyan]")
        step_start = time.time()
        with ProgressMonitor(console, enabled=True) as progress:
            from pytest_coverage_impact.call_graph import build_call_graph

            call_graph = build_call_graph(analyzer.source_dir, progress_monitor=progress)
        timings["Build Call Graph"] = time.time() - step_start
        console.print(f"[green]✓[/green] Found {len(call_graph.graph)} functions")

        # Step 3: Load coverage data
        console.print("\n[bold cyan]Step 2: Loading Coverage Data[/bold cyan]")
        step_start = time.time()
        from pytest_coverage_impact.impact_calculator import load_coverage_data

        coverage_data = load_coverage_data(coverage_file)
        timings["Load Coverage Data"] = time.time() - step_start
        num_files = len(coverage_data.get("files", {}))
        console.print(f"[green]✓[/green] Loaded coverage for {num_files} files")

        # Step 4: Calculate impact scores
        console.print("\n[bold cyan]Step 3: Calculating Impact Scores[/bold cyan]")
        step_start = time.time()
        with ProgressMonitor(console, enabled=True) as progress:
            from pytest_coverage_impact.impact_calculator import ImpactCalculator

            calculator = ImpactCalculator(call_graph, coverage_data)
            impact_scores = calculator.calculate_impact_scores(progress_monitor=progress)
        timings["Calculate Impact Scores"] = time.time() - step_start
        console.print(f"[green]✓[/green] Calculated scores for {len(impact_scores)} functions")

        # Step 5: Estimate complexity (if model available)
        console.print("\n[bold cyan]Step 4: Estimating Complexity[/bold cyan]")
        step_start = time.time()
        model_path = analyzer._get_default_model_path()
        if model_path and model_path.exists():
            with ProgressMonitor(console, enabled=True) as progress:
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
        from pytest_coverage_impact.prioritizer import Prioritizer

        Prioritizer.prioritize_functions(
            impact_scores,
            complexity_scores if model_path and model_path.exists() else {},
            confidence_scores if model_path and model_path.exists() else {},
        )
        timings["Prioritize Functions"] = time.time() - step_start

        timings["Total Time"] = time.time() - start_total

        # Display timing summary
        console.print("\n" + "=" * 80)
        console.print("[bold green]Performance Summary[/bold green]")
        console.print("=" * 80)

        table = Table(title="Execution Times", show_header=True, header_style="bold magenta")
        table.add_column("Step", style="cyan", no_wrap=True)
        table.add_column("Time", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")

        total_time = timings["Total Time"]
        for step_name, step_time in timings.items():
            if step_name == "Total Time":
                continue
            percentage = (step_time / total_time * 100) if total_time > 0 else 0
            table.add_row(step_name, format_time(step_time), f"{percentage:.1f}%")

        table.add_section()
        table.add_row("[bold]TOTAL[/bold]", format_time(total_time), "100.0%", style="bold green")

        console.print(table)

        # Identify bottlenecks
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
                    f"  • Second slowest: [yellow]{second_slowest[0]}[/yellow] ({format_time(second_slowest[1])}, {percentage2:.1f}%)"
                )

        # Success criteria
        console.print("\n[bold green]✓ Analysis completed successfully![/bold green]")
        if total_time > 300:  # 5 minutes
            console.print(
                f"[red]⚠ Total time ({format_time(total_time)}) exceeds 5 minutes - consider optimizations[/red]"
            )
        elif total_time > 120:  # 2 minutes
            console.print(
                f"[yellow]⚠ Total time ({format_time(total_time)}) exceeds 2 minutes - acceptable but could be improved[/yellow]"
            )
        else:
            console.print(f"[green]✓ Total time ({format_time(total_time)}) is reasonable[/green]")

        return 0

    except Exception as e:
        console.print(f"\n[red]✗ Error during analysis: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
