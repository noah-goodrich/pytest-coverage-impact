"""Configuration management for pytest-coverage-impact"""

import os
from pathlib import Path
from typing import Optional

import pytest

from pytest_coverage_impact.utils import resolve_model_path_with_auto_detect


def _get_model_path_from_ini(config: pytest.Config, project_root: Path) -> Optional[Path]:
    """Get model path from pytest.ini configuration

    Args:
        config: Pytest Config object
        project_root: Project root directory

    Returns:
        Path to model file, or None if not found
    """
    try:
        ini_path = config.getini("coverage_impact_model_path")
        if ini_path:
            return resolve_model_path_with_auto_detect(ini_path, project_root)
    except (ValueError, AttributeError, KeyError, TypeError):
        pass

    return None


def _get_model_path_from_env(project_root: Path) -> Optional[Path]:
    """Get model path from environment variable

    Args:
        project_root: Project root directory

    Returns:
        Path to model file, or None if not found
    """
    env_path = os.getenv("PYTEST_COVERAGE_IMPACT_MODEL_PATH")
    if env_path:
        return resolve_model_path_with_auto_detect(env_path, project_root)

    return None


def _get_model_path_from_project_dir(project_root: Path) -> Optional[Path]:
    """Get model path from project directory (user-trained model)

    Args:
        project_root: Project root directory

    Returns:
        Path to model file, or None if not found
    """
    project_model_dir = project_root / ".coverage_impact" / "models"
    if project_model_dir.exists() and project_model_dir.is_dir():
        from pytest_coverage_impact.ml.versioning import get_latest_version

        latest = get_latest_version(
            project_model_dir, "complexity_model_v", ".pkl")
        if latest:
            return latest[1]

    return None


def _get_default_bundled_model_path() -> Optional[Path]:
    """Get default bundled model path from plugin directory

    Returns:
        Path to bundled model file, or None if not found
    """
    plugin_dir = Path(__file__).parent
    plugin_model_path = plugin_dir / "ml" / "models" / "complexity_model_v1.0.pkl"
    if plugin_model_path.exists():
        return plugin_model_path.resolve()

    return None


def get_model_path(config: pytest.Config, project_root: Path) -> Optional[Path]:
    """Get the ML model path from configuration

    Supports both file paths and directory paths:
    - File path: Returns the file if it exists
    - Directory path: Auto-detects the highest version model in the directory

    Priority order (highest to lowest):
    1. CLI option: `--coverage-impact-model-path` (handled in plugin.py)
    2. pytest.ini config: `coverage_impact_model_path`
    3. Environment variable: `PYTEST_COVERAGE_IMPACT_MODEL_PATH`
    4. Project directory: `<project_root>/.coverage_impact/models/` (auto-detects latest)
    5. Plugin directory: `<plugin_dir>/ml/models/complexity_model_v1.0.pkl`

    Args:
        config: Pytest Config object
        project_root: Project root directory

    Returns:
        Path to model file, or None if not found
    """
    # Priority 2: pytest.ini configuration
    model_path = _get_model_path_from_ini(config, project_root)
    if model_path:
        return model_path

    # Priority 3: Environment variable
    model_path = _get_model_path_from_env(project_root)
    if model_path:
        return model_path

    # Priority 4: Project directory (user-trained model)
    model_path = _get_model_path_from_project_dir(project_root)
    if model_path:
        return model_path

    # Priority 5: Plugin directory (default bundled model)
    return _get_default_bundled_model_path()
