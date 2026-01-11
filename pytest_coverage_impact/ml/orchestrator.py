"""Orchestrator for ML training and data collection workflows"""

import sys
import json
import traceback
from pathlib import Path
from typing import Optional

from rich.console import Console

from pytest_coverage_impact.ml.complexity_model import ComplexityModel
from pytest_coverage_impact.ml.training_data_collector import TrainingDataCollector
from pytest_coverage_impact.ml.versioning import get_next_version
from pytest_coverage_impact.utils import resolve_path, ensure_parent_directory_exists


class MLOrchestrator:
    """Orchestrates ML model training and data collection commands"""

    def __init__(self, config=None):
        self.config = config
        self.console = Console()
        self.project_root = Path(config.rootdir) if config else Path.cwd()

    def handle_collect_training_data(self, output_path: Path) -> Path:
        """Handle training data collection with auto-versioning

        Args:
            output_path: Requested output path (file or directory)

        Returns:
            Path to saved training data file
        """
        self.console.print("[bold blue]Collecting Training Data[/bold blue]")
        self.console.print("=" * 60)

        # Determine the actual output path (handle directories and versioning)
        final_path = self._determine_output_path(output_path)
        ensure_parent_directory_exists(final_path)

        self.console.print(f"Project root: {self.project_root}")
        self.console.print(f"Output path: {final_path}")
        self.console.print("")

        try:
            collector = TrainingDataCollector(self.project_root, None)
            training_data = collector.collect_training_data()

            # Version is part of the filename already handled by _determine_output_path logic usually,
            # but TrainingDataCollector might need it for metadata.
            # We can extract it from the path.
            version = self._extract_version_from_path(final_path)

            collector.save_training_data(training_data, final_path, version=version)
            self.console.print(f"\n[green]✓[/green] Training data saved to {final_path}")
            return final_path
        except Exception as e:
            self.console.print(f"\n[red]✗ Error collecting training data: {e}[/red]")
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise

    def handle_train_model(self, training_data_path: Path) -> None:
        """Handle model training

        Args:
            training_data_path: Path to training data JSON
        """
        self.console.print("[bold blue]Training ML Model[/bold blue]")
        self.console.print("=" * 60)

        training_data_path = resolve_path(training_data_path, self.project_root)
        self.console.print(f"Training data: {training_data_path}")

        if not training_data_path.exists():
            self.console.print(f"[red]✗ Training data file not found: {training_data_path}[/red]")
            sys.exit(1)

        examples = self._load_training_data(training_data_path)
        self.console.print(f"[green]✓[/green] Loaded {len(examples)} training examples")

        self._train_and_save_model(examples, training_data_path)

    def handle_train(self) -> None:
        """Handle combined training: collect data and train model in one command"""
        self.console.print("[bold blue]Training ML Model[/bold blue]")
        self.console.print("=" * 60)

        # Step 1: Collect training data (with auto-versioning)
        self.console.print("\n[bold]Step 1: Collecting Training Data[/bold]")
        training_data_dir = self.project_root / ".coverage_impact" / "training_data"
        training_data_path = self.handle_collect_training_data(training_data_dir)

        # Step 2: Train model (with auto-versioning)
        self.console.print("\n[bold]Step 2: Training Model[/bold]")
        self.handle_train_model(training_data_path)

        self.console.print("\n[green]✓[/green] [bold]Training complete![/bold]")

    def _determine_output_path(self, output_path: Path) -> Path:
        """Determine path for training data output, handling versioning"""
        if not output_path.exists() or output_path.is_dir() or "v" not in output_path.name:
            if output_path.is_dir() or not output_path.exists():
                data_dir = resolve_path(output_path, self.project_root)
            else:
                data_dir = output_path.parent

            # Ensure we're working with the training_data directory
            if data_dir.name != "training_data" and (data_dir / "training_data").exists():
                data_dir = data_dir / "training_data"

            version, path = get_next_version(data_dir, "dataset_v", ".json")
            self.console.print(f"[dim]Auto-incrementing version to {version}[/dim]")
            return path

        return resolve_path(output_path, self.project_root)

    def _extract_version_from_path(self, path: Path) -> str:
        """Extract version string from filename"""
        import re
        match = re.search(r"v(\d+\.\d+)", path.name)
        return match.group(1) if match else "1.0"

    def _load_training_data(self, path: Path):
        """Load training data from JSON file"""
        self.console.print("[dim]Loading training data...[/dim]")
        try:
            with open(path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
            return dataset.get("examples", [])
        except Exception as e:
            self.console.print(f"[red]✗ Error loading training data: {e}[/red]")
            sys.exit(1)

    def _train_and_save_model(self, examples, source_path: Path) -> None:
        """Train model and save it"""
        self.console.print("[dim]Training model...[/dim]")
        try:
            model = ComplexityModel()
            metrics = model.train(examples)

            self.console.print("[green]✓[/green] Model trained successfully")
            self.console.print(f"  R² Score: {metrics.get('r2_score', 'N/A'):.3f}")
            self.console.print(f"  MAE: {metrics.get('mae', 'N/A'):.3f}")
            self.console.print(f"  RMSE: {metrics.get('rmse', 'N/A'):.3f}")

            # Save model to default location with auto-incrementing version
            model_dir = self.project_root / ".coverage_impact" / "models"
            model_dir.mkdir(parents=True, exist_ok=True)

            version, model_path = get_next_version(model_dir, "complexity_model_v", ".pkl")
            self.console.print(f"[dim]Auto-incrementing model version to {version}[/dim]")

            model.save(
                model_path,
                metadata={
                    "version": version,
                    "metrics": metrics,
                    "training_examples": len(examples),
                    "training_data_source": str(source_path),
                },
            )

            self.console.print(f"\n[green]✓[/green] Model saved to {model_path}")
            self.console.print("\n[yellow]Tip:[/yellow] Configure in pytest.ini (point to directory - auto-detects latest):")
            self.console.print("  [pytest]")
            self.console.print("  coverage_impact_model_path = .coverage_impact/models")

        except Exception as e:
            self.console.print(f"\n[red]✗ Error training model: {e}[/red]")
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)
