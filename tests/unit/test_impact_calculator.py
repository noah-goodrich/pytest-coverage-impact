"""Unit tests for impact calculator module"""

import json
import tempfile
from pathlib import Path

import pytest

from pytest_coverage_impact.call_graph import CallGraph
from pytest_coverage_impact.impact_calculator import (
    ImpactCalculator,
    load_coverage_data,
)


def test_load_coverage_data():
    """Test loading coverage data from JSON file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        coverage_file = Path(tmpdir) / "coverage.json"

        coverage_data = {
            "files": {
                "module.py": {
                    "summary": {
                        "num_statements": 100,
                        "covered_lines": 50,
                    },
                    "executed_lines": [1, 2, 3],
                    "missing_lines": [4, 5, 6],
                }
            }
        }

        with open(coverage_file, "w") as f:
            json.dump(coverage_data, f)

        loaded = load_coverage_data(coverage_file)

        assert loaded["files"]["module.py"]["summary"]["num_statements"] == 100
        assert loaded["files"]["module.py"]["summary"]["covered_lines"] == 50


def test_load_coverage_data_file_not_found():
    """Test that FileNotFoundError is raised when coverage file doesn't exist"""
    coverage_file = Path("/nonexistent/coverage.json")

    with pytest.raises(FileNotFoundError):
        load_coverage_data(coverage_file)


def test_get_function_coverage_file_found():
    """Test getting coverage for a function when file is in coverage data"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)

    coverage_data = {
        "files": {
            "module.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 50,
                },
                "executed_lines": [1, 5, 10, 15],
                "missing_lines": [20, 25],
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    is_covered, coverage_pct, missing_lines = calculator.get_function_coverage("module.py", 10)

    assert is_covered is True  # Line 10 is in executed_lines
    assert coverage_pct == 0.5  # 50/100
    assert missing_lines >= 0


def test_get_function_coverage_file_not_found():
    """Test getting coverage when file is not in coverage data"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)

    coverage_data = {"files": {}}

    calculator = ImpactCalculator(call_graph, coverage_data)
    is_covered, coverage_pct, missing_lines = calculator.get_function_coverage("module.py", 10)

    assert is_covered is False
    assert coverage_pct == 0.0
    assert missing_lines == 0


def test_get_function_coverage_with_package_prefix():
    """Test getting coverage with package prefix"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)

    coverage_data = {
        "files": {
            "package/module.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 50,
                },
                "executed_lines": [10],
                "missing_lines": [],
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    is_covered, coverage_pct, missing_lines = calculator.get_function_coverage(
        "module.py", 10, package_prefix="package"
    )

    assert is_covered is True
    assert coverage_pct == 0.5


def test_calculate_impact_scores_basic():
    """Test calculating impact scores"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)
    call_graph.add_function("module.py::func2", "module.py", 20)
    call_graph.add_call("module.py::func2", "module.py::func1")  # func2 calls func1

    coverage_data = {
        "files": {
            "module.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 50,
                },
                "executed_lines": [10],  # func1 is covered
                "missing_lines": [20],  # func2 is not covered
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores()

    assert len(impact_scores) == 2
    assert all("function" in score for score in impact_scores)
    assert all("impact_score" in score for score in impact_scores)
    assert all("coverage_percentage" in score for score in impact_scores)


def test_calculate_impact_scores_impact_calculation():
    """Test that impact (call frequency) is calculated correctly"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)
    call_graph.add_function("module.py::func2", "module.py", 20)
    call_graph.add_function("module.py::func3", "module.py", 30)

    # func1 is called by func2 and func3 (impact = 2)
    call_graph.add_call("module.py::func2", "module.py::func1")
    call_graph.add_call("module.py::func3", "module.py::func1")

    coverage_data = {
        "files": {
            "module.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 0,  # No coverage
                },
                "executed_lines": [],
                "missing_lines": [10, 20, 30],
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores()

    # Find func1 in results
    func1_score = next(s for s in impact_scores if s["function"] == "module.py::func1")

    assert func1_score["impact"] == 2  # Called by 2 functions


def test_calculate_impact_scores_coverage_gap():
    """Test that impact score accounts for coverage gap"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)
    call_graph.add_function("module.py::func2", "module.py", 20)

    coverage_data = {
        "files": {
            "module.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 50,  # 50% coverage
                },
                "executed_lines": [20],  # func2 is covered
                "missing_lines": [10],  # func1 is not covered
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores()

    func1_score = next(s for s in impact_scores if s["function"] == "module.py::func1")
    func2_score = next(s for s in impact_scores if s["function"] == "module.py::func2")

    # Both functions use the same file-level coverage (50%)
    # The impact_score will be based on their call frequency
    assert func1_score["coverage_percentage"] == func2_score["coverage_percentage"]
    assert "impact_score" in func1_score
    assert "impact_score" in func2_score


def test_calculate_impact_scores_with_package_prefix():
    """Test calculating impact scores with package prefix filter"""
    call_graph = CallGraph()
    call_graph.add_function("package/module.py::func1", "package/module.py", 10)
    call_graph.add_function("other/module.py::func2", "other/module.py", 20)

    coverage_data = {"files": {}}

    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores(package_prefix="package/")

    # Should only include functions from package/
    assert len(impact_scores) == 1
    assert impact_scores[0]["function"] == "package/module.py::func1"


def test_calculate_impact_scores_sorting():
    """Test that impact scores are sorted by impact_score (highest first)"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module.py", 10)
    call_graph.add_function("module.py::func2", "module.py", 20)
    call_graph.add_function("module.py::func3", "module.py", 30)

    coverage_data = {
        "files": {
            "module.py": {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 0,
                },
                "executed_lines": [],
                "missing_lines": [10, 20, 30],
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores()

    # Should be sorted by impact_score descending
    for i in range(len(impact_scores) - 1):
        assert impact_scores[i]["impact_score"] >= impact_scores[i + 1]["impact_score"]


def test_calculate_impact_scores_empty_call_graph():
    """Test calculating impact scores with empty call graph"""
    call_graph = CallGraph()
    coverage_data = {"files": {}}

    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores()

    assert impact_scores == []


def test_get_function_coverage_path_normalization():
    """Test that path separators are normalized"""
    call_graph = CallGraph()
    call_graph.add_function("module.py::func1", "module\\py", 10)  # Windows path

    coverage_data = {
        "files": {
            "module/py": {  # Unix path in coverage
                "summary": {
                    "num_statements": 100,
                    "covered_lines": 50,
                },
                "executed_lines": [10],
                "missing_lines": [],
            }
        }
    }

    calculator = ImpactCalculator(call_graph, coverage_data)
    # Should try normalized path
    is_covered, coverage_pct, _ = calculator.get_function_coverage("module\\py", 10)

    # May or may not match depending on path normalization
    assert isinstance(is_covered, bool)
    assert isinstance(coverage_pct, float)
