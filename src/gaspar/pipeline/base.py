"""
Base pipeline components for GASPAR system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from ..config.base import GasparConfig
from ..storage import StorageFactory, BaseStorage

class PipelineContext(BaseModel):
    """Context for pipeline execution."""
    run_id: str
    config: GasparConfig
    state: Dict[str, Any] = None
    artifacts: Dict[str, str] = None
    _storage: Optional[BaseStorage] = None

    def get_storage(self) -> BaseStorage:
        """Get storage instance."""
        if not self._storage:
            self._storage = StorageFactory.create(self.config.storage)
        return self._storage

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True

class StepResult(BaseModel):
    """Result of pipeline step execution."""
    success: bool = True
    error_message: Optional[str] = None
    outputs: Dict[str, Any] = None
    artifacts: Dict[str, str] = None

class PipelineStep(ABC):
    """Base class for pipeline steps."""
    
    def __init__(self, name: str):
        """
        Initialize pipeline step.
        
        Args:
            name: Step name
        """
        self.name = name
    
    @abstractmethod
    async def execute(self, context: PipelineContext) -> StepResult:
        """
        Execute pipeline step.
        
        Args:
            context: Pipeline execution context
            
        Returns:
            Step execution result
        """
        pass

    async def validate(self, result: StepResult) -> bool:
        """
        Validate step execution result.
        
        Args:
            result: Step result to validate
            
        Returns:
            True if valid
        """
        return result.success