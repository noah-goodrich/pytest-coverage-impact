"""Unit tests for config module"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


from pytest_coverage_impact.core.config import get_model_path


def test_get_model_path_default_bundled_model(monkeypatch):
    """Test that default bundled model is returned when no config is set"""
    # Mock config with no ini setting
    config = Mock()
    config.getini = Mock(return_value=None)

    # Clear environment variable
    if "PYTEST_COVERAGE_IMPACT_MODEL_PATH" in os.environ:
        monkeypatch.delenv("PYTEST_COVERAGE_IMPACT_MODEL_PATH")

    project_root = Path("/tmp/test_project")

    model_path = get_model_path(config, project_root)

    # Should return bundled model path
    assert model_path is not None
    assert model_path.name == "complexity_model_v1.0.pkl"
    assert model_path.exists()


def test_get_model_path_ini_file_absolute():
    """Test pytest.ini with absolute file path"""
    config = Mock()
    config.getini = Mock(return_value="/tmp/models/complexity_model_v1.0.pkl")

    with tempfile.TemporaryDirectory() as tmpdir:
        model_file = Path(tmpdir) / "complexity_model_v1.0.pkl"
        model_file.touch()

        config.getini = Mock(return_value=str(model_file))
        project_root = Path("/tmp/test_project")

        model_path = get_model_path(config, project_root)

        assert model_path == model_file.resolve()


def test_get_model_path_ini_file_relative():
    """Test pytest.ini with relative file path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        model_file = project_root / "models" / "complexity_model_v1.0.pkl"
        model_file.parent.mkdir()
        model_file.touch()

        config = Mock()
        config.getini = Mock(return_value="models/complexity_model_v1.0.pkl")

        model_path = get_model_path(config, project_root)

        assert model_path == model_file.resolve()


def test_get_model_path_ini_directory_with_model():
    """Test pytest.ini with directory path that contains models"""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = Path(tmpdir) / "models"
        model_dir.mkdir()

        # Create model files with versions
        (model_dir / "complexity_model_v1.0.pkl").touch()
        (model_dir / "complexity_model_v1.2.pkl").touch()
        (model_dir / "complexity_model_v1.1.pkl").touch()

        config = Mock()
        config.getini = Mock(return_value=str(model_dir))

        project_root = Path("/tmp/test_project")

        model_path = get_model_path(config, project_root)

        # Should return highest version
        assert model_path is not None
        assert model_path.name == "complexity_model_v1.2.pkl"


def test_get_model_path_ini_directory_empty():
    """Test pytest.ini with empty directory (should fall back)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = Path(tmpdir) / "models"
        model_dir.mkdir()
        # Directory exists but is empty

        config = Mock()
        config.getini = Mock(return_value=str(model_dir))

        project_root = Path("/tmp/test_project")

        # Should fall through to bundled model
        model_path = get_model_path(config, project_root)

        assert model_path is not None
        assert "complexity_model_v1.0.pkl" in str(model_path)


def test_get_model_path_env_var_file():
    """Test environment variable with file path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_file = Path(tmpdir) / "model.pkl"
        model_file.touch()

        with patch.dict(os.environ, {"PYTEST_COVERAGE_IMPACT_MODEL_PATH": str(model_file)}):
            config = Mock()
            config.getini = Mock(return_value=None)

            project_root = Path("/tmp/test_project")

            model_path = get_model_path(config, project_root)

            assert model_path == model_file.resolve()


def test_get_model_path_env_var_directory():
    """Test environment variable with directory path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_dir = Path(tmpdir) / "models"
        model_dir.mkdir()
        (model_dir / "complexity_model_v1.5.pkl").touch()

        with patch.dict(os.environ, {"PYTEST_COVERAGE_IMPACT_MODEL_PATH": str(model_dir)}):
            config = Mock()
            config.getini = Mock(return_value=None)

            project_root = Path("/tmp/test_project")

            model_path = get_model_path(config, project_root)

            assert model_path.name == "complexity_model_v1.5.pkl"


def test_get_model_path_project_directory():
    """Test project directory fallback"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        model_dir = project_root / ".coverage_impact" / "models"
        model_dir.mkdir(parents=True)
        (model_dir / "complexity_model_v2.0.pkl").touch()

        config = Mock()
        config.getini = Mock(return_value=None)

        if "PYTEST_COVERAGE_IMPACT_MODEL_PATH" in os.environ:
            with patch.dict(os.environ, {}, clear=True):
                model_path = get_model_path(config, project_root)
        else:
            model_path = get_model_path(config, project_root)

        assert model_path.name == "complexity_model_v2.0.pkl"


def test_get_model_path_project_directory_empty():
    """Test project directory empty (should fall back to bundled)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        model_dir = project_root / ".coverage_impact" / "models"
        model_dir.mkdir(parents=True)
        # Directory exists but is empty

        config = Mock()
        config.getini = Mock(return_value=None)

        if "PYTEST_COVERAGE_IMPACT_MODEL_PATH" in os.environ:
            with patch.dict(os.environ, {}, clear=True):
                model_path = get_model_path(config, project_root)
        else:
            model_path = get_model_path(config, project_root)

        # Should fall back to bundled model
        assert model_path is not None
        assert "complexity_model_v1.0.pkl" in str(model_path)


def test_get_model_path_priority_order():
    """Test that priority order is respected (ini > env > project > bundled)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create models at different priority levels
        ini_model = Path(tmpdir) / "ini_model.pkl"
        ini_model.touch()

        env_model = Path(tmpdir) / "env_model.pkl"
        env_model.touch()

        project_root = Path(tmpdir) / "project"
        project_root.mkdir()
        project_model_dir = project_root / ".coverage_impact" / "models"
        project_model_dir.mkdir(parents=True)
        (project_model_dir / "complexity_model_v1.0.pkl").touch()

        # Test ini has highest priority
        config = Mock()
        config.getini = Mock(return_value=str(ini_model))

        with patch.dict(os.environ, {"PYTEST_COVERAGE_IMPACT_MODEL_PATH": str(env_model)}):
            model_path = get_model_path(config, project_root)
            assert model_path == ini_model.resolve()


def test_get_model_path_ini_exception_handling():
    """Test that exceptions in ini parsing are handled gracefully"""
    config = Mock()
    config.getini = Mock(side_effect=ValueError("Invalid config"))

    project_root = Path("/tmp/test_project")

    # Should not raise, should fall through to next priority
    model_path = get_model_path(config, project_root)

    # Should fall back to bundled model
    assert model_path is not None


def test_get_model_path_relative_path_resolution():
    """Test that relative paths are resolved relative to project root"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        model_file = project_root / "custom_models" / "model.pkl"
        model_file.parent.mkdir()
        model_file.touch()

        config = Mock()
        config.getini = Mock(return_value="custom_models/model.pkl")

        model_path = get_model_path(config, project_root)

        assert model_path == model_file.resolve()


def test_get_model_path_nonexistent_file():
    """Test that nonexistent file paths are handled gracefully"""
    config = Mock()
    config.getini = Mock(return_value="/nonexistent/model.pkl")

    project_root = Path("/tmp/test_project")

    # Should fall through to next priority
    model_path = get_model_path(config, project_root)

    # Should fall back to bundled model
    assert model_path is not None
