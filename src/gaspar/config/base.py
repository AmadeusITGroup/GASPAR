"""
Base configuration classes for GASPAR system.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator

class ModelConfig(BaseModel):
    """Configuration for LLM models."""
    provider: str
    model_name: str
    token: str
    api_base: Optional[str] = None
    additional_params: Dict[str, Any] = dict  # Using dict as default_factory

    @field_validator('provider')
    def validate_provider(cls, v):
        valid_providers = {'openai', 'anthropic', 'mistral'}
        if v not in valid_providers:
            raise ValueError(f'Provider must be one of {valid_providers}')
        return v

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "extra": "forbid"
    }

class StorageConfig(BaseModel):
    """Configuration for storage backend."""
    type: str
    connection_string: Optional[str] = None
    container: Optional[str] = None
    local_path: Optional[str] = None

    @field_validator('type')
    def validate_type(cls, v):
        valid_types = {'local', 'azure'}
        if v not in valid_types:
            raise ValueError(f'Storage type must be one of {valid_types}')
        return v

    model_config = {
        "validate_assignment": True,
        "extra": "forbid"
    }

class PipelineConfig(BaseModel):
    """Configuration for pipeline execution."""
    batch_size: int = 100
    max_retries: int = 3
    temp_directory: str = "./temp"
    monitoring_interval: int = 1  # seconds
    min_sampling_rate: float = 0.1
    max_sampling_rate: float = 1.0
    max_batch_multiplier: int = 10  # max_batch_size = batch_size * max_batch_multiplier

class GasparConfig(BaseModel):
    """Main configuration class for GASPAR system."""
    model: ModelConfig
    storage: StorageConfig
    pipeline: PipelineConfig = PipelineConfig()  # Default pipeline config if not provided
    logging_level: str = "INFO"

    @field_validator('logging_level')
    def validate_logging_level(cls, v):
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f'Logging level must be one of {valid_levels}')
        return v.upper()