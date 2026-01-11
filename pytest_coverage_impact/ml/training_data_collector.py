"""Collect training data by mapping functions to tests and extracting features"""

import ast
import json
import re  # Moved to top
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pytest_coverage_impact.call_graph import build_call_graph, CallGraph
from pytest_coverage_impact.ml.feature_extractor import FeatureExtractor
from pytest_coverage_impact.ml.test_analyzer import TestAnalyzer
from pytest_coverage_impact.utils import (
    parse_ast_tree,
    find_function_node_by_line,
)  # Moved to top


class TrainingDataCollector:
    """Collect training data from codebase"""

    def __init__(self, root: Path, package_prefix: Optional[str] = None):
        """Initialize collector

        Args:
            root: Root directory of codebase
            package_prefix: Optional package prefix to filter functions
        """
        self.root = Path(root).resolve()
        self.package_prefix = package_prefix
        self.call_graph: Optional[CallGraph] = None

    def _build_call_graph(self) -> CallGraph:
        """Build call graph from codebase"""
        print("Building call graph...")
        return build_call_graph(self.root, self.package_prefix)

    def _find_test_files(self) -> List[Path]:
        """Find all test files in codebase"""
        print("Finding test files...")
        test_files = TestAnalyzer.find_test_files(self.root)
        print(f"Found {len(test_files)} test files")
        return test_files

    def _should_include_function(self, _func_name: str, func_data: Dict) -> bool:
        """Check if function should be included in training data

        Args:
            _func_name: Function signature (unused)
            func_data: Function data from call graph

        Returns:
            True if function should be included
        """
        # Filter by package prefix if provided
        if self.package_prefix:
            file_path = func_data.get("file", "")
            if not file_path.startswith(self.package_prefix):
                return False

        file_path = func_data.get("file")
        line_num = func_data.get("line")

        if not file_path or not line_num:
            return False

        # Check if file exists
        func_file = self.root / file_path
        if not func_file.exists():
            return False

        return True

    def _extract_function_node(self, func_file: Path, line_num: int) -> Optional[ast.FunctionDef]:
        """Extract function AST node from file

        Args:
            func_file: Path to function's source file
            line_num: Line number of function definition

        Returns:
            FunctionDef AST node, or None if not found
        """
        return find_function_node_by_line(func_file, line_num)

    def _extract_test_complexity_for_function(
        self, func_file: Path, test_files: List[Path]
    ) -> Tuple[List[float], List[str]]:
        """Extract test complexity labels for a function

        Args:
            func_file: Path to function's source file
            test_files: List of all test files

        Returns:
            Tuple of (test_complexities_list, test_files_used_list)
        """
        test_analyzer = TestAnalyzer()
        # JUSTIFICATION: TestAnalyzer usage for complexity logic
        # pylint: disable=clean-arch-demeter
        test_matches = test_analyzer.map_function_to_tests(func_file, test_files, self.root)

        if not test_matches:
            return [], []

        test_complexities = []
        test_files_used = []

        for test_file in test_matches:
            test_features = test_analyzer.extract_test_complexity(test_file)
            complexity_label = test_analyzer.calculate_complexity_label(test_features)
            test_complexities.append(complexity_label)
            test_files_used.append(str(test_file.relative_to(self.root)))
        # pylint: enable=clean-arch-demeter

        return test_complexities, test_files_used

    def _process_function(self, func_name: str, func_data: Dict, test_files: List[Path]) -> Optional[Dict]:
        """Process a single function to extract training data

        Args:
            func_name: Function signature
            func_data: Function data from call graph
            test_files: List of all test files

        Returns:
            Training data dictionary, or None if function should be skipped
        """
        if not self._should_include_function(func_name, func_data):
            return None

        file_path = func_data.get("file")
        line_num = func_data.get("line")
        func_file = self.root / file_path

        # Find test matches
        test_complexities, test_files_used = self._extract_test_complexity_for_function(func_file, test_files)

        if not test_complexities:
            # No test found - skip for now
            return None

        # Extract function features
        func_node = self._extract_function_node(func_file, line_num)
        if not func_node:
            return None

        # Get module tree for context
        tree = parse_ast_tree(func_file)
        if not tree:
            return None

        features = FeatureExtractor.extract_features(func_node, tree, str(func_file))

        # Use average complexity if multiple tests
        avg_complexity = sum(test_complexities) / len(test_complexities) if test_complexities else 0.0

        return {
            "function_signature": func_name,
            "file_path": file_path,
            "line": line_num,
            "features": features,
            "complexity_label": avg_complexity,
            "test_files": test_files_used,
            "num_tests": len(test_complexities),
        }

    def collect_training_data(self) -> List[Dict]:
        """Collect training data: function features + test complexity labels

        Returns:
            List of training examples, each with:
            - function_signature: str
            - features: Dict[str, float]
            - complexity_label: float (0-1)
            - test_file: str
        """
        # Build call graph
        self.call_graph = self._build_call_graph()

        # Find all test files
        test_files = self._find_test_files()

        # Extract training data
        training_data = []

        for func_name, func_data in self.call_graph.graph.items():
            training_example = self._process_function(func_name, func_data, test_files)
            if training_example:
                training_data.append(training_example)

        print(f"Collected {len(training_data)} training examples")
        return training_data

    def save_training_data(self, training_data: List[Dict], output_path: Path, version: Optional[str] = None) -> str:
        """Save training data to JSON file

        Args:
            training_data: List of training examples
            output_path: Path to save JSON file
            version: Optional version string (if None, extracted from filename)

        Returns:
            Version string used
        """
        # JUSTIFICATION: mkdir is safe on Path parent
        # pylint: disable=clean-arch-demeter
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # pylint: enable=clean-arch-demeter

        # Extract version from filename if not provided
        if version is None:
            match = re.search(r"v(\d+\.\d+)", output_path.name)
            if match:
                # JUSTIFICATION: Regex match group access is safe
                # pylint: disable=clean-arch-demeter
                version = match.group(1)
                # pylint: enable=clean-arch-demeter
            else:
                version = "1.0"

        dataset = {
            "version": version,
            "total_examples": len(training_data),
            "examples": training_data,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        print(f"Saved training data to {output_path}")
        return version


def collect_training_data_from_codebase(root: Path, output_path: Path, package_prefix: Optional[str] = None) -> Path:
    """Convenience function to collect and save training data

    Args:
        root: Root directory of codebase
        output_path: Path to save training data JSON (can be directory for auto-versioning)
        package_prefix: Optional package prefix to filter functions

    Returns:
        Path to saved training data file
    """
    collector = TrainingDataCollector(root, package_prefix)
    # JUSTIFICATION: Factory function convenience wrapper
    # pylint: disable=clean-arch-demeter
    training_data = collector.collect_training_data()
    # pylint: enable=clean-arch-demeter

    # Extract version from filename if present
    match = re.search(r"v(\d+\.\d+)", output_path.name)
    # JUSTIFICATION: Regex match group access is safe
    # pylint: disable=clean-arch-demeter
    version = match.group(1) if match else None
    # pylint: enable=clean-arch-demeter

    # JUSTIFICATION: Delegating to collector instance
    # pylint: disable=clean-arch-demeter
    collector.save_training_data(training_data, output_path, version=version)
    # pylint: enable=clean-arch-demeter
    return output_path
