"""Extract static code features from functions for ML complexity estimation"""

import ast
from typing import Dict, List, Optional


class FeatureExtractor:
    """Extract static code features from function AST nodes"""

    @staticmethod
    def extract_features(
        func_node: ast.FunctionDef,
        module_tree: Optional[ast.AST] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, float]:
        """Extract features from a function AST node

        Args:
            func_node: Function definition AST node
            module_tree: Optional full module AST for context
            file_path: Optional file path for external dependency detection

        Returns:
            Dictionary of feature names to values
        """
        features = {}

        # Size metrics
        features["lines_of_code"] = FeatureExtractor._count_lines(func_node)
        features["num_statements"] = FeatureExtractor._count_statements(func_node)
        features["cyclomatic_complexity"] = FeatureExtractor._cyclomatic_complexity(func_node)
        features["num_parameters"] = len(func_node.args.args)
        features["has_variadic_args"] = func_node.args.vararg is not None or func_node.args.kwarg is not None

        # Control flow complexity
        features["num_branches"] = FeatureExtractor._count_branches(func_node)
        features["num_loops"] = FeatureExtractor._count_loops(func_node)
        features["num_exceptions"] = FeatureExtractor._count_exceptions(func_node)
        features["num_returns"] = FeatureExtractor._count_returns(func_node)

        # Dependency metrics
        calls = FeatureExtractor._extract_function_calls(func_node)
        features["num_function_calls"] = len(calls)
        features["num_unique_calls"] = len(set(calls))

        # Type indicators
        features["is_method"] = FeatureExtractor._is_method(func_node, module_tree)
        features["is_async"] = isinstance(func_node, ast.AsyncFunctionDef)

        # External interaction indicators
        if file_path:
            features["uses_filesystem"] = FeatureExtractor._detect_filesystem_usage(func_node)
            features["uses_network"] = FeatureExtractor._detect_network_usage(func_node)
            features["uses_snowflake"] = FeatureExtractor._detect_snowflake_usage(func_node)
        else:
            features["uses_filesystem"] = 0.0
            features["uses_network"] = 0.0
            features["uses_snowflake"] = 0.0

        return features

    @staticmethod
    def _count_lines(func_node: ast.FunctionDef) -> float:
        """Count approximate lines of code in function"""
        if not func_node.body:
            return 1.0
        return float(func_node.end_lineno - func_node.lineno + 1)

    @staticmethod
    def _count_statements(func_node: ast.FunctionDef) -> float:
        """Count statements in function body"""
        count = 0
        for node in ast.walk(func_node):
            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AugAssign,
                    ast.AnnAssign,
                    ast.Return,
                    ast.Delete,
                    ast.Pass,
                    ast.Break,
                    ast.Continue,
                    ast.Raise,
                    ast.Assert,
                ),
            ):
                count += 1
        return float(count)

    @staticmethod
    def _cyclomatic_complexity(func_node: ast.FunctionDef) -> float:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1

        return float(complexity)

    @staticmethod
    def _count_branches(func_node: ast.FunctionDef) -> float:
        """Count branch statements (if/elif/else)"""
        count = 0
        for node in ast.walk(func_node):
            if isinstance(node, ast.If):
                count += 1
                if node.orelse:
                    count += len([n for n in node.orelse if isinstance(n, ast.If)])
        return float(count)

    @staticmethod
    def _count_loops(func_node: ast.FunctionDef) -> float:
        """Count loop statements"""
        count = 0
        for node in ast.walk(func_node):
            if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                count += 1
        return float(count)

    @staticmethod
    def _count_exceptions(func_node: ast.FunctionDef) -> float:
        """Count exception handlers"""
        count = 0
        for node in ast.walk(func_node):
            if isinstance(node, ast.Try):
                count += len(node.handlers)
        return float(count)

    @staticmethod
    def _count_returns(func_node: ast.FunctionDef) -> float:
        """Count return statements"""
        count = 0
        for node in ast.walk(func_node):
            if isinstance(node, ast.Return):
                count += 1
        return float(count)

    @staticmethod
    def _extract_function_calls(func_node: ast.FunctionDef) -> List[str]:
        """Extract function call names from function"""
        calls = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        calls.append(f"{node.func.value.id}.{node.func.attr}")

        return calls

    @staticmethod
    def _is_method(func_node: ast.FunctionDef, module_tree: Optional[ast.AST]) -> float:
        """Check if function is a method (belongs to a class)"""
        if module_tree is None:
            return 0.0

        for node in ast.walk(module_tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item == func_node:
                        return 1.0

        return 0.0

    @staticmethod
    def _detect_filesystem_usage(func_node: ast.FunctionDef) -> float:
        """Detect filesystem access (open, Path, etc.)"""
        filesystem_keywords = {"open", "read", "write", "Path", "file", "filepath"}

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in filesystem_keywords:
                        return 1.0
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in filesystem_keywords:
                        return 1.0

        return 0.0

    @staticmethod
    def _detect_network_usage(func_node: ast.FunctionDef) -> float:
        """Detect network calls (requests, urllib, etc.)"""
        network_keywords = {"request", "get", "post", "urlopen", "fetch", "http"}

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if any(keyword in node.func.id.lower() for keyword in network_keywords):
                        return 1.0
                elif isinstance(node.func, ast.Attribute):
                    if any(keyword in node.func.attr.lower() for keyword in network_keywords):
                        return 1.0

        return 0.0

    @staticmethod
    def _detect_snowflake_usage(func_node: ast.FunctionDef) -> float:
        """Detect Snowflake/Snowpark API usage"""
        snowflake_keywords = {"snowflake", "snowpark", "session", "snowpark"}

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if any(keyword in node.func.id.lower() for keyword in snowflake_keywords):
                        return 1.0
                elif isinstance(node.func, ast.Attribute):
                    attr_lower = node.func.attr.lower()
                    if any(keyword in attr_lower for keyword in snowflake_keywords):
                        return 1.0

        return 0.0
