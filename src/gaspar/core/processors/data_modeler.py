"""
Data distribution modeling component for GASPAR system.
"""
import math
from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np
from pydantic import BaseModel, Field
from sklearn.preprocessing import StandardScaler
from .ipa_processor import PrivacyRule


class FieldDistribution(BaseModel):
    """Statistical distribution of a field."""
    mean: Optional[float] = None
    std: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    quantiles: Dict[str, float] = None
    sample_size: int = 0
    last_update: datetime = Field(default_factory=datetime.now)
    categorical_counts: Optional[Dict[str, int]] = None


class DataDistributionModeler:
    """Models data distributions for privacy-related fields."""

    def __init__(
            self,
            privacy_rules: List[PrivacyRule],
            min_samples: int = 100,
            update_interval: int = 3600  # 1 hour
    ):
        """
        Initialize data modeler.

        Args:
            privacy_rules: List of privacy rules from IPA
            min_samples: Minimum samples before modeling
            update_interval: Seconds between distribution updates
        """
        self.rules = {rule.field_name: rule for rule in privacy_rules}
        self.min_samples = min_samples
        self.update_interval = update_interval
        self.distributions: Dict[str, FieldDistribution] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self._sample_buffers: Dict[str, List[Any]] = {
            field: [] for field in self.rules
        }

    async def update_distributions(
            self,
            data_batch: List[Dict[str, Any]]
    ) -> Dict[str, FieldDistribution]:
        """
        Update field distributions with new data.

        Args:
            data_batch: Batch of data records

        Returns:
            Updated distributions
        """
        # Buffer samples for each field
        for record in data_batch:
            for field, value in record.items():
                if field in self.rules:
                    self._sample_buffers[field].append(value)

        # Process fields with enough samples
        updated_distributions = {}
        for field, samples in self._sample_buffers.items():
            if len(samples) >= self.min_samples:
                distribution = self._model_distribution(field, samples)
                self.distributions[field] = distribution
                updated_distributions[field] = distribution
                # Clear buffer after processing
                self._sample_buffers[field] = []

            # Check if existing distribution needs update
            elif (field in self.distributions and
                  (datetime.now() - self.distributions[field].last_update).total_seconds()
                  > self.update_interval):
                distribution = self._model_distribution(field, samples)
                self.distributions[field] = distribution
                updated_distributions[field] = distribution
                self._sample_buffers[field] = []

        return updated_distributions

    def get_sampling_weights(
            self,
            data_batch: List[Dict[str, Any]]
    ) -> List[float]:
        """
        Calculate sampling weights for records.

        Args:
            data_batch: Batch of data records

        Returns:
            List of sampling weights
        """
        if not self.distributions:
            return [1.0] * len(data_batch)

        weights = []
        for record in data_batch:
            record_weight = 1.0
            anomaly_scores = []

            for field, value in record.items():
                if field in self.distributions:
                    score = self.calculate_anomaly_score(field, value)
                    if score is not None:
                        anomaly_scores.append(score)

            if anomaly_scores:
                # Higher weights for potentially anomalous records
                record_weight = max(anomaly_scores)

            weights.append(record_weight)

        # Normalize weights
        if weights:
            weights = np.array(weights)
            weights = weights / weights.sum()

        return weights.tolist()

    def _model_distribution(
            self,
            field: str,
            samples: List[Any]
    ) -> FieldDistribution:
        """Model distribution for a field."""
        rule = self.rules[field]
        if rule.allowed and not rule.pii:
            if rule.data_type in ["integer", "float"]:
                # Numeric field
                numeric_samples = [
                    float(s) for s in samples
                    if s is not None and str(s).strip()
                ]

                if not numeric_samples:
                    return FieldDistribution(
                        sample_size=len(samples),
                        last_update=datetime.now()
                    )

                # Update scaler
                if field not in self.scalers:
                    self.scalers[field] = StandardScaler()

                # Fit scaler with new data
                X = np.array(numeric_samples).reshape(-1, 1)
                self.scalers[field].partial_fit(X)

                return FieldDistribution(
                    mean=float(np.mean(numeric_samples)),
                    std=float(np.std(numeric_samples)),
                    min_value=float(np.min(numeric_samples)),
                    max_value=float(np.max(numeric_samples)),
                    quantiles={
                        "25": float(np.percentile(numeric_samples, 25)),
                        "50": float(np.percentile(numeric_samples, 50)),
                        "75": float(np.percentile(numeric_samples, 75))
                    },
                    sample_size=len(samples),
                    last_update=datetime.now()
                )
            else:
                # Categorical field
                value_counts = {}
                for value in samples:
                    if value is not None:
                        str_value = str(value).strip()
                        value_counts[str_value] = value_counts.get(str_value, 0) + 1
                #print("value_counts in data modeler: ", value_counts)
                return FieldDistribution(
                    sample_size=len(samples),
                    last_update=datetime.now(),
                    categorical_counts=value_counts
                )

    def calculate_anomaly_score(
            self,
            field: str,
            value: Any
    ) -> Optional[float]:
        """
        Calculate anomaly score for a value.

        For numerical fields, uses z-scores.
        For categorical fields, uses a combination of:
        - Frequency deviation
        - Probability deviation from expected distribution
        """
        if field not in self.distributions:
            return None

        distribution = self.distributions[field]
        rule = self.rules[field]

        # Handle numerical fields
        if rule.data_type in ["integer", "float"]:
            try:
                numeric_value = float(value)
                if field in self.scalers:
                    # Use scaled distance from mean
                    scaled_value = self.scalers[field].transform(
                        [[numeric_value]]
                    )[0][0]
                    return abs(scaled_value)
                else:
                    # Fallback to basic z-score if no scaler
                    if distribution.std:
                        return abs(
                            (numeric_value - distribution.mean) / distribution.std
                        )
            except (ValueError, TypeError):
                return None

        # Handle categorical fields
        elif distribution and distribution.categorical_counts:
            str_value = str(value).strip()
            total_samples = distribution.sample_size

            # If value has never been seen before, it's potentially anomalous
            if str_value not in distribution.categorical_counts:
                return 1.0

            # Get count of this value
            count = distribution.categorical_counts.get(str_value, 0)
            if count == 0:
                return 1.0

            # Calculate multiple anomaly indicators
            scores = []

            # 1. Frequency-based score - how rare is this value?
            frequency = count / total_samples
            frequency_score = 1.0 - frequency
            scores.append(frequency_score)

            # 2. Probability deviation score - how much does this deviate from expected probability?
            # Calculate entropy of distribution
            probs = [c / total_samples for c in distribution.categorical_counts.values()]
            entropy = -sum(p * math.log2(p) if p > 0 else 0 for p in probs)

            # Uniform distribution would have maximum entropy
            max_entropy = math.log2(len(distribution.categorical_counts))
            if max_entropy > 0:
                # Calculate how much this value deviates from uniform distribution
                expected_prob = 1.0 / len(distribution.categorical_counts)
                actual_prob = frequency
                prob_deviation = abs(actual_prob - expected_prob) / expected_prob
                # Normalize based on overall entropy 
                entropy_ratio = entropy / max_entropy if max_entropy > 0 else 1.0
                deviation_score = prob_deviation * (1.0 - entropy_ratio)
                scores.append(deviation_score)

            # Combine scores - using maximum as it represents the most anomalous dimension
            if scores:
                return min(1.0, max(scores))

            # Fallback to inverse frequency if no other scores available
            return min(1.0, 1.0 / (frequency * 10)) if frequency > 0 else 1.0

        return None