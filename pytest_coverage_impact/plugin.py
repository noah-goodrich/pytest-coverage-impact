"""Main pytest plugin for coverage impact analysis"""

import sys
from pathlib import Path

import pytest


def pytest_load_initial_conftests(early_config, parser, args):
    """Hook to modify command line arguments before they're processed"""
    # Automatically add --cov-report=json if --coverage-impact is used
    if "--coverage-impact" in args:
        # Check if --cov-report=json is already specified
        has_cov_report_json = any(
            "--cov-report=json" in arg or "--cov-report" in arg and "json" in arg for arg in args)

        if not has_cov_report_json:
            # Add --cov-report=json to ensure coverage.json is generated
            args.append("--cov-report=json")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add command-line options for coverage impact plugin"""
    group = parser.getgroup(
        "coverage-impact", "Coverage impact analysis with ML complexity estimation")

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

    # Handle training data collection (runs before tests)
    collect_path = config.getoption("--coverage-impact-collect-training-data")
    if collect_path:
        _handle_collect_training_data(config, Path(collect_path))
        # Exit early - we're just collecting data, not running tests
        sys.exit(0)

    # Handle model training (runs before tests)
    train_data_path = config.getoption("--coverage-impact-train-model")
    if train_data_path:
        _handle_train_model(config, Path(train_data_path))
        # Exit early - we're just training, not running tests
        sys.exit(0)

    # Handle combined train command (collect + train)
    if config.getoption("--coverage-impact-train"):
        _handle_train(config)
        # Exit early - we're just training, not running tests
        sys.exit(0)


def _handle_collect_training_data(config: pytest.Config, output_path: Path) -> Path:
    """Handle training data collection with auto-versioning

    Returns:
        Path to saved training data file
    """
    from rich.console import Console
    from pytest_coverage_impact.ml.training_data_collector import TrainingDataCollector
    from pytest_coverage_impact.ml.versioning import get_next_version

    console = Console()
    console.print("[bold blue]Collecting Training Data[/bold blue]")
    console.print("=" * 60)

    project_root = Path(config.rootdir)

    # Determine the actual output path (handle directories and versioning)
    if not output_path.exists() or output_path.is_dir() or "v" not in output_path.name:
        # Use versioning - find the directory
        if output_path.is_dir() or not output_path.exists():
            from pytest_coverage_impact.utils import resolve_path

            training_data_dir = resolve_path(output_path, project_root)
        else:
            training_data_dir = output_path.parent

        # Ensure we're working with the training_data directory
        if training_data_dir.name != "training_data" and (training_data_dir / "training_data").exists():
            training_data_dir = training_data_dir / "training_data"

        version, output_path = get_next_version(
            training_data_dir, "dataset_v", ".json")
        console.print(f"[dim]Auto-incrementing version to {version}[/dim]")
    else:
        # Use the provided path as-is
        from pytest_coverage_impact.utils import resolve_path

        output_path = resolve_path(output_path, project_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"Project root: {project_root}")
    console.print(f"Output path: {output_path}")
    console.print("")

    try:
        collector = TrainingDataCollector(project_root, None)
        training_data = collector.collect_training_data()

        # Extract version from filename
        import re

        match = re.search(r"v(\d+\.\d+)", output_path.name)
        version = match.group(1) if match else "1.0"

        collector.save_training_data(
            training_data, output_path, version=version)
        console.print(
            f"\n[green]✓[/green] Training data saved to {output_path}")
        return output_path
    except Exception as e:
        console.print(f"\n[red]✗ Error collecting training data: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise


def _handle_train_model(config: pytest.Config, training_data_path: Path) -> None:
    """Handle model training"""
    import json
    from rich.console import Console
    from pytest_coverage_impact.ml.complexity_model import ComplexityModel

    console = Console()
    console.print("[bold blue]Training ML Model[/bold blue]")
    console.print("=" * 60)

    project_root = Path(config.rootdir)
    from pytest_coverage_impact.utils import resolve_path

    training_data_path = resolve_path(training_data_path, project_root)

    console.print(f"Training data: {training_data_path}")

    if not training_data_path.exists():
        console.print(
            f"[red]✗ Training data file not found: {training_data_path}[/red]")
        sys.exit(1)

    # Load training data
    console.print("[dim]Loading training data...[/dim]")
    try:
        with open(training_data_path, "r") as f:
            dataset = json.load(f)
        examples = dataset.get("examples", [])
        console.print(
            f"[green]✓[/green] Loaded {len(examples)} training examples")
    except Exception as e:
        console.print(f"[red]✗ Error loading training data: {e}[/red]")
        sys.exit(1)

    # Train model
    console.print("[dim]Training model...[/dim]")
    try:
        model = ComplexityModel()
        metrics = model.train(examples)

        console.print("[green]✓[/green] Model trained successfully")
        console.print(f"  R² Score: {metrics.get('r2_score', 'N/A'):.3f}")
        console.print(f"  MAE: {metrics.get('mae', 'N/A'):.3f}")
        console.print(f"  RMSE: {metrics.get('rmse', 'N/A'):.3f}")

        # Save model to default location with auto-incrementing version
        from pytest_coverage_impact.ml.versioning import get_next_version

        model_dir = project_root / ".coverage_impact" / "models"
        model_dir.mkdir(parents=True, exist_ok=True)

        version, model_path = get_next_version(
            model_dir, "complexity_model_v", ".pkl")
        console.print(
            f"[dim]Auto-incrementing model version to {version}[/dim]")

        model.save(
            model_path,
            metadata={
                "version": version,
                "metrics": metrics,
                "training_examples": len(examples),
                "training_data_source": str(training_data_path),
            },
        )

        console.print(f"\n[green]✓[/green] Model saved to {model_path}")
        console.print(
            "\n[yellow]Tip:[/yellow] Configure in pytest.ini (point to directory - auto-detects latest):")
        console.print("  [pytest]")
        console.print("  coverage_impact_model_path = .coverage_impact/models")

    except Exception as e:
        console.print(f"\n[red]✗ Error training model: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


def _handle_train(config: pytest.Config) -> None:
    """Handle combined training: collect data and train model in one command"""
    from rich.console import Console

    console = Console()
    console.print("[bold blue]Training ML Model[/bold blue]")
    console.print("=" * 60)

    project_root = Path(config.rootdir)

    # Step 1: Collect training data (with auto-versioning)
    console.print("\n[bold]Step 1: Collecting Training Data[/bold]")
    training_data_dir = project_root / ".coverage_impact" / "training_data"
    training_data_path = _handle_collect_training_data(
        config, training_data_dir)

    # Step 2: Train model (with auto-versioning)
    console.print("\n[bold]Step 2: Training Model[/bold]")
    _handle_train_model(config, training_data_path)

    console.print("\n[green]✓[/green] [bold]Training complete![/bold]")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate coverage impact report after test session"""
    if not session.config.getoption("--coverage-impact"):
        return

    try:
        from pytest_coverage_impact.analyzer import CoverageImpactAnalyzer
        from pytest_coverage_impact.config import get_model_path
        from pytest_coverage_impact.reporters import TerminalReporter, JSONReporter
        from rich.console import Console

        console = Console()
        console.print("\n[bold blue]Coverage Impact Analysis[/bold blue]")
        console.print("=" * 60)

        # Determine project root
        project_root = Path(session.config.rootdir)

        # Check if we have coverage data
        coverage_file = project_root / "coverage.json"
        if not coverage_file.exists():
            console.print(
                "[yellow]⚠ Warning: coverage.json not found. Run pytest with --cov first.[/yellow]")
            return

        # Create analyzer and get model path
        analyzer = CoverageImpactAnalyzer(project_root)
        console.print("[dim]Analyzing coverage impact...[/dim]")

        # Get model path (CLI > config system)
        cli_model_path = session.config.getoption(
            "--coverage-impact-model-path")
        model_path = analyzer.get_model_path(
            cli_model_path) if cli_model_path else None

        if not model_path:
            # Fallback to config system
            from pytest_coverage_impact.config import get_model_path

            model_path = get_model_path(session.config, project_root)

        # Perform analysis with model path
        try:
            results = analyzer.analyze(coverage_file, model_path=model_path)
        except FileNotFoundError as e:
            console.print(f"[yellow]⚠ {e}[/yellow]")
            return
        except ValueError as e:
            console.print(f"[yellow]⚠ {e}[/yellow]")
            return

        call_graph = results["call_graph"]
        impact_scores = results["impact_scores"]
        complexity_scores = results.get("complexity_scores", {})
        prioritized = results["prioritized"]

        console.print(
            f"[green]✓[/green] Found {len(call_graph.graph)} functions")
        console.print(
            f"[green]✓[/green] Calculated scores for {len(impact_scores)} functions")

        if complexity_scores:
            console.print(
                f"[green]✓[/green] Estimated complexity for {len(complexity_scores)} functions")

        console.print(
            f"[green]✓[/green] Prioritized {len(prioritized)} functions")

        # Generate terminal report
        top_n = session.config.getoption("--coverage-impact-top", default=20)
        console.print("\n")
        reporter = TerminalReporter(console)
        reporter.generate_report(prioritized, top_n=top_n)

        # Generate JSON report if requested
        json_path = session.config.getoption("--coverage-impact-json")
        if json_path:
            json_reporter = JSONReporter()
            json_reporter.generate_report(impact_scores, Path(json_path))
            console.print(
                f"\n[green]✓[/green] JSON report saved to {json_path}")

        # Generate HTML report if requested
        html_path = session.config.getoption("--coverage-impact-html")
        if html_path:
            console.print("\n[yellow]⚠ HTML reports coming soon[/yellow]")

    except Exception as e:
        console.print(
            f"\n[red]✗ Error generating coverage impact report: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
