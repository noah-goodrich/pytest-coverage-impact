"""AST-based call graph builder for analyzing function dependencies"""

import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from pytest_coverage_impact.gateways.utils import extract_method_name_from_full_name


@dataclass
class FunctionMetadata:
    """Metadata for a function definition"""

    full_name: str
    file_path: str
    line: int
    is_method: bool = False
    class_name: Optional[str] = None


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

    def add_function(self, metadata: FunctionMetadata) -> None:
        """Add a function definition to the graph"""
        self.graph[metadata.full_name]["file"] = metadata.file_path
        self.graph[metadata.full_name]["line"] = metadata.line
        self.graph[metadata.full_name]["is_method"] = metadata.is_method
        self.graph[metadata.full_name]["class_name"] = metadata.class_name

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
                    method_name = extract_method_name_from_full_name(full_name)
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
        self,
        caller_name: str,
        caller_data: Dict,
        calls_to_add: List[str],
        calls_to_remove: List[str],
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

    def resolve_method_calls(self, progress_monitor=None) -> None:
        """Resolve method calls like logger.error() to actual method definitions

        This matches calls like:
        - logger.error() → SnowfortLogger.error()
        - self.logger.error() → SnowfortLogger.error()
        - obj.method() → ClassName.method()

        Args:
            progress_monitor: Optional progress monitor for showing progress
        """
        class_methods = self._build_class_methods_mapping()

        # Create progress task if monitor provided
        task_id = None
        if progress_monitor:
            total_callers = len(self.graph)
            task_id = progress_monitor.add_task("[yellow]Resolving method calls", total=total_callers)

        # Resolve calls for each caller
        for idx, (caller_name, caller_data) in enumerate(list(self.graph.items())):
            calls_to_remove = []
            calls_to_add = []

            for call in caller_data["calls"]:
                new_calls_to_add, new_calls_to_remove = self._resolve_method_call(call, class_methods)
                calls_to_add.extend(new_calls_to_add)
                calls_to_remove.extend(new_calls_to_remove)

            # Update calls
            if calls_to_add or calls_to_remove:
                self._update_calls_for_caller(caller_name, caller_data, calls_to_add, calls_to_remove)

            # Update progress
            if progress_monitor and task_id:
                if (idx + 1) % 100 == 0 or idx == len(self.graph) - 1:
                    progress_monitor.update(
                        task_id,
                        advance=1,
                        description=f"[yellow]Resolving method calls: {idx + 1}/{total_callers}",
                    )

        if progress_monitor and task_id:
            progress_monitor.complete_task(task_id)

    def calculate_all_impacts(self) -> Dict[str, int]:
        """Calculate impact scores for all functions using dynamic programming

        Impact = direct_callers + sum(impact of all direct_callers)
        This is much faster than calling get_impact() for each function individually.

        Uses memoization and processes functions in dependency order to avoid redundant calculations.

        Returns:
            Dictionary mapping function names to their impact scores
        """
        visited: Set[str] = set()

        def compute_impact(func_name: str) -> int:
            """Compute impact for a function using memoization"""
            # Check cache first
            if func_name in self._impact_cache:
                return self._impact_cache[func_name]

            # Check for cycles
            if func_name in visited:
                # Cycle detected - return 0 to break recursion
                return 0

            visited.add(func_name)

            # Count direct callers
            direct_calls = len(self.graph[func_name]["called_by"])

            # Count indirect calls: sum of impacts of all direct callers
            indirect_calls = 0
            for caller in self.graph[func_name]["called_by"]:
                indirect_calls += compute_impact(caller)

            total_impact = direct_calls + indirect_calls

            # Cache and return
            self._impact_cache[func_name] = total_impact
            visited.remove(func_name)  # Remove from visited after processing

            return total_impact

        # Compute impact for all functions
        for func_name in self.graph:
            if func_name not in self._impact_cache:
                compute_impact(func_name)

        # Return all cached impacts
        return dict(self._impact_cache)

    def get_impact(self, function_name: str) -> int:
        """Calculate total impact (direct + indirect callers) for a function

        Uses cached results from calculate_all_impacts() - always call calculate_all_impacts()
        first for best performance.
        """
        # Get from cache (should be populated by calculate_all_impacts)
        return self._impact_cache.get(function_name, 0)


