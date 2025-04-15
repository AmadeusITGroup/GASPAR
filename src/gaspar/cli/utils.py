"""
Utility functions for GASPAR CLI.
"""

import os
import sys
from typing import Optional, TextIO
import yaml


def validate_file_path(path: str, must_exist: bool = True) -> str:
    """
    Validate file path.

    Args:
        path: File path to validate
        must_exist: Whether file must exist

    Returns:
        Validated file path

    Raises:
        ValueError: If path is invalid
    """
    if must_exist and not os.path.exists(path):
        raise ValueError(f"File not found: {path}")

    if must_exist and not os.path.isfile(path):
        raise ValueError(f"Not a file: {path}")

    return os.path.abspath(path)


def load_yaml_config(path: str) -> dict:
    """
    Load YAML configuration file.

    Args:
        path: Path to YAML file

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If file is invalid
    """
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Error loading configuration file: {str(e)}")


def get_output_stream(path: Optional[str] = None) -> TextIO:
    """
    Get output stream for results.

    Args:
        path: Optional path to output file

    Returns:
        Output stream (file or stdout)
    """
    if path:
        try:
            return open(path, 'w')
        except Exception as e:
            raise ValueError(f"Error opening output file: {str(e)}")
    return sys.stdout