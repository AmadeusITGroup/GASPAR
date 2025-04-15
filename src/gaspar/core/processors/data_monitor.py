"""
Data feed monitoring component for GASPAR system.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from datetime import datetime, timedelta
import numpy as np
from pydantic import BaseModel, Field

from ..analyzers import AnomalyDetail
from ..types import PrivacyRule, DataSample
from .data_modeler import DataDistributionModeler


class MonitoringStats(BaseModel):
    """Monitoring statistics."""
    total_records: int = 0
    sampled_records: int = 0
    violation_count: int = 0
    initial_violations: int = 0
    last_sample_time: Optional[datetime] = None
    current_sampling_rate: float = 0.1
    distribution_updates: int = 0
    avg_batch_processing_time: float = 0.0
    detected_anomalies: Dict[str, int] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.detected_anomalies is None:
            self.detected_anomalies = {}

    def update_anomaly_count(self, violation_type: str) -> None:
        """Update the count for a specific violation type."""
        current_count = self.detected_anomalies.get(violation_type, 0)
        self.detected_anomalies[violation_type] = current_count + 1


class DataFeedMonitor:
    """Monitor for continuous data feed analysis."""

    def __init__(
            self,
            privacy_rules: List[PrivacyRule],
            data_modeler: DataDistributionModeler,
            initial_sampling_rate: float = 0.1,
            min_batch_size: int = 100,
            max_batch_size: int = 10000,
            monitoring_interval: timedelta = timedelta(hours=1),
            initial_anomalies: Optional[List[AnomalyDetail]] = None
    ):
        """Initialize monitor."""
        self.rules = {rule.field_name: rule for rule in privacy_rules}
        self.data_modeler = data_modeler
        self.sampling_rate = initial_sampling_rate
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.monitoring_interval = monitoring_interval
        self.stats = MonitoringStats(current_sampling_rate=initial_sampling_rate)
        self._violation_buffer: List[AnomalyDetail] = []
        self._running = False
        self._processing_times: List[float] = []

        #print("monitor init done")
        #print("initial_anomalies: ", initial_anomalies)

        # Initialize with any existing anomalies
        if initial_anomalies:
            self.stats.initial_violations = len(initial_anomalies)
            self.stats.violation_count = len(initial_anomalies)
            # Track anomaly types
            for anomaly in initial_anomalies:
                self.stats.update_anomaly_count(anomaly.violation_type)
        #print("monitor init done final")
        #print("self.stats: ", self.stats)

    async def start_monitoring(
        self,
        data_source: AsyncIterator[Dict[str, Any]],
        violation_callback: Optional[Callable[[List[AnomalyDetail]], None]] = None
    ):
        """
        Start monitoring data feed.

        Args:
            data_source: Async iterator providing data
            violation_callback: Optional callback for violations
        """
        self._running = True

        while self._running:
            try:
                batch = []
                batch_start = datetime.now()

                # Collect batch of records
                async for record in data_source:
                    self.stats.total_records += 1

                    # Create sample
                    sample = DataSample(
                        timestamp=datetime.now(),
                        source=record.get("source", "unknown"),
                        data=record,
                        metadata={}
                    )

                    # Apply sampling
                    if np.random.random() < self.sampling_rate:
                        batch.append(sample)
                        self.stats.sampled_records += 1

                    if len(batch) >= self.max_batch_size:
                        break

                #if len(batch) < self.min_batch_size:
                    #continue

                # Process batch
                violations = await self._process_batch(batch)
                #print("violations in monitoring: ", violations)

                # Update statistics
                self.stats.violation_count += len(violations)
                self.stats.last_sample_time = datetime.now()

                # Handle violations
                if violations and violation_callback:
                    await violation_callback(violations)

                # Buffer violations
                self._violation_buffer.extend(violations)

                # Wait for next interval if needed
                batch_duration = (datetime.now() - batch_start).total_seconds()
                if batch_duration < self.monitoring_interval.total_seconds():
                    await asyncio.sleep(
                        self.monitoring_interval.total_seconds() - batch_duration
                    )

            except Exception as e:
                print(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(1)

    def stop_monitoring(self):
        """Stop monitoring."""
        self._running = False

    def _get_expected_pattern(self, rule: PrivacyRule) -> str:
        """Get expected pattern from rule."""
        if not rule.allowed:
            return "field_not_allowed"

        patterns = []
        if rule.constraints:
            if rule.constraints.min_value is not None:
                patterns.append(f">= {rule.constraints.min_value}")
            if rule.constraints.max_value is not None:
                patterns.append(f"<= {rule.constraints.max_value}")
            if rule.constraints.allowed_values:
                patterns.append(f"in {rule.constraints.allowed_values}")
            if rule.constraints.regex_pattern:
                patterns.append(f"matches {rule.constraints.regex_pattern}")
            if rule.constraints.custom_validation:
                patterns.append(f"validates {rule.constraints.custom_validation}")

        return " AND ".join(patterns) if patterns else "any_value"

    async def _process_batch(self, batch: List[DataSample]) -> List[AnomalyDetail]:
        """Process batch of samples."""
        violations = []

        # Update distributions
        batch_data = [sample.data for sample in batch]
        await self.data_modeler.update_distributions(batch_data)
        self.stats.distribution_updates += 1

        # Check each sample
        for sample in batch:
            sample_violations = []

            for field_name, rule in self.rules.items():
                field_value = sample.data.get(field_name)

                # Skip if field not present
                if field_value is None:
                    continue

                # Check if field is allowed
                if not rule.allowed:
                    sample_violations.append(
                        AnomalyDetail(
                            timestamp=sample.timestamp,
                            field_name=field_name,
                            actual_value=field_value,
                            expected_pattern=self._get_expected_pattern(rule),
                            violation_type="forbidden_field",
                            severity="HIGH",
                            confidence=1.0,
                            context={
                                "source": sample.source,
                                "rule": rule.dict()
                            }
                        )
                    )
                    continue

                # Check constraints
                if rule.constraints:
                    if not self._check_constraints(field_value, rule):
                        # Get distribution metrics if available
                        dist_metrics = None
                        if self.data_modeler and field_name in self.data_modeler.distributions:
                            dist = self.data_modeler.distributions[field_name]
                            if dist:
                                dist_metrics = {
                                    "mean": dist.mean,
                                    "std": dist.std,
                                    "min": dist.min_value,
                                    "max": dist.max_value
                                }

                        sample_violations.append(
                            AnomalyDetail(
                                timestamp=sample.timestamp,
                                field_name=field_name,
                                actual_value=field_value,
                                expected_pattern=self._get_expected_pattern(rule),
                                violation_type="constraint_violation",
                                severity="MEDIUM",
                                confidence=0.95,
                                context={
                                    "source": sample.source,
                                    "rule": rule.dict()
                                },
                                distribution_metrics=dist_metrics
                            )
                        )

            violations.extend(sample_violations)

        return violations

    def _check_constraints(self, value: Any, rule: PrivacyRule) -> bool:
        """Check field constraints."""
        if not rule.constraints:
            return True

        try:
            if (rule.constraints.min_value is not None and
                isinstance(value, (int, float)) and
                value < rule.constraints.min_value):
                return False

            if (rule.constraints.max_value is not None and
                isinstance(value, (int, float)) and
                value > rule.constraints.max_value):
                return False

            if (rule.constraints.allowed_values is not None and
                str(value) not in rule.constraints.allowed_values):
                return False

            if (rule.constraints.regex_pattern is not None and
                not re.match(rule.constraints.regex_pattern, str(value))):
                return False

            return True

        except Exception:
            return False