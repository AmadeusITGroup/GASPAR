"""
Deployment step for GASPAR pipeline.
Handles safe deployment of generated privacy filters.
"""

import os
import importlib.util
from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
from ..base import PipelineStep, PipelineContext, StepResult
from ...core.analyzers import Filter, FilterCode


class DeploymentResult(StepResult):
    """Results from filter deployment."""
    deployed_filters: List[str] = None
    deployment_time: datetime = None
    quarantine_path: str = None


class DeploymentStep(PipelineStep):
    """Step for deploying privacy filters."""

    def __init__(self):
        """Initialize deployment step."""
        super().__init__("deployment")
        self.active_filters = {}
        self.quarantine_data = []

    async def execute(self, context: PipelineContext) -> DeploymentResult:
        """
        Execute deployment step.

        Args:
            context: Pipeline execution context

        Returns:
            Deployment results
        """
        try:
            # Get generated filters
            filters = context.state.get("filters", [])
            if not filters:
                return DeploymentResult(
                    success=True,
                    error_message="No filters to deploy"
                )

            # Create deployment directory
            deploy_path = os.path.join(
                context.config.pipeline.temp_directory,
                f"filters_{context.run_id}"
            )
            os.makedirs(deploy_path, exist_ok=True)

            # Create quarantine directory
            quarantine_path = os.path.join(
                context.config.pipeline.temp_directory,
                f"quarantine_{context.run_id}"
            )
            os.makedirs(quarantine_path, exist_ok=True)

            # Deploy each filter
            deployed_filters = []
            for filter in filters:
                try:
                    # Get filter code
                    filter_code = context.state.get("generated_code", {}).get(filter.name)
                    if not filter_code:
                        continue

                    # Deploy filter
                    filter_path = await self._deploy_filter(
                        filter,
                        filter_code,
                        deploy_path
                    )

                    if filter_path:
                        deployed_filters.append(filter_path)

                        # Load and register filter
                        loaded_filter = await self._load_filter(filter_path)
                        if loaded_filter:
                            self.active_filters[filter.name] = {
                                "filter": loaded_filter,
                                "metadata": filter.dict()
                            }

                except Exception as e:
                    print(f"Error deploying filter {filter.name}: {str(e)}")
                    continue

            deployment_time = datetime.now()

            return DeploymentResult(
                success=True,
                outputs={
                    "deployed_filters": deployed_filters,
                    "deployment_time": deployment_time,
                    "quarantine_path": quarantine_path
                },
                artifacts={
                    "filters": deploy_path,
                    "quarantine": quarantine_path
                },
                deployed_filters=deployed_filters,
                deployment_time=deployment_time,
                quarantine_path=quarantine_path
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                error_message=f"Error in deployment step: {str(e)}"
            )

    async def _deploy_filter(
            self,
            filter: Filter,
            filter_code: FilterCode,
            deploy_path: str
    ) -> Optional[str]:
        """Deploy a single filter."""
        # Create filter file
        filter_path = os.path.join(deploy_path, f"{filter.name}.py")

        try:
            # Write filter code
            with open(filter_path, 'w') as f:
                f.write(filter_code.code)

            # Write tests if available
            if filter_code.tests:
                test_path = os.path.join(deploy_path, f"test_{filter.name}.py")
                with open(test_path, 'w') as f:
                    f.write(filter_code.tests)

            # Run tests if available
            if filter_code.tests:
                test_result = await self._run_tests(test_path)
                if not test_result:
                    print(f"Tests failed for filter {filter.name}")
                    return None

            return filter_path

        except Exception as e:
            print(f"Error deploying filter {filter.name}: {str(e)}")
            return None

    async def _load_filter(self, filter_path: str) -> Optional[callable]:
        """Load a deployed filter."""
        try:
            # Load module
            spec = importlib.util.spec_from_file_location(
                "filter_module",
                filter_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get filter function
            filter_name = os.path.basename(filter_path)[:-3]  # Remove .py
            if hasattr(module, filter_name):
                return getattr(module, filter_name)

            return None

        except Exception as e:
            print(f"Error loading filter {filter_path}: {str(e)}")
            return None

    async def _run_tests(self, test_path: str) -> bool:
        """Run tests for a filter."""
        try:
            # Run pytest on the test file
            import pytest
            result = pytest.main(["-v", test_path])
            return result == 0

        except Exception as e:
            print(f"Error running tests {test_path}: {str(e)}")
            return False

    async def process_record(
            self,
            record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a record through active filters.

        Args:
            record: Record to process

        Returns:
            Processing results including quarantine decision
        """
        results = {
            "record": record,
            "quarantine": False,
            "matched_filters": [],
            "actions": []
        }

        for filter_name, filter_info in self.active_filters.items():
            try:
                if filter_info["filter"](record):
                    results["matched_filters"].append(filter_name)
                    results["quarantine"] = True
                    results["actions"].extend(
                        [a.dict() for a in filter_info["metadata"]["actions"]]
                    )
            except Exception as e:
                print(f"Error applying filter {filter_name}: {str(e)}")
                continue

        if results["quarantine"]:
            self.quarantine_data.append({
                "timestamp": datetime.now().isoformat(),
                "record": record,
                "filters": results["matched_filters"],
                "actions": results["actions"]
            })

        return results

    async def get_quarantine_stats(self) -> Dict[str, Any]:
        """Get quarantine statistics."""
        filter_stats = {}
        for entry in self.quarantine_data:
            for filter_name in entry["filters"]:
                if filter_name not in filter_stats:
                    filter_stats[filter_name] = {
                        "count": 0,
                        "last_match": None
                    }
                filter_stats[filter_name]["count"] += 1
                filter_stats[filter_name]["last_match"] = entry["timestamp"]

        return {
            "total_quarantined": len(self.quarantine_data),
            "filter_stats": filter_stats,
            "active_filters": len(self.active_filters)
        }