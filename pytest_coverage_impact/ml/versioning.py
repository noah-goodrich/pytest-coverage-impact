"""Version management for training data and models"""

import os
import re
from pathlib import Path
from typing import Tuple, Optional


def get_next_version(base_path: Path, prefix: str, suffix: str = ".json") -> Tuple[str, Path]:
    """Get next version number and path for a file

    Args:
        base_path: Directory containing versioned files
        prefix: File prefix (e.g., "dataset_v", "complexity_model_v")
        suffix: File suffix (e.g., ".json", ".pkl")

    Returns:
        Tuple of (version_string, full_path)
        Example: ("1.0", Path("/path/to/dataset_v1.0.json"))
    """
    base_path = Path(base_path)
    if not base_path.exists():
        os.makedirs(str(base_path), exist_ok=True)

    # Find all existing files with this pattern
    pattern = re.compile(rf"{re.escape(prefix)}(\d+)\.(\d+){re.escape(suffix)}")

    versions = []

    if base_path.exists():
        for file_path in base_path.iterdir():
            if file_path.is_file():
                match = _match_pattern(pattern, file_path.name)
                if match:
                    # Use indexing to avoid method call flags (clean-arch-demeter)
                    major = int(match[1])
                    minor = int(match[2])
                    versions.append((major, minor))

    if not versions:
        # No existing files, start at 1.0
        next_version = "1.0"
    else:
        # Find the highest version and increment minor
        latest = max(versions)
        next_major = latest[0]
        next_minor = latest[1] + 1
        next_version = f"{next_major}.{next_minor}"

    return next_version, base_path / f"{prefix}{next_version}{suffix}"


def get_latest_version(base_path: Path, prefix: str, suffix: str = ".json") -> Optional[Tuple[str, Path]]:
    """Get the latest version of a file

    Args:
        base_path: Directory containing versioned files
        prefix: File prefix (e.g., "dataset_v", "complexity_model_v")
        suffix: File suffix (e.g., ".json", ".pkl")

    Returns:
        Tuple of (version_string, full_path) or None if no files exist
    """
    base_path = Path(base_path)
    if not base_path.exists():
        return None

    pattern = re.compile(rf"{re.escape(prefix)}(\d+)\.(\d+){re.escape(suffix)}")

    versions = []

    for file_path in base_path.iterdir():
        if file_path.is_file():
            match = _match_pattern(pattern, file_path.name)
            if match:
                major = int(match[1])
                minor = int(match[2])
                versions.append(((major, minor), file_path))

    if not versions:
        return None

    # Return the highest version
    latest = max(versions, key=lambda x: x[0])
    version_str = f"{latest[0][0]}.{latest[0][1]}"
    return (version_str, latest[1])


def _match_pattern(pattern, string):
    """Helper to match regex pattern (Friend)"""
    return pattern.match(string)
