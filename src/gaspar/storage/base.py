"""
Base storage interface for GASPAR system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, BinaryIO, List
from ..config.base import StorageConfig


class BaseStorage(ABC):
    """Base class for storage implementations."""

    def __init__(self, config: StorageConfig):
        """
        Initialize storage.

        Args:
            config: Storage configuration
        """
        self.config = config
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize storage connection."""
        pass

    @abstractmethod
    async def read_text(self, path: str) -> str:
        """
        Read text content from storage.

        Args:
            path: Path to content

        Returns:
            Text content
        """
        pass

    @abstractmethod
    async def write_text(self, path: str, content: str) -> None:
        """
        Write text content to storage.

        Args:
            path: Path to write to
            content: Content to write
        """
        pass

    @abstractmethod
    async def read_json(self, path: str) -> Dict[str, Any]:
        """
        Read JSON content from storage.

        Args:
            path: Path to content

        Returns:
            Parsed JSON content
        """
        pass

    @abstractmethod
    async def write_json(self, path: str, content: Dict[str, Any]) -> None:
        """
        Write JSON content to storage.

        Args:
            path: Path to write to
            content: Content to write
        """
        pass

    @abstractmethod
    async def read_binary(self, path: str) -> bytes:
        """
        Read binary content from storage.

        Args:
            path: Path to content

        Returns:
            Binary content
        """
        pass

    @abstractmethod
    async def write_binary(self, path: str, content: bytes) -> None:
        """
        Write binary content to storage.

        Args:
            path: Path to write to
            content: Content to write
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if path exists in storage.

        Args:
            path: Path to check

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """
        Delete content from storage.

        Args:
            path: Path to delete
        """
        pass

    @abstractmethod
    async def list_dir(self, path: str) -> List[str]:
        """
        List contents of directory.

        Args:
            path: Directory path

        Returns:
            List of contents
        """
        pass