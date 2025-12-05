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


def test_complexity_estimator_fallback_complexity():
    """Test fallback complexity calculation when model not available"""
    estimator = ComplexityEstimator()

    code = """
def simple_func():
    pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    complexity = estimator._fallback_complexity(func_node)

    assert 0.0 <= complexity <= 1.0


def test_complexity_estimator_fallback_complexity_with_branches():
    """Test fallback complexity with control flow"""
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

    complexity = estimator._fallback_complexity(func_node)

    assert 0.0 <= complexity <= 1.0
    # Should be higher than simple function
    assert complexity > 0.0


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


def test_complexity_estimator_estimate_without_confidence():
    """Test complexity estimation without confidence intervals"""
    estimator = ComplexityEstimator()

    code = """
def test_func():
    return 42
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    score, lower, upper = estimator.estimate_complexity(func_node, with_confidence=False)

    assert 0.0 <= score <= 1.0
    assert lower is None
    assert upper is None


def test_complexity_estimator_is_available_without_model():
    """Test is_available returns False when model not loaded"""
    estimator = ComplexityEstimator()

    assert estimator.is_available() is False


def test_complexity_estimator_load_model_nonexistent():
    """Test loading model from nonexistent path"""
    estimator = ComplexityEstimator()

    nonexistent_path = Path("/nonexistent/model.pkl")

    # Should not raise if path doesn't exist during init
    estimator = ComplexityEstimator(model_path=nonexistent_path)

    assert estimator.model is None


def test_complexity_estimator_with_mock_model():
    """Test estimator with mock model"""
    estimator = ComplexityEstimator()

    # Create mock model
    mock_model = Mock()
    mock_model.is_trained = True
    mock_model.predict = Mock(return_value=0.65)
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
        mock_extract.return_value = {"lines_of_code": 10.0, "cyclomatic_complexity": 1.0}

        score, lower, upper = estimator.estimate_complexity(func_node, with_confidence=True)

        assert score == 0.65
        assert lower == 0.55
        assert upper == 0.75
        assert estimator.is_available() is True


def test_complexity_estimator_estimate_without_confidence_with_model():
    """Test estimation without confidence when model is loaded"""
    estimator = ComplexityEstimator()

    mock_model = Mock()
    mock_model.is_trained = True
    mock_model.predict = Mock(return_value=0.7)

    estimator.model = mock_model

    code = """
def test_func():
    pass
"""
    tree = ast.parse(code)
    func_node = tree.body[0]

    with patch("pytest_coverage_impact.ml.complexity_estimator.FeatureExtractor.extract_features") as mock_extract:
        mock_extract.return_value = {"lines_of_code": 5.0}

        score, lower, upper = estimator.estimate_complexity(func_node, with_confidence=False)

        assert score == 0.7
        assert lower is None
        assert upper is None
