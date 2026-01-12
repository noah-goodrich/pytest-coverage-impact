"""Shared fixtures for coverage impact tests"""

import tempfile
import json
from pathlib import Path

import pytest


@pytest.fixture
def temp_project():
    """Create a temporary project structure with coverage data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test_project"
        project_root.mkdir()
        source_dir = project_root / "src"
        source_dir.mkdir()
        (source_dir / "main.py").write_text("def main():\n    print('hello')\n    return 0\n")
        (source_dir / "__init__.py").touch()

        # Create dummy coverage.json
        coverage_file = project_root / "coverage.json"
        with open(coverage_file, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "files": {
                            "src/main.py": {
                                "summary": {"num_statements": 1, "covered_lines": 1, "missing_lines": 0},
                                "executed_lines": [1],
                                "missing_lines": [],
                            }
                        }
                    }
                )
            )

        yield project_root, source_dir, coverage_file
