"""Unit tests for complexity model module"""

import tempfile
from pathlib import Path

import pytest

from pytest_coverage_impact.ml.complexity_model import ComplexityModel


def test_complexity_model_initialization():
    """Test model initialization"""
    model = ComplexityModel()

    assert model.is_trained is False
    assert model.feature_names == []
    assert model.model is not None


def test_complexity_model_train_empty_data():
    """Test that training with empty data raises ValueError"""
    model = ComplexityModel()

    with pytest.raises(ValueError, match="Training data is empty"):
        model.train([])


def test_complexity_model_train_basic():
    """Test basic model training"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    # Need at least 10 samples for 20% test split to have 2 samples (for R2)
    training_data = [
        {
            "features": {
                "lines_of_code": float(i * 10),
                "cyclomatic_complexity": float(i % 5),
                "num_parameters": float(i % 3),
            },
            "complexity_label": float(i % 10) / 10.0,
        }
        for i in range(1, 11)
    ]
    metrics = model.train(training_data)

    assert model.is_trained is True
    assert len(model.feature_names) == 3
    assert "train_mae" in metrics
    assert "test_mae" in metrics
    assert "test_r2" in metrics
    assert "cv_r2_mean" in metrics


def test_complexity_model_predict_not_trained():
    """Test that predict raises error when model not trained"""
    model = ComplexityModel()

    with pytest.raises(ValueError, match="Model not trained"):
        model.predict({"lines_of_code": 10.0})


def test_complexity_model_predict():
    """Test model prediction"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    # Train with sufficient data for CV
    training_data = [
        {"features": {"lines_of_code": 10.0, "cyclomatic_complexity": 1.0}, "complexity_label": 0.3},
        {"features": {"lines_of_code": 50.0, "cyclomatic_complexity": 5.0}, "complexity_label": 0.7},
        {"features": {"lines_of_code": 30.0, "cyclomatic_complexity": 3.0}, "complexity_label": 0.5},
        {"features": {"lines_of_code": 20.0, "cyclomatic_complexity": 2.0}, "complexity_label": 0.4},
        {"features": {"lines_of_code": 40.0, "cyclomatic_complexity": 4.0}, "complexity_label": 0.6},
        {"features": {"lines_of_code": 60.0, "cyclomatic_complexity": 6.0}, "complexity_label": 0.8},
        {"features": {"lines_of_code": 70.0, "cyclomatic_complexity": 7.0}, "complexity_label": 0.9},
        {"features": {"lines_of_code": 80.0, "cyclomatic_complexity": 8.0}, "complexity_label": 0.2},
        {"features": {"lines_of_code": 90.0, "cyclomatic_complexity": 9.0}, "complexity_label": 0.1},
        {"features": {"lines_of_code": 11.0, "cyclomatic_complexity": 1.1}, "complexity_label": 0.3},
    ]

    model.train(training_data)

    # Predict
    prediction = model.predict(
        {
            "lines_of_code": 30.0,
            "cyclomatic_complexity": 3.0,
        }
    )

    assert 0.0 <= prediction <= 1.0


