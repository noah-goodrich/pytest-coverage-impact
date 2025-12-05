"""Main API for complexity estimation with confidence intervals"""

import ast
from pathlib import Path
from typing import Optional, Tuple

from pytest_coverage_impact.ml.complexity_model import ComplexityModel
from pytest_coverage_impact.ml.feature_extractor import FeatureExtractor


class ComplexityEstimator:
    """Estimate test complexity for functions with confidence intervals"""

    def __init__(self, model_path: Optional[Path] = None):
        """Initialize estimator

        Args:
            model_path: Optional path to trained model file.
                       If None, will use default model location.
        """
        self.model: Optional[ComplexityModel] = None
        self.model_path = model_path

        if model_path and model_path.exists():
            self.load_model(model_path)

    def load_model(self, model_path: Path) -> None:
        """Load trained model

        Args:
            model_path: Path to model file
        """
        self.model = ComplexityModel.load(model_path)
        self.model_path = model_path

    def estimate_complexity(
        self,
        func_node: ast.FunctionDef,
        module_tree: Optional[ast.AST] = None,
        file_path: Optional[str] = None,
        with_confidence: bool = True,
        confidence_level: float = 0.95,
    ) -> Tuple[float, Optional[float], Optional[float]]:
        """Estimate complexity for a function

        Args:
            func_node: Function definition AST node
            module_tree: Optional full module AST for context
            file_path: Optional file path for external dependency detection
            with_confidence: Whether to return confidence intervals
            confidence_level: Confidence level (0.95 for 95% CI)

        Returns:
            Tuple of (complexity_score, lower_bound, upper_bound)
            If with_confidence=False or model not loaded, bounds will be None
        """
        if self.model is None:
            # Fallback: simple heuristic if model not available
            return self._fallback_complexity(func_node), None, None

        # Extract features
        features = FeatureExtractor.extract_features(func_node, module_tree, file_path)

        # Predict with confidence intervals
        if with_confidence:
            score, lower, upper = self.model.predict_with_confidence(features, confidence_level)
            return (score, lower, upper)
        else:
            score = self.model.predict(features)
            return (score, None, None)

    def _fallback_complexity(self, func_node: ast.FunctionDef) -> float:
        """Simple fallback complexity estimation when model not available

        Args:
            func_node: Function definition AST node

        Returns:
            Simple complexity estimate (0-1)
        """
        # Simple heuristic based on lines and branches
        lines = func_node.end_lineno - func_node.lineno + 1 if func_node.end_lineno else 10

        branches = 0
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                branches += 1

        # Normalize: lines/200 + branches/10, capped at 1.0
        complexity = min(1.0, (lines / 200.0) + (branches / 10.0))
        return complexity

    def is_available(self) -> bool:
        """Check if model is loaded and available

        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None and self.model.is_trained
