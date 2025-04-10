"""
Feature processor for modeling data distributions in GASPAR system.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from pydantic import BaseModel
from .base import BaseProcessor, ProcessorResult


class FeatureStats(BaseModel):
    """Statistical features of a field."""
    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    q1: float = 0.0
    q2: float = 0.0
    q3: float = 0.0
    unique_count: int = 0
    null_count: int = 0


class FeatureResult(ProcessorResult):
    """Feature processing results."""
    features: Dict[str, FeatureStats] = dict
    correlations: Dict[str, Dict[str, float]] = dict
    anomaly_scores: Dict[str, List[float]] = dict


class FeatureProcessor(BaseProcessor):
    """Processor for extracting and modeling features."""

    def __init__(self, sample_size: Optional[int] = None):
        """
        Initialize feature processor.

        Args:
            sample_size: Optional size for data sampling
        """
        self.sample_size = sample_size
        self.scaler = StandardScaler()

    async def process(self, data: pd.DataFrame) -> FeatureResult:
        """
        Process data to extract features and model distributions.

        Args:
            data: DataFrame containing the data to process

        Returns:
            FeatureResult containing statistical analysis
        """
        try:
            # Sample data if needed
            if self.sample_size and len(data) > self.sample_size:
                data = data.sample(n=self.sample_size, random_state=42)

            # Calculate features for each numeric column
            features = {}
            numeric_cols = data.select_dtypes(include=[np.number]).columns

            for col in numeric_cols:
                col_data = data[col].dropna()
                if len(col_data) > 0:
                    features[col] = FeatureStats(
                        mean=float(col_data.mean()),
                        std=float(col_data.std()),
                        min=float(col_data.min()),
                        max=float(col_data.max()),
                        q1=float(col_data.quantile(0.25)),
                        q2=float(col_data.quantile(0.50)),
                        q3=float(col_data.quantile(0.75)),
                        unique_count=int(col_data.nunique()),
                        null_count=int(data[col].isna().sum())
                    )

            # Calculate correlations
            correlations = {}
            if len(numeric_cols) > 1:
                corr_matrix = data[numeric_cols].corr()
                for col1 in numeric_cols:
                    correlations[col1] = {
                        col2: float(corr_matrix.loc[col1, col2])
                        for col2 in numeric_cols
                        if col1 != col2
                    }

            # Calculate anomaly scores using Z-scores
            anomaly_scores = {}
            for col in numeric_cols:
                col_data = data[col].dropna()
                if len(col_data) > 0:
                    scaled_data = self.scaler.fit_transform(col_data.values.reshape(-1, 1))
                    anomaly_scores[col] = scaled_data.flatten().tolist()

            result = FeatureResult(
                success=True,
                data={
                    "feature_count": len(features),
                    "sample_size": len(data)
                },
                features=features,
                correlations=correlations,
                anomaly_scores=anomaly_scores
            )

            if not await self.validate(result):
                return FeatureResult(
                    success=False,
                    error_message="Invalid processing result"
                )

            return result

        except Exception as e:
            return FeatureResult(
                success=False,
                error_message=f"Error processing features: {str(e)}"
            )

    async def validate(self, result: FeatureResult) -> bool:
        """
        Validate feature processing results.

        Args:
            result: Processing result to validate

        Returns:
            True if valid, False otherwise
        """
        if not await super().validate(result):
            return False

        # Additional feature-specific validation
        return (
                len(result.features) > 0 and
                all(isinstance(stats, FeatureStats) for stats in result.features.values())
        )