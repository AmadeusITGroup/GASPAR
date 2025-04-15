"""
Base analyzer interface for GASPAR system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AnalyzerResult(BaseModel):
    """Base class for analyzer results."""
    success: bool
    error_message: Optional[str] = None
    data: Dict[str, Any] = None

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
        "json_schema_extra": {
            "data": {"default_factory": dict}
        }
    }


class BaseAnalyzer(ABC):
    """Base class for analyzers."""

    @abstractmethod
    async def analyze(self, data: Any) -> AnalyzerResult:
        """
        Analyze input data.

        Args:
            data: Input data to analyze

        Returns:
            AnalyzerResult containing analysis outcome
        """
        pass

    async def validate(self, result: AnalyzerResult) -> bool:
        """
        Validate analysis results.

        Args:
            result: Analysis result to validate

        Returns:
            True if valid, False otherwise
        """
        return result.success and result.data is not None