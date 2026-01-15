"""Coverage impact analysis orchestrator - extractable business logic"""

import ast
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pytest_coverage_impact.gateways.call_graph import build_call_graph
from pytest_coverage_impact.core.config import (
    get_default_bundled_model_path,
    get_model_path_from_env,
    get_model_path_from_project_dir,
)
from pytest_coverage_impact.core.impact_calculator import (
    ImpactCalculator,
    load_coverage_data,
)
from pytest_coverage_impact.ml.complexity_estimator import ComplexityEstimator
from pytest_coverage_impact.core.prioritizer import Prioritizer
from pytest_coverage_impact.gateways.progress import ProgressMonitor
from pytest_coverage_impact.gateways.utils import (
    parse_ast_tree,
    resolve_model_path_with_auto_detect,
)


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
        self._ast_cache: Dict[Path, ast.AST] = {}  # Cache AST trees by file path

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

    def analyze(
        self,
        coverage_file: Optional[Path] = None,
        model_path: Optional[Path] = None,
        progress_monitor: Optional[ProgressMonitor] = None,
    ) -> Dict:
        """Perform full coverage impact analysis

        Args:
            coverage_file: Optional path to coverage.json (defaults to project_root/coverage.json)
            model_path: Optional path to ML model (auto-detected if not provided)
            progress_monitor: Optional progress monitor for showing progress

        Returns:
            Dictionary with analysis results:
            - call_graph: CallGraph object
            - impact_scores: List of impact score dicts
            - complexity_scores: Dict mapping function signatures to complexity scores
            - confidence_scores: Dict mapping function signatures to confidence scores
            - prioritized: List of prioritized functions
            - timings: Dict with timing information for each step
        """
        timings = {}

        if coverage_file is None:
            coverage_file = self.project_root / "coverage.json"

        if not coverage_file.exists():
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")

        # Build call graph
        step_start = time.time()
        call_graph = build_call_graph(self.source_dir, progress_monitor=progress_monitor)
        timings["build_call_graph"] = time.time() - step_start

        if len(call_graph.graph) == 0:
            raise ValueError("No functions found in codebase")

        # Load coverage data
        step_start = time.time()
        coverage_data = load_coverage_data(coverage_file)
        timings["load_coverage_data"] = time.time() - step_start

        # Calculate impact scores
        step_start = time.time()
        calculator = ImpactCalculator(call_graph, coverage_data)
        impact_scores = self._run_impact_calculation(calculator, progress_monitor)
        timings["calculate_impact_scores"] = time.time() - step_start

        # Estimate complexity with ML
        step_start = time.time()
        complexity_scores, confidence_scores = self._estimate_complexities(
            impact_scores, model_path=model_path, progress_monitor=progress_monitor
        )
        timings["estimate_complexity"] = time.time() - step_start

        # Prioritize functions
        step_start = time.time()
        prioritized = Prioritizer.prioritize_functions(impact_scores, complexity_scores, confidence_scores)
        timings["prioritize_functions"] = time.time() - step_start

        # Clear AST cache after analysis to free memory
        self._ast_cache.clear()

        return {
            "call_graph": call_graph,
            "impact_scores": impact_scores,
            "complexity_scores": complexity_scores,
            "confidence_scores": confidence_scores,
            "prioritized": prioritized,
            "timings": timings,
            "totals": coverage_data.get("totals", {}),
            "files": coverage_data.get("files", {}),
        }

    @staticmethod
    def _run_impact_calculation(calculator, progress_monitor):
        """Helper to run impact calculation (Friend)"""
        return calculator.calculate_impact_scores(progress_monitor=progress_monitor)

    def _estimate_complexities(  # noqa: C901 - Orchestrates ML complexity estimation with progress tracking
        self,
        impact_scores: List[Dict],
        model_path: Optional[Path] = None,
        limit: int = 100,
        progress_monitor: Optional[ProgressMonitor] = None,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Estimate complexity scores using ML model

        Args:
            impact_scores: List of impact score dictionaries
            model_path: Optional path to ML model (auto-detected if not provided)
            limit: Maximum number of functions to analyze (for performance)
            progress_monitor: Optional progress monitor for showing progress

        Returns:
            Tuple of (complexity_scores_dict, confidence_scores_dict)
        """
        complexity_scores = {}
        confidence_scores = {}

        if model_path is None:
            # Auto-detect model path using default system
            model_path = self._get_default_model_path()

        if model_path and not model_path.exists():
            # Warn? Or just fallback.
            model_path = None

        try:
            estimator = ComplexityEstimator(model_path)
            task_id = self._create_progress_task(progress_monitor, limit, impact_scores)

            # Estimate complexity for top functions (limit for performance)
            progress_data = (progress_monitor, task_id)
            scores = (complexity_scores, confidence_scores)

            for _, item in enumerate(impact_scores[:limit]):
                self._process_single_complexity_estimate(estimator, item, progress_data, scores)

            if progress_monitor and task_id:
                progress_monitor.complete_task(task_id)

        # JUSTIFICATION: Orchestrator must catch model errors to return partial results safely
        except Exception:  # pylint: disable=broad-exception-caught
            # Model loading/estimation failed - return empty scores
            pass

        return complexity_scores, confidence_scores

    def _create_progress_task(self, progress_monitor, limit, impact_scores):
        """Create progress task for complexity estimation"""
        if not progress_monitor:
            return None
        return progress_monitor.add_task("[cyan]Estimating complexity", total=min(limit, len(impact_scores)))

    @staticmethod
    def _advance_progress(progress_monitor, task_id):
        """Advance progress by 1 step"""
        if progress_monitor and task_id:
            progress_monitor.update(task_id, advance=1)

    def _process_single_complexity_estimate(self, estimator, item, progress_data, scores):
        """Process complexity estimation for a single function"""
        progress_monitor, task_id = progress_data
        complexity_scores, confidence_scores = scores
        func_file = self.source_dir / item["file"]

        if not func_file.exists():
            self._advance_progress(progress_monitor, task_id)
            return

        try:
            # Update progress with current function
            if progress_monitor and task_id:
                func_name = item["function"].split("::")[-1]
                progress_monitor.update_description(task_id, f"[cyan]Estimating complexity: {func_name}")

            score, lower, upper = self._estimate_function_complexity(
                estimator, func_file, item["line"], item["function"]
            )

            if score is not None:
                complexity_scores[item["function"]] = score
                self._update_confidence_scores(confidence_scores, item["function"], lower, upper)

            self._advance_progress(progress_monitor, task_id)
        # JUSTIFICATION: Functional error in one function estimation should not crash the batch process
        except Exception:  # pylint: disable=broad-exception-caught
            self._advance_progress(progress_monitor, task_id)

    @staticmethod
    def _update_confidence_scores(confidence_scores, function_name, lower, upper):
        """Calculate and update confidence scores"""
        if lower is not None and upper is not None:
            interval_width = upper - lower
            confidence = max(0.0, min(1.0, 1.0 - interval_width))
            confidence_scores[function_name] = confidence

    def _get_default_model_path(self) -> Optional[Path]:
        """Get default model path using config system (without pytest config object)

        Returns:
            Path to model file, or None if not found
        """
        # Priority 1: Environment variable
        model_path = get_model_path_from_env(self.project_root)
        if model_path:
            return model_path

        # Priority 2: Project directory (user-trained model)
        model_path = get_model_path_from_project_dir(self.project_root)
        if model_path:
            return model_path

        # Priority 3: Plugin directory (default bundled model)
        return get_default_bundled_model_path()

    def _get_ast_tree(self, func_file: Path) -> Optional[ast.AST]:
        """Get AST tree for a file, using cache if available

        Args:
            func_file: Path to Python source file

        Returns:
            AST tree, or None if parsing failed
        """
        # Check cache first
        if func_file in self._ast_cache:
            return self._ast_cache[func_file]

        # Parse and cache
        tree = parse_ast_tree(func_file)
        if tree:
            self._ast_cache[func_file] = tree
        return tree

    def _estimate_function_complexity(
        self,
        estimator: ComplexityEstimator,
        func_file: Path,
        line_num: int,
        _func_signature: str,
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

        # Get AST tree (uses cache)
        tree = self._get_ast_tree(func_file)
        if not tree:
            return None, None, None

        # Find function node in cached tree
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.lineno == line_num:
                    func_node = node
                    break

        if not func_node:
            return None, None, None

        score, lower, upper = estimator.estimate_complexity(func_node, tree, str(func_file))
        return score, lower, upper

    def get_model_path(self, cli_model_path: Optional[str] = None) -> Optional[Path]:
        """Get ML model path using priority order

        Args:
            cli_model_path: Optional CLI-provided model path (highest priority)

        Returns:
            Path to model file, or None if not found
        """
        if cli_model_path:
            return resolve_model_path_with_auto_detect(cli_model_path, self.project_root)

        # Use config system (pytest.ini, env var, defaults)
        return self._get_default_model_path()
