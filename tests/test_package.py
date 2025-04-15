#!/usr/bin/env python3
"""
Simple test to verify that the GASPAR package is correctly installed and importable.
"""

import unittest
import asyncio


class TestGaspar(unittest.TestCase):
    """Basic tests for GASPAR."""

    def test_import(self):
        """Test that the package can be imported."""
        from gaspar.config import GasparConfig, ModelConfig, StorageConfig, PipelineConfig

        # Create a test configuration
        config = GasparConfig(
            model=ModelConfig(
                provider="openai",
                model_name="gpt-4",
                token="test-key"
            ),
            storage=StorageConfig(
                type="local",
                local_path="./data"
            ),
            pipeline=PipelineConfig(
                batch_size=10,
                max_retries=2,
                temp_directory="./temp"
            ),
            logging_level="DEBUG"
        )

        # Verify configuration was created correctly
        self.assertEqual(config.model.provider, "openai")
        self.assertEqual(config.storage.type, "local")
        self.assertEqual(config.pipeline.batch_size, 10)


if __name__ == "__main__":
    unittest.main()