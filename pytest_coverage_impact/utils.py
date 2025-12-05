"""Utility functions for path resolution and AST operations"""

import ast
from pathlib import Path
from typing import Optional


def resolve_path(path: Path, project_root: Path) -> Path:
    """Resolve a path relative to project root if not absolute

    Args:
        path: Path to resolve (can be absolute or relative)
        project_root: Project root directory

    Returns:
        Resolved absolute path
    """
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def resolve_model_path_with_auto_detect(
    path_str: str, project_root: Path, prefix: str = "complexity_model_v", suffix: str = ".pkl"
) -> Optional[Path]:
    """Resolve model path from string with automatic version detection for directories

    Args:
        path_str: Path string (file or directory)
        project_root: Project root directory
        prefix: File prefix for version detection (default: "complexity_model_v")
        suffix: File suffix for version detection (default: ".pkl")

    Returns:
        Path to model file, or None if not found
    """
    model_path = resolve_path(Path(path_str), project_root)

    if model_path.is_dir():
        from pytest_coverage_impact.ml.versioning import get_latest_version

        latest = get_latest_version(model_path, prefix, suffix)
        if latest:
            return latest[1]
    elif model_path.exists() and model_path.is_file():
        return model_path

    return None


def find_function_node_by_line(file_path: Path, line_num: int) -> Optional[ast.FunctionDef]:
    """Find a function AST node by line number in a file

    Args:
        file_path: Path to Python source file
        line_num: Line number of function definition

    Returns:
        FunctionDef AST node, or None if not found
    """
    tree = parse_ast_tree(file_path)
    if not tree:
        return None

    # Find function node
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.lineno == line_num:
                return node

    return None


def parse_ast_tree(file_path: Path) -> Optional[ast.AST]:
    """Parse a Python file into an AST tree

    Args:
        file_path: Path to Python source file

    Returns:
        AST tree, or None if parsing failed
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, IOError):
        return None
