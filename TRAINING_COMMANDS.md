# Model Training

Train custom ML models with automatic versioning.

## Quick Start

```bash
# Combined command - collects data and trains model
pytest --coverage-impact-train
```

This automatically:
- Collects training data → `dataset_v1.0.json` (auto-increments)
- Trains model → `complexity_model_v1.0.pkl` (auto-increments)
- Saves to `.coverage_impact/` directory

## Individual Commands

### Collect Training Data

```bash
# Directory path - auto-versions (recommended)
pytest --coverage-impact-collect-training-data=.coverage_impact/training_data/

# Or specify exact file
pytest --coverage-impact-collect-training-data=.coverage_impact/training_data/dataset_v2.0.json
```

### Train Model

```bash
pytest --coverage-impact-train-model=.coverage_impact/training_data/dataset_v1.0.json
```

## Auto-Versioning

Both training data and models are automatically versioned:
- Training data: `dataset_v1.0.json`, `dataset_v1.1.json`, etc.
- Models: `complexity_model_v1.0.pkl`, `complexity_model_v1.1.pkl`, etc.

Plugin auto-detects latest version when using directory paths.

## Using Your Model

Once trained, configure model path in `pytest.ini`:

```ini
[pytest]
coverage_impact_model_path = .coverage_impact/models
```

Plugin automatically uses the highest version model in the directory.

## How It Works

1. Maps functions to their existing tests
2. Extracts static code features (cyclomatic complexity, dependencies, etc.)
3. Analyzes test complexity (lines, mocks, fixtures, markers)
4. Creates training dataset (features → test complexity label)
5. Trains Random Forest model
6. Saves model with metadata

## Requirements

- Existing tests in your codebase
- Coverage data (`coverage.json`)
- Functions to test mapping (uses naming conventions)
