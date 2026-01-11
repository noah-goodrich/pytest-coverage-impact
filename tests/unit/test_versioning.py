"""Unit tests for versioning module"""

import tempfile
from pathlib import Path


from pytest_coverage_impact.ml.versioning import get_latest_version, get_next_version


def test_get_next_version_empty_directory():
    """Test getting next version when directory is empty"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        version, path = get_next_version(base_path, "test_v", ".txt")

        assert version == "1.0"
        assert path.name == "test_v1.0.txt"
        assert path.parent == base_path


def test_get_next_version_with_existing_files():
    """Test getting next version when files already exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create existing files
        (base_path / "test_v1.0.txt").touch()
        (base_path / "test_v1.1.txt").touch()

        version, path = get_next_version(base_path, "test_v", ".txt")

        assert version == "1.2"
        assert path.name == "test_v1.2.txt"


def test_get_next_version_increment_minor():
    """Test that minor version is incremented"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "test_v1.5.txt").touch()

        version, path = get_next_version(base_path, "test_v", ".txt")

        assert version == "1.6"
        assert path.name == "test_v1.6.txt"


def test_get_next_version_creates_directory():
    """Test that get_next_version creates directory if it doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / "new" / "nested" / "dir"

        _, path = get_next_version(base_path, "test_v", ".txt")

        assert base_path.exists()
        assert path.parent == base_path


def test_get_next_version_ignores_non_matching_files():
    """Test that non-matching files are ignored"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create matching and non-matching files
        (base_path / "test_v1.0.txt").touch()
        (base_path / "other_v1.0.txt").touch()
        (base_path / "test_v1.5.json").touch()
        (base_path / "random_file.txt").touch()

        version, path = get_next_version(base_path, "test_v", ".txt")

        # Should only consider test_v*.txt files
        assert version == "1.1"
        assert path.name == "test_v1.1.txt"


def test_get_next_version_pkl_suffix():
    """Test with .pkl suffix for model files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "model_v1.0.pkl").touch()
        (base_path / "model_v1.3.pkl").touch()

        version, path = get_next_version(base_path, "model_v", ".pkl")

        assert version == "1.4"
        assert path.name == "model_v1.4.pkl"
        assert path.suffix == ".pkl"


def test_get_next_version_json_suffix():
    """Test with .json suffix for training data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "dataset_v1.0.json").touch()
        (base_path / "dataset_v2.5.json").touch()

        version, path = get_next_version(base_path, "dataset_v", ".json")

        assert version == "2.6"
        assert path.name == "dataset_v2.6.json"
        assert path.suffix == ".json"


def test_get_latest_version_empty_directory():
    """Test getting latest version when directory is empty"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        result = get_latest_version(base_path, "test_v", ".txt")

        assert result is None


def test_get_latest_version_nonexistent_directory():
    """Test getting latest version when directory doesn't exist"""
    base_path = Path("/nonexistent/directory")

    result = get_latest_version(base_path, "test_v", ".txt")

    assert result is None


def test_get_latest_version_single_file():
    """Test getting latest version with single file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        file_path = base_path / "test_v1.5.txt"
        file_path.touch()

        result = get_latest_version(base_path, "test_v", ".txt")

        assert result is not None
        version, path = result
        assert version == "1.5"
        assert path == file_path


def test_get_latest_version_multiple_files():
    """Test getting latest version with multiple files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "test_v1.0.txt").touch()
        (base_path / "test_v1.8.txt").touch()
        (base_path / "test_v1.3.txt").touch()
        latest_file = base_path / "test_v1.8.txt"

        result = get_latest_version(base_path, "test_v", ".txt")

        assert result is not None
        version, path = result
        assert version == "1.8"
        assert path == latest_file


def test_get_latest_version_major_version_handling():
    """Test that major versions are handled correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "test_v1.9.txt").touch()
        (base_path / "test_v2.0.txt").touch()
        (base_path / "test_v1.5.txt").touch()

        result = get_latest_version(base_path, "test_v", ".txt")

        assert result is not None
        version, path = result
        assert version == "2.0"
        assert path.name == "test_v2.0.txt"


def test_get_latest_version_ignores_non_matching_files():
    """Test that get_latest_version ignores non-matching files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "test_v1.5.txt").touch()
        (base_path / "other_v2.0.txt").touch()
        (base_path / "test_v1.3.json").touch()

        result = get_latest_version(base_path, "test_v", ".txt")

        assert result is not None
        version, path = result
        assert version == "1.5"
        assert path.name == "test_v1.5.txt"


def test_get_latest_version_complexity_model():
    """Test getting latest version for complexity model files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "complexity_model_v1.0.pkl").touch()
        (base_path / "complexity_model_v1.2.pkl").touch()
        (base_path / "complexity_model_v1.1.pkl").touch()

        result = get_latest_version(base_path, "complexity_model_v", ".pkl")

        assert result is not None
        version, path = result
        assert version == "1.2"
        assert path.name == "complexity_model_v1.2.pkl"


def test_get_latest_version_dataset():
    """Test getting latest version for dataset files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "dataset_v1.0.json").touch()
        (base_path / "dataset_v1.5.json").touch()

        result = get_latest_version(base_path, "dataset_v", ".json")

        assert result is not None
        version, path = result
        assert version == "1.5"
        assert path.name == "dataset_v1.5.json"


def test_get_latest_version_directory_contains_subdirectories():
    """Test that subdirectories are ignored"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "test_v1.0.txt").touch()
        subdir = base_path / "subdir"
        subdir.mkdir()
        (subdir / "test_v2.0.txt").touch()

        result = get_latest_version(base_path, "test_v", ".txt")

        # Should only find files in base_path, not subdirectories
        assert result is not None
        version, _ = result
        assert version == "1.0"


def test_get_next_version_with_subdirectories():
    """Test that get_next_version ignores subdirectories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        (base_path / "test_v1.0.txt").touch()
        subdir = base_path / "subdir"
        subdir.mkdir()
        (subdir / "test_v2.0.txt").touch()

        version, path = get_next_version(base_path, "test_v", ".txt")

        # Should only consider files in base_path
        assert version == "1.1"
        assert path.name == "test_v1.1.txt"
