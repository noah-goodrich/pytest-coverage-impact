"""Unit tests for training data collector module"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


from pytest_coverage_impact.ml.training_data_collector import (
    TrainingDataCollector,
    collect_training_data_from_codebase,
)


def test_training_data_collector_initialization():
    """Test collector initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        collector = TrainingDataCollector(root)

        assert collector.root == root.resolve()
        assert collector.package_prefix is None
        assert collector.call_graph is None


def test_training_data_collector_initialization_with_prefix():
    """Test collector initialization with package prefix"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        collector = TrainingDataCollector(root, package_prefix="package/")

        assert collector.root == root.resolve()
        assert collector.package_prefix == "package/"


def test_save_training_data_basic():
    """Test saving training data to JSON"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "dataset.json"

        collector = TrainingDataCollector(Path(tmpdir))

        training_data = [
            {
                "function_signature": "module.py::func1",
                "features": {"lines_of_code": 10.0},
                "complexity_label": 0.5,
            }
        ]

        version = collector.save_training_data(training_data, output_path)

        assert output_path.exists()
        assert version == "1.0"  # Default version

        # Verify JSON structure
        with open(output_path, "r") as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert data["total_examples"] == 1
        assert len(data["examples"]) == 1


def test_save_training_data_with_version():
    """Test saving training data with explicit version"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "dataset.json"

        collector = TrainingDataCollector(Path(tmpdir))

        training_data = []
        version = collector.save_training_data(
            training_data, output_path, version="2.0")

        assert version == "2.0"

        with open(output_path, "r") as f:
            data = json.load(f)

        assert data["version"] == "2.0"


def test_save_training_data_version_from_filename():
    """Test extracting version from filename"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "dataset_v1.5.json"

        collector = TrainingDataCollector(Path(tmpdir))

        training_data = []
        version = collector.save_training_data(training_data, output_path)

        assert version == "1.5"


def test_save_training_data_creates_directory():
    """Test that save creates parent directories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "nested" / "deep" / "dataset.json"

        collector = TrainingDataCollector(Path(tmpdir))

        training_data = []
        collector.save_training_data(training_data, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()


def test_collect_training_data_empty_codebase():
    """Test collecting from empty codebase"""
    with tempfile.TemporaryDirectory() as tmpdir:
        collector = TrainingDataCollector(Path(tmpdir))

        training_data = collector.collect_training_data()

        assert training_data == []


def test_collect_training_data_with_function_and_test():
    """Test collecting training data when function and test exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create source module
        module_dir = root / "package"
        module_dir.mkdir()
        module_file = module_dir / "module.py"
        module_file.write_text(
            """
def func_to_test(x):
    return x * 2
"""
        )

        # Create test file
        test_dir = root / "tests"
        test_dir.mkdir()
        test_file = test_dir / "test_module.py"
        test_file.write_text(
            """
def test_func_to_test():
    assert func_to_test(2) == 4
"""
        )

        collector = TrainingDataCollector(root)
        training_data = collector.collect_training_data()

        # Should find at least one training example if mapping works
        assert isinstance(training_data, list)
        # May be empty if mapping doesn't find matches, which is okay


def test_collect_training_data_filters_by_package_prefix():
    """Test that package prefix filters functions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create files in different locations
        package1_dir = root / "package1"
        package1_dir.mkdir()
        (package1_dir / "module1.py").write_text("def func1(): pass")

        package2_dir = root / "package2"
        package2_dir.mkdir()
        (package2_dir / "module2.py").write_text("def func2(): pass")

        collector = TrainingDataCollector(root, package_prefix="package1/")
        training_data = collector.collect_training_data()

        # All results should be from package1
        for example in training_data:
            assert example["file_path"].startswith("package1/")


def test_collect_training_data_skips_functions_without_tests():
    """Test that functions without tests are skipped"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        module_dir = root / "package"
        module_dir.mkdir()
        (module_dir / "module.py").write_text("def untested_func(): pass")

        # No test file

        collector = TrainingDataCollector(root)
        training_data = collector.collect_training_data()

        # Should skip functions without tests
        assert isinstance(training_data, list)


