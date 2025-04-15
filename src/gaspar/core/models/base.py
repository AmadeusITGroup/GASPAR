"""
Base LLM model interface for GASPAR system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from ...config.base import ModelConfig


class BaseLLM(ABC):
    """Base class for LLM implementations."""

    def __init__(self, config: ModelConfig):
        """
        Initialize LLM with configuration.

        Args:
            config: Model configuration
        """
        self.config = config
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize model-specific components."""
        pass

    @abstractmethod
    async def analyze_privacy_document(self, content: str) -> Dict[str, Any]:
        """
        Analyze privacy document to extract fields and identify sensitive information.

        Args:
            content: Document content to analyze

        Returns:
            Dictionary containing extracted fields and analysis
        """
        pass

    @abstractmethod
    async def identify_anomalies(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze fields for potential privacy anomalies.

        Args:
            fields: List of extracted fields to analyze

        Returns:
            List of identified anomalies
        """
        pass

    @abstractmethod
    async def generate_filter(self, anomalies: List[Dict[str, Any]]) -> str:
        """
        Generate filter code based on identified anomalies.

        Args:
            anomalies: List of anomalies to filter

        Returns:
            Generated filter code as string
        """
        pass