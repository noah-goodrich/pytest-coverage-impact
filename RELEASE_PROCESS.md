# Release Process

Automated PyPI publishing via GitHub Actions when tags are pushed.

## Quick Start

1. Update CHANGELOG.md and version numbers
2. Commit: `git commit -m "Bump version to 0.1.0"`
3. Create and push tag: `git tag -a v0.1.0 -m "Release" && git push origin v0.1.0`
4. GitHub Actions automatically builds, tests, publishes to PyPI, and creates a release

## Version Format

- Use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`
- Tag format: `v<VERSION>` (e.g., `v0.1.0`, not `0.1.0`)
- Update in two places:
  - `pytest_coverage_impact/__init__.py`: `__version__ = "0.1.0"`
  - `pyproject.toml`: `version = "0.1.0"`

## Release Workflow

### Manual Steps (You Control)

1. Update CHANGELOG.md with new version
2. Update version in `__init__.py` and `pyproject.toml`
3. Commit changes
4. Create annotated tag: `git tag -a v0.1.0 -m "Release version 0.1.0"`
5. Push tag: `git push origin v0.1.0`

### Automated Steps (CI/CD)

1. ✅ Extracts version from tag
2. ✅ Verifies version matches code
3. ✅ Runs all tests
4. ✅ Builds package
5. ✅ Verifies package contents
6. ✅ Publishes to PyPI
7. ✅ Creates GitHub Release

## PyPI Setup

### Trusted Publishing (Recommended)

1. Go to https://pypi.org/manage/account/
2. Enable "Trusted Publishing" for your GitHub repository
3. No API tokens needed - workflow authenticates automatically

### Alternative: API Token

If not using trusted publishing:
1. Create API token at https://pypi.org/manage/account/token/
2. Add to GitHub Secrets as `PYPI_API_TOKEN`

## Helper Script

Use `./scripts/release.sh 0.1.0` to automate version updates and tag creation.

## Troubleshooting

**Version mismatch**: Ensure tag version (without `v`) matches `__version__` in code
**Tag exists**: Delete with `git tag -d v0.1.0 && git push origin :refs/tags/v0.1.0`
**Publish failed**: Check PyPI settings and GitHub Actions logs
