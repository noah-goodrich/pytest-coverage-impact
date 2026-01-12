"""Functional test: Test call graph builder and impact calculation on snowfort codebase

These tests run against the real snowfort codebase and are slow.
They should be excluded from normal unit/integration test runs.
"""

from pathlib import Path

from pytest_coverage_impact.gateways.call_graph import build_call_graph
from pytest_coverage_impact.core.impact_calculator import ImpactCalculator, load_coverage_data


def test_build_call_graph_on_snowfort():
    """Test building call graph on actual snowfort codebase"""
    snowfort_path = Path("/development/snowfort/snowfort")

    if not snowfort_path.exists():
        # Skip if snowfort not available
        return

    # Don't use package_prefix since we're already inside the snowfort directory
    call_graph = build_call_graph(snowfort_path)

    # Verify we found some functions
    assert len(call_graph.graph) > 0, "Should find at least some functions"

    # Verify graph structure
    for func_name, func_data in list(call_graph.graph.items())[:10]:
        assert "file" in func_data, f"Function {func_name} should have file"
        assert "line" in func_data, f"Function {func_name} should have line"
        assert "calls" in func_data, f"Function {func_name} should have calls set"
        assert "called_by" in func_data, f"Function {func_name} should have called_by set"

    # Check for some known functions
    func_names = list(call_graph.graph.keys())
    assert any("cli.py" in name for name in func_names), "Should find cli.py functions"

    print(f"\n✅ Built call graph with {len(call_graph.graph)} functions")


def test_impact_calculation_on_snowfort():
    """Test impact calculation on snowfort codebase"""

    snowfort_path = Path("/development/snowfort/snowfort")
    coverage_file = Path("/development/snowfort/coverage.json")

    if not snowfort_path.exists() or not coverage_file.exists():
        # Skip if snowfort or coverage not available
        return

    # Build call graph (no prefix since we're already in snowfort directory)
    call_graph = build_call_graph(snowfort_path)

    # Load coverage data
    coverage_data = load_coverage_data(coverage_file)

    # Calculate impact scores
    calculator = ImpactCalculator(call_graph, coverage_data)
    impact_scores = calculator.calculate_impact_scores()

    # Verify we got results
    assert len(impact_scores) > 0, "Should calculate impact scores for some functions"

    # Verify impact scores structure
    for score in impact_scores[:5]:
        assert "function" in score
        assert "impact" in score
        assert "impact_score" in score
        assert "coverage_percentage" in score
        assert score["impact_score"] >= 0, "Impact score should be non-negative"

    print(f"\n✅ Calculated impact scores for {len(impact_scores)} functions")
    if impact_scores:
        top_func = impact_scores[0]["function"]
        top_impact = impact_scores[0]["impact_score"]
        print(f"   Top function: {top_func} (impact={top_impact:.2f})")
