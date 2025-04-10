"""
Pipeline executor for GASPAR system.
"""

import uuid
import asyncio
from typing import List, Optional, Dict, Any, AsyncIterator

import numpy as np

from .base import PipelineStep, PipelineContext
from .steps.analysis import AnalysisStep
from .steps.modeling import ModelingStep
from .steps.detection import DetectionStep
from .steps.deployment import DeploymentStep
from ..config.base import GasparConfig
from ..core.processors import DataFeedMonitor

class PipelineExecutor:
    """Executor for GASPAR pipeline."""

    def __init__(self, config: GasparConfig):
        """Initialize executor."""
        self.config = config
        self.steps: List[PipelineStep] = [
            AnalysisStep(),
            ModelingStep(),
            DetectionStep(),
            DeploymentStep()
        ]
        self._monitor: Optional[DataFeedMonitor] = None
        self._monitor_task: Optional[asyncio.Task] = None

    async def execute(
        self,
        document_path: str,
        initial_data: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[PipelineContext]:
        """Execute pipeline."""
        try:
            # Initialize context
            context = PipelineContext(
                run_id=str(uuid.uuid4()),
                config=self.config,
                state={
                    "document_path": document_path,
                    "initial_data": initial_data or []
                },
                artifacts={}
            )

            # Execute steps
            for step in self.steps:
                print(f"Executing step: {step.name}")
                result = await step.execute(context)

                if not result or not result.success:
                    print(f"Pipeline failed at step {step.name}: {result.error_message if result else 'No result'}")
                    return None

                # Update context
                context.state.update(result.outputs or {})
                context.artifacts.update(result.artifacts or {})

                # Initialize monitoring after modeling step
                if step.name == "modeling":
                    self._monitor = result.outputs.get("data_monitor")
                    if self._monitor and initial_data:
                        batch = []
                        for record in initial_data:
                            # Apply sampling
                            if np.random.random() < self._monitor.sampling_rate:
                                batch.append(record)
                        await self._monitor.data_modeler.update_distributions(batch)

            return context

        except Exception as e:
            print(f"Pipeline execution failed: {str(e)}")
            return None

    async def monitor_data_source(
        self,
        data_source: AsyncIterator[Dict[str, Any]],
        violation_callback: Optional[callable] = None
    ) -> None:
        """Monitor data source."""
        if not self._monitor:
            print("Data monitor not initialized. Run pipeline first.")
            return

        await self._monitor.start_monitoring(
            data_source=data_source,
            violation_callback=violation_callback
        )

    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        if self._monitor:
            self._monitor.stop_monitoring()
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None

    async def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        if not self._monitor:
            return {}

        # Get field distributions from data modeler
        field_distributions = {}
        if self._monitor.data_modeler:
            field_distributions = {
                field: dist.dict()
                for field, dist in self._monitor.data_modeler.distributions.items()
            }

        return {
            "total_records": self._monitor.stats.total_records,
            "sampled_records": self._monitor.stats.sampled_records,
            "violation_count": self._monitor.stats.violation_count,
            "initial_violations": self._monitor.stats.initial_violations,
            "current_sampling_rate": self._monitor.stats.current_sampling_rate,
            "distribution_updates": self._monitor.stats.distribution_updates,
            "anomaly_types": self._monitor.stats.detected_anomalies,
            "field_distributions": field_distributions,
            "last_update": self._monitor.stats.last_sample_time.isoformat()
            if self._monitor.stats.last_sample_time else None
        }