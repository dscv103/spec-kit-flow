"""
Custom exceptions for SpecKit Core.

This module defines all custom exceptions used by speckit_core functions.
"""

__all__ = [
    "SpecKitError",
    "NotInGitRepoError",
    "FeatureNotFoundError",
    "TaskParseError",
    "ConfigurationError",
]


class SpecKitError(Exception):
    """Base exception for all SpecKit errors."""
    pass


class NotInGitRepoError(SpecKitError):
    """Raised when operation requires a git repository but none is found."""
    pass


class FeatureNotFoundError(SpecKitError):
    """Raised when a feature branch or spec directory is not found."""
    pass


class TaskParseError(SpecKitError):
    """Raised when task parsing fails due to invalid syntax."""
    pass


class ConfigurationError(SpecKitError):
    """Raised when configuration is invalid or missing."""
    pass
