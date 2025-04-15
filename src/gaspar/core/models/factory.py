"""
Factory for creating LLM instances.
"""

from typing import Dict, Type
from .base import BaseLLM
from .openai_model import OpenAIModel
from ...config.base import ModelConfig


class ModelFactory:
    """Factory for creating LLM instances."""

    _models: Dict[str, Type[BaseLLM]] = {
        'openai': OpenAIModel,
        # Add other models as they are implemented
        # 'anthropic': AnthropicModel,
        # 'mistral': MistralModel,
    }

    @classmethod
    def create(cls, config: ModelConfig) -> BaseLLM:
        """
        Create an LLM instance based on configuration.

        Args:
            config: Model configuration

        Returns:
            Initialized LLM instance

        Raises:
            ValueError: If provider is not supported
        """
        model_class = cls._models.get(config.provider.lower())
        if not model_class:
            raise ValueError(
                f"Unsupported model provider: {config.provider}. "
                f"Supported providers: {list(cls._models.keys())}"
            )

        return model_class(config)