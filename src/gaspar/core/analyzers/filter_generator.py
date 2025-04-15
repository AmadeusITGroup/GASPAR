"""
Filter generator for GASPAR system.
Generates data filters based on distribution anomalies and privacy rules.
"""

import os
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from ..processors import PrivacyRule, DataDistributionModeler
from .anomaly_detector import AnomalyDetail

class FilterCondition(BaseModel):
    """Condition for filtering data."""
    field: str
    operator: str  # 'eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'in', 'not_in', 'match', 'not_match'
    value: Any
    logic: str = "AND"  # 'AND' or 'OR'
    confidence: float = 1.0

class FilterAction(BaseModel):
    """Action to take on filtered data."""
    action_type: str  # 'quarantine', 'transform', 'alert', 'block'
    destination: Optional[str] = None
    transformation: Optional[str] = None
    alert_level: Optional[str] = None

class Filter(BaseModel):
    """Complete filter definition."""
    name: str
    description: str
    conditions: List[FilterCondition] = None
    actions: List[FilterAction] = None
    enabled: bool = True
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = None

class FilterCode(BaseModel):
    """Generated filter code."""
    code: str
    language: str = "python"
    tests: Optional[str] = None
    validation: Optional[str] = None

class FilterGeneratorResult(BaseModel):
    """Results from filter generation."""
    success: bool = True
    error_message: Optional[str] = None
    filters: List[Filter] = None
    generated_code: Dict[str, FilterCode] = None
    coverage: Dict[str, bool] = None

