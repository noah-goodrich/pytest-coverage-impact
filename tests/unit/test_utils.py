"""Unit tests for utility functions"""

import ast
from pathlib import Path


from pytest_coverage_impact.gateways.utils import (
    find_function_node_by_line,
    parse_ast_tree,
    resolve_model_path_with_auto_detect,
    resolve_path,
)


def test_resolve_path_relative():
    """Test resolving a relative path"""
    project_root = Path("/project")
    relative_path = Path("models/model.pkl")

    result = resolve_path(relative_path, project_root)
    assert result == Path("/project/models/model.pkl").resolve()


def test_resolve_path_absolute():
    """Test resolving an absolute path (should not change)"""
    project_root = Path("/project")
    absolute_path = Path("/absolute/path/model.pkl")

    result = resolve_path(absolute_path, project_root)
    assert result == Path("/absolute/path/model.pkl").resolve()


def test_resolve_model_path_with_auto_detect_file_exists(tmp_path):
    """Test resolving model path when file exists"""
    project_root = tmp_path / "project"
    project_root.mkdir()
    model_file = project_root / "model.pkl"
    model_file.write_bytes(b"model data")

    result = resolve_model_path_with_auto_detect("model.pkl", project_root)
    assert result == model_file.resolve()


def test_resolve_model_path_with_auto_detect_file_not_found(tmp_path):
    """Test resolving model path when file doesn't exist"""
    project_root = tmp_path / "project"
    project_root.mkdir()

    result = resolve_model_path_with_auto_detect("nonexistent.pkl", project_root)
    assert result is None


def test_resolve_model_path_with_auto_detect_directory(tmp_path):
    """Test resolving model path from directory with versioned files"""
    project_root = tmp_path / "project"
    project_root.mkdir()
    model_dir = project_root / "models"
    model_dir.mkdir()

    # Create versioned model files
    (model_dir / "complexity_model_v1.0.pkl").write_bytes(b"v1.0")
    (model_dir / "complexity_model_v1.1.pkl").write_bytes(b"v1.1")
    (model_dir / "complexity_model_v2.0.pkl").write_bytes(b"v2.0")

    result = resolve_model_path_with_auto_detect("models", project_root)
    assert result == (model_dir / "complexity_model_v2.0.pkl").resolve()


def test_resolve_model_path_with_auto_detect_empty_directory(tmp_path):
    """Test resolving model path from empty directory"""
    project_root = tmp_path / "project"
    project_root.mkdir()
    model_dir = project_root / "models"
    model_dir.mkdir()

    result = resolve_model_path_with_auto_detect("models", project_root)
    assert result is None


def test_parse_ast_tree_valid_file(tmp_path):
    """Test parsing a valid Python file"""
    python_file = tmp_path / "test.py"
    python_file.write_text("def hello():\n    return 'world'\n")

    tree = parse_ast_tree(python_file)
    assert tree is not None
    assert isinstance(tree, ast.Module)
    assert len(tree.body) == 1
    assert isinstance(tree.body[0], ast.FunctionDef)
    assert tree.body[0].name == "hello"


def test_parse_ast_tree_invalid_syntax(tmp_path):
    """Test parsing a file with invalid syntax"""
    python_file = tmp_path / "invalid.py"
    python_file.write_text("def hello(\n    # Invalid syntax\n")

    tree = parse_ast_tree(python_file)
    assert tree is None


def test_parse_ast_tree_nonexistent_file(tmp_path):
    """Test parsing a nonexistent file"""
    nonexistent_file = tmp_path / "nonexistent.py"

    tree = parse_ast_tree(nonexistent_file)
    assert tree is None


def test_find_function_node_by_line_found(tmp_path):
    """Test finding a function node by line number"""
    python_file = tmp_path / "test.py"
    python_file.write_text("def first():\n    pass\n\ndef second():\n    pass\n")

    func_node = find_function_node_by_line(python_file, 1)
    assert func_node is not None
    assert isinstance(func_node, ast.FunctionDef)
    assert func_node.name == "first"

    func_node = find_function_node_by_line(python_file, 4)
    assert func_node is not None
    assert isinstance(func_node, ast.FunctionDef)
    assert func_node.name == "second"


def test_find_function_node_by_line_not_found(tmp_path):
    """Test finding a function node when line doesn't contain a function"""
    python_file = tmp_path / "test.py"
    python_file.write_text("def hello():\n    return 'world'\n")

    func_node = find_function_node_by_line(python_file, 2)
    assert func_node is None


def test_find_function_node_by_line_invalid_file(tmp_path):
    """Test finding function node in invalid file"""
    python_file = tmp_path / "invalid.py"
    python_file.write_text("invalid syntax here\n")

    func_node = find_function_node_by_line(python_file, 1)
    assert func_node is None


def test_resolve_model_path_with_auto_detect_custom_prefix_suffix(tmp_path):
    """Test resolving model path with custom prefix and suffix"""
    project_root = tmp_path / "project"
    project_root.mkdir()
    model_dir = project_root / "models"
    model_dir.mkdir()

    # Create versioned files with custom prefix
    (model_dir / "custom_v1.0.json").write_bytes(b'{"version": "1.0"}')
    (model_dir / "custom_v2.0.json").write_bytes(b'{"version": "2.0"}')

    result = resolve_model_path_with_auto_detect("models", project_root, prefix="custom_v", suffix=".json")
    assert result == (model_dir / "custom_v2.0.json").resolve()