def test_complexity_model_predict_missing_features():
    """Test prediction with missing features (should default to 0.0)"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    training_data = [
        {"features": {"lines_of_code": 10.0, "cyclomatic_complexity": 1.0}, "complexity_label": 0.3},
        {"features": {"lines_of_code": 20.0, "cyclomatic_complexity": 2.0}, "complexity_label": 0.4},
        {"features": {"lines_of_code": 30.0, "cyclomatic_complexity": 3.0}, "complexity_label": 0.5},
        {"features": {"lines_of_code": 40.0, "cyclomatic_complexity": 4.0}, "complexity_label": 0.6},
        {"features": {"lines_of_code": 50.0, "cyclomatic_complexity": 5.0}, "complexity_label": 0.7},
        {"features": {"lines_of_code": 60.0, "cyclomatic_complexity": 6.0}, "complexity_label": 0.8},
        {"features": {"lines_of_code": 70.0, "cyclomatic_complexity": 7.0}, "complexity_label": 0.9},
        {"features": {"lines_of_code": 80.0, "cyclomatic_complexity": 8.0}, "complexity_label": 0.2},
        {"features": {"lines_of_code": 90.0, "cyclomatic_complexity": 9.0}, "complexity_label": 0.1},
        {"features": {"lines_of_code": 11.0, "cyclomatic_complexity": 1.1}, "complexity_label": 0.3},
    ]

    model.train(training_data)

    # Predict with missing feature (should use 0.0)
    prediction = model.predict(
        {
            "lines_of_code": 10.0,
            # cyclomatic_complexity missing - should default to 0.0
        }
    )

    assert 0.0 <= prediction <= 1.0


def test_complexity_model_predict_with_confidence():
    """Test prediction with confidence intervals"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    training_data = [
        {"features": {"lines_of_code": 10.0, "cyclomatic_complexity": 1.0}, "complexity_label": 0.3},
        {"features": {"lines_of_code": 50.0, "cyclomatic_complexity": 5.0}, "complexity_label": 0.7},
        {"features": {"lines_of_code": 30.0, "cyclomatic_complexity": 3.0}, "complexity_label": 0.5},
        {"features": {"lines_of_code": 20.0, "cyclomatic_complexity": 2.0}, "complexity_label": 0.4},
        {"features": {"lines_of_code": 40.0, "cyclomatic_complexity": 4.0}, "complexity_label": 0.6},
        {"features": {"lines_of_code": 60.0, "cyclomatic_complexity": 6.0}, "complexity_label": 0.8},
        {"features": {"lines_of_code": 70.0, "cyclomatic_complexity": 7.0}, "complexity_label": 0.9},
        {"features": {"lines_of_code": 80.0, "cyclomatic_complexity": 8.0}, "complexity_label": 0.2},
        {"features": {"lines_of_code": 90.0, "cyclomatic_complexity": 9.0}, "complexity_label": 0.1},
        {"features": {"lines_of_code": 11.0, "cyclomatic_complexity": 1.1}, "complexity_label": 0.3},
    ]

    model.train(training_data)

    score, lower, upper = model.predict_with_confidence(
        {
            "lines_of_code": 30.0,
            "cyclomatic_complexity": 3.0,
        }
    )

    assert 0.0 <= score <= 1.0
    assert 0.0 <= lower <= 1.0
    assert 0.0 <= upper <= 1.0
    assert lower <= score <= upper


def test_complexity_model_predict_with_confidence_not_trained():
    """Test that predict_with_confidence raises error when not trained"""
    model = ComplexityModel()

    with pytest.raises(ValueError, match="Model not trained"):
        model.predict_with_confidence({"lines_of_code": 10.0})


def test_complexity_model_get_feature_importance_not_trained():
    """Test that get_feature_importance raises error when not trained"""
    model = ComplexityModel()

    with pytest.raises(ValueError, match="Model not trained"):
        model.get_feature_importance()


