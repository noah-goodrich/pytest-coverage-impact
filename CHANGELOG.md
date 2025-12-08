# Changelog

All notable changes to pytest-coverage-impact will be documented in this file.

## [0.1.0] - 2024-01-XX (Initial Release)

### Added

#### Core Features
- **Call Graph Analysis**: AST-based call graph builder that tracks function relationships
  - Finds all functions in codebase
  - Tracks which functions call which other functions
  - Calculates call frequency (direct + indirect)
  - Tested on codebases with 1000+ functions

- **Impact Score Calculation**: Identifies high-impact, low-coverage functions
  - Formula: `impact_score = call_frequency × (1 - coverage_pct)`
  - Integrates with coverage.json data
  - Handles various file path formats

- **ML Complexity Estimation**: Machine learning model for predicting test complexity
  - Extracts 20+ static code features (cyclomatic complexity, dependencies, control flow)
  - Random Forest regression model
  - Predicts normalized complexity score (0-1)
  - **Confidence intervals** showing prediction uncertainty
  - Format: `0.65 [0.55 - 0.75]` (95% CI)

- **Prioritization Framework**: Ranks functions by test priority
  - Formula: `priority = (impact × confidence) / (complexity × effort)`
  - Identifies high-impact, low-complexity functions first
  - Helps developers focus on highest-value tests

- **Terminal Reports**: Rich formatted output
  - Beautiful tables with color coding
  - Shows priority, impact, complexity, coverage
  - Sortable by priority score

- **JSON Reports**: Machine-readable output
  - Full function data with all scores
  - Easy to parse and integrate with other tools

#### ML Components
- **Feature Extractor**: Extracts static code features for ML
  - Size metrics (lines, statements, cyclomatic complexity)
  - Control flow complexity (branches, loops, exceptions)
  - Dependency metrics (function calls, external APIs)
  - Type indicators (methods, async, parameters)

- **Test Analyzer**: Analyzes test files for complexity labels
  - Maps functions to their tests
  - Extracts test complexity features
  - Calculates training labels from actual test complexity

- **Training Data Collector**: Builds ML training datasets
  - Scans codebase for function-test pairs
  - Extracts features and labels
  - Generates JSON training datasets

- **Complexity Model**: ML model implementation
  - Random Forest Regressor
  - Model training and evaluation
  - Model serialization/loading
  - Confidence interval calculation

- **Complexity Estimator**: Prediction API
  - Load trained models
  - Predict complexity with confidence intervals
  - Fallback heuristic when model unavailable

#### Plugin Integration
- Pytest plugin hooks for automatic analysis
- CLI options:
  - `--coverage-impact`: Enable analysis
  - `--coverage-impact-top=N`: Show top N functions
  - `--coverage-impact-json=PATH`: Generate JSON report
  - `--coverage-impact-html=PATH`: HTML report (coming soon)
  - `--coverage-impact-feedback`: Interactive feedback (coming soon)

### Technical Details

#### Architecture Improvements
- **Better Class Detection**: Uses AST visitor pattern instead of naive tree walking
- **Flexible Path Matching**: Handles different coverage.json file path formats
- **Automatic Source Detection**: Tries multiple common directory patterns
- **Graceful Degradation**: Works without ML model (uses heuristics)

#### Performance Optimizations
- Limits complexity estimation to top 100 functions for performance
- Efficient AST parsing with early exits
- Optimized call graph traversal

### Documentation

- Comprehensive README with usage examples
- Implementation plan with detailed tasks
- Status documentation
- Scope analysis for feature decisions

### Testing

- Unit tests for call graph builder (6 tests)
- Integration tests on real codebase (2 tests)
- All tests passing
- Tested on snowfort codebase (1,381 functions)

### Model Performance

- **Training Examples**: 512 function-test pairs
- **Model Version**: v1.0
- **Test R²**: 0.041 (expected to improve with more data)
- **Note**: Model performance is expected to be low initially and will improve with:
  - More training data
  - Developer feedback
  - Model retraining

### Known Limitations

- Model performance is low with limited training data (will improve)
- Complexity estimation limited to top 100 functions for performance
- Test mapping uses simple naming conventions (could be enhanced)
- HTML reports not yet implemented
- Feedback system not yet implemented

### Upcoming Features

- Developer feedback collection system
- Model retraining pipeline
- HTML report generation
- PyPI publishing
- Historical trend analysis (v2.0)
