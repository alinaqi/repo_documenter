"""
Repository Documentation Generator

A Python tool that automatically clones GitHub repositories from an organization
and generates comprehensive documentation using Anthropic's Claude AI.
"""

__version__ = "1.0.0"

from .core.documenter import RepoDocumenter
from .main import main

__all__ = ["RepoDocumenter", "main"] 