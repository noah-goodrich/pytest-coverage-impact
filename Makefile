.PHONY: clean test lint format

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f .coverage
	rm -f coverage.xml
	rm -f coverage.json

test:
	@if pytest --help | grep -q "coverage-impact"; then \
		pytest --coverage-impact tests/unit --cov=pytest_coverage_impact --cov-report=xml --cov-report=term-missing -v; \
	else \
		pytest tests/unit --cov=pytest_coverage_impact --cov-report=xml --cov-report=term-missing -v; \
	fi

lint:
	ruff check pytest_coverage_impact/ tests/
	@if pip show pylint-clean-architecture > /dev/null 2>&1 || [ -d "/development/pylint-clean-architecture" ]; then \
		pylint --load-plugins=clean_architecture_linter pytest_coverage_impact/ tests/; \
	else \
		pylint pytest_coverage_impact/ tests/; \
	fi

format:
	ruff format pytest_coverage_impact/ tests/
