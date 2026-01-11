"""Unit tests for call graph builder"""

import ast
from pathlib import Path
from pytest_coverage_impact.call_graph import (
    CallGraph,
    CallGraphVisitor,
    find_python_files,
    FunctionMetadata,
)


def test_call_graph_initialization():
    """Test CallGraph initialization"""
    graph = CallGraph()
    assert graph.graph == {}


def test_call_graph_add_function():
    """Test adding functions to call graph"""
    graph = CallGraph()
    metadata = FunctionMetadata(full_name="module.py::func1", file_path="module.py", line=10)
    graph.add_function(metadata)

    assert "module.py::func1" in graph.graph
    assert graph.graph["module.py::func1"]["file"] == "module.py"
    assert graph.graph["module.py::func1"]["line"] == 10


def test_call_graph_add_call():
    """Test adding call relationships"""
    graph = CallGraph()
    graph.add_function(FunctionMetadata("module.py::caller", "module.py", 10))
    graph.add_function(FunctionMetadata("module.py::callee", "module.py", 20))
    graph.add_call("module.py::caller", "module.py::callee")

    assert "module.py::callee" in graph.graph["module.py::caller"]["calls"]
    assert "module.py::caller" in graph.graph["module.py::callee"]["called_by"]


def test_call_graph_get_impact():
    """Test impact calculation"""
    graph = CallGraph()

    # Create a simple call chain: func1 -> func2 -> func3
    graph.add_function(FunctionMetadata("module.py::func1", "module.py", 10))
    graph.add_function(FunctionMetadata("module.py::func2", "module.py", 20))
    graph.add_function(FunctionMetadata("module.py::func3", "module.py", 30))

    graph.add_call("module.py::func1", "module.py::func2")
    graph.add_call("module.py::func2", "module.py::func3")

    # Pre-compute all impacts (required for get_impact to work)
    graph.calculate_all_impacts()

    # func3 has 2 indirect callers (func1, func2)
    impact = graph.get_impact("module.py::func3")
    assert impact == 2


def test_call_graph_visitor():
    """Test AST visitor for function calls"""
    code = """
def func1():
    func2()
    obj.method()
"""
    tree = ast.parse(code)

    visitor = CallGraphVisitor()
    visitor.visit(tree)

    assert "func2" in visitor.calls
    assert "obj.method" in visitor.calls


def test_find_python_files(tmp_path: Path):
    """Test finding Python files"""
    # Create test structure
    (tmp_path / "module1.py").write_text("def func(): pass")
    (tmp_path / "module2.py").write_text("def func(): pass")
    (tmp_path / "test_file.py").write_text("def func(): pass")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "module1.pyc").write_bytes(b"fake")

    files = find_python_files(tmp_path, exclude_patterns=["test", "__pycache__"])

    # Should exclude test_file.py and __pycache__ files
    file_names = [f.name for f in files]
    assert "test_file.py" not in file_names
    assert "module1.py" in file_names
    assert "module2.py" in file_names
    assert len([f for f in files if "__pycache__" in str(f)]) == 0
