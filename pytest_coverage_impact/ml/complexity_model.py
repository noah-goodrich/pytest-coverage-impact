"""ML model for complexity estimation"""

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class ComplexityModel:
    """Random Forest model for predicting test complexity"""

    def __init__(self, n_estimators: int = 100, max_depth: int = 10, random_state: int = 42):
        """Initialize model

        Args:
            n_estimators: Number of trees in forest
            max_depth: Maximum depth of trees
            random_state: Random seed for reproducibility
        """
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,  # Use all available cores
        )
        self.feature_names: List[str] = []
        self.is_trained = False

    # JUSTIFICATION: High number of locals required for model training configuration
    # pylint: disable=too-many-locals
    # JUSTIFICATION: Method name 'train' is standard for ML models
    # pylint: disable=invalid-name
    def train(self, training_data: List[Dict]) -> Dict[str, float]:
        """Train model on training data

        Args:
            training_data: List of training examples with 'features' and 'complexity_label'

        Returns:
            Dictionary with training metrics (MAE, RMSE, R²)
        """
        if not training_data:
            raise ValueError("Training data is empty")

        # Extract features and labels
        X, y = self._extract_features_and_labels(training_data)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train model
        print(f"Training model on {len(X_train)} examples...")
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        metrics = {
            "train_mae": mean_absolute_error(y_train, y_pred_train),
            "train_rmse": np.sqrt(mean_squared_error(y_train, y_pred_train)),
            "train_r2": r2_score(y_train, y_pred_train),
            "test_mae": mean_absolute_error(y_test, y_pred_test),
            "test_rmse": np.sqrt(mean_squared_error(y_test, y_pred_test)),
            "test_r2": r2_score(y_test, y_pred_test),
        }

        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring="r2")
        # JUSTIFICATION: numpy method chaining is standard usage
        # pylint: disable=clean-arch-demeter
        metrics["cv_r2_mean"] = float(cv_scores.mean())
        metrics["cv_r2_std"] = float(cv_scores.std())
        # pylint: enable=clean-arch-demeter

        print("Training complete!")
        print(f"  Test R²: {metrics['test_r2']:.3f}")
        print(f"  Test MAE: {metrics['test_mae']:.3f}")
        print(f"  CV R²: {metrics['cv_r2_mean']:.3f} ± {metrics['cv_r2_std']:.3f}")

        return metrics

    def _extract_features_and_labels(self, training_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Extract features and labels from training data"""
        X = []
        y_labels = []

        # Get feature names from first example
        if training_data:
            self.feature_names = sorted(training_data[0]["features"].keys())

        for example in training_data:
            features = example["features"]
            label = example["complexity_label"]

            # Create feature vector in consistent order
            feature_vector = [features.get(name, 0.0) for name in self.feature_names]
            X.append(feature_vector)
            y_labels.append(label)

        return np.array(X), np.array(y_labels)

    def predict(self, features: Dict[str, float]) -> float:
        """Predict complexity for a function

        Args:
            features: Dictionary of feature values

        Returns:
            Predicted complexity score (0-1)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        # Create feature vector
        feature_vector = np.array([[features.get(name, 0.0) for name in self.feature_names]])

        prediction = self.model.predict(feature_vector)[0]

        # Clamp to [0, 1]
        return max(0.0, min(1.0, prediction))

    def predict_with_confidence(
        self, features: Dict[str, float], confidence_level: float = 0.95
    ) -> Tuple[float, float, float]:
        """Predict complexity with confidence intervals

        Uses Random Forest's tree variance for uncertainty estimation.

        Args:
            features: Dictionary of feature values
            confidence_level: Confidence level (default 0.95 for 95% CI)

        Returns:
            Tuple of (prediction, lower_bound, upper_bound)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        # Create feature vector
        feature_vector = np.array([[features.get(name, 0.0) for name in self.feature_names]])

        tree_predictions = np.array([tree.predict(feature_vector)[0] for tree in self.model.estimators_])

        # Calculate mean and std
        mean_pred = np.mean(tree_predictions)
        std_pred = np.std(tree_predictions)

        # Calculate confidence interval (assuming normal distribution)
        # For 95% CI: z = 1.96
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 99% CI

        lower_bound = mean_pred - z_score * std_pred
        upper_bound = mean_pred + z_score * std_pred

        # Clamp to [0, 1]
        mean_pred = max(0.0, min(1.0, mean_pred))
        lower_bound = max(0.0, min(1.0, lower_bound))
        upper_bound = max(0.0, min(1.0, upper_bound))

        return (mean_pred, lower_bound, upper_bound)

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")

        importances = self.model.feature_importances_
        return dict(zip(self.feature_names, importances))

    def save(self, model_path: Path, metadata: Optional[Dict] = None) -> None:
        """Save model to file

        Args:
            model_path: Path to save model (.pkl file)
            metadata: Optional metadata to save alongside model
        """
        # JUSTIFICATION: Pathlib parent.mkdir is standard usage
        # pylint: disable=clean-arch-demeter
        model_path.parent.mkdir(parents=True, exist_ok=True)
        # pylint: enable=clean-arch-demeter

        model_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "is_trained": self.is_trained,
            "metadata": metadata or {},
        }

        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)

        print(f"Model saved to {model_path}")

    @classmethod
    def load(cls, model_path: Path) -> "ComplexityModel":
        """Load model from file

        Args:
            model_path: Path to model file

        Returns:
            Loaded ComplexityModel instance
        """
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)

        instance = cls()
        instance.model = model_data["model"]
        instance.feature_names = model_data["feature_names"]
        instance.is_trained = model_data["is_trained"]

        return instance
