"""Calculate coverage impact scores for functions"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pytest_coverage_impact.call_graph import CallGraph


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

    def get_function_coverage(
        self, file_path: str, line_num: int, package_prefix: Optional[str] = None
    ) -> Tuple[bool, float, int]:
        """Get coverage information for a function

        Args:
            file_path: Relative file path
            line_num: Line number of function definition
            package_prefix: Optional package prefix to match in coverage data

        Returns:
            Tuple of (is_covered, coverage_percentage, missing_lines)
        """
        # Try different file path formats to match coverage data
        file_keys = [
            file_path,
            f"{package_prefix}/{file_path}" if package_prefix else file_path,
            file_path.replace("\\", "/"),  # Normalize path separators
        ]

        files_data = self.coverage_data.get("files", {})

        for file_key in file_keys:
            if file_key in files_data:
                file_data = files_data[file_key]
                summary = file_data.get("summary", {})

                total_lines = summary.get("num_statements", 0)
                covered_lines = summary.get("covered_lines", 0)

                if total_lines > 0:
                    coverage_pct = covered_lines / total_lines
                else:
                    coverage_pct = 0.0

                # Check if function line is covered
                executed_lines = file_data.get("executed_lines", [])
                is_covered = line_num in executed_lines

                # Count missing lines near function (approximate function coverage)
                missing_lines = file_data.get("missing_lines", [])
                function_missing = len([line for line in missing_lines if line_num <= line <= line_num + 50])

                return is_covered, coverage_pct, function_missing

        # File not in coverage data
        return False, 0.0, 0

    def calculate_impact_scores(self, package_prefix: Optional[str] = None) -> List[Dict]:
        """Calculate impact scores for all functions

        Args:
            package_prefix: Optional package prefix to filter functions

        Returns:
            List of function data with impact scores, sorted by impact score
        """
        impact_scores = []

        for func_name, func_data in self.call_graph.graph.items():
            # Filter by package prefix if provided
            if package_prefix:
                if not func_name.startswith(package_prefix):
                    continue

            # Calculate impact (call frequency)
            impact = self.call_graph.get_impact(func_name)

            # Get coverage info
            file_path = func_data["file"]
            line_num = func_data["line"]

            if file_path and line_num:
                is_covered, coverage_pct, missing_lines = self.get_function_coverage(
                    file_path, line_num, package_prefix
                )

                # Calculate impact score: impact * (1 - coverage)
                impact_score = impact * (1.0 - coverage_pct)

                impact_scores.append(
                    {
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
                )

        # Sort by impact score (highest first)
        impact_scores.sort(key=lambda x: x["impact_score"], reverse=True)

        return impact_scores


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
