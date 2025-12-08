#!/bin/bash
# Test the build process locally (simulates what GitHub Actions does)
# Usage: ./scripts/test_build.sh

set -e

echo "🧪 Testing build process locally..."
echo ""

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
  echo "❌ Error: Must be run from project root"
  exit 1
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/
echo "✅ Cleaned"

# Install build dependencies
echo ""
echo "📦 Installing build dependencies..."
python -m pip install --upgrade pip
pip install build twine
echo "✅ Dependencies installed"

# Run tests first
echo ""
echo "🧪 Running tests..."
pip install -e ".[dev]"
pytest tests/unit -v --tb=short
echo "✅ Tests passed"

# Build package
echo ""
echo "🔨 Building package..."
python -m build
echo "✅ Build completed"

# List files
echo ""
echo "📦 Files in dist/:"
ls -lah dist/

# Verify package contents
echo ""
echo "🔍 Verifying package contents..."

SRC_DIST=$(ls dist/*.tar.gz 2>/dev/null | head -1)

if [ -z "$SRC_DIST" ]; then
  echo "❌ No source distribution found in dist/"
  ls -lah dist/ || echo "dist/ directory does not exist"
  exit 1
fi

echo "Found package: $SRC_DIST"
echo ""
echo "Key files in package:"
tar -tzf "$SRC_DIST" | grep -E "(LICENSE|\.pkl|README|MANIFEST)" | head -10

# Verify ML model is included
echo ""
if tar -tzf "$SRC_DIST" | grep -q "\.pkl"; then
  echo "✅ ML model file found in package"
else
  echo "❌ ML model file NOT found in package"
  echo ""
  echo "All files in package:"
  tar -tzf "$SRC_DIST" | head -30
  exit 1
fi

# Verify LICENSE is included
if tar -tzf "$SRC_DIST" | grep -q "LICENSE"; then
  echo "✅ LICENSE file found in package"
else
  echo "❌ LICENSE file NOT found in package"
  exit 1
fi

# Verify README is included
if tar -tzf "$SRC_DIST" | grep -q "README.md"; then
  echo "✅ README.md file found in package"
else
  echo "❌ README.md file NOT found in package"
  exit 1
fi

echo ""
echo "✅ All verifications passed!"
echo ""
echo "📦 Package is ready: $SRC_DIST"
echo ""
echo "To check package contents:"
echo "  tar -tzf $SRC_DIST | less"
echo ""
echo "To test installation:"
echo "  pip install $SRC_DIST"
