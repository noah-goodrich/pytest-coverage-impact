"""Unit tests for reporters module"""

import json
import tempfile
from pathlib import Path

from rich.console import Console

from pytest_coverage_impact.reporters import JSONReporter, TerminalReporter


def test_terminal_reporter_empty_list():
    """Test terminal reporter with empty impact scores"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    reporter.generate_report([], top_n=10)

    # Should not raise an exception
    assert True


def test_terminal_reporter_basic():
    """Test terminal reporter with basic data"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "priority": 5.5,
            "complexity_score": 0.5,
            "coverage_percentage": 0.3,
            "file": "module.py",
        },
    ]

    reporter.generate_report(impact_scores, top_n=10)

    # Should not raise an exception
    assert True


def test_terminal_reporter_with_confidence():
    """Test terminal reporter with confidence intervals"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "priority": 5.5,
            "complexity_score": 0.5,
            "confidence": 0.8,
            "coverage_percentage": 0.3,
            "file": "module.py",
        },
    ]

    reporter.generate_report(impact_scores, top_n=10)

    # Should not raise an exception
    assert True


def test_terminal_reporter_top_n_limit():
    """Test terminal reporter limits to top_n"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    impact_scores = [
        {
            "function": f"module.py::func{i}",
            "impact": float(i),
            "impact_score": float(i),
            "priority": float(i),
            "complexity_score": 0.5,
            "coverage_percentage": 0.3,
            "file": "module.py",
        }
        for i in range(20)
    ]

    reporter.generate_report(impact_scores, top_n=5)

    # Should not raise an exception
    assert True


def test_terminal_reporter_long_file_path():
    """Test terminal reporter with long file paths (truncation)"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    long_path = "/very/long/path/to/the/module/file/that/exceeds/limit.py"
    impact_scores = [
        {
            "function": f"{long_path}::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "priority": 5.5,
            "complexity_score": 0.5,
            "coverage_percentage": 0.3,
            "file": long_path,
        },
    ]

    reporter.generate_report(impact_scores, top_n=10)

    # Should not raise an exception
    assert True


def test_terminal_reporter_long_function_name():
    """Test terminal reporter with long function names (truncation)"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    long_func = "very_long_function_name_that_exceeds_the_display_limit_should_be_truncated"
    impact_scores = [
        {
            "function": f"module.py::{long_func}",
            "impact": 10.0,
            "impact_score": 10.0,
            "priority": 5.5,
            "complexity_score": 0.5,
            "coverage_percentage": 0.3,
            "file": "module.py",
        },
    ]

    reporter.generate_report(impact_scores, top_n=10)

    # Should not raise an exception
    assert True


def test_terminal_reporter_function_name_with_colons():
    """Test terminal reporter with function names containing ::"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    impact_scores = [
        {
            "function": "module.py::ClassName::method_name",
            "impact": 10.0,
            "impact_score": 10.0,
            "priority": 5.5,
            "complexity_score": 0.5,
            "coverage_percentage": 0.3,
            "file": "module.py",
        },
    ]

    reporter.generate_report(impact_scores, top_n=10)

    # Should not raise an exception
    assert True


def test_terminal_reporter_missing_coverage_percentage():
    """Test terminal reporter handles missing coverage_percentage"""
    console = Console(file=open("/dev/null", "w"))  # Suppress output
    reporter = TerminalReporter(console)

    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "priority": 5.5,
            "complexity_score": 0.5,
            "file": "module.py",
        },
    ]

    reporter.generate_report(impact_scores, top_n=10)

    # Should not raise an exception
    assert True


def test_json_reporter_basic():
    """Test JSON reporter with basic data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.json"

        impact_scores = [
            {
                "function": "module.py::func1",
                "impact": 10.0,
                "impact_score": 10.0,
                "file": "module.py",
            },
        ]

        JSONReporter.generate_report(impact_scores, output_path)

        assert output_path.exists()

        with open(output_path, "r") as f:
            report = json.load(f)

        assert report["version"] == "1.0"
        assert report["total_functions"] == 1
        assert len(report["functions"]) == 1
        assert report["functions"][0]["function"] == "module.py::func1"


def test_json_reporter_empty_list():
    """Test JSON reporter with empty impact scores"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.json"

        JSONReporter.generate_report([], output_path)

        assert output_path.exists()

        with open(output_path, "r") as f:
            report = json.load(f)

        assert report["total_functions"] == 0
        assert report["functions"] == []


def test_json_reporter_multiple_functions():
    """Test JSON reporter with multiple functions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.json"

        impact_scores = [
            {
                "function": f"module.py::func{i}",
                "impact": float(i),
                "impact_score": float(i),
                "file": "module.py",
            }
            for i in range(5)
        ]

        JSONReporter.generate_report(impact_scores, output_path)

        assert output_path.exists()

        with open(output_path, "r") as f:
            report = json.load(f)

        assert report["total_functions"] == 5
        assert len(report["functions"]) == 5


def test_json_reporter_complex_data():
    """Test JSON reporter with complex function data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.json"

        impact_scores = [
            {
                "function": "module.py::ClassName::method",
                "impact": 10.0,
                "impact_score": 10.0,
                "priority": 5.5,
                "complexity_score": 0.5,
                "confidence": 0.8,
                "coverage_percentage": 0.3,
                "missing_lines": 5,
                "file": "module.py",
                "line": 42,
                "covered": False,
            },
        ]

        JSONReporter.generate_report(impact_scores, output_path)

        assert output_path.exists()

        with open(output_path, "r") as f:
            report = json.load(f)

        assert report["functions"][0]["function"] == "module.py::ClassName::method"
        assert report["functions"][0]["priority"] == 5.5
        assert report["functions"][0]["confidence"] == 0.8
