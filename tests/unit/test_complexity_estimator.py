"""Unit tests for complexity estimator module"""

import ast
from pathlib import Path
from unittest.mock import Mock, patch


from pytest_coverage_impact.ml.complexity_estimator import ComplexityEstimator


def test_complexity_estimator_init_without_model():
    """Test estimator initialization without model"""
    estimator = ComplexityEstimator()

    assert estimator.model is None
    assert estimator.model_path is None
    assert estimator.is_available() is False
    assert estimator.confidence_level == 0.95


def test_complexity_estimator_fallback_via_public_api():
    """Test fallback complexity calculation when model not available (public API)"""
    estimator = ComplexityEstimator()

    code = """
def simple_func():
    pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    # Should use fallback when model is None
    score, _, _ = estimator.estimate_complexity(func_node)

    assert 0.0 <= score <= 1.0


def test_complexity_estimator_fallback_complexity_with_branches_public():
    """Test fallback complexity with control flow (public API)"""
    estimator = ComplexityEstimator()

    code = """
def complex_func(x):
    if x > 0:
        for i in range(10):
            if i % 2 == 0:
                pass
    return x
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    score, _, _ = estimator.estimate_complexity(func_node)

    assert 0.0 <= score <= 1.0
    # Should be higher than simple function (0.05 vs >0.05) if heuristics work
    # Simple function (2 lines) -> 2/200 = 0.01
    # Complex function (7 lines + 3 branches) -> 7/200 + 3/10 = 0.035 + 0.3 = 0.335
    assert score > 0.05


def test_complexity_estimator_estimate_without_model():
    """Test complexity estimation without model (uses fallback)"""
    estimator = ComplexityEstimator()

    code = """
def test_func():
    x = 1
    return x
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    score, lower, upper = estimator.estimate_complexity(func_node)

    assert 0.0 <= score <= 1.0
    assert lower is None
    assert upper is None


def test_complexity_estimator_is_available_without_model():
    """Test is_available returns False when model not loaded"""
    estimator = ComplexityEstimator()

    assert estimator.is_available() is False


def test_complexity_estimator_load_model_nonexistent():
    """Test loading model from nonexistent path"""
    nonexistent_path = Path("/nonexistent/model.pkl")

    # Should not raise if path doesn't exist during init
    estimator = ComplexityEstimator(model_path=nonexistent_path)

    assert estimator.model is None


def test_complexity_estimator_with_mock_model():
    """Test estimator with mock model"""
    estimator = ComplexityEstimator()
    estimator.confidence_level = 0.95

    # Create mock model
    mock_model = Mock()
    mock_model.is_trained = True
    # Predict with confidence should be called
    mock_model.predict_with_confidence = Mock(return_value=(0.65, 0.55, 0.75))

    estimator.model = mock_model

    code = """
def test_func():
    return 42
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    # Mock feature extractor
    with patch("pytest_coverage_impact.ml.complexity_estimator.FeatureExtractor.extract_features") as mock_extract:
        mock_extract.return_value = {
            "lines_of_code": 10.0,
            "cyclomatic_complexity": 1.0,
        }

        score, lower, upper = estimator.estimate_complexity(func_node)

        assert score == 0.65
        assert lower == 0.55
        assert upper == 0.75
        assert estimator.is_available() is True
