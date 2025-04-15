"""
Shared data types for GASPAR system.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class PrivacyLevel(str, Enum):
    """Privacy level classification."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"

class DataConstraint(BaseModel):
    """Data field constraints."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    regex_pattern: Optional[str] = None
    custom_validation: Optional[str] = None

class PrivacyRule(BaseModel):
    """Privacy rule for a data field."""
    field_name: str
    data_type: str
    allowed: bool = True
    privacy_level: PrivacyLevel
    constraints: Optional[DataConstraint] = None
    description: Optional[str] = None
    required_transformations: List[str] = None

class DataSample(BaseModel):
    """Data sample from feed."""
    timestamp: datetime
    source: str
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None