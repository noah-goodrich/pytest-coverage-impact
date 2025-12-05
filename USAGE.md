# Usage Guide

Complete guide for using pytest-coverage-impact.

## Installation

```bash
pip install pytest-coverage-impact
```

## Basic Usage

```bash
# Run coverage impact analysis (--cov-report=json auto-added)
pytest --cov=your_project --coverage-impact

# Show top 10 functions
pytest --cov=your_project --coverage-impact --coverage-impact-top=10

# Generate JSON report
pytest --cov=your_project --coverage-impact --coverage-impact-json=report.json
```

## Understanding Output

### Terminal Report Columns

- **Priority**: Ranking (1 = highest priority)
- **Score**: Priority score (higher = more important)
- **Impact**: Call frequency × coverage gap
- **Complexity**: ML-predicted complexity (0-1 scale) with confidence interval
- **Coverage %**: Current test coverage

### Priority Score

Higher priority = test first:
- High Impact: Function called frequently
- Low Coverage: Function not well tested
- Low Complexity: Easy to write tests for
- High Confidence: ML model is confident

### Complexity Scale

- **0.0 - 0.3**: Low complexity (easy)
- **0.3 - 0.7**: Medium complexity
- **0.7 - 1.0**: High complexity (hard)

### Confidence Intervals

- **Narrow** (e.g., `[±0.05]`): Model is confident
- **Wide** (e.g., `[±0.30]`): Model is uncertain (may need more training data)

## JSON Report Format

```json
{
  "version": "1.0",
  "total_functions": 562,
  "functions": [
    {
      "function": "module.py::function_name",
      "file": "module.py",
      "line": 42,
      "impact": 12.5,
      "impact_score": 8.75,
      "complexity_score": 0.65,
      "confidence": 0.85,
      "priority": 2.45,
      "coverage_percentage": 0.3
    }
  ]
}
```

## Training Custom Models

See [TRAINING_COMMANDS.md](TRAINING_COMMANDS.md) for details.

Quick start:
```bash
pytest --coverage-impact-train
```

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for model path configuration.

## Troubleshooting

**Plugin not found**: `pip install -e pytest-coverage-impact/`
**No functions found**: Check source directory exists
**Coverage data not found**: Run with `--cov=project --coverage-impact`
**Model not loading**: Optional - plugin works without it (uses heuristics)

## Tips

1. Generate complete coverage first
2. Focus on top 10-20 by priority
3. Consider complexity when planning tests
4. Use confidence intervals to assess model certainty
5. Retrain model periodically as codebase grows
