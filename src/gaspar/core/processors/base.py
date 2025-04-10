"""
Base processor interface for GASPAR system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ProcessorResult(BaseModel):
    """Base class for processor results."""
    success: bool
    error_message: Optional[str] = None
    data: Dict[str, Any] = dict


async def validate(result: ProcessorResult) -> bool:
    """
    Validate processing results.

    Args:
        result: Processing result to validate

    Returns:
        True if valid, False otherwise
    """
    return result.success and result.data is not None


class BaseProcessor(ABC):
    """Base class for document processors."""

    @abstractmethod
    async def process(self, content: Any) -> ProcessorResult:
        """
        Process input content.

        Args:
            content: Input content to process

        Returns:
            ProcessorResult containing processing outcome
        """
        pass

