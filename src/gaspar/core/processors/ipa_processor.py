"""
IPA document processor for GASPAR system.
Extracts privacy rules and data constraints from Initial Privacy Assessment documents.
"""
import json
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

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
    pii: bool = False
    privacy_level: PrivacyLevel
    constraints: Optional[DataConstraint] = None
    sensitivity: Optional[str] = None
    required_transformations: List[str] = None

class IPAResult(BaseModel):
    """Results from IPA processing."""
    success: bool = True
    error_message: Optional[str] = None
    rules: List[PrivacyRule] = None
    data_sources: List[str] = None
    monitoring_requirements: Dict[str, Any] = None

class IPAProcessor:
    """Processor for Initial Privacy Assessment documents."""

    def __init__(self, llm):
        """Initialize processor with LLM."""
        self.llm = llm

    async def process(self, content: str) -> IPAResult:
        """
        Process IPA document to extract privacy rules.

        Args:
            content: IPA document content

        Returns:
            IPAResult containing extracted rules and requirements
        """
        try:
            # Analyze document using LLM
            analysis = await self.llm.analyze_privacy_document(content)
            analysis_json = json.loads(analysis)
            #print(analysis_json)

            # Extract privacy rules
            rules = []
            for field in analysis_json.get("fields", []):
                #print(field)

                constraints = None
                if field.get("constraints"):
                    constraints = DataConstraint(
                        min_value=field["constraints"].get("min_value"),
                        max_value=field["constraints"].get("max_value"),
                        allowed_values=field["constraints"].get("allowed_values"),
                        regex_pattern=field["constraints"].get("regex_pattern"),
                        custom_validation=field["constraints"].get("custom_validation")
                    )

                rules.append(PrivacyRule(
                    field_name=field["name"],
                    data_type=field["type"],
                    allowed=field.get("allowed", True),
                    pii=field.get("pii", False),
                    privacy_level=field.get("privacy_level", PrivacyLevel.CONFIDENTIAL),
                    constraints=constraints,
                    sensitivity=field["sensitivity"],
                    required_transformations=field.get("required_transformations", [])
                ))

            # Extract monitoring requirements
            monitoring_reqs = {
                "sampling_rate": analysis_json.get("sampling_rate", 1),
                "batch_size": analysis_json.get("batch_size", 1),
                "monitoring_interval": analysis_json.get("monitoring_interval", "1h"),
                "alert_thresholds": analysis_json.get("alert_thresholds", {
                    "violation_rate": 0.01,
                    "confidence_threshold": 0.95
                })
            }

            return IPAResult(
                success=True,
                rules=rules,
                data_sources=analysis_json.get("data_sources", []),
                monitoring_requirements=monitoring_reqs
            )

        except Exception as e:
            return IPAResult(
                success=False,
                error_message=f"Error processing IPA document: {str(e)}"
            )

    def validate_rules(self, rules: List[PrivacyRule]) -> bool:
        """
        Validate extracted privacy rules.

        Args:
            rules: List of privacy rules to validate

        Returns:
            True if rules are valid
        """
        if not rules:
            return False

        # Check for rule completeness
        for rule in rules:
            if not rule.field_name or not rule.data_type:
                return False

            # Validate constraints if present
            if rule.constraints:
                if (rule.constraints.min_value is not None and
                    rule.constraints.max_value is not None and
                    rule.constraints.min_value > rule.constraints.max_value):
                    return False

        return True