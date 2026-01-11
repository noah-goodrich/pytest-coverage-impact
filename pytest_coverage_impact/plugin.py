"""Main pytest plugin for coverage impact analysis"""

import sys
import traceback
from pathlib import Path

import pytest
from rich.console import Console
from rich.table import Table

from pytest_coverage_impact.analyzer import CoverageImpactAnalyzer
from pytest_coverage_impact.config import get_model_path
from pytest_coverage_impact.ml.orchestrator import MLOrchestrator
from pytest_coverage_impact.progress import ProgressMonitor
from pytest_coverage_impact.reporters import TerminalReporter, JSONReporter


def pytest_load_initial_conftests(early_config, parser, args):
    """Hook to modify command line arguments before they're processed"""
    # Automatically add --cov-report=json if --coverage-impact is used
    if "--coverage-impact" in args:
        # Check if --cov-report=json is already specified
        has_cov_report_json = any("--cov-report=json" in arg or "--cov-report" in arg and "json" in arg for arg in args)

        if not has_cov_report_json:
            # Add --cov-report=json to ensure coverage.json is generated
            args.append("--cov-report=json")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for coverage impact plugin"""
    group = parser.getgroup("coverage-impact", "Coverage impact analysis with ML complexity estimation")

    group.addoption(
        "--coverage-impact",
        action="store_true",
        default=False,
        help="Enable coverage impact analysis with ML complexity estimation",
    )

    group.addoption(
        "--coverage-impact-json",
        action="store",
        default=None,
        metavar="PATH",
        help="Output coverage impact analysis as JSON to the specified path",
    )

    group.addoption(
        "--coverage-impact-html",
        action="store",
        default=None,
        metavar="PATH",
        help="Output coverage impact analysis as HTML report to the specified path",
    )

    group.addoption(
        "--coverage-impact-top",
        action="store",
        type=int,
        default=20,
        metavar="N",
        help="Show top N functions by priority (default: 20)",
    )

    group.addoption(
        "--coverage-impact-model-path",
        action="store",
        default=None,
        metavar="PATH",
        help="Path to ML model file (overrides pytest.ini config and env var)",
    )

    group.addoption(
        "--coverage-impact-feedback",
        action="store_true",
        default=False,
        help="Enable interactive feedback collection for ML model improvement",
    )

    group.addoption(
        "--coverage-impact-feedback-stats",
        action="store_true",
        default=False,
        help="Show feedback statistics",
    )

    group.addoption(
        "--coverage-impact-retrain",
        action="store_true",
        default=False,
        help="Retrain ML model with accumulated feedback data",
    )

    group.addoption(
        "--coverage-impact-collect-training-data",
        action="store",
        default=None,
        metavar="PATH",
        help="Collect training data from codebase and save to JSON file",
    )

    group.addoption(
        "--coverage-impact-train-model",
        action="store",
        default=None,
        metavar="TRAINING_DATA_JSON",
        help="Train ML model from training data JSON file. Model saved to .coverage_impact/models/",
    )

    group.addoption(
        "--coverage-impact-train",
        action="store_true",
        default=False,
        help="Collect training data and train model in one command. Auto-increments versions.",
    )

    # Register ini option for model path configuration
    parser.addini(
        "coverage_impact_model_path",
        "Path to ML complexity model file (relative to project root or absolute)",
        type="string",
        default=None,
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register plugin when --coverage-impact flag is used"""
    # Register markers
    config.addinivalue_line(
        "markers",
        "coverage_impact: marks tests as part of coverage impact analysis",
    )

    orchestrator = MLOrchestrator(config)

    # Handle training data collection (runs before tests)
    collect_path = config.getoption("--coverage-impact-collect-training-data")
    if collect_path:
        orchestrator.handle_collect_training_data(Path(collect_path))
        # Exit early - we're just collecting data, not running tests
        sys.exit(0)

    # Handle model training (runs before tests)
    train_data_path = config.getoption("--coverage-impact-train-model")
    if train_data_path:
        orchestrator.handle_train_model(Path(train_data_path))
        # Exit early - we're just training, not running tests
        sys.exit(0)

    # Handle combined train command (collect + train)
    if config.getoption("--coverage-impact-train"):
        orchestrator.handle_train()
        # Exit early - we're just training, not running tests
        sys.exit(0)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate coverage impact report after test session"""
    config = session.config

    # Simple usage to avoid unused-argument warning
    if exitstatus != 0:
        pass

    if not config.getoption("--coverage-impact"):
        return

    try:
        console = Console()
        console.print("\n[bold blue]Coverage Impact Analysis[/bold blue]")
        console.print("=" * 60)

        # Determine project root
        project_root = Path(config.rootdir)

        # Check if we have coverage data
        coverage_file = project_root / "coverage.json"
        if not coverage_file.exists():
            console.print("[yellow]⚠ Warning: coverage.json not found. Run pytest with --cov first.[/yellow]")
            return

        # Create analyzer and get model path
        analyzer = CoverageImpactAnalyzer(project_root)

        # Get model path (CLI > config system)
        cli_model_path = config.getoption("--coverage-impact-model-path")
        model_path = analyzer.get_model_path(cli_model_path) if cli_model_path else None

        if not model_path:
            # Fallback to config system
            model_path = get_model_path(config, project_root)

        _run_analysis(analyzer, coverage_file, model_path, console, config)

    except Exception as e:  # pylint: disable=broad-exception-caught
        # We can't avoid broad exception here as it's the top level hook handler
        console_instance = Console()
        console_instance.print(f"\n[red]✗ Error generating coverage impact report: {e}[/red]")
        console_instance.print(f"[dim]{traceback.format_exc()}[/dim]")


def _run_analysis(analyzer, coverage_file, model_path, console, config):
    """Run the analysis steps"""
    # Create progress monitor for analysis
    with ProgressMonitor(console, enabled=True) as progress:
        console.print("[dim]Analyzing coverage impact...[/dim]")

        # Perform analysis with model path and progress monitor
        results = analyzer.analyze(coverage_file, model_path=model_path, progress_monitor=progress)

        call_graph = results["call_graph"]
        impact_scores = results["impact_scores"]
        complexity_scores = results.get("complexity_scores", {})
        prioritized = results["prioritized"]
        timings = results.get("timings", {})

        console.print(f"[green]✓[/green] Found {len(call_graph.graph)} functions")
        console.print(f"[green]✓[/green] Calculated scores for {len(impact_scores)} functions")

        if complexity_scores:
            console.print(f"[green]✓[/green] Estimated complexity for {len(complexity_scores)} functions")

        console.print(f"[green]✓[/green] Prioritized {len(prioritized)} functions")

    # Generate terminal report (outside progress monitor)
    top_n = config.getoption("--coverage-impact-top", default=20)
    console.print("\n")
    reporter = TerminalReporter(console)

    # Print timings first? Or last? Original was inside progress monitor block.
    # But progress monitor console usage might conflict.
    # The original _print_timings was called inside _run_analysis inside progress block.
    # But _print_timings uses console.

    reporter.print_timings(results.get("timings", {}))
    reporter.generate_report(prioritized, top_n=top_n, totals=results.get("totals"), files=results.get("files"))

    # Generate JSON report if requested
    json_path = config.getoption("--coverage-impact-json")
    if json_path:
        json_reporter = JSONReporter()
        json_reporter.generate_report(impact_scores, Path(json_path))
        console.print(f"\n[green]✓[/green] JSON report saved to {json_path}")

    # Generate HTML report if requested
    html_path = config.getoption("--coverage-impact-html")
    if html_path:
        console.print("\n[yellow]⚠ HTML reports coming soon[/yellow]")



