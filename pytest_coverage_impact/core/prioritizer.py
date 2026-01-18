"""Prioritization framework for coverage impact analysis"""

from typing import Dict, List, Optional


class Prioritizer:
    """Prioritize functions based on impact, complexity, and confidence"""

    @staticmethod
    def calculate_priority(
        impact_score: float,
        complexity_score: float,
        confidence: float = 1.0,
        effort_multiplier: float = 1.0,
    ) -> float:
        """Calculate priority score for a function

        Formula: Priority = (Coverage Impact × Confidence) / (Test Complexity × Effort)

        Higher priority = higher impact, lower complexity

        Args:
            impact_score: Coverage impact score (from impact calculator)
            complexity_score: Test complexity score (0-1, from ML model)
            confidence: Confidence in prediction (0-1, default 1.0)
            effort_multiplier: Effort multiplier (default 1.0, can be derived from complexity)

        Returns:
            Priority score (higher = more important to test)
        """
        # Avoid division by zero
        denominator = (complexity_score + 0.1) * (effort_multiplier + 0.1)

        priority = (impact_score * confidence) / denominator

        return priority

    @staticmethod
    def prioritize_functions(
        impact_scores: List[Dict],
        complexity_scores: Optional[Dict[str, float]] = None,
        confidence_scores: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        """Prioritize functions based on impact and complexity

        Args:
            impact_scores: List of impact score dictionaries
            complexity_scores: Optional dict mapping function signatures to complexity scores
            confidence_scores: Optional dict mapping function signatures to confidence scores

        Returns:
            List of function data with priority scores, sorted by priority (highest first)
        """
        prioritized = []

        if not impact_scores:
            return []

        # Find maximum impact score for normalization
        max_impact = max(item.get("impact_score", 0) for item in impact_scores)
        if max_impact == 0:
            max_impact = 1.0

        prioritized = []

        for item in impact_scores:
            func_signature = item["function"]

            # Get complexity score (default to 0.5 if not available)
            complexity = 0.5
            if complexity_scores and func_signature in complexity_scores:
                complexity = complexity_scores[func_signature]

            # Get confidence (default to 1.0 if not available)
            confidence = 1.0
            if confidence_scores and func_signature in confidence_scores:
                confidence = confidence_scores[func_signature]

            # Normalize impact score to 0-100 range
            raw_impact = item["impact_score"]
            normalized_impact = (raw_impact / max_impact) * 100.0

            # Derive effort from complexity (more complex = more effort)
            effort = 1.0 + (complexity * 2.0)  # Effort ranges from 1.0 to 3.0

            # Calculate priority using normalized impact
            priority = Prioritizer.calculate_priority(
                impact_score=normalized_impact,
                complexity_score=complexity,
                confidence=confidence,
                effort_multiplier=effort,
            )

            # Add to result
            result = item.copy()
            result["complexity_score"] = complexity
            result["confidence"] = confidence
            result["priority"] = priority
            result["impact_score_normalized"] = normalized_impact
            prioritized.append(result)

        # Sort by priority (highest first), then by impact for tie-breaking
        prioritized.sort(key=lambda x: (x["priority"], x.get("impact", 0)), reverse=True)

        # Filter out functions with zero impact (unused functions)
        prioritized_with_impact = [f for f in prioritized if f.get("impact", 0) > 0]

        return prioritized_with_impact if prioritized_with_impact else prioritized
