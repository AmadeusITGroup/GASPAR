"""
Models for IPA rules and data validation.
"""

from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel

class DataType(str, Enum):
    """Supported data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    ADDRESS = "address"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    CUSTOM = "custom"

class RuleType(str, Enum):
    """Types of validation rules."""
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    RESTRICTED = "restricted"  # Allowed with conditions

class ValidationRule(BaseModel):
    """Rule for data validation."""
    field_name: str
    data_type: DataType
    rule_type: RuleType
    description: str
    pattern: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    conditions: Optional[Dict[str, Any]] = None

    model_config = {
        "validate_assignment": True,
        "frozen": True
    }

class IPARules(BaseModel):
    """Collection of IPA rules."""
    rules: List[ValidationRule] = None
    global_rules: Dict[str, Any] = None
    version: str = "1.0"

    model_config = {
        "validate_assignment": True,
        "json_schema_extra": {
            "rules": {"default_factory": list},
            "global_rules": {"default_factory": dict}
        }
    }

    def get_field_rules(self, field_name: str) -> List[ValidationRule]:
        """Get all rules for a specific field."""
        return [rule for rule in self.rules if rule.field_name == field_name]

    def get_rules_by_type(self, rule_type: RuleType) -> List[ValidationRule]:
        """Get all rules of a specific type."""
        return [rule for rule in self.rules if rule.rule_type == rule_type]

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a new validation rule."""
        self.rules.append(rule)

    def remove_rule(self, field_name: str, rule_type: RuleType) -> None:
        """Remove rules for a field of specific type."""
        self.rules = [
            rule for rule in self.rules
            if not (rule.field_name == field_name and rule.rule_type == rule_type)
        ]

class DataProfile(BaseModel):
    """Profile of analyzed data field."""
    field_name: str
    data_type: DataType
    sample_size: int
    unique_values: int
    null_count: int
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    patterns: List[str] = None
    example_values: List[Any] = None

    model_config = {
        "validate_assignment": True,
        "json_schema_extra": {
            "patterns": {"default_factory": list},
            "example_values": {"default_factory": list}
        }
    }

class Violation(BaseModel):
    """Detected rule violation."""
    field_name: str
    rule: ValidationRule
    value: Any
    violation_type: str
    description: str
    severity: str
    sample_id: Optional[str] = None
    context: Dict[str, Any] = None

    model_config = {
        "validate_assignment": True,
        "json_schema_extra": {
            "context": {"default_factory": dict}
        }
    }