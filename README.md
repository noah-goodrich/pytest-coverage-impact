# pytest-coverage-impact

ML-powered test coverage analysis plugin for pytest that identifies high-impact, low-complexity areas to test first.

## Features

- **Coverage Impact Analysis**: Builds call graphs to identify high-impact functions
- **ML Complexity Estimation**: Predicts test complexity with confidence intervals
- **Prioritization**: Suggests what to test first based on impact and complexity
- **Works Out of the Box**: Includes pre-trained model, no configuration required
- **Fast Performance**: Optimized for speed (analyzes 1700+ functions in ~1.5 seconds)
- **Real-time Progress**: Visual progress bars and step-by-step timing

## Installation

```bash
pip install pytest-coverage-impact
```

## Quick Start

```bash
# Run coverage impact analysis (--cov-report=json automatically added)
pytest --cov=your_project --coverage-impact

# Show top 10 functions by priority
pytest --cov=your_project --coverage-impact --coverage-impact-top=10

# Generate JSON report
pytest --cov=your_project --coverage-impact --coverage-impact-json=report.json
```

## Example Output

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
5. **Reporting**: Generates formatted reports showing what to test first

## Model Training (Optional)

Plugin includes pre-trained model - no training required. To customize:

```bash
# Combined command - collects data and trains model
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

## Documentation

- **[docs/USAGE.md](docs/USAGE.md)** - Complete usage guide with examples
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Configure plugin settings and model paths
- **[docs/TRAINING_COMMANDS.md](docs/TRAINING_COMMANDS.md)** - Train custom ML models
- **[docs/FORMULA_EXPLANATION.md](docs/FORMULA_EXPLANATION.md)** - How scores are calculated
- **[docs/CONFIDENCE_AND_PRIORITY.md](docs/CONFIDENCE_AND_PRIORITY.md)** - How confidence affects prioritization
- **[docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md)** - Releasing and publishing to PyPI
- **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** - Performance optimizations explained
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

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
