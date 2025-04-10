"""
Command Line Interface for GASPAR system.
"""

import asyncio
import logging
import argparse
from typing import Optional
from ..config import load_config
from ..pipeline.executor import PipelineExecutor


async def run_pipeline(
        document_path: str,
        config_path: Optional[str] = None,
        verbose: bool = False
) -> None:
    """
    Run the GASPAR pipeline.

    Args:
        document_path: Path to document to analyze
        config_path: Optional path to configuration file
        verbose: Enable verbose logging
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('gaspar')

    try:
        # Load configuration
        logger.debug("Loading configuration...")
        config = load_config(config_path)

        # Initialize pipeline
        logger.debug("Initializing pipeline...")
        executor = PipelineExecutor(config)

        # Execute pipeline
        logger.info(f"Processing document: {document_path}")
        result = await executor.execute(document_path)

        if result and result.success:
            logger.info("Pipeline execution completed successfully")
            logger.debug(f"Generated artifacts: {result.artifacts}")
        else:
            logger.error("Pipeline execution failed")
            if result:
                logger.error(f"Error: {result.error_message}")

    except Exception as e:
        logger.exception("Pipeline execution failed with error")
        raise


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GASPAR - GenAI-powered System for Privacy incident Analysis and Recovery"
    )

    parser.add_argument(
        "document",
        help="Path to the document to analyze"
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default=None
    )

    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose logging",
        action="store_true"
    )

    args = parser.parse_args()

    try:
        asyncio.run(run_pipeline(
            document_path=args.document,
            config_path=args.config,
            verbose=args.verbose
        ))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()