class FilterGenerator:
    """Generator for privacy protection filters."""

    def __init__(
        self,
        rules: List[PrivacyRule],
        data_modeler: DataDistributionModeler,
        min_confidence: float = 0.8,
        batch_filters: bool = True
    ):
        """
        Initialize filter generator.

        Args:
            rules: Privacy rules from IPA
            data_modeler: Data distribution modeler
            min_confidence: Minimum confidence for filter generation
            batch_filters: Whether to combine similar filters
        """
        self.rules = {rule.field_name: rule for rule in rules}
        self.data_modeler = data_modeler
        self.min_confidence = min_confidence
        self.batch_filters = batch_filters

    async def generate_filters(
        self,
        anomalies: List[AnomalyDetail]
    ) -> FilterGeneratorResult:
        """
        Generate filters based on detected anomalies.

        Args:
            anomalies: List of detected anomalies

        Returns:
            Generated filters and code
        """
        try:
            # Filter high-confidence anomalies
            valid_anomalies = [
                a for a in anomalies
                if a.confidence >= self.min_confidence
            ]

            if not valid_anomalies:
                return FilterGeneratorResult(
                    success=True,
                    filters=[],
                    coverage={}
                )

            # Generate filters
            if self.batch_filters:
                filters = await self._generate_batched_filters(valid_anomalies)
            else:
                filters = await self._generate_individual_filters(valid_anomalies)

            # Generate code for each filter
            generated_code = {}
            for filter in filters:
                code = await self._generate_filter_code(filter)
                generated_code[filter.name.replace(" ", "_")] = code

            # Track field coverage
            coverage = {
                rule.field_name: any(
                    f.conditions[0].field == rule.field_name
                    for f in filters
                )
                for rule in self.rules.values()
            }

            return FilterGeneratorResult(
                success=True,
                filters=filters,
                generated_code=generated_code,
                coverage=coverage
            )

        except Exception as e:
            return FilterGeneratorResult(
                success=False,
                error_message=f"Error generating filters: {str(e)}"
            )

    async def _generate_batched_filters(
        self,
        anomalies: List[AnomalyDetail]
    ) -> List[Filter]:
        """Generate batched filters for related anomalies."""
        filters = []
        field_anomalies: Dict[str, List[AnomalyDetail]] = {}

        # Group anomalies by field
        for anomaly in anomalies:
            if anomaly.field_name not in field_anomalies:
                field_anomalies[anomaly.field_name] = []
            field_anomalies[anomaly.field_name].append(anomaly)

        # Create filter for each field
        for field_name, field_anomalies_list in field_anomalies.items():
            rule = self.rules.get(field_name)
            if not rule:
                continue

            # Get distribution for the field
            distribution = self.data_modeler.distributions.get(field_name)
            conditions = []

            # Handle required fields
            if hasattr(rule, 'required') and rule.required:
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="exists",
                    value=False,  # Check for missing required fields
                    confidence=1.0,
                    logic="OR"
                ))

            # Handle not allowed fields (like SSN)
            if not rule.allowed:
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="exists",
                    value=True,
                    confidence=1.0,
                    logic="OR"
                ))

            # Handle field-specific validations
            if field_name == "social_security_number":
                # Check SSN format
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="not_match",
                    value=r"^\d{3}-\d{2}-\d{4}$",
                    confidence=1.0,
                    logic="OR"
                ))
            elif field_name == "email_address":
                # Check email format
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="not_match",
                    value=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    confidence=1.0,
                    logic="OR"
                ))
            elif field_name == "phone_number":
                # Check phone format
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="not_match",
                    value=r"^\d{3}-\d{3}-\d{4}$",
                    confidence=1.0,
                    logic="OR"
                ))
            elif field_name == "date_of_birth":
                # Check date format and range
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="not_match",
                    value=r"^\d{4}-\d{2}-\d{2}$",
                    confidence=1.0,
                    logic="OR"
                ))
                # Add check for future dates
                conditions.append(FilterCondition(
                    field=field_name,
                    operator="gt",
                    value=datetime.now().date().isoformat(),
                    confidence=1.0,
                    logic="OR"
                ))
            elif field_name == "banking_information":
                # Check banking info structure
                conditions.extend([
                    FilterCondition(
                        field="banking_information.routing_number",
                        operator="not_match",
                        value=r"^\d{9}$",
                        confidence=1.0,
                        logic="OR"
                    ),
                    FilterCondition(
                        field="banking_information.account_number",
                        operator="not_match",
                        value=r"^\d{8,17}$",
                        confidence=1.0,
                        logic="OR"
                    )
                ])

            # Add distribution-based conditions for numerical fields
            if distribution and rule.data_type in ["integer", "float"]:
                # Extract numerical anomalies
                numeric_anomalies = [a for a in field_anomalies_list if
                                    a.violation_type == "distribution_anomaly" or
                                    a.distribution_metrics]

                if numeric_anomalies:
                    # Get values flagged as anomalies
                    anomaly_values = []
                    for a in numeric_anomalies:
                        try:
                            val = float(a.actual_value)
                            anomaly_values.append(val)
                        except (ValueError, TypeError):
                            continue

                    if anomaly_values:
                        # Find low and high thresholds from anomalies
                        min_anomaly = min(anomaly_values)
                        max_anomaly = max(anomaly_values)

                        # Create conditions based on observed anomalies
                        if min_anomaly < distribution.mean - (2 * distribution.std):
                            conditions.append(FilterCondition(
                                field=field_name,
                                operator="lt",
                                value=max(min_anomaly, distribution.mean - (3 * distribution.std)),
                                confidence=0.95,
                                logic="OR"
                            ))

                        if max_anomaly > distribution.mean + (2 * distribution.std):
                            conditions.append(FilterCondition(
                                field=field_name,
                                operator="gt",
                                value=min(max_anomaly, distribution.mean + (3 * distribution.std)),
                                confidence=0.95,
                                logic="OR"
                            ))

            # Add distribution-based conditions for categorical fields
            if distribution and distribution.categorical_counts:
                # Extract categorical anomalies
                categorical_anomalies = [a for a in field_anomalies_list if
                                        a.violation_type == "distribution_anomaly" or
                                        (str(a.actual_value) not in distribution.categorical_counts)]

                if categorical_anomalies:
                    # Method 1: Collect specific anomalous values
                    anomalous_values = set()
                    for anomaly in categorical_anomalies:
                        anomalous_values.add(str(anomaly.actual_value))

                    if anomalous_values:
                        # Create a filter condition for these specific values
                        conditions.append(FilterCondition(
                            field=field_name,
                            operator="in",
                            value=list(anomalous_values),
                            confidence=0.9,
                            logic="OR"
                        ))

                    # Method 2: Look for patterns in anomalies
                    suspicious_patterns = self._extract_suspicious_patterns(
                        [str(a.actual_value) for a in categorical_anomalies]
                    )

                    for pattern in suspicious_patterns:
                        conditions.append(FilterCondition(
                            field=field_name,
                            operator="match",
                            value=pattern,
                            confidence=0.85,
                            logic="OR"
                        ))

            if conditions:
                filters.append(Filter(
                    name=f"filter_{field_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    description=f"Privacy filter for {field_name}",
                    conditions=conditions,
                    actions=self._create_actions(
                        max(a.severity for a in field_anomalies_list)
                    ),
                    priority=self._calculate_priority(
                        len(field_anomalies_list) / len(anomalies),
                        max(a.severity for a in field_anomalies_list)
                    ),
                    metadata={
                        "field": field_name,
                        "rule_type": "not_allowed" if not rule.allowed else "validation",
                        "anomaly_count": len(field_anomalies_list),
                        "avg_confidence": sum(a.confidence for a in field_anomalies_list) / len(field_anomalies_list),
                        "distribution_metrics": distribution.dict() if distribution else None
                    }
                ))

        return filters

    async def _generate_individual_filters(
        self,
        anomalies: List[AnomalyDetail]
    ) -> List[Filter]:
        """Generate individual filters for each anomaly."""
        filters = []

        for anomaly in anomalies:
            rule = self.rules.get(anomaly.field_name)
            if not rule:
                continue

            conditions = []

            if anomaly.violation_type == "distribution_anomaly":
                # Create distribution-based condition
                if anomaly.distribution_metrics:
                    if rule.data_type in ["integer", "float"]:
                        mean = anomaly.distribution_metrics.get("mean")
                        std = anomaly.distribution_metrics.get("std")
                        if mean is not None and std is not None:
                            if float(anomaly.actual_value) > mean + (2 * std):
                                conditions.append(FilterCondition(
                                    field=anomaly.field_name,
                                    operator="gt",
                                    value=mean + (2 * std),
                                    confidence=anomaly.confidence
                                ))
                            elif float(anomaly.actual_value) < mean - (2 * std):
                                conditions.append(FilterCondition(
                                    field=anomaly.field_name,
                                    operator="lt",
                                    value=mean - (2 * std),
                                    confidence=anomaly.confidence
                                ))
            else:
                # Create value-based condition
                conditions.append(FilterCondition(
                    field=anomaly.field_name,
                    operator="eq",
                    value=anomaly.actual_value,
                    confidence=anomaly.confidence
                ))

            if conditions:
                filters.append(Filter(
                    name=f"anomaly_{anomaly.field_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    description=f"Filter for {anomaly.violation_type} in {anomaly.field_name}",
                    conditions=conditions,
                    actions=self._create_actions(anomaly.severity),
                    priority=self._calculate_priority(
                        anomaly.confidence,
                        anomaly.severity
                    ),
                    metadata={
                        "violation_type": anomaly.violation_type,
                        "confidence": anomaly.confidence,
                        "distribution_metrics": anomaly.distribution_metrics
                    }
                ))

        return filters

    def _extract_suspicious_patterns(self, values: List[str]) -> List[str]:
        """
        Extract suspicious patterns from anomalous values.

        Args:
            values: List of anomalous string values

        Returns:
            List of regex patterns that may indicate anomalies
        """
        patterns = []

        # Look for common prefixes/suffixes
        if len(values) >= 3:  # Need at least a few samples to find patterns
            # Check for common prefix
            prefix = os.path.commonprefix(values)
            if len(prefix) >= 3:  # Minimum prefix length to be meaningful
                patterns.append(f"^{re.escape(prefix)}.*")

            # Check for common suffix
            reversed_values = [v[::-1] for v in values]
            suffix = os.path.commonprefix(reversed_values)[::-1]
            if len(suffix) >= 3:
                patterns.append(f".*{re.escape(suffix)}$")

        # Look for special characters or unusual formats
        special_chars_pattern = r'[@#$%^&*()+=\[\]{}|\\:;<>?/~`]'
        special_chars_count = sum(1 for v in values if re.search(special_chars_pattern, v))
        if special_chars_count >= len(values) / 2:
            patterns.append(special_chars_pattern)

        # Look for unusual length
        lengths = [len(v) for v in values]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        if avg_length > 50:  # Unusually long values
            patterns.append(f"^.{{{int(avg_length-10)},}}$")

        return patterns

    async def _generate_filter_code(self, filter: Filter) -> FilterCode:
        """Generate executable code for a filter."""
        conditions_code = []
        for condition in filter.conditions:
            if condition.operator == "exists":
                conditions_code.append(f"'{condition.field}' in record")
            elif condition.operator in ["eq", "ne", "gt", "lt", "gte", "lte"]:
                op_map = {
                    "eq": "==", "ne": "!=", "gt": ">",
                    "lt": "<", "gte": ">=", "lte": "<="
                }
                conditions_code.append(
                    f"record.get('{condition.field}') {op_map[condition.operator]} {repr(condition.value)}"
                )
            elif condition.operator in ["in", "not_in"]:
                op = "in" if condition.operator == "in" else "not in"
                conditions_code.append(
                    f"record.get('{condition.field}') {op} {repr(condition.value)}"
                )
            elif condition.operator in ["match", "not_match"]:
                op = "" if condition.operator == "match" else "not "
                conditions_code.append(
                    f"{op}re.match({repr(condition.value)}, str(record.get('{condition.field}', '')))"
                )

        conditions_str = f" {filter.conditions[0].logic} ".join(conditions_code)

        code = f"""
import re
from typing import Dict, Any

def {filter.name.replace(" ", "_")}(record: Dict[str, Any]) -> bool:
    \"\"\"
    Check if record matches filter conditions.
    
    Args:
        record: Data record to check
        
    Returns:
        True if record should be filtered
    \"\"\"
    try:
        return {conditions_str}
    except Exception:
        return False
"""

        # Generate tests
        tests = self._generate_tests(filter)

        return FilterCode(
            code=code,
            language="python",
            tests=tests
        )

    def _create_actions(self, severity: str) -> List[FilterAction]:
        """Create actions based on severity."""
        actions = []

        # Primary action is always quarantine
        actions.append(FilterAction(
            action_type="quarantine",
            destination="quarantine_storage"
        ))

        # Add alerts based on severity
        if severity == "HIGH":
            actions.append(FilterAction(
                action_type="alert",
                alert_level="HIGH",
                destination="security_team"
            ))
        elif severity == "MEDIUM":
            actions.append(FilterAction(
                action_type="alert",
                alert_level="MEDIUM",
                destination="data_team"
            ))

        return actions

    def _calculate_priority(self, confidence: float, severity: str) -> int:
        """Calculate filter priority."""
        severity_score = {
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1
        }.get(severity, 1)

        return min(100, int(confidence * 100) + severity_score * 20)

    def _generate_tests(self, filter: Filter) -> str:
        """Generate test cases for a filter."""
        tests = []

        # Positive test (should trigger filter)
        tests.append(f"""
def test_{filter.name.replace(" ", "_")}_positive():
    # Test case that should trigger the filter
    record = {{
        {", ".join(f"'{c.field}': {repr(c.value)}" for c in filter.conditions)}
    }}
    assert {filter.name.replace(" ", "_")}(record) is True
""")

        # Negative test (should not trigger filter)
        negative_case = {}
        for condition in filter.conditions:
            if condition.operator in ["eq", "ne", "gt", "lt", "gte", "lte"]:
                if isinstance(condition.value, (int, float)):
                    negative_case[condition.field] = condition.value + 100
                else:
                    negative_case[condition.field] = "valid_value"
            elif condition.operator in ["in", "not_in"]:
                negative_case[condition.field] = "valid_value"

        if negative_case:
            tests.append(f"""
def test_{filter.name.replace(" ", "_")}_negative():
    # Test case that should not trigger the filter
    record = {repr(negative_case)}
    assert {filter.name.replace(" ", "_")}(record) is False
""")

        return "\n".join(tests)