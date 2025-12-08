"""AST-based call graph builder for analyzing function dependencies"""

import ast
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple


class CallGraph:
    """Represents the call graph of a codebase"""

    def __init__(self):
        self.graph: Dict[str, Dict] = defaultdict(
            lambda: {
                "calls": set(),  # Functions this function calls
                "called_by": set(),  # Functions that call this function
                "file": None,
                "line": None,
                "is_method": False,
                "class_name": None,
            }
        )
        self._impact_cache: Dict[str, int] = {}

    def add_function(
        self,
        full_name: str,
        file_path: str,
        line: int,
        is_method: bool = False,
        class_name: Optional[str] = None,
    ) -> None:
        """Add a function definition to the graph"""
        self.graph[full_name]["file"] = file_path
        self.graph[full_name]["line"] = line
        self.graph[full_name]["is_method"] = is_method
        self.graph[full_name]["class_name"] = class_name

    def add_call(self, caller: str, callee: str) -> None:
        """Add a call relationship: caller → callee"""
        self.graph[caller]["calls"].add(callee)
        self.graph[callee]["called_by"].add(caller)

    def _build_class_methods_mapping(self) -> Dict[str, List[str]]:
        """Build mapping of class methods: {ClassName.method_name: [full_names]}

        Returns:
            Dictionary mapping class method keys to lists of full function names
        """
        class_methods: Dict[str, List[str]] = defaultdict(list)

        for full_name, func_data in self.graph.items():
            class_name = func_data.get("class_name")
            if class_name:
                # Extract method name from full_name like "logger.py::SnowfortLogger.error"
                if "::" in full_name and "." in full_name:
                    method_name = full_name.split(".")[-1]
                    key = f"{class_name}.{method_name}"
                    class_methods[key].append(full_name)

        return class_methods

    def _resolve_method_call(self, call: str, class_methods: Dict[str, List[str]]) -> Tuple[List[str], List[str]]:
        """Resolve a single method call to actual method definitions

        Args:
            call: Method call string (e.g., "logger.error" or "self.logger.error")
            class_methods: Mapping of class methods

        Returns:
            Tuple of (calls_to_add, calls_to_remove)
        """
        if "." not in call:
            return [], []

        parts = call.split(".")
        calls_to_add = []
        calls_to_remove = []

        if len(parts) == 2:
            # Simple case: logger.error
            method_name = parts[1]
            matches = self._find_method_matches(method_name, class_methods)
            if matches:
                calls_to_add.extend(matches)
                calls_to_remove.append(call)

        elif len(parts) == 3:
            # Nested: self.logger.error
            method_name = parts[-1]
            matches = self._find_method_matches(method_name, class_methods)
            if matches:
                calls_to_add.extend(matches)
                calls_to_remove.append(call)

        return calls_to_add, calls_to_remove

    def _find_method_matches(self, method_name: str, class_methods: Dict[str, List[str]]) -> List[str]:
        """Find all method definitions matching a method name

        Args:
            method_name: Name of the method to find
            class_methods: Mapping of class methods

        Returns:
            List of matching method full names
        """
        matches = []
        for class_method_key, method_definitions in class_methods.items():
            _, method = class_method_key.split(".", 1)
            if method == method_name:
                matches.extend(method_definitions)

        return matches

    def _update_calls_for_caller(
        self, caller_name: str, caller_data: Dict, calls_to_add: List[str], calls_to_remove: List[str]
    ) -> None:
        """Update call graph for a caller with resolved method calls

        Args:
            caller_name: Name of the calling function
            caller_data: Dictionary containing caller's call graph data
            calls_to_add: List of resolved method calls to add
            calls_to_remove: List of unresolved method calls to remove
        """
        for call_to_remove in calls_to_remove:
            caller_data["calls"].discard(call_to_remove)
            # Remove from called_by as well
            if call_to_remove in self.graph:
                self.graph[call_to_remove]["called_by"].discard(caller_name)

        for call_to_add in calls_to_add:
            caller_data["calls"].add(call_to_add)
            self.graph[call_to_add]["called_by"].add(caller_name)

    def resolve_method_calls(self) -> None:
        """Resolve method calls like logger.error() to actual method definitions

        This matches calls like:
        - logger.error() → SnowfortLogger.error()
        - self.logger.error() → SnowfortLogger.error()
        - obj.method() → ClassName.method()
        """
        class_methods = self._build_class_methods_mapping()

        # Resolve calls for each caller
        for caller_name, caller_data in list(self.graph.items()):
            calls_to_remove = []
            calls_to_add = []

            for call in caller_data["calls"]:
                new_calls_to_add, new_calls_to_remove = self._resolve_method_call(call, class_methods)
                calls_to_add.extend(new_calls_to_add)
                calls_to_remove.extend(new_calls_to_remove)

            # Update calls
            if calls_to_add or calls_to_remove:
                self._update_calls_for_caller(caller_name, caller_data, calls_to_add, calls_to_remove)

    def get_impact(self, function_name: str, visited: Optional[Set[str]] = None) -> int:
        """Calculate total impact (direct + indirect callers) for a function

        Uses memoization to cache results and prevent redundant calculations.
        """
        # Check cache first (only for top-level calls without visited set)
        if visited is None and function_name in self._impact_cache:
            return self._impact_cache[function_name]

        if visited is None:
            visited = set()

        if function_name in visited:
            return 0

        visited.add(function_name)

        # Count direct callers
        direct_calls = len(self.graph[function_name]["called_by"])

        # Count indirect calls (recursively)
        indirect_calls = 0
        for caller in self.graph[function_name]["called_by"]:
            indirect_calls += self.get_impact(caller, visited.copy())

        total_impact = direct_calls + indirect_calls

        # Cache the result (only cache at top level to avoid circular dependency issues)
        if len(visited) == 1:  # Top-level call
            self._impact_cache[function_name] = total_impact

        return total_impact


