"""
Azure Blob Storage implementation for GASPAR system.
"""

import json
from typing import Any, Dict, Optional, cast, List
import azure.storage.blob.aio as azure_blob
from azure.core.exceptions import ResourceNotFoundError
from .base import BaseStorage

class AzureStorage(BaseStorage):
    """Azure Blob Storage implementation."""

    def _initialize(self) -> None:
        """Initialize Azure Blob Storage connection."""
        if not self.config.connection_string:
            raise ValueError("connection_string is required for AzureStorage")
        if not self.config.container:
            raise ValueError("container is required for AzureStorage")

        self.service_client = cast(
            azure_blob.BlobServiceClient,
            azure_blob.BlobServiceClient.from_connection_string(self.config.connection_string)
        )
        self.container_client = cast(
            azure_blob.ContainerClient,
            self.service_client.get_container_client(self.config.container)
        )

    async def read_text(self, path: str) -> str:
        """Read text blob from Azure Storage."""
        blob_client = self.container_client.get_blob_client(path)
        try:
            download_stream = await blob_client.download_blob()
            return await download_stream.content_as_text()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {path}")

    async def write_text(self, path: str, content: str) -> None:
        """Write text blob to Azure Storage."""
        blob_client = self.container_client.get_blob_client(path)
        await blob_client.upload_blob(content, overwrite=True)

    async def read_json(self, path: str) -> Dict[str, Any]:
        """Read JSON blob from Azure Storage."""
        content = await self.read_text(path)
        return json.loads(content)

    async def write_json(self, path: str, content: Dict[str, Any]) -> None:
        """Write JSON blob to Azure Storage."""
        json_str = json.dumps(content, indent=2)
        await self.write_text(path, json_str)

    async def read_binary(self, path: str) -> bytes:
        """Read binary blob from Azure Storage."""
        blob_client = self.container_client.get_blob_client(path)
        try:
            download_stream = await blob_client.download_blob()
            return await download_stream.content_as_bytes()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {path}")

    async def write_binary(self, path: str, content: bytes) -> None:
        """Write binary blob to Azure Storage."""
        blob_client = self.container_client.get_blob_client(path)
        await blob_client.upload_blob(content, overwrite=True)

    async def exists(self, path: str) -> bool:
        """Check if blob exists in Azure Storage."""
        blob_client = self.container_client.get_blob_client(path)
        return await blob_client.exists()

    async def delete(self, path: str) -> None:
        """Delete blob from Azure Storage."""
        blob_client = self.container_client.get_blob_client(path)
        try:
            await blob_client.delete_blob()
        except ResourceNotFoundError:
            pass

    async def list_dir(self, path: str) -> List[str]:
        """List blobs in Azure Storage directory."""
        path = path.rstrip('/')
        if path:
            path = path + '/'

        # List blobs with prefix
        blobs = []
        async for blob in self.container_client.list_blobs(name_starts_with=path):
            name = blob.name
            if name.startswith(path):
                name = name[len(path):]
            blobs.append(name)
        return blobs

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.service_client.close()
        await self.container_client.close()