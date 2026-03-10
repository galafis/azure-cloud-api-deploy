"""Deployment strategies for cloud applications.

Implements blue-green, canary, and rolling deployment strategies,
each simulating the staged rollout of application updates.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StrategyType(Enum):
    """Available deployment strategy types."""

    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"


@dataclass
class DeploymentStep:
    """A single step within a deployment strategy execution.

    Attributes:
        step_number: Sequential step number.
        action: Description of the action taken.
        status: Step status (pending, in_progress, completed, failed).
        timestamp: When the step was executed.
        details: Additional step details.
    """

    step_number: int = 0
    action: str = ""
    status: str = "pending"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "action": self.action,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class BlueGreenStrategy:
    """Blue-Green deployment strategy.

    Maintains two identical production environments (blue and green).
    Traffic is switched from the current active environment to the
    newly deployed one once health checks pass.
    """

    def __init__(self) -> None:
        self.active_slot: str = "blue"
        self.inactive_slot: str = "green"
        self.steps: list[DeploymentStep] = []

    def execute(
        self,
        app_name: str,
        version: str,
        health_check_passed: bool = True,
    ) -> dict:
        """Execute a blue-green deployment.

        Steps:
        1. Deploy new version to inactive slot
        2. Run health checks on inactive slot
        3. Switch traffic to the new slot
        4. Keep old slot as rollback target

        Args:
            app_name: The application name.
            version: The version being deployed.
            health_check_passed: Simulated health check result.

        Returns:
            Deployment result dictionary.
        """
        self.steps = []

        # Step 1: Deploy to inactive slot
        self._add_step(
            1,
            f"Deploy {app_name}:{version} to {self.inactive_slot} slot",
            "completed",
            {"slot": self.inactive_slot, "version": version},
        )

        # Step 2: Run health checks
        health_status = "completed" if health_check_passed else "failed"
        self._add_step(
            2,
            f"Health check on {self.inactive_slot} slot",
            health_status,
            {"healthy": health_check_passed},
        )

        if not health_check_passed:
            self._add_step(
                3,
                f"Deployment aborted - health check failed on {self.inactive_slot}",
                "failed",
            )
            return {
                "success": False,
                "strategy": "blue_green",
                "message": "Health check failed, deployment aborted",
                "active_slot": self.active_slot,
                "steps": [s.to_dict() for s in self.steps],
            }

        # Step 3: Switch traffic
        old_active = self.active_slot
        self.active_slot, self.inactive_slot = self.inactive_slot, self.active_slot
        self._add_step(
            3,
            f"Traffic switched from {old_active} to {self.active_slot}",
            "completed",
            {"old_active": old_active, "new_active": self.active_slot},
        )

        # Step 4: Keep old slot for rollback
        self._add_step(
            4,
            f"Old slot {self.inactive_slot} retained for rollback",
            "completed",
        )

        return {
            "success": True,
            "strategy": "blue_green",
            "message": f"Deployment successful. Active: {self.active_slot}",
            "active_slot": self.active_slot,
            "rollback_slot": self.inactive_slot,
            "steps": [s.to_dict() for s in self.steps],
        }

    def rollback(self) -> dict:
        """Rollback to the previous slot.

        Returns:
            Rollback result dictionary.
        """
        old_active = self.active_slot
        self.active_slot, self.inactive_slot = self.inactive_slot, self.active_slot
        return {
            "success": True,
            "message": f"Rolled back from {old_active} to {self.active_slot}",
            "active_slot": self.active_slot,
        }

    def _add_step(
        self,
        number: int,
        action: str,
        status: str,
        details: Optional[dict] = None,
    ) -> None:
        self.steps.append(
            DeploymentStep(
                step_number=number,
                action=action,
                status=status,
                details=details or {},
            )
        )


class CanaryStrategy:
    """Canary deployment strategy.

    Gradually shifts traffic from the old version to the new version
    in configurable percentage increments. If issues are detected at
    any stage, the deployment can be rolled back.
    """

    def __init__(self, increments: Optional[list[int]] = None) -> None:
        self.increments = increments or [10, 25, 50, 75, 100]
        self.current_traffic_pct: int = 0
        self.steps: list[DeploymentStep] = []

    def execute(
        self,
        app_name: str,
        version: str,
        failure_at_pct: Optional[int] = None,
    ) -> dict:
        """Execute a canary deployment.

        Gradually increases traffic to the new version based on
        configured increment percentages.

        Args:
            app_name: The application name.
            version: The version being deployed.
            failure_at_pct: Simulated failure percentage (None for no failure).

        Returns:
            Deployment result dictionary.
        """
        self.steps = []
        self.current_traffic_pct = 0

        for pct in self.increments:
            if failure_at_pct is not None and pct >= failure_at_pct:
                self._add_step(
                    len(self.steps) + 1,
                    f"Canary failed at {pct}% traffic for {app_name}:{version}",
                    "failed",
                    {"traffic_percentage": pct, "error": "Health check failure"},
                )
                return {
                    "success": False,
                    "strategy": "canary",
                    "message": f"Canary deployment failed at {pct}% traffic",
                    "current_traffic_pct": self.current_traffic_pct,
                    "steps": [s.to_dict() for s in self.steps],
                }

            self.current_traffic_pct = pct
            self._add_step(
                len(self.steps) + 1,
                f"Routing {pct}% traffic to {app_name}:{version}",
                "completed",
                {"traffic_percentage": pct},
            )

        return {
            "success": True,
            "strategy": "canary",
            "message": f"Canary deployment complete at 100% for {app_name}:{version}",
            "current_traffic_pct": 100,
            "steps": [s.to_dict() for s in self.steps],
        }

    def _add_step(
        self,
        number: int,
        action: str,
        status: str,
        details: Optional[dict] = None,
    ) -> None:
        self.steps.append(
            DeploymentStep(
                step_number=number,
                action=action,
                status=status,
                details=details or {},
            )
        )


class RollingStrategy:
    """Rolling deployment strategy.

    Updates instances one batch at a time, keeping a portion of
    the old version running while new instances come online.
    Supports configurable batch sizes and max unavailable settings.
    """

    def __init__(
        self, batch_size: int = 1, max_unavailable: int = 1
    ) -> None:
        self.batch_size = batch_size
        self.max_unavailable = max_unavailable
        self.steps: list[DeploymentStep] = []

    def execute(
        self,
        app_name: str,
        version: str,
        total_replicas: int = 3,
        failure_at_batch: Optional[int] = None,
    ) -> dict:
        """Execute a rolling deployment.

        Updates instances in batches, waiting for each batch to become
        healthy before proceeding to the next.

        Args:
            app_name: The application name.
            version: The version being deployed.
            total_replicas: Total number of replicas to update.
            failure_at_batch: Simulated failure at a specific batch number.

        Returns:
            Deployment result dictionary.
        """
        self.steps = []
        batches = self._calculate_batches(total_replicas)
        updated_count = 0

        for batch_num, batch_indices in enumerate(batches, 1):
            if failure_at_batch is not None and batch_num >= failure_at_batch:
                self._add_step(
                    len(self.steps) + 1,
                    f"Batch {batch_num} failed for {app_name}:{version}",
                    "failed",
                    {
                        "batch": batch_num,
                        "instances": batch_indices,
                        "error": "Instance failed to start",
                    },
                )
                return {
                    "success": False,
                    "strategy": "rolling",
                    "message": f"Rolling update failed at batch {batch_num}",
                    "updated_count": updated_count,
                    "total_replicas": total_replicas,
                    "steps": [s.to_dict() for s in self.steps],
                }

            self._add_step(
                len(self.steps) + 1,
                f"Updating batch {batch_num}: instances {batch_indices}",
                "completed",
                {"batch": batch_num, "instances": batch_indices, "version": version},
            )
            updated_count += len(batch_indices)

        return {
            "success": True,
            "strategy": "rolling",
            "message": f"Rolling update complete for {app_name}:{version}",
            "updated_count": updated_count,
            "total_replicas": total_replicas,
            "steps": [s.to_dict() for s in self.steps],
        }

    def _calculate_batches(self, total: int) -> list[list[int]]:
        """Split replicas into batches based on batch_size."""
        batches = []
        for i in range(0, total, self.batch_size):
            batch = list(range(i, min(i + self.batch_size, total)))
            batches.append(batch)
        return batches

    def _add_step(
        self,
        number: int,
        action: str,
        status: str,
        details: Optional[dict] = None,
    ) -> None:
        self.steps.append(
            DeploymentStep(
                step_number=number,
                action=action,
                status=status,
                details=details or {},
            )
        )
