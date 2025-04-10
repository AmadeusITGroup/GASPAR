"""
Modeling step for GASPAR pipeline.
Sets up data monitoring and sampling based on IPA fields.
"""

from datetime import timedelta
from ...core.processors import (
    DataFeedMonitor,
    DataDistributionModeler
)
from ..base import PipelineStep, PipelineContext, StepResult


def _parse_interval(interval_str: str) -> int:
    """Parse interval string to seconds."""
    unit = interval_str[-1].lower()
    value = int(interval_str[:-1])

    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        return 3600  # Default to 1 hour


class ModelingStep(PipelineStep):
    """Step for modeling data distributions and setting up sampling."""

    def __init__(self):
        """Initialize modeling step."""
        super().__init__("modeling")

    async def execute(self, context: PipelineContext) -> StepResult:
        """
        Execute modeling step.

        Args:
            context: Pipeline execution context

        Returns:
            Step execution result
        """
        try:
            # Get privacy rules and monitoring requirements
            privacy_rules = context.state.get("privacy_rules")
            if not privacy_rules:
                return StepResult(
                    success=False,
                    error_message="No privacy rules available from analysis step"
                )

            monitoring_reqs = context.state.get("monitoring_requirements", {})

            # Initialize data modeler for distribution analysis
            data_modeler = DataDistributionModeler(
                privacy_rules=privacy_rules,
                min_samples=monitoring_reqs.get("min_samples", 100),
                update_interval=monitoring_reqs.get("update_interval", 3600)
            )

            # Initialize data monitor with adaptive sampling
            data_monitor = DataFeedMonitor(
                privacy_rules=privacy_rules,
                data_modeler=data_modeler,
                initial_sampling_rate=monitoring_reqs.get("sampling_rate", 0.1),
                min_batch_size=monitoring_reqs.get("batch_size", 100),
                monitoring_interval=timedelta(
                    seconds=_parse_interval(
                        monitoring_reqs.get("monitoring_interval", "1h")
                    )
                )
            )

            # Store monitor configuration
            storage = context.get_storage()
            config_path = f"monitor_config_{context.run_id}.json"
            await storage.write_json(config_path, {
                "sampling_settings": {
                    "initial_rate": data_monitor.sampling_rate,
                    "min_batch_size": data_monitor.min_batch_size,
                    "max_batch_size": data_monitor.max_batch_size,
                    "update_interval": data_modeler.update_interval
                },
                "monitoring_interval": str(data_monitor.monitoring_interval),
                "alert_thresholds": monitoring_reqs.get("alert_thresholds", {})
            })

            return StepResult(
                success=True,
                outputs={
                    "data_monitor": data_monitor,
                    "data_modeler": data_modeler,
                    "monitoring_config": {
                        "sampling_rate": data_monitor.sampling_rate,
                        "batch_size": data_monitor.min_batch_size,
                        "monitoring_interval": str(data_monitor.monitoring_interval)
                    }
                },
                artifacts={
                    "monitor_config": config_path
                }
            )

        except Exception as e:
            return StepResult(
                success=False,
                error_message=f"Error in modeling step: {str(e)}"
            )

