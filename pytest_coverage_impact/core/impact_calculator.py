"""Calculate coverage impact scores for functions"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pytest_coverage_impact.gateways.call_graph import CallGraph


class ImpactCalculator:
    """Calculate impact scores based on call frequency and coverage"""

    def __init__(self, call_graph: CallGraph, coverage_data: Dict):
        """Initialize calculator with call graph and coverage data

        Args:
            call_graph: CallGraph object with function relationships
            coverage_data: Coverage data dict from coverage.json
        """
        self.call_graph = call_graph
        self.coverage_data = coverage_data
        # Pre-compute normalized coverage path mapping for fast lookups
        self._coverage_path_map = self._build_coverage_path_map()

    def _build_coverage_path_map(self) -> Dict[str, Dict]:
        """Build normalized path mapping for fast coverage lookups

        Normalizes all paths in coverage data to handle different path formats.
        This allows single lookup instead of trying multiple path formats.

        Returns:
            Dictionary mapping normalized paths to coverage data
        """
        path_map: Dict[str, Dict] = {}
        files_data = self.coverage_data.get("files", {})

        for file_key, file_data in files_data.items():
            # Normalize path: handle Windows/Unix separators, remove leading slashes
            normalized = file_key.replace("\\", "/").lstrip("/")
            path_map[normalized] = file_data

            # Also add variations for common patterns
            if "/" in normalized:
                # Add without leading directory (for relative paths)
                parts = normalized.split("/")
                if len(parts) > 1:
                    path_map["/".join(parts[1:])] = file_data
                    path_map[parts[-1]] = file_data  # Just filename

        return path_map

    def _normalize_path(self, file_path: str, package_prefix: Optional[str] = None) -> str:
        """Normalize a file path for coverage lookup

        Args:
            file_path: Relative file path
            package_prefix: Optional package prefix

        Returns:
            Normalized path string
        """
        # Normalize separators
        normalized = file_path.replace("\\", "/").lstrip("/")

        # Try with package prefix
        if package_prefix:
            prefixed = f"{package_prefix}/{normalized}".replace("\\", "/").lstrip("/")
            if prefixed in self._coverage_path_map:
                return prefixed

        return normalized

    def get_function_coverage(
        self, file_path: str, line_num: int, package_prefix: Optional[str] = None
    ) -> Tuple[bool, float, int]:
        """Get coverage information for a function

        Uses pre-computed path mapping for fast lookups.

        Args:
            file_path: Relative file path
            line_num: Line number of function definition
            package_prefix: Optional package prefix to match in coverage data

        Returns:
            Tuple of (is_covered, coverage_percentage, missing_lines)
        """
        # Try normalized path lookup (single attempt instead of multiple)
        normalized = self._normalize_path(file_path, package_prefix)

        if normalized in self._coverage_path_map:
            file_data = self._coverage_path_map[normalized]
            return self._extract_summary_from_data(file_data, line_num)

        # Fallback: try original path formats (for backward compatibility)
        file_keys = [
            file_path,
            f"{package_prefix}/{file_path}" if package_prefix else file_path,
            file_path.replace("\\", "/"),
        ]

        files_data = self.coverage_data.get("files", {})
        for file_key in file_keys:
            if file_key in files_data:
                return self._extract_summary_from_data(files_data[file_key], line_num)

        # File not in coverage data
        return False, 0.0, 0

    @staticmethod
    def _extract_summary_from_data(file_data: Dict, line_num: int) -> Tuple[bool, float, int]:
        """Helper to extract coverage summary from file data (Friend)"""
        summary = file_data.get("summary", {})
        total_lines = summary.get("num_statements", 0)
        covered_lines = summary.get("covered_lines", 0)

        if total_lines > 0:
            coverage_pct = covered_lines / total_lines
        else:
            coverage_pct = 0.0

        executed_lines = file_data.get("executed_lines", [])
        is_covered = line_num in executed_lines

        missing_lines = file_data.get("missing_lines", [])
        # Count missing lines near function (approximate function coverage)
        function_missing = len([line for line in missing_lines if line_num <= line <= line_num + 50])

        return is_covered, coverage_pct, function_missing

    def calculate_impact_scores(self, package_prefix: Optional[str] = None, progress_monitor=None) -> List[Dict]:
        """Calculate impact scores for all functions

        Args:
            package_prefix: Optional package prefix to filter functions
            progress_monitor: Optional progress monitor for showing progress

        Returns:
            List of function data with impact scores, sorted by impact score
        """
        impact_scores = []

        # Pre-compute all impact scores at once (much faster than per-function calls)
        if progress_monitor:
            task_id = progress_monitor.add_task("[blue]Calculating impact scores", total=1)
            progress_monitor.update_description(task_id, "[blue]Pre-computing all impact scores...")

        all_impacts = self.call_graph.calculate_all_impacts()

        if progress_monitor:
            progress_monitor.complete_task(task_id)
            task_id = progress_monitor.add_task("[blue]Computing impact scores", total=len(all_impacts))

        # Filter functions first to get accurate count
        func_items = list(self.call_graph.graph.items())
        if package_prefix:
            func_items = [(name, data) for name, data in func_items if name.startswith(package_prefix)]

        for func_name, func_data in func_items:
            # Get pre-computed impact
            impact = all_impacts.get(func_name, 0)
            file_path = func_data["file"]
            line_num = func_data["line"]

            if file_path and line_num:
                item = self._create_impact_item(func_name, func_data, impact, package_prefix)
                impact_scores.append(item)

            # Update progress
            if progress_monitor and task_id:
                func_name_short = func_name.split("::")[-1]
                progress_monitor.update_description(task_id, f"[blue]Computing impact scores: {func_name_short}")
                progress_monitor.update(task_id, advance=1)

        # Sort by impact score (highest first)
        impact_scores.sort(key=lambda x: x["impact_score"], reverse=True)

        if progress_monitor and task_id:
            progress_monitor.complete_task(task_id)

        return impact_scores

    def _create_impact_item(self, func_name, func_data, impact, package_prefix):
        """Create a single impact score item"""
        file_path = func_data["file"]
        line_num = func_data["line"]

        is_covered, coverage_pct, missing_lines = self.get_function_coverage(file_path, line_num, package_prefix)

        # Calculate impact score: impact * (1 - coverage)
        impact_score = impact * (1.0 - coverage_pct)

        return {
            "function": func_name,
            "file": file_path,
            "line": line_num,
            "impact": impact,
            "covered": is_covered,
            "coverage_percentage": coverage_pct,
            "missing_lines": missing_lines,
            "impact_score": impact_score,
            "is_method": func_data.get("is_method", False),
            "class_name": func_data.get("class_name"),
        }


def load_coverage_data(coverage_file: Path) -> Dict:
    """Load coverage data from JSON file

    Args:
        coverage_file: Path to coverage.json file

    Returns:
        Coverage data dictionary

    Raises:
        FileNotFoundError: If coverage file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not coverage_file.exists():
        raise FileNotFoundError(f"Coverage file not found: {coverage_file}")

    with open(coverage_file, "r", encoding="utf-8") as f:
        return json.load(f)