class CallGraphVisitor(ast.NodeVisitor):
    """AST visitor for extracting function calls"""

    def __init__(self):
        self.calls: Set[str] = set()

    def visit(self, node: ast.AST) -> None:
        """Override visit to dispatch custom method names"""
        if isinstance(node, ast.Call):
            self.extract_call(node)
        self.generic_visit(node)

    def extract_call(self, node: ast.Call) -> None:
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

    def _get_attribute_chain(self, node: ast.Attribute) -> Optional[str]:
        """Build attribute chain string for nested attributes"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        if isinstance(node.value, ast.Attribute):
            parent = self._get_attribute_chain(node.value)
            return f"{parent}.{node.attr}" if parent else None
        return None


class FunctionVisitor(ast.NodeVisitor):
    """Visitor to extract functions and their class context"""

    def __init__(self, call_graph, file_path_rel):
        self.call_graph = call_graph
        self.file_path_rel = file_path_rel
        self.current_class = None
        self.is_interface_class = False

    # JUSTIFICATION: Required by ast.NodeVisitor interface which uses camelCase for visit_ methods
    def visit_ClassDef(self, node: ast.ClassDef):  # pylint: disable=invalid-name
        """Track current class and check if it's an interface"""
        old_class = self.current_class
        old_is_interface = self.is_interface_class

        self.current_class = node.name
        self.is_interface_class = self._check_if_interface(node)

        self.generic_visit(node)

        self.current_class = old_class
        self.is_interface_class = old_is_interface

    # JUSTIFICATION: Required by ast.NodeVisitor interface which uses camelCase for visit_ methods
    def visit_FunctionDef(self, node: ast.FunctionDef):  # pylint: disable=invalid-name
        """Extract function definition"""
        func_name = node.name

        # Skip private/dunder methods
        if func_name.startswith("__") and func_name.endswith("__"):
            self.generic_visit(node)
            return

        # Filter out interface stubs and empty methods
        if self.is_interface_class or self._is_empty_function(node):
            self.generic_visit(node)
            return

        # Build full function identifier
        if self.current_class:
            full_name = f"{self.file_path_rel}::{self.current_class}.{func_name}"
            is_method = True
            class_name = self.current_class
        else:
            full_name = f"{self.file_path_rel}::{func_name}"
            is_method = False
            class_name = None

        # Add function to graph
        self.call_graph.add_function(
            FunctionMetadata(
                full_name=full_name,
                file_path=self.file_path_rel,
                line=node.lineno,
                is_method=is_method,
                class_name=class_name,
            )
        )

        # Extract calls within this function
        visitor = CallGraphVisitor()
        self._run_visitor(visitor, node)

        # Add call relationships
        for called_func in visitor.calls:
            self.call_graph.add_call(caller=full_name, callee=called_func)

        self.generic_visit(node)

    def _check_if_interface(self, node):
        """Check if class inherits from Protocol or ABC"""
        for base in node.bases:
            # Match 'Protocol', 'ABC', 'typing.Protocol', 'abc.ABC'
            if isinstance(base, ast.Name) and base.id in ("Protocol", "ABC"):
                return True
            if isinstance(base, ast.Attribute) and base.attr in ("Protocol", "ABC"):
                return True
        return False

    def _is_empty_function(self, node):
        """Check if function only contains docstrings, ellipsis, or pass"""
        for stmt in node.body:
            # Skip docstrings and Ellipsis (...)
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue
            # Skip pass
            if isinstance(stmt, ast.Pass):
                continue
            # Skip raise NotImplementedError
            if isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Name) and stmt.exc.id == "NotImplementedError":
                    continue
                if (
                    isinstance(stmt.exc, ast.Call)
                    and isinstance(stmt.exc.func, ast.Name)
                    and stmt.exc.func.id == "NotImplementedError"
                ):
                    continue
            # If we found anything else, it's not empty
            return False
        return True

    @staticmethod
    def _run_visitor(visitor, node):
        """Helper to run AST visitor (Friend)"""
        visitor.visit(node)


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


def build_call_graph(root: Path, package_prefix: Optional[str] = None, progress_monitor=None) -> CallGraph:
    """Build call graph from codebase AST

    Args:
        root: Root directory of the codebase
        package_prefix: Optional package prefix to filter functions (e.g., "snowfort/")
        progress_monitor: Optional progress monitor for showing progress

    Returns:
        CallGraph object with function relationships
    """
    call_graph = CallGraph()
    files = find_python_files(root)
    root_path = Path(root).resolve()

    # Create progress task for file parsing
    file_task_id = None
    if progress_monitor:
        file_task_id = progress_monitor.add_task("[green]Parsing files", total=len(files))

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            file_path_rel = str(file_path.relative_to(root_path))

            # Filter by package prefix if provided (at file level)
            if package_prefix and not file_path_rel.startswith(package_prefix):
                # Prefix might be part of the path, startswith is safer.
                # e.g. prefix "pytest_coverage_impact", file "pytest_coverage_impact/plugin.py"
                continue

            # Extract all function and method definitions
            visitor = FunctionVisitor(call_graph, file_path_rel)
            _run_visitor(visitor, tree)

            # Update progress with current file
            if progress_monitor and file_task_id:
                file_name = _get_filename(file_path_rel)
                progress_monitor.update_description(file_task_id, f"[green]Parsing files: {file_name}")
                progress_monitor.update(file_task_id, advance=1)

        except (SyntaxError, UnicodeDecodeError, IOError):
            # Skip files that can't be parsed
            if progress_monitor and file_task_id:
                progress_monitor.update(file_task_id, advance=1)
            continue

    # After building the graph, resolve method calls
    _resolve_calls(call_graph, progress_monitor)

    if progress_monitor and file_task_id:
        progress_monitor.complete_task(file_task_id)

    return call_graph


def _run_visitor(visitor, tree):
    """Helper to run AST visitor (Friend)"""
    visitor.visit(tree)


def _get_filename(path_str):
    """Helper to get filename from path (Friend)"""
    return path_str.rsplit("/", 1)[-1]


def _resolve_calls(call_graph, progress_monitor):
    """Helper to resolve method calls (Friend)"""
    call_graph.resolve_method_calls(progress_monitor=progress_monitor)
