#!/bin/bash
# Release script for pytest-coverage-impact
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.1.0

set -e

VERSION=$1

if [ -z "$VERSION" ]; then
  echo "❌ Error: Version required"
  echo "Usage: $0 <version>"
  echo "Example: $0 0.1.0"
  exit 1
fi

# Validate version format (basic semantic versioning check)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
  echo "❌ Invalid version format: $VERSION"
  echo "Use semantic versioning (e.g., 0.1.0, 1.0.0, 0.1.0a1)"
  exit 1
fi

echo "🚀 Preparing release $VERSION..."

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
  echo "⚠️  Warning: There are uncommitted changes."
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Update version in __init__.py
echo "📝 Updating version in pytest_coverage_impact/__init__.py..."
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" pytest_coverage_impact/__init__.py

# Update version in pyproject.toml
echo "📝 Updating version in pyproject.toml..."
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

echo "✅ Updated versions in code"

# Show what changed
echo ""
echo "Changes:"
git diff pytest_coverage_impact/__init__.py pyproject.toml

echo ""
read -p "Commit these changes? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  git add pytest_coverage_impact/__init__.py pyproject.toml
  git commit -m "Bump version to $VERSION"
  echo "✅ Committed version bump"
fi

# Create tag
echo ""
echo "📝 Creating tag v$VERSION..."
read -p "Create and push tag v$VERSION? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  git tag -a "v$VERSION" -m "Release version $VERSION"
  echo "✅ Tag created: v$VERSION"
  echo ""
  echo "Next step: Push the tag to trigger GitHub Actions"
  echo "  git push origin v$VERSION"
fi
