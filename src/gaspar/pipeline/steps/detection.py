"""
Detection step for GASPAR pipeline.
Handles anomaly detection and filter generation.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from ...core.analyzers import (
    PrivacyAnomalyDetector,
    FilterGenerator,
    AnomalyDetail
)
from ...core.processors import DataDistributionModeler, DataFeedMonitor
from ...core.types import DataSample
from ..base import PipelineStep, PipelineContext, StepResult

class DetectionStep(PipelineStep):
    """Step for detecting privacy anomalies and generating filters."""

    def __init__(self):
        """Initialize detection step."""
        super().__init__("detection")

    async def execute(self, context: PipelineContext) -> StepResult:
        """
        Execute detection step.

        Args:
            context: Pipeline execution context

        Returns:
            Step execution result
        """
        try:
            # Get required components from context
            privacy_rules = context.state.get("privacy_rules")
            data_modeler = context.state.get("data_modeler")
            initial_data = context.state.get("initial_data", [])

            if not privacy_rules:
                return StepResult(
                    success=False,
                    error_message="No privacy rules available from analysis step"
                )

            if not data_modeler:
                # Create new data modeler if not provided
                data_modeler = DataDistributionModeler(
                    privacy_rules=privacy_rules,
                    min_samples=context.config.pipeline.batch_size,
                    update_interval=3600  # 1 hour default
                )
                if initial_data:
                    await data_modeler.update_distributions(initial_data)

            # Initialize detectors
            anomaly_detector = PrivacyAnomalyDetector(
                rules=privacy_rules,
                data_modeler=data_modeler,
                sensitivity_threshold=0.95,
                use_adaptive_thresholds=True
            )

            filter_generator = FilterGenerator(
                rules=privacy_rules,
                data_modeler=data_modeler,
                min_confidence=0.8,
                batch_filters=True
            )

            # Process initial data if available
            anomalies: List[AnomalyDetail] = []
            total_processed = 0
            if initial_data:
                # Convert records to DataSample objects
                samples = [
                    DataSample(
                        timestamp=datetime.fromisoformat(record.get("timestamp", datetime.now().isoformat()))
                        if isinstance(record.get("timestamp"), str)
                        else datetime.now(),
                        source="initial_data",
                        data=record,
                        metadata={}
                    )
                    for record in initial_data
                ]

                total_processed = len(samples)

                # Detect anomalies
                analysis_result = await anomaly_detector.analyze(samples)
                if not analysis_result.success:
                    return StepResult(
                        success=False,
                        error_message=f"Anomaly detection failed: {analysis_result.error_message}"
                    )

                anomalies.extend(analysis_result.anomalies)

            # Generate filters based on detected anomalies
            filter_result = await filter_generator.generate_filters(anomalies)

            if not filter_result.success:
                return StepResult(
                    success=False,
                    error_message=f"Filter generation failed: {filter_result.error_message}"
                )

            try:
                pipeline_config = context.config.pipeline

                data_monitor = DataFeedMonitor(
                    privacy_rules=privacy_rules,
                    data_modeler=data_modeler,
                    initial_sampling_rate=pipeline_config.max_sampling_rate,
                    min_batch_size=100,
                    max_batch_size=pipeline_config.batch_size * pipeline_config.max_batch_multiplier,
                    monitoring_interval=timedelta(seconds=pipeline_config.monitoring_interval),
                    initial_anomalies=anomalies
                )

                # Update monitor's initial statistics
                data_monitor.stats.total_records = total_processed
                data_monitor.stats.sampled_records = total_processed
                data_monitor.stats.distribution_updates = getattr(data_modeler, 'update_count', 1)

            except Exception as e:
                return StepResult(
                    success=False,
                    error_message=f"Error initializing data monitor: {str(e)}"
                )


            # Store results
            storage = context.get_storage()

            # Save anomaly detections
            anomalies_path = f"anomalies_{context.run_id}.json"
            await storage.write_json(anomalies_path, {
                "timestamp": datetime.now().isoformat(),
                "anomalies": [self._serialize_anomaly(a) for a in anomalies],
                "total_records": total_processed,
                "anomaly_count": len(anomalies),
                "anomaly_types": self._get_anomaly_types(anomalies)
            })

            # Save generated filters
            filters_path = f"filters_{context.run_id}.json"
            await storage.write_json(filters_path, {
                "timestamp": datetime.now().isoformat(),
                "filters": [self._serialize_filter(f) for f in filter_result.filters],
                "coverage": filter_result.coverage
            })


            # Save generated code
            code_path = f"filter_code_{context.run_id}.py"
            code_content = "# Generated Privacy Filters\n\n"
            for filter_name, code in filter_result.generated_code.items():
                code_content += f"# {filter_name}\n{code.code}\n\n"
            await storage.write_text(code_path, code_content)

            return StepResult(
                success=True,
                outputs={
                    "anomaly_detector": anomaly_detector,
                    "filter_generator": filter_generator,
                    "data_monitor": data_monitor,
                    "anomalies": anomalies,
                    "filters": filter_result.filters,
                    "stats": {
                        "total_records": total_processed,
                        "anomaly_count": len(anomalies),
                        "filter_count": len(filter_result.filters),
                        "field_coverage": filter_result.coverage,
                        "anomaly_types": self._get_anomaly_types(anomalies)
                    }
                },
                artifacts={
                    "anomalies": anomalies_path,
                    "filters": filters_path,
                    "filter_code": code_path
                }
            )

        except Exception as e:
            return StepResult(
                success=False,
                error_message=f"Error in detection step: {str(e)}"
            )

    def _serialize_anomaly(self, anomaly: AnomalyDetail) -> Dict[str, Any]:
        """Convert AnomalyDetail object to serializable format."""
        anomaly_dict = anomaly.__dict__
        if isinstance(anomaly_dict.get("timestamp"), datetime):
            anomaly_dict["timestamp"] = anomaly_dict["timestamp"].isoformat()
        return anomaly_dict

    def _serialize_filter(self, filter_obj) -> Dict[str, Any]:
        """Convert Filter object and its nested objects to serializable format."""
        try:
            # Handle case when filter_obj is None
            if filter_obj is None:
                return {}

            # Start with a base dictionary
            result = {
                "name": str(getattr(filter_obj, 'name', '')),
                "description": str(getattr(filter_obj, 'description', '')),
                "enabled": bool(getattr(filter_obj, 'enabled', True)),
                "priority": int(getattr(filter_obj, 'priority', 0)),
                "conditions": [],
                "actions": [],
                "metadata": {}
            }

            # Handle created_at datetime
            if hasattr(filter_obj, 'created_at'):
                if isinstance(filter_obj.created_at, datetime):
                    result["created_at"] = filter_obj.created_at.isoformat()
                else:
                    result["created_at"] = str(filter_obj.created_at)
            else:
                result["created_at"] = datetime.now().isoformat()

            # Handle conditions
            if hasattr(filter_obj, 'conditions') and filter_obj.conditions:
                result["conditions"] = [
                    self._serialize_condition(c) for c in filter_obj.conditions
                ]

            # Handle actions
            if hasattr(filter_obj, 'actions') and filter_obj.actions:
                result["actions"] = [
                    self._serialize_action(a) for a in filter_obj.actions
                ]

            # Handle metadata - ensure it's JSON serializable
            if hasattr(filter_obj, 'metadata') and filter_obj.metadata:
                result["metadata"] = self._ensure_serializable(filter_obj.metadata)

            return result
        except Exception as e:
            # Fallback to simple serialization if errors occur
            return {
                "name": str(getattr(filter_obj, 'name', 'unknown')),
                "error": f"Serialization failed: {str(e)}"
            }

    def _serialize_condition(self, condition) -> Dict[str, Any]:
        """Convert FilterCondition object to serializable format."""
        try:
            if condition is None:
                return {}

            # Create a base dict with default values
            result = {
                "field": str(getattr(condition, 'field', '')),
                "operator": str(getattr(condition, 'operator', '')),
                "value": None,
                "logic": str(getattr(condition, 'logic', 'AND')),
                "confidence": float(getattr(condition, 'confidence', 1.0))
            }

            # Handle special value serialization
            if hasattr(condition, 'value'):
                result["value"] = self._ensure_serializable(condition.value)

            return result
        except Exception as e:
            return {"error": f"Condition serialization failed: {str(e)}"}

    def _serialize_action(self, action) -> Dict[str, Any]:
        """Convert FilterAction object to serializable format."""
        try:
            if action is None:
                return {}

            return {
                "action_type": str(getattr(action, 'action_type', '')),
                "destination": self._ensure_serializable(getattr(action, 'destination', None)),
                "transformation": self._ensure_serializable(getattr(action, 'transformation', None)),
                "alert_level": str(getattr(action, 'alert_level', '')) if getattr(action, 'alert_level', None) else None
            }
        except Exception as e:
            return {"error": f"Action serialization failed: {str(e)}"}

    def _ensure_serializable(self, value: Any) -> Any:
        """Ensure a value is JSON serializable."""
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, (list, tuple)):
            return [self._ensure_serializable(item) for item in value]

        if isinstance(value, set):
            return [self._ensure_serializable(item) for item in value]

        if isinstance(value, dict):
            return {
                str(k): self._ensure_serializable(v)
                for k, v in value.items()
            }

        if hasattr(value, 'dict') and callable(getattr(value, 'dict')):
            # Handle Pydantic models
            return self._ensure_serializable(value.dict())

        if hasattr(value, '__dict__'):
            # Handle custom objects
            return self._ensure_serializable(value.__dict__)

        # Default fallback - convert to string
        return str(value)

    def _get_anomaly_types(self, anomalies: List[AnomalyDetail]) -> Dict[str, int]:
        """Get count of each anomaly type."""
        type_counts = {}
        for anomaly in anomalies:
            type_counts[anomaly.violation_type] = type_counts.get(anomaly.violation_type, 0) + 1
        return type_counts