class CallGraphVisitor(ast.NodeVisitor):
    """AST visitor for extracting function calls"""

    def __init__(self):
        self.calls: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        """Extract function calls from AST"""
        if isinstance(node.func, ast.Name):
            # Direct function call: function()
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Method call: obj.method()
            if isinstance(node.func.value, ast.Name):
                self.calls.add(f"{node.func.value.id}.{node.func.attr}")
            elif isinstance(node.func.value, ast.Attribute):
                # Nested attribute: obj.attr.method()
                attr_chain = self._get_attribute_chain(node.func.value)
                if attr_chain:
                    self.calls.add(f"{attr_chain}.{node.func.attr}")

        self.generic_visit(node)

    def _get_attribute_chain(self, node: ast.Attribute) -> Optional[str]:
        """Build attribute chain string for nested attributes"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            parent = self._get_attribute_chain(node.value)
            return f"{parent}.{node.attr}" if parent else None
        return None


def find_python_files(root: Path, exclude_patterns: Optional[List[str]] = None) -> List[Path]:
    """Find all Python files in the codebase

    Args:
        root: Root directory to search
        exclude_patterns: List of patterns to exclude from file paths relative to root
                         (e.g., ['test', '__pycache__'])

    Returns:
        List of Python file paths
    """
    if exclude_patterns is None:
        exclude_patterns = ["test", "__pycache__"]

    files = []
    root_path = Path(root).resolve()

    for path in root_path.rglob("*.py"):
        # Get path relative to root for pattern matching
        try:
            rel_path = path.relative_to(root_path)
            path_str = str(rel_path)

            # Check if any exclude pattern matches (in directory or filename)
            if not any(pattern in path_str for pattern in exclude_patterns):
                files.append(path)
        except ValueError:
            # Path is outside root, skip
            continue

    return files


def build_call_graph(root: Path, package_prefix: Optional[str] = None) -> CallGraph:
    """Build call graph from codebase AST

    Args:
        root: Root directory of the codebase
        package_prefix: Optional package prefix to filter functions (e.g., "snowfort/")

    Returns:
        CallGraph object with function relationships
    """
    call_graph = CallGraph()
    files = find_python_files(root)
    root_path = Path(root).resolve()

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            file_path_rel = str(file_path.relative_to(root_path))

            # Filter by package prefix if provided (at file level)
            if package_prefix and not file_path_rel.startswith(package_prefix):
                continue

            # Extract all function and method definitions
            class FunctionVisitor(ast.NodeVisitor):
                """Visitor to extract functions and their class context"""

                def __init__(self, call_graph, file_path_rel):
                    self.call_graph = call_graph
                    self.file_path_rel = file_path_rel
                    self.current_class = None

                def visit_ClassDef(self, node):
                    """Track current class"""
                    old_class = self.current_class
                    self.current_class = node.name
                    self.generic_visit(node)
                    self.current_class = old_class

                def visit_FunctionDef(self, node):
                    """Extract function definition"""
                    func_name = node.name

                    # Build full function identifier
                    if self.current_class:
                        full_name = f"{self.file_path_rel}::{self.current_class}.{func_name}"
                        is_method = True
                        class_name = self.current_class
                    else:
                        full_name = f"{self.file_path_rel}::{func_name}"
                        is_method = False
                        class_name = None

                    # Skip private/dunder methods for now
                    if func_name.startswith("__") and func_name.endswith("__"):
                        self.generic_visit(node)
                        return

                    # Add function to graph
                    call_graph.add_function(
                        full_name=full_name,
                        file_path=self.file_path_rel,
                        line=node.lineno,
                        is_method=is_method,
                        class_name=class_name,
                    )

                    # Extract calls within this function
                    visitor = CallGraphVisitor()
                    visitor.visit(node)

                    # Add call relationships
                    for called_func in visitor.calls:
                        call_graph.add_call(caller=full_name, callee=called_func)

                    self.generic_visit(node)

            visitor = FunctionVisitor(call_graph, file_path_rel)
            visitor.visit(tree)

        except (SyntaxError, UnicodeDecodeError, IOError):
            # Skip files that can't be parsed
            continue

    # After building the graph, resolve method calls
    call_graph.resolve_method_calls()

    return call_graph
