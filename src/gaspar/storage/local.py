"""
Local filesystem storage implementation for GASPAR system.
"""

import os
import json
from typing import Any, Dict, Optional, List
import aiofiles
from .base import BaseStorage


class LocalStorage(BaseStorage):
    """Local filesystem storage implementation."""

    def _initialize(self) -> None:
        """Initialize local storage directory."""
        if not self.config.local_path:
            raise ValueError("local_path is required for LocalStorage")

        os.makedirs(self.config.local_path, exist_ok=True)

    def _get_full_path(self, path: str) -> str:
        """Get full filesystem path."""
        return os.path.join(self.config.local_path, path)

    async def read_text(self, path: str) -> str:
        """Read text file from local filesystem."""
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, mode='r', encoding='utf-8') as f:
            return await f.read()

    async def write_text(self, path: str, content: str) -> None:
        """Write text file to local filesystem."""
        full_path = self._get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, mode='w', encoding='utf-8') as f:
            await f.write(content)

    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read JSON file from local filesystem."""
        content = await self.read_text(path)
        return json.loads(content)

    async def write_json(self, path: str, content: Dict[str, Any]) -> None:
        """Write JSON file to local filesystem."""
        json_str = json.dumps(content, indent=2)
        await self.write_text(path, json_str)

    async def read_binary(self, path: str) -> bytes:
        """Read binary file from local filesystem."""
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, mode='rb') as f:
            return await f.read()

    async def write_binary(self, path: str, content: bytes) -> None:
        """Write binary file to local filesystem."""
        full_path = self._get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, mode='wb') as f:
            await f.write(content)

    async def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        full_path = self._get_full_path(path)
        return os.path.exists(full_path)

    async def delete(self, path: str) -> None:
        """Delete file from local filesystem."""
        full_path = self._get_full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)

    async def list_dir(self, path: str) -> List[str]:
        """List contents of local filesystem directory."""
        full_path = self._get_full_path(path)
        if not os.path.exists(full_path):
            return []
        return os.listdir(full_path)