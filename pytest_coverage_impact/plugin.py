"""Main pytest plugin for coverage impact analysis"""

import sys
import traceback
from pathlib import Path

import pytest
from rich.console import Console

from pytest_coverage_impact.logic.analyzer import CoverageImpactAnalyzer
from pytest_coverage_impact.core.config import get_model_path
from pytest_coverage_impact.ml.gateway import MLGateway
from pytest_coverage_impact.gateways.progress import ProgressMonitor
from pytest_coverage_impact.gateways.reporters import TerminalReporter, JSONReporter
from pytest_coverage_impact.ui import SystemUI


def pytest_load_initial_conftests(args):
    """Hook to modify command line arguments before they're processed"""
    # Automatically add --cov-report=json if --coverage-impact is used
    if "--coverage-impact" in args:
        # Check if --cov-report=json is already specified
        has_cov_report_json = any("--cov-report=json" in arg or "--cov-report" in arg and "json" in arg for arg in args)

        if not has_cov_report_json:
            # Add --cov-report=json to ensure coverage.json is generated
            args.append("--cov-report=json")


def _configure_group(group) -> None:
    """Configure arguments for the coverage-impact group

    Helper to resolve Law of Demeter violations (group.addoption).
    """
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


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for coverage impact plugin"""
    group = parser.getgroup("coverage-impact", "Coverage impact analysis with ML complexity estimation")
    _configure_group(group)

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

    gateway = MLGateway(config)

    # Handle training data collection (runs before tests)
    collect_path = config.getoption("--coverage-impact-collect-training-data")
    if collect_path:
        _collect_training_data(gateway, collect_path)
        # Exit early - we're just collecting data, not running tests
        sys.exit(0)

    # Handle model training (runs before tests)
    train_data_path = config.getoption("--coverage-impact-train-model")
    if train_data_path:
        _train_model(gateway, train_data_path)
        # Exit early - we're just training, not running tests
        sys.exit(0)

    # Handle combined train command (collect + train)
    if config.getoption("--coverage-impact-train"):
        _train_combined(gateway)
        # Exit early - we're just training, not running tests
        sys.exit(0)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Stellar Handshake: Sensoria Calibration"""
    SystemUI.announce_initialization(session.config)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate coverage impact report after test session"""
    config = session.config

    # Simple usage to avoid unused-argument warning
    if exitstatus != 0:
        pass

    if not config.getoption("--coverage-impact"):
        return

    try:
        SystemUI.announce_section("Coverage Impact Analysis")

        # Determine project root
        project_root = Path(config.rootdir)

        # Check if we have coverage data
        coverage_file = project_root / "coverage.json"
        if not coverage_file.exists():
            SystemUI.announce_warning("coverage.json not found. Run pytest with --cov first.")
            return

        # Create analyzer and get model path
        analyzer = CoverageImpactAnalyzer(project_root)

        # Get model path (CLI > config system)
        cli_model_path = config.getoption("--coverage-impact-model-path")
        model_path = _resolve_model_path(analyzer, cli_model_path) if cli_model_path else None

        if not model_path:
            # Fallback to config system
            model_path = get_model_path(config, project_root)

        _run_analysis(analyzer, coverage_file, model_path, config)

    # JUSTIFICATION: Top-level entry point must catch all exceptions to prevent crash dump
    except Exception as e:  # pylint: disable=broad-exception-caught
        # JUSTIFICATION: Report generation should not crash the test session
        SystemUI.announce_error(f"generating coverage impact report: {e}")
        # Print full traceback for debugging if verbose
        SystemUI.announce_error(f"[dim]{traceback.format_exc()}[/dim]")


def _collect_training_data(gateway, collect_path):
    """Helper to collect training data via gateway"""
    gateway.handle_collect_training_data(Path(collect_path))


def _train_model(gateway, train_data_path):
    """Helper to train model via gateway"""
    gateway.handle_train_model(Path(train_data_path))


def _train_combined(gateway):
    """Helper to run combined training via gateway"""
    gateway.handle_train()


def _run_analysis(analyzer, coverage_file, model_path, config):
    """Run the analysis steps"""
    # Create console for progress monitor
    console = Console()

    # Create progress monitor for analysis
    with ProgressMonitor(console, enabled=True) as progress:
        SystemUI.announce_progress("Analyzing coverage impact...")

        # Perform analysis with model path and progress monitor
        results = analyzer.analyze(coverage_file, model_path=model_path, progress_monitor=progress)

        call_graph = results["call_graph"]
        impact_scores = results["impact_scores"]
        complexity_scores = results.get("complexity_scores", {})
        prioritized = results["prioritized"]

        SystemUI.announce_success(f"Found {len(call_graph.graph)} functions")
        SystemUI.announce_success(f"Calculated scores for {len(impact_scores)} functions")

        if complexity_scores:
            SystemUI.announce_success(f"Estimated complexity for {len(complexity_scores)} functions")

        SystemUI.announce_success(f"Prioritized {len(prioritized)} functions")

    _generate_terminal_report(console, config, results, prioritized)
    _generate_json_report(config, impact_scores)
    _check_html_report(config)


def _resolve_model_path(analyzer, cli_model_path):
    """Helper to resolve model path via analyzer"""
    return analyzer.get_model_path(cli_model_path)


def _run_terminal_reporter(reporter, results, prioritized, top_n):
    """Helper to run terminal reporter"""
    reporter.print_timings(results.get("timings", {}))
    reporter.generate_report(
        prioritized,
        top_n=top_n,
        totals=results.get("totals"),
        files=results.get("files"),
    )


def _run_json_reporter(json_reporter, impact_scores, json_path):
    """Helper to generate JSON report"""
    json_reporter.generate_report(impact_scores, Path(json_path))


def _generate_terminal_report(console, config, results, prioritized):
    """Generate and print the terminal report"""
    top_n = config.getoption("--coverage-impact-top", default=20)
    console.print("\n")
    reporter = TerminalReporter(console)
    _run_terminal_reporter(reporter, results, prioritized, top_n)


def _generate_json_report(config, impact_scores):
    """Generate and save the JSON report if requested"""
    json_path = config.getoption("--coverage-impact-json")
    if json_path:
        json_reporter = JSONReporter()
        _run_json_reporter(json_reporter, impact_scores, json_path)
        SystemUI.announce_success(f"JSON report saved to {json_path}")


def _check_html_report(config):
    """Check and notify about HTML report status"""
    html_path = config.getoption("--coverage-impact-html")
    if html_path:
        SystemUI.announce_warning("HTML reports coming soon")
