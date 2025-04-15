"""
OpenAI model implementation for GASPAR system.
"""

from typing import Any, Dict, List
import json
try:
    from pyspark.resource import requests
except ImportError:
    import requests
import requests

from .base import BaseLLM


def _create_analysis_prompt(content: str) -> str:
    """Create prompt for document analysis."""
    return f"""
    Analyze the following document for privacy-related fields and sensitive information.
    Extract all relevant fields and categorize them by sensitivity level.
    Provide the output in JSON format with the following structure:
    {{
        "fields": [
            {{"name": "field_name", "type": "field_type", "sensitivity": "HIGH/MEDIUM/LOW", "allowed": True/False",
            "required_transformations": ["HASHING", "PARTIAL_HASHING", "ANONYMIZATION"] or [] if no transformation required,
            "privacy_level": "CONFIDENTIAL/PUBLIC/RESTRICTED/INTERNAL","pii": True/False}}
        ],
        "categories": ["PII", "Financial", "Health", etc.],
        "overall_risk": "HIGH/MEDIUM/LOW"
    }}

    Document content:
    {content}
    
    Don't output anything else apart from the json result
    """


def _create_anomaly_prompt(fields: List[Dict[str, Any]]) -> str:
    """Create prompt for anomaly detection."""
    fields_str = json.dumps(fields, indent=2)
    return f"""
    Analyze these fields for potential privacy anomalies or unusual patterns.
    Consider data types, values, and relationships between fields.
    Provide output in JSON format with the following structure:
    {{
        "anomalies": [
            {{
                "field": "field_name",
                "type": "anomaly_type",
                "description": "description",
                "risk_level": "HIGH/MEDIUM/LOW",
                "recommended_action": "action"
            }}
        ]
    }}

    Fields to analyze:
    {fields_str}
    """


def _create_filter_prompt(anomalies: List[Dict[str, Any]]) -> str:
    """Create prompt for filter generation."""
    anomalies_str = json.dumps(anomalies, indent=2)
    return f"""
    Generate Python code to filter out or transform data based on these anomalies.
    The code should:
    1. Handle each anomaly type appropriately
    2. Be efficient and maintainable
    3. Include proper error handling
    4. Be well-documented
    5. Return filtered/transformed data

    Anomalies to handle:
    {anomalies_str}
    """


class OpenAIModel(BaseLLM):
    """OpenAI model implementation."""

    def _initialize(self) -> None:
        """Initialize OpenAI client."""
        self.token = self.config.token
        self.base_url=self.config.api_base if self.config.api_base else None
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"}

    async def analyze_privacy_document(self, content: str) -> Dict[str, Any]:
        """Analyze privacy document using OpenAI."""
        prompt = _create_analysis_prompt(content)
        payload = {"model": self.config.model_name, "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 2000,
                   "temperature": 0.1}

        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload))
        if response.status_code == 200:
            response_data = response.json()
            choices = response_data.get('choices', 'Field not found')
            content = choices[0]["message"]["content"]
            return content
        else:
            print(f"Request failed with status code {response.status_code}")

    async def identify_anomalies(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify anomalies in extracted fields."""
        prompt = _create_anomaly_prompt(fields)
        payload = {"model": self.config.model_name, "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 2000,
                   "temperature": 0.1}

        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload))
        if response.status_code == 200:
            response_data = response.json()
            choices = response_data.get('choices', 'Field not found')
            content = choices[0]["message"]["content"]["anomalies"]
            return content
        else:
            print(f"Request failed with status code {response.status_code}")

    async def generate_filter(self, anomalies: List[Dict[str, Any]]) -> str:
        """Generate filter code for identified anomalies."""
        prompt = _create_filter_prompt(anomalies)

        payload = {"model": self.config.model_name, "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 2000,
                   "temperature": 0.1}

        response = requests.post(self.base_url, headers=self.headers, data=json.dumps(payload))
        if response.status_code == 200:
            response_data = response.json()
            choices = response_data.get('choices', 'Field not found')
            content = choices[0]["message"]["content"]
            return content
        else:
            print(f"Request failed with status code {response.status_code}")