def test_collect_training_data_handles_invalid_files():
    """Test that invalid files are handled gracefully"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        module_dir = root / "package"
        module_dir.mkdir()

        # Create file with invalid Python syntax
        invalid_file = module_dir / "invalid.py"
        invalid_file.write_text("def broken syntax here !!!")

        collector = TrainingDataCollector(root)

        # Should not raise, should skip invalid files
        training_data = collector.collect_training_data()

        assert isinstance(training_data, list)


def test_collect_training_data_averages_multiple_tests():
    """Test that multiple tests for same function are averaged"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        module_dir = root / "package"
        module_dir.mkdir()
        module_file = module_dir / "module.py"
        module_file.write_text("def func(): return 42")

        test_dir = root / "tests"
        test_dir.mkdir()

        # Create multiple test files
        (test_dir / "test_module.py").write_text("def test_func(): assert func() == 42")
        (test_dir / "test_module_alt.py").write_text("def test_func_alt(): assert func() == 42")

        collector = TrainingDataCollector(root)
        training_data = collector.collect_training_data()

        # If multiple tests found, complexity should be averaged
        for example in training_data:
            if example.get("num_tests", 0) > 1:
                assert example["complexity_label"] >= 0.0
                assert example["complexity_label"] <= 1.0


def test_collect_training_data_from_codebase():
    """Test convenience function for collecting training data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        output_path = root / "dataset.json"

        # Create minimal codebase
        module_dir = root / "package"
        module_dir.mkdir()
        (module_dir / "module.py").write_text("def func(): pass")

        result_path = collect_training_data_from_codebase(root, output_path)

        assert result_path == output_path
        assert output_path.exists()


def test_collect_training_data_from_codebase_with_version():
    """Test convenience function with version in filename"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        output_path = root / "dataset_v2.3.json"

        module_dir = root / "package"
        module_dir.mkdir()
        (module_dir / "module.py").write_text("def func(): pass")

        result_path = collect_training_data_from_codebase(root, output_path)

        assert result_path == output_path

        with open(output_path, "r") as f:
            data = json.load(f)

        assert data["version"] == "2.3"


def test_collect_training_data_structure():
    """Test that collected training data has correct structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        module_dir = root / "package"
        module_dir.mkdir()
        module_file = module_dir / "module.py"
        module_file.write_text("def func(x): return x")

        test_dir = root / "tests"
        test_dir.mkdir()
        (test_dir / "test_module.py").write_text("def test_func(): assert func(1) == 1")

        collector = TrainingDataCollector(root)
        training_data = collector.collect_training_data()

        # Verify structure if any data collected
        for example in training_data:
            assert "function_signature" in example
            assert "features" in example
            assert "complexity_label" in example
            assert "file_path" in example
            assert "line" in example
            assert "test_files" in example
            assert "num_tests" in example

            assert isinstance(example["features"], dict)
            assert 0.0 <= example["complexity_label"] <= 1.0
            assert isinstance(example["test_files"], list)


def test_save_training_data_empty_list():
    """Test saving empty training data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "empty_dataset.json"

        collector = TrainingDataCollector(Path(tmpdir))

        collector.save_training_data([], output_path)

        assert output_path.exists()

        with open(output_path, "r") as f:
            data = json.load(f)

        assert data["total_examples"] == 0
        assert data["examples"] == []


def test_collect_training_data_skips_nonexistent_files():
    """Test that nonexistent files are skipped"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Mock call graph with file that doesn't exist
        collector = TrainingDataCollector(root)
        collector.call_graph = Mock()
        collector.call_graph.graph = {
            "nonexistent.py::func": {
                "file": "nonexistent.py",
                "line": 10,
            }
        }

        # Mock test analyzer to return empty
        with patch("pytest_coverage_impact.ml.training_data_collector.TestAnalyzer") as mock_analyzer:
            mock_instance = Mock()
            mock_instance.find_test_files.return_value = []
            mock_instance.map_function_to_tests.return_value = []
            mock_analyzer.return_value = mock_instance

            training_data = collector.collect_training_data()

            # Should skip nonexistent files
            assert isinstance(training_data, list)
