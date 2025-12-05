"""Unit tests for prioritizer module"""

from pytest_coverage_impact.prioritizer import Prioritizer


def test_calculate_priority_basic():
    """Test basic priority calculation"""
    priority = Prioritizer.calculate_priority(
        impact_score=10.0, complexity_score=0.5, confidence=1.0, effort_multiplier=2.0
    )

    # Priority = (10.0 * 1.0) / ((0.5 + 0.1) * (2.0 + 0.1))
    # = 10.0 / (0.6 * 2.1) = 10.0 / 1.26 ≈ 7.94
    assert priority > 7.0
    assert priority < 8.5


def test_calculate_priority_high_impact_low_complexity():
    """Test priority with high impact and low complexity (should be high priority)"""
    priority = Prioritizer.calculate_priority(
        impact_score=20.0, complexity_score=0.1, confidence=1.0, effort_multiplier=1.0
    )

    # High impact, low complexity should yield high priority
    assert priority > 15.0


def test_calculate_priority_low_impact_high_complexity():
    """Test priority with low impact and high complexity (should be low priority)"""
    priority = Prioritizer.calculate_priority(
        impact_score=2.0, complexity_score=0.9, confidence=1.0, effort_multiplier=3.0
    )

    # Low impact, high complexity should yield low priority
    assert priority < 2.0


def test_calculate_priority_with_confidence():
    """Test priority calculation with confidence factor"""
    priority_high_conf = Prioritizer.calculate_priority(
        impact_score=10.0, complexity_score=0.5, confidence=1.0, effort_multiplier=2.0
    )

    priority_low_conf = Prioritizer.calculate_priority(
        impact_score=10.0, complexity_score=0.5, confidence=0.5, effort_multiplier=2.0
    )

    # Lower confidence should result in lower priority
    assert priority_high_conf > priority_low_conf


def test_calculate_priority_zero_complexity():
    """Test priority calculation with zero complexity (edge case)"""
    # Should handle zero complexity gracefully (adds 0.1 to avoid division by zero)
    priority = Prioritizer.calculate_priority(
        impact_score=10.0, complexity_score=0.0, confidence=1.0, effort_multiplier=1.0
    )

    assert priority > 0
    assert isinstance(priority, float)


def test_calculate_priority_zero_effort():
    """Test priority calculation with zero effort (edge case)"""
    # Should handle zero effort gracefully (adds 0.1 to avoid division by zero)
    priority = Prioritizer.calculate_priority(
        impact_score=10.0, complexity_score=0.5, confidence=1.0, effort_multiplier=0.0
    )

    assert priority > 0
    assert isinstance(priority, float)


def test_prioritize_functions_basic():
    """Test basic function prioritization"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
        {
            "function": "module.py::func2",
            "impact": 5.0,
            "impact_score": 5.0,
            "coverage_percentage": 0.3,
            "file": "module.py",
        },
    ]

    prioritized = Prioritizer.prioritize_functions(impact_scores)

    assert len(prioritized) == 2
    assert "priority" in prioritized[0]
    assert "complexity_score" in prioritized[0]
    assert "confidence" in prioritized[0]
    # First function should have higher priority
    assert prioritized[0]["priority"] >= prioritized[1]["priority"]


def test_prioritize_functions_with_complexity():
    """Test prioritization with complexity scores"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
        {
            "function": "module.py::func2",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
    ]

    complexity_scores = {
        "module.py::func1": 0.2,  # Low complexity
        "module.py::func2": 0.8,  # High complexity
    }

    prioritized = Prioritizer.prioritize_functions(impact_scores, complexity_scores=complexity_scores)

    # func1 should have higher priority (same impact, lower complexity)
    assert prioritized[0]["function"] == "module.py::func1"
    assert prioritized[0]["complexity_score"] == 0.2


def test_prioritize_functions_with_confidence():
    """Test prioritization with confidence scores"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
        {
            "function": "module.py::func2",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
    ]

    confidence_scores = {
        "module.py::func1": 1.0,  # High confidence
        "module.py::func2": 0.5,  # Low confidence
    }

    prioritized = Prioritizer.prioritize_functions(impact_scores, confidence_scores=confidence_scores)

    # func1 should have higher priority (same impact, higher confidence)
    assert prioritized[0]["function"] == "module.py::func1"
    assert prioritized[0]["confidence"] == 1.0


def test_prioritize_functions_default_complexity():
    """Test that default complexity (0.5) is used when not provided"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
    ]

    prioritized = Prioritizer.prioritize_functions(impact_scores)

    assert prioritized[0]["complexity_score"] == 0.5  # Default value


def test_prioritize_functions_default_confidence():
    """Test that default confidence (1.0) is used when not provided"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
    ]

    prioritized = Prioritizer.prioritize_functions(impact_scores)

    assert prioritized[0]["confidence"] == 1.0  # Default value


def test_prioritize_functions_zero_impact_filtering():
    """Test that functions with zero impact are filtered out when others have impact"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
        {
            "function": "module.py::func2",
            "impact": 0.0,
            "impact_score": 0.0,
            "coverage_percentage": 1.0,
            "file": "module.py",
        },
    ]

    prioritized = Prioritizer.prioritize_functions(impact_scores)

    # Only func1 should be in results (func2 has zero impact)
    assert len(prioritized) == 1
    assert prioritized[0]["function"] == "module.py::func1"


def test_prioritize_functions_all_zero_impact():
    """Test that all functions are included if all have zero impact"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 0.0,
            "impact_score": 0.0,
            "coverage_percentage": 1.0,
            "file": "module.py",
        },
        {
            "function": "module.py::func2",
            "impact": 0.0,
            "impact_score": 0.0,
            "coverage_percentage": 1.0,
            "file": "module.py",
        },
    ]

    prioritized = Prioritizer.prioritize_functions(impact_scores)

    # All functions should be included if all have zero impact
    assert len(prioritized) == 2


def test_prioritize_functions_empty_list():
    """Test prioritization with empty impact scores list"""
    prioritized = Prioritizer.prioritize_functions([])

    assert prioritized == []


def test_prioritize_functions_effort_calculation():
    """Test that effort is derived from complexity"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
    ]

    complexity_scores = {
        "module.py::func1": 0.5,
    }

    prioritized = Prioritizer.prioritize_functions(impact_scores, complexity_scores=complexity_scores)

    # Effort should be derived: 1.0 + (0.5 * 2.0) = 2.0
    # This is used internally in priority calculation
    assert prioritized[0]["complexity_score"] == 0.5
    # Priority should reflect the effort multiplier
    assert prioritized[0]["priority"] > 0


def test_prioritize_functions_sorting():
    """Test that functions are sorted by priority (highest first)"""
    impact_scores = [
        {
            "function": "module.py::func1",
            "impact": 5.0,
            "impact_score": 5.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
        {
            "function": "module.py::func2",
            "impact": 20.0,
            "impact_score": 20.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
        {
            "function": "module.py::func3",
            "impact": 10.0,
            "impact_score": 10.0,
            "coverage_percentage": 0.5,
            "file": "module.py",
        },
    ]

    prioritized = Prioritizer.prioritize_functions(impact_scores)

    # Should be sorted by priority (highest first)
    assert len(prioritized) == 3
    assert prioritized[0]["impact_score"] >= prioritized[1]["impact_score"]
    assert prioritized[1]["impact_score"] >= prioritized[2]["impact_score"]
