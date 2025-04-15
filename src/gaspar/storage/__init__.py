"""
Storage package for GASPAR system.
"""

from typing import Type
from .base import BaseStorage
from .local import LocalStorage
from .azure import AzureStorage
from ..config.base import StorageConfig


class StorageFactory:
    """Factory for creating storage instances."""

    _storages = {
        'local': LocalStorage,
        'azure': AzureStorage
    }

    @classmethod
    def create(cls, config: StorageConfig) -> BaseStorage:
        """
        Create storage instance based on configuration.

        Args:
            config: Storage configuration

        Returns:
            Initialized storage instance

        Raises:
            ValueError: If storage type is not supported
        """
        storage_class = cls._storages.get(config.type.lower())
        if not storage_class:
            raise ValueError(
                f"Unsupported storage type: {config.type}. "
                f"Supported types: {list(cls._storages.keys())}"
            )

        return storage_class(config)


__all__ = [
    'BaseStorage',
    'LocalStorage',
    'AzureStorage',
    'StorageFactory'
]