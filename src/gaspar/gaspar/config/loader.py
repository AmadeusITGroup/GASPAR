"""
Configuration loader for GASPAR system.
"""

import os
from typing import Optional, Dict, Any
import yaml

from gaspar.config import ModelConfig, StorageConfig, PipelineConfig, GasparConfig


def load_env_file(env_path: str = '.env') -> Dict[str, str]:
    """
    Simple .env file loader
    """
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def get_env_value(key: str, default: Any = None, env_vars: Dict[str, str] = None) -> Any:
    """
    Get value from environment variables or env file
    """
    return os.environ.get(key) or (env_vars or {}).get(key) or default

def load_config(config_path: Optional[str] = None, env_path: str = '.env') -> GasparConfig:
    """
    Load configuration from environment variables and optional YAML file.

    Args:
        config_path: Optional path to YAML configuration file
        env_path: Path to .env file

    Returns:
        GasparConfig instance
    """
    # Load .env file if it exists
    env_vars = load_env_file(env_path)

    # Load YAML config if provided
    yaml_config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f) or {}

    # Create model config
    model_config = ModelConfig(
        provider=get_env_value('LLM_PROVIDER',
                             yaml_config.get('model', {}).get('provider', 'openai'),
                             env_vars),
        model_name=get_env_value('LLM_MODEL_NAME',
                               yaml_config.get('model', {}).get('model_name', 'gpt-4'),
                               env_vars),
        token=get_env_value('LLM_API_KEY',
                            yaml_config.get('model', {}).get('token', ''),
                            env_vars),
        api_base=get_env_value('LLM_API_BASE',
                             yaml_config.get('model', {}).get('api_base'),
                             env_vars),
        additional_params=yaml_config.get('model', {}).get('additional_params', {})
    )

    # Create storage config
    storage_config = StorageConfig(
        type=get_env_value('STORAGE_TYPE',
                          yaml_config.get('storage', {}).get('type', 'local'),
                          env_vars),
        connection_string=get_env_value('STORAGE_CONNECTION_STRING',
                                      yaml_config.get('storage', {}).get('connection_string'),
                                      env_vars),
        container=get_env_value('STORAGE_CONTAINER',
                              yaml_config.get('storage', {}).get('container'),
                              env_vars),
        local_path=get_env_value('LOCAL_STORAGE_PATH',
                               yaml_config.get('storage', {}).get('local_path', './data'),
                               env_vars)
    )

    # Create pipeline config
    pipeline_config = PipelineConfig(
        batch_size=int(get_env_value('BATCH_SIZE',
                                   yaml_config.get('pipeline', {}).get('batch_size', 100),
                                   env_vars)),
        max_retries=int(get_env_value('MAX_RETRIES',
                                    yaml_config.get('pipeline', {}).get('max_retries', 3),
                                    env_vars)),
        temp_directory=yaml_config.get('pipeline', {}).get('temp_directory', './temp')
    )

    # Create main config
    return GasparConfig(
        model=model_config,
        storage=storage_config,
        pipeline=pipeline_config,
        logging_level=get_env_value('LOG_LEVEL',
                                  yaml_config.get('logging_level', 'INFO'),
                                  env_vars)
    )