"""Coverage impact analysis orchestrator - extractable business logic"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pytest_coverage_impact.call_graph import build_call_graph
from pytest_coverage_impact.impact_calculator import ImpactCalculator, load_coverage_data
from pytest_coverage_impact.ml.complexity_estimator import ComplexityEstimator
from pytest_coverage_impact.prioritizer import Prioritizer


class CoverageImpactAnalyzer:
    """Orchestrates coverage impact analysis - testable business logic"""

    def __init__(self, project_root: Path, source_dir: Optional[Path] = None):
        """Initialize analyzer

        Args:
            project_root: Root directory of the project
            source_dir: Optional source directory (auto-detected if not provided)
        """
        self.project_root = Path(project_root).resolve()
        self.source_dir = source_dir if source_dir else self._find_source_directory()

    def _find_source_directory(self) -> Path:
        """Find the source code directory

        Common patterns: project_name/, src/, lib/, or same as project root

        Returns:
            Path to source directory
        """
        possible_dirs = [
            self.project_root / self.project_root.name,  # e.g., snowfort/snowfort
            self.project_root / "src",
            self.project_root / "lib",
            self.project_root,  # Fallback
        ]

        for dir_path in possible_dirs:
            if dir_path.exists() and dir_path.is_dir():
                # Check if it has Python files
                python_files = list(dir_path.rglob("*.py"))
                if python_files and not any("test" in str(f) for f in python_files[:10]):
                    return dir_path

        return self.project_root

    def analyze(self, coverage_file: Optional[Path] = None, model_path: Optional[Path] = None) -> Dict:
        """Perform full coverage impact analysis

        Args:
            coverage_file: Optional path to coverage.json (defaults to project_root/coverage.json)
            model_path: Optional path to ML model (auto-detected if not provided)

        Returns:
            Dictionary with analysis results:
            - call_graph: CallGraph object
            - impact_scores: List of impact score dicts
            - complexity_scores: Dict mapping function signatures to complexity scores
            - confidence_scores: Dict mapping function signatures to confidence scores
            - prioritized: List of prioritized functions
        """
        if coverage_file is None:
            coverage_file = self.project_root / "coverage.json"

        if not coverage_file.exists():
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")

        # Build call graph
        call_graph = build_call_graph(self.source_dir)

        if len(call_graph.graph) == 0:
            raise ValueError("No functions found in codebase")

        # Load coverage data
        coverage_data = load_coverage_data(coverage_file)

        # Calculate impact scores
        calculator = ImpactCalculator(call_graph, coverage_data)
        impact_scores = calculator.calculate_impact_scores()

        # Estimate complexity with ML
        complexity_scores, confidence_scores = self._estimate_complexities(impact_scores, model_path=model_path)

        # Prioritize functions
        prioritized = Prioritizer.prioritize_functions(impact_scores, complexity_scores, confidence_scores)

        return {
            "call_graph": call_graph,
            "impact_scores": impact_scores,
            "complexity_scores": complexity_scores,
            "confidence_scores": confidence_scores,
            "prioritized": prioritized,
        }

    def _estimate_complexities(
        self, impact_scores: List[Dict], model_path: Optional[Path] = None, limit: int = 100
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Estimate complexity scores using ML model

        Args:
            impact_scores: List of impact score dictionaries
            model_path: Optional path to ML model (auto-detected if not provided)
            limit: Maximum number of functions to analyze (for performance)

        Returns:
            Tuple of (complexity_scores_dict, confidence_scores_dict)
        """
        complexity_scores = {}
        confidence_scores = {}

        if model_path is None:
            # Auto-detect model path using default system
            model_path = self._get_default_model_path()

        if not model_path or not model_path.exists():
            return complexity_scores, confidence_scores

        try:
            estimator = ComplexityEstimator(model_path)

            # Estimate complexity for top functions (limit for performance)
            for item in impact_scores[:limit]:
                func_file = self.source_dir / item["file"]
                if not func_file.exists():
                    continue

                try:
                    score, lower, upper = self._estimate_function_complexity(
                        estimator, func_file, item["line"], item["function"]
                    )

                    if score is not None:
                        complexity_scores[item["function"]] = score

                        # Calculate confidence from interval width
                        if lower is not None and upper is not None:
                            interval_width = upper - lower
                            confidence = max(0.0, min(1.0, 1.0 - interval_width))
                            confidence_scores[item["function"]] = confidence
                except Exception:
                    continue
        except Exception:
            # Model loading/estimation failed - return empty scores
            pass

        return complexity_scores, confidence_scores

    def _get_default_model_path(self) -> Optional[Path]:
        """Get default model path using config system (without pytest config object)

        Returns:
            Path to model file, or None if not found
        """
        import os

        # Priority 1: Environment variable
        env_path = os.getenv("PYTEST_COVERAGE_IMPACT_MODEL_PATH")
        if env_path:
            from pytest_coverage_impact.utils import resolve_model_path_with_auto_detect

            return resolve_model_path_with_auto_detect(env_path, self.project_root)

        # Priority 2: Project directory (user-trained model)
        project_model_dir = self.project_root / ".coverage_impact" / "models"
        if project_model_dir.exists() and project_model_dir.is_dir():
            from pytest_coverage_impact.ml.versioning import get_latest_version

            latest = get_latest_version(project_model_dir, "complexity_model_v", ".pkl")
            if latest:
                return latest[1]

        # Priority 3: Plugin directory (default bundled model)
        plugin_dir = Path(__file__).parent
        plugin_model_path = plugin_dir / "ml" / "models" / "complexity_model_v1.0.pkl"
        if plugin_model_path.exists():
            return plugin_model_path.resolve()

        return None

    def _estimate_function_complexity(
        self, estimator: ComplexityEstimator, func_file: Path, line_num: int, func_signature: str
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Estimate complexity for a single function

        Args:
            estimator: ComplexityEstimator instance
            func_file: Path to function's source file
            line_num: Line number of function definition
            func_signature: Function signature for error context

        Returns:
            Tuple of (score, lower_bound, upper_bound) or (None, None, None) if failed
        """
        from pytest_coverage_impact.utils import find_function_node_by_line, parse_ast_tree

        func_node = find_function_node_by_line(func_file, line_num)
        if not func_node:
            return None, None, None

        tree = parse_ast_tree(func_file)
        if not tree:
            return None, None, None

        score, lower, upper = estimator.estimate_complexity(func_node, tree, str(func_file), with_confidence=True)
        return score, lower, upper

    def get_model_path(self, cli_model_path: Optional[str] = None) -> Optional[Path]:
        """Get ML model path using priority order

        Args:
            cli_model_path: Optional CLI-provided model path (highest priority)

        Returns:
            Path to model file, or None if not found
        """
        if cli_model_path:
            from pytest_coverage_impact.utils import resolve_model_path_with_auto_detect

            return resolve_model_path_with_auto_detect(cli_model_path, self.project_root)

        # Use config system (pytest.ini, env var, defaults)
        return self._get_default_model_path()
