"""
Analysis step for GASPAR pipeline.
Handles IPA document analysis and rule extraction.
"""

from typing import Any, Dict
from ...core.models import ModelFactory
from ...core.processors import IPAProcessor
from ..base import PipelineStep, PipelineContext, StepResult

class AnalysisStep(PipelineStep):
    """Step for analyzing IPA documents and extracting privacy rules."""

    def __init__(self):
        """Initialize analysis step."""
        super().__init__("analysis")

    async def execute(self, context: PipelineContext) -> StepResult:
        """
        Execute analysis step.

        Args:
            context: Pipeline execution context

        Returns:
            Step execution result
        """
        try:
            # Get document path from context
            document_path = context.state.get("document_path")
            if not document_path:
                return StepResult(
                    success=False,
                    error_message="No document path provided in pipeline context"
                )

            # Initialize LLM
            model = ModelFactory.create(context.config.model)

            # Initialize IPA processor
            processor = IPAProcessor(model)

            # Read document content
            storage = context.get_storage()
            content = await storage.read_text(document_path)

            # Process IPA document
            result = await processor.process(content)

            if not result.success:
                return StepResult(
                    success=False,
                    error_message=f"IPA processing failed: {result.error_message}"
                )

            # Store rules in artifact
            rules_path = f"rules_{context.run_id}.json"
            await storage.write_json(rules_path, {
                "rules": [rule.dict() for rule in result.rules],
                "data_sources": result.data_sources,
                "monitoring_requirements": result.monitoring_requirements
            })

            # Return results
            return StepResult(
                success=True,
                outputs={
                    "privacy_rules": result.rules,
                    "data_sources": result.data_sources,
                    "monitoring_requirements": result.monitoring_requirements
                },
                artifacts={
                    "rules": rules_path
                }
            )

        except Exception as e:
            return StepResult(
                success=False,
                error_message=f"Error in analysis step: {str(e)}"
            )