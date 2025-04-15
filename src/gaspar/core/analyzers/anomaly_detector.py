"""
Privacy anomaly detector for GASPAR system.
Integrates with data distribution modeling for anomaly detection.
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from ..types import DataSample, PrivacyRule
from ..processors import DataDistributionModeler
import numpy as np


class AnomalyDetail(BaseModel):
    """Detailed information about detected anomaly."""
    timestamp: datetime
    field_name: str
    actual_value: Any
    expected_pattern: str
    violation_type: str
    severity: str
    confidence: float
    context: Dict[str, Any] = None
    distribution_metrics: Optional[Dict[str, Optional[float]]]

class BatchAnomalyStats(BaseModel):
    """Statistics for batch anomaly detection."""
    total_records: int = 0
    anomaly_count: int = 0
    field_stats: Dict[str, Dict[str, int]] = None
    distribution_updates: int = 0

class AnomalyResult(BaseModel):
    """Results from anomaly detection."""
    success: bool = True
    error_message: Optional[str] = None
    anomalies: List[AnomalyDetail] = None
    stats: BatchAnomalyStats = Field(default_factory=BatchAnomalyStats)

class PrivacyAnomalyDetector:
    """Detector for privacy-related anomalies in data feeds."""

    def __init__(
        self,
        rules: List[PrivacyRule],
        data_modeler: DataDistributionModeler,
        sensitivity_threshold: float = 0.95,
        use_adaptive_thresholds: bool = True
    ):
        """
        Initialize anomaly detector.

        Args:
            rules: Privacy rules from IPA
            data_modeler: Data distribution modeler
            sensitivity_threshold: Base threshold for anomaly detection
            use_adaptive_thresholds: Whether to adapt thresholds based on data
        """
        self.rules = {rule.field_name: rule for rule in rules}
        self.data_modeler = data_modeler
        self.base_threshold = sensitivity_threshold
        self.use_adaptive_thresholds = use_adaptive_thresholds
        self.field_thresholds: Dict[str, float] = {}
        self._anomaly_history: List[AnomalyDetail] = []

    async def analyze(
        self,
        samples: List[DataSample]
    ) -> AnomalyResult:
        """
        Analyze data samples for privacy anomalies.

        Args:
            samples: List of data samples to analyze

        Returns:
            Analysis results
        """
        try:
            anomalies = []
            stats = BatchAnomalyStats(total_records=len(samples))

            # Update data distributions
            batch_data = [sample.data for sample in samples]
            updated_distributions = await self.data_modeler.update_distributions(batch_data)
            stats.distribution_updates = len(updated_distributions)

            # Process each sample
            for sample in samples:
                sample_anomalies = await self._analyze_sample(sample)
                if sample_anomalies:
                    anomalies.extend(sample_anomalies)
                    stats.anomaly_count += len(sample_anomalies)

                    # Ensure field_stats is initialized
                    if stats.field_stats is None:
                        stats.field_stats = {}

                    # Update field stats
                    for anomaly in sample_anomalies:
                        if anomaly.field_name not in stats.field_stats:
                            stats.field_stats[anomaly.field_name] = {
                                "total": 0,
                                "violations": 0
                            }
                        stats.field_stats[anomaly.field_name]["total"] += 1
                        stats.field_stats[anomaly.field_name]["violations"] += 1

            # Update anomaly history
            self._anomaly_history.extend(anomalies)
            if len(self._anomaly_history) > 1000:  # Keep last 1000 anomalies
                self._anomaly_history = self._anomaly_history[-1000:]

            # Update thresholds if adaptive
            if self.use_adaptive_thresholds:
                self._update_thresholds()

            return AnomalyResult(
                success=True,
                anomalies=anomalies,
                stats=stats
            )

        except Exception as e:
            return AnomalyResult(
                success=False,
                error_message=f"Error in anomaly detection: {str(e)}"
            )

    async def _analyze_sample(
        self,
        sample: DataSample
    ) -> List[AnomalyDetail]:
        """Analyze single data sample for anomalies."""
        anomalies = []
        if not sample or not sample.data:
            return anomalies

        if not self.rules:
            return anomalies

        for field_name, rule in self.rules.items():

            value = sample.data.get(field_name)

            if value is None:
                continue

            # Check basic rule violations
            if not rule.allowed:
                anomalies.append(self._create_anomaly_detail(
                    sample, field_name, "forbidden_field"
                ))
                continue

            # Get distribution-based anomaly score
            anomaly_score = self.data_modeler.calculate_anomaly_score(
                field_name, value
            )

            if anomaly_score is not None:
                threshold = self.field_thresholds.get(
                    field_name, self.base_threshold
                )

                if anomaly_score > threshold:
                    distribution = self.data_modeler.distributions.get(field_name)
                    anomalies.append(self._create_anomaly_detail(
                        sample,
                        field_name,
                        "distribution_anomaly",
                        confidence=anomaly_score,
                        distribution_metrics={
                            "score": anomaly_score,
                            "threshold": threshold,
                            "mean": distribution.mean if distribution else None,
                            "std": distribution.std if distribution else None
                        }
                    ))

            # Check rule constraints
            if rule.constraints and not self._check_constraints(value, rule):
                anomalies.append(self._create_anomaly_detail(
                    sample, field_name, "constraint_violation"
                ))

        return anomalies

    def _create_anomaly_detail(
        self,
        sample: DataSample,
        field_name: str,
        violation_type: str,
        confidence: float = 1.0,
        distribution_metrics: Optional[Dict[str, float]] = None
    ) -> AnomalyDetail:
        """Create anomaly detail record."""
        severity = self._calculate_severity(confidence)

        return AnomalyDetail(
            timestamp=sample.timestamp,
            field_name=field_name,
            actual_value=sample.data[field_name],
            expected_pattern=self._get_expected_pattern(self.rules[field_name]),
            violation_type=violation_type,
            severity=severity,
            confidence=confidence,
            context={
                "source": sample.source,
                "metadata": sample.metadata
            },
            distribution_metrics=distribution_metrics
        )

    def _update_thresholds(self):
        """Update field-specific thresholds based on anomaly history."""
        if not self._anomaly_history:
            return

        for field_name in self.rules:
            field_anomalies = [
                a for a in self._anomaly_history
                if a.field_name == field_name
            ]

            if field_anomalies:
                # Calculate threshold based on historical anomaly scores
                scores = [
                    a.confidence for a in field_anomalies
                    if a.violation_type == "distribution_anomaly"
                ]
                if scores:
                    # Use percentile as threshold
                    self.field_thresholds[field_name] = max(
                        self.base_threshold,
                        np.percentile(scores, 95)
                    )

    def _calculate_severity(self, confidence: float) -> str:
        """Calculate severity based on confidence score."""
        if confidence > 0.9:
            return "HIGH"
        elif confidence > 0.7:
            return "MEDIUM"
        return "LOW"

    def _get_expected_pattern(self, rule: PrivacyRule) -> str:
        """Get expected pattern from rule and distribution."""
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

        # Add distribution information if available
        distribution = self.data_modeler.distributions.get(rule.field_name)
        if distribution and distribution.mean is not None:
            patterns.append(
                f"typical range: {distribution.mean:.2f} ± {distribution.std:.2f}"
            )

        return " AND ".join(patterns) if patterns else "any_value"

    def _check_constraints(self, value: Any, rule: PrivacyRule) -> bool:
        """Check value against rule constraints."""
        if not rule.constraints:
            return True

        try:
            # Numeric constraints
            if isinstance(value, (int, float)):
                if (rule.constraints.min_value is not None and
                    value < rule.constraints.min_value):
                    return False
                if (rule.constraints.max_value is not None and
                    value > rule.constraints.max_value):
                    return False

            # Allowed values constraint
            if (rule.constraints.allowed_values is not None and
                str(value) not in rule.constraints.allowed_values):
                return False

            # Regex pattern constraint
            if (rule.constraints.regex_pattern is not None and
                not re.match(rule.constraints.regex_pattern, str(value))):
                return False

            return True

        except Exception:
            return False