def test_complexity_model_get_feature_importance():
    """Test getting feature importance"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    training_data = [
        {"features": {"lines_of_code": 10.0, "cyclomatic_complexity": 1.0}, "complexity_label": 0.3},
        {"features": {"lines_of_code": 50.0, "cyclomatic_complexity": 5.0}, "complexity_label": 0.7},
        {"features": {"lines_of_code": 30.0, "cyclomatic_complexity": 3.0}, "complexity_label": 0.5},
        {"features": {"lines_of_code": 20.0, "cyclomatic_complexity": 2.0}, "complexity_label": 0.4},
        {"features": {"lines_of_code": 40.0, "cyclomatic_complexity": 4.0}, "complexity_label": 0.6},
        {"features": {"lines_of_code": 60.0, "cyclomatic_complexity": 6.0}, "complexity_label": 0.8},
        {"features": {"lines_of_code": 70.0, "cyclomatic_complexity": 7.0}, "complexity_label": 0.9},
        {"features": {"lines_of_code": 80.0, "cyclomatic_complexity": 8.0}, "complexity_label": 0.2},
        {"features": {"lines_of_code": 90.0, "cyclomatic_complexity": 9.0}, "complexity_label": 0.1},
        {"features": {"lines_of_code": 11.0, "cyclomatic_complexity": 1.1}, "complexity_label": 0.3},
    ]

    model.train(training_data)

    importance = model.get_feature_importance()

    assert isinstance(importance, dict)
    assert "lines_of_code" in importance
    assert "cyclomatic_complexity" in importance
    assert all(isinstance(v, (int, float)) for v in importance.values())


def test_complexity_model_save_and_load():
    """Test saving and loading model"""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "model.pkl"

        # Train and save
        model = ComplexityModel(n_estimators=10, random_state=42)
        training_data = [
            {"features": {"lines_of_code": 10.0, "cyclomatic_complexity": 1.0}, "complexity_label": 0.3},
            {"features": {"lines_of_code": 20.0, "cyclomatic_complexity": 2.0}, "complexity_label": 0.4},
            {"features": {"lines_of_code": 30.0, "cyclomatic_complexity": 3.0}, "complexity_label": 0.5},
            {"features": {"lines_of_code": 40.0, "cyclomatic_complexity": 4.0}, "complexity_label": 0.6},
            {"features": {"lines_of_code": 50.0, "cyclomatic_complexity": 5.0}, "complexity_label": 0.7},
            {"features": {"lines_of_code": 60.0, "cyclomatic_complexity": 6.0}, "complexity_label": 0.8},
            {"features": {"lines_of_code": 70.0, "cyclomatic_complexity": 7.0}, "complexity_label": 0.9},
            {"features": {"lines_of_code": 80.0, "cyclomatic_complexity": 8.0}, "complexity_label": 0.2},
            {"features": {"lines_of_code": 90.0, "cyclomatic_complexity": 9.0}, "complexity_label": 0.1},
            {"features": {"lines_of_code": 11.0, "cyclomatic_complexity": 1.1}, "complexity_label": 0.3},
        ]

        model.train(training_data)
        model.save(model_path, metadata={"version": "1.0"})

        assert model_path.exists()

        # Load
        loaded_model = ComplexityModel.load(model_path)

        assert loaded_model.is_trained is True
        assert loaded_model.feature_names == model.feature_names

        # Test prediction works
        prediction = loaded_model.predict(
            {
                "lines_of_code": 10.0,
                "cyclomatic_complexity": 1.0,
            }
        )

        assert 0.0 <= prediction <= 1.0


def test_complexity_model_predict_clamping():
    """Test that predictions are clamped to [0, 1]"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    training_data = [{"features": {"lines_of_code": float(i * 10)}, "complexity_label": 0.5} for i in range(1, 11)]

    model.train(training_data)

    # Even with extreme values, should be clamped
    prediction = model.predict(
        {
            "lines_of_code": 10000.0,  # Extreme value
        }
    )

    assert 0.0 <= prediction <= 1.0


def test_complexity_model_confidence_interval_clamping():
    """Test that confidence intervals are clamped to [0, 1]"""
    model = ComplexityModel(n_estimators=10, random_state=42)

    # Need at least 10 samples
    training_data = [
        {"features": {"lines_of_code": float(i * 10)}, "complexity_label": 0.5 + (i * 0.04)} for i in range(1, 11)
    ]

    model.train(training_data)

    score, lower, upper = model.predict_with_confidence(
        {
            "lines_of_code": 10.0,
        }
    )

    assert 0.0 <= score <= 1.0
    assert 0.0 <= lower <= 1.0
    assert 0.0 <= upper <= 1.0
