<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/noah-goodrich/pytest-coverage-impact/main/assets/hero-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/noah-goodrich/pytest-coverage-impact/main/assets/hero-light.png">
  <img alt="Stellar Engineering Command Banner" src="https://raw.githubusercontent.com/noah-goodrich/pytest-coverage-impact/main/assets/hero-light.png" width="100%">
</picture>

![PyPI](https://img.shields.io/pypi/v/pytest-coverage-impact?color=C41E3A&labelColor=333333)
![Build Status](https://img.shields.io/github/actions/workflow/status/noah-goodrich/pytest-coverage-impact/ci.yml?branch=main&color=007BFF&labelColor=333333&label=Build%20Status)
![Python Versions](https://img.shields.io/pypi/pyversions/pytest-coverage-impact?color=F9A602&labelColor=333333)
![License](https://img.shields.io/github/license/noah-goodrich/pytest-coverage-impact?color=F9A602&labelColor=333333)

![PyPI](https://img.shields.io/pypi/v/pytest-coverage-impact?color=C41E3A&labelColor=333333)
![Build Status](https://img.shields.io/github/actions/workflow/status/noah-goodrich/pytest-coverage-impact/ci.yml?branch=main&color=007BFF&labelColor=333333&label=Build%20Status)
![Python Versions](https://img.shields.io/pypi/pyversions/pytest-coverage-impact?color=F9A602&labelColor=333333)
![License](https://img.shields.io/github/license/noah-goodrich/pytest-coverage-impact?color=F9A602&labelColor=333333)

Captain's Log: ML-powered **Sensor Telemetry Analysis** module for pytest that identifies high-impact, low-complexity areas to test first.

Scanning the planetary surface (codebase) to determine sensor coverage (test coverage) and identify critical impact zones for the fleet.

## Features

- **Coverage Impact Analysis**: Builds call graphs to identify high-impact functions
- **ML Complexity Estimation**: Predicts test complexity with confidence intervals
- **Prioritization**: Suggests what to test first based on impact and complexity
- **Refitted Out of the Box**: Includes pre-trained model, no console calibration required
- **Warp Speed Performance**: Optimized for speed (analyzes 1700+ functions in ~1.5 seconds)
- **Real-time Telemetry**: Visual progress bars and step-by-step timing

## Docking Procedures

```bash
pip install pytest-coverage-impact
```

## Flight Manual

```bash
# Run sensor telemetry analysis (--cov-report=json automatically added)
pytest --cov=your_project --coverage-impact

# Show top 10 functions by priority
pytest --cov=your_project --coverage-impact --coverage-impact-top=10

# Generate Telemetry Data (JSON report)
pytest --cov=your_project --coverage-impact --coverage-impact-json=report.json
```

### Example Telemetry Output

```
Top Functions by Priority (Impact / Complexity)
┏━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Priority ┃ Score ┃ Impact ┃ Complexity ┃ Function   ┃
┡━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│        1 │  2.45 │   12.5 │  0.65 [±0.15] │ module.py │
```

## How It Works

1. **Call Graph Analysis**: Parses AST to build function call relationships
2. **Impact Calculation**: `impact = call_frequency × (1 - coverage_pct)`
3. **Complexity Estimation**: Uses Random Forest ML model (0-1 scale)
4. **Prioritization**: `priority = (impact × confidence) / (complexity × effort)`
5. **Reporting**: Generates formatted sensor reports showing what to test first

## Model Training (Optional)

Module includes pre-trained model - no training required. To recalibrate:

```bash
# Combined command - collects telemetry and recalibrates model
pytest --coverage-impact-train
```

See [docs/TRAINING_COMMANDS.md](docs/TRAINING_COMMANDS.md) for details.

## Requirements

- Python 3.8+
- pytest 7.0+
- coverage 6.0+
- scikit-learn 1.0+
- numpy 1.20+
- rich 13.0+ (terminal formatting)

## Mission Log

- **[CHANGELOG.md](CHANGELOG.md)** - Mission history and sector updates

## Documentation

- **[docs/USAGE.md](docs/USAGE.md)** - Complete Flight Manual with examples
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Console Calibration settings and model paths
- **[docs/TRAINING_COMMANDS.md](docs/TRAINING_COMMANDS.md)** - Recalibrate custom ML models
- **[docs/FORMULA_EXPLANATION.md](docs/FORMULA_EXPLANATION.md)** - How telemetry scores are calculated
- **[docs/CONFIDENCE_AND_PRIORITY.md](docs/CONFIDENCE_AND_PRIORITY.md)** - How confidence affects prioritization
- **[docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md)** - Launch procedures and publishing to sector PyPI
- **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** - Warp speed optimizations explained

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black pytest_coverage_impact tests/
ruff check pytest_coverage_impact tests/
```

## License

MIT License
