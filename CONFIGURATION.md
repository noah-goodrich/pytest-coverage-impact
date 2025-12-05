# Configuration

Configure ML model path via CLI, pytest.ini, or environment variable.

## Priority Order

1. CLI: `--coverage-impact-model-path=PATH`
2. pytest.ini: `coverage_impact_model_path`
3. Env var: `PYTEST_COVERAGE_IMPACT_MODEL_PATH`
4. Default: `.coverage_impact/models/` (auto-detects latest version)
5. Fallback: Bundled default model

## Recommended: pytest.ini

```ini
[pytest]
# Directory path - auto-detects latest version
coverage_impact_model_path = .coverage_impact/models
```

**Directory vs File**: Use directory to auto-detect highest version model (e.g., `v1.2.pkl` if `v1.0.pkl`, `v1.1.pkl`, `v1.2.pkl` exist)

## Examples

### pytest.ini (Project-level)
```ini
[pytest]
coverage_impact_model_path = .coverage_impact/models
```

### Environment Variable (CI/CD)
```bash
export PYTEST_COVERAGE_IMPACT_MODEL_PATH=.coverage_impact/models
```

### CLI (One-off)
```bash
pytest --coverage-impact --coverage-impact-model-path=.coverage_impact/models
```

## Path Resolution

- Relative paths: Resolved from project root (where pytest runs)
- Absolute paths: Used as-is
- Directories: Auto-detects highest version model
- Files: Uses specific file

## Default Locations

- Project: `.coverage_impact/models/` (user-trained models)
- Plugin: Bundled default model (fallback)
