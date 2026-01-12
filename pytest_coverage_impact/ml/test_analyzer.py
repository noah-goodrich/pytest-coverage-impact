"""Analyze test files to extract complexity features and map to functions"""

import ast
from pathlib import Path
from typing import Dict, List


class TestAnalyzer:
    """Analyze test files to extract complexity features"""

    @staticmethod
    def find_test_files(root: Path, test_pattern: str = "test_*.py") -> List[Path]:
        """Find all test files in the codebase

        Args:
            root: Root directory to search
            test_pattern: Glob pattern for test files

        Returns:
            List of test file paths
        """
        test_files = []
        for path in root.rglob(test_pattern):
            if "__pycache__" not in str(path):
                test_files.append(path)
        return test_files

    @staticmethod
    def map_function_to_tests(function_file: Path, test_files: List[Path], root: Path) -> List[Path]:
        """Map a function file to its corresponding test files

        Uses naming convention: test_<module_name>.py tests <module_name>.py

        Args:
            function_file: Path to the function's source file
            test_files: List of all test files
            root: Root directory of the project

        Returns:
            List of test file paths that test this function
        """
        # Get relative path from root
        try:
            rel_path = function_file.relative_to(root)
        except ValueError:
            return []

        # Extract module name (without .py)
        module_name = rel_path.stem

        # Find test files that match this module
        matching_tests = []
        for test_file in test_files:
            try:
                test_rel = test_file.relative_to(root)
                # Check if test file is in tests/ directory and matches module
                if "test" in str(test_rel.parent).lower():
                    # Pattern: test_<module_name>.py or test_<module_name>_*.py
                    test_name = test_rel.stem
                    if test_name.startswith("test_") and module_name in test_name:
                        matching_tests.append(test_file)
            except ValueError:
                continue

        return matching_tests

    @staticmethod
    def extract_test_complexity(test_file: Path) -> Dict[str, float]:
        """Extract complexity features from a test file

        Args:
            test_file: Path to test file

        Returns:
            Dictionary of test complexity features
        """
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(test_file))
        except (SyntaxError, UnicodeDecodeError, IOError):
            return {
                "test_lines": 0.0,
                "num_assertions": 0.0,
                "num_test_cases": 0.0,
                "num_mocks": 0.0,
                "num_fixtures": 0.0,
                "has_integration_marker": 0.0,
                "has_e2e_marker": 0.0,
                "has_slow_marker": 0.0,
            }

        # JUSTIFICATION: Internal static method calls
        # pylint: disable=clean-arch-visibility
        features = {
            "test_lines": TestAnalyzer._count_test_lines(tree),
            "num_assertions": TestAnalyzer._count_assertions(tree),
            "num_test_cases": TestAnalyzer._count_test_functions(tree),
            "num_mocks": TestAnalyzer._count_mocks(tree),
            "num_fixtures": TestAnalyzer._count_fixtures(tree),
            "has_integration_marker": TestAnalyzer._has_marker(tree, "integration"),
            "has_e2e_marker": TestAnalyzer._has_marker(tree, "e2e"),
            "has_slow_marker": TestAnalyzer._has_marker(tree, "slow"),
        }
        # pylint: enable=clean-arch-visibility

        return features

    @staticmethod
    def calculate_complexity_label(test_features: Dict[str, float]) -> float:
        """Calculate normalized complexity label from test features

        Formula: min(1.0, (test_lines/100) + (num_mocks*0.1) +
                 (has_integration*0.3) + (has_e2e*0.5))

        Args:
            test_features: Dictionary of test complexity features

        Returns:
            Normalized complexity score (0-1)
        """
        test_lines = test_features.get("test_lines", 0.0)
        num_mocks = test_features.get("num_mocks", 0.0)
        has_integration = test_features.get("has_integration_marker", 0.0)
        has_e2e = test_features.get("has_e2e_marker", 0.0)

        complexity = (test_lines / 100.0) + (num_mocks * 0.1) + (has_integration * 0.3) + (has_e2e * 0.5)

        return min(1.0, complexity)

    @staticmethod
    def _count_test_lines(tree: ast.AST) -> float:
        """Count total lines in test functions"""
        total_lines = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    if node.end_lineno and node.lineno:
                        total_lines += node.end_lineno - node.lineno + 1
        return float(total_lines)

    @staticmethod
    def _count_assertions(tree: ast.AST) -> float:
        """Count assertion statements"""
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                count += 1
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in (
                        "assert",
                        "assertEqual",
                        "assertTrue",
                        "assertFalse",
                        "assertIn",
                        "assertIs",
                        "assertIsNone",
                        "assertRaises",
                    ):
                        count += 1
        return float(count)

    @staticmethod
    def _count_test_functions(tree: ast.AST) -> float:
        """Count test functions (functions starting with test_)"""
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    count += 1
        return float(count)

    @staticmethod
    def _count_mocks(tree: ast.AST) -> float:
        """Count mock usage (MagicMock, Mock, patch, etc.)"""
        count = 0
        mock_keywords = {"mock", "MagicMock", "Mock", "patch", "mocker"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in mock_keywords:
                        count += 1
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in mock_keywords:
                        count += 1

        return float(count)

    @staticmethod
    def _count_fixture_decorators(tree: ast.AST) -> float:
        """Count @pytest.fixture decorators"""
        # JUSTIFICATION: Nested loops required for AST traversal
        # pylint: disable=too-many-nested-blocks
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr == "fixture":
                                count += 1
                    elif isinstance(decorator, ast.Name):
                        if decorator.id == "fixture":
                            count += 1
        return float(count)

    @staticmethod
    def _count_fixture_parameters(tree: ast.AST) -> float:
        """Count fixture parameters in test functions"""
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    # Fixtures are typically parameters in test functions
                    if arg.arg not in ("self", "cls"):
                        count += 0.5  # Count as half (might be regular param)
        return float(count)

    @staticmethod
    def _count_fixtures(tree: ast.AST) -> float:
        """Count pytest fixtures used"""
        # JUSTIFICATION: Internal static method calls
        # pylint: disable=clean-arch-visibility
        decorator_count = TestAnalyzer._count_fixture_decorators(tree)
        parameter_count = TestAnalyzer._count_fixture_parameters(tree)
        # pylint: enable=clean-arch-visibility
        return float(decorator_count + parameter_count)

    @staticmethod
    def _check_decorator_for_marker(decorator: ast.expr, marker_name: str) -> bool:
        """Check if a decorator represents a pytest marker

        Args:
            decorator: AST node for decorator
            marker_name: Name of marker to check for

        Returns:
            True if decorator is the specified marker
        """
        if not isinstance(decorator, ast.Call):
            return False

        if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != "mark":
            return False

        # Check args for marker name
        for arg in decorator.args:
            if isinstance(arg, ast.Name) and arg.id == marker_name:
                return True
            if isinstance(arg, ast.Constant) and arg.value == marker_name:
                return True
        return False

    @staticmethod
    def _has_marker(tree: ast.AST, marker_name: str) -> float:
        """Check if test file has a specific pytest marker"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # JUSTIFICATION: Internal static method calls
                    # pylint: disable=clean-arch-visibility
                    if TestAnalyzer._check_decorator_for_marker(decorator, marker_name):
                        return 1.0
                    # pylint: enable=clean-arch-visibility
        return 0.0
