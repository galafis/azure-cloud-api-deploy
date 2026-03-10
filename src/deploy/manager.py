"""Deployment management with versioning support.

Provides CRUD operations for managing application deployments
with version tracking, rollback capabilities, and deployment history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class DeploymentStatus(Enum):
    """Possible states of a deployment."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


@dataclass
class DeploymentVersion:
    """Represents a specific version of a deployment.

    Attributes:
        version: Semantic version string (e.g., '1.2.3').
        image: Container image reference.
        config: Configuration key-value pairs.
        created_at: When this version was created.
    """

    version: str = ""
    image: str = ""
    config: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "image": self.image,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Deployment:
    """Represents an application deployment.

    Attributes:
        id: Unique deployment identifier.
        app_name: Name of the application being deployed.
        environment: Target environment (dev, staging, prod).
        current_version: The currently active version.
        previous_version: The previously active version (for rollback).
        status: Current deployment status.
        strategy: Deployment strategy used (blue_green, canary, rolling).
        replicas: Number of desired replicas.
        versions: History of deployment versions.
        created_at: When the deployment was created.
        updated_at: When the deployment was last updated.
        completed_at: When the deployment completed.
        error_message: Error description if deployment failed.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    app_name: str = ""
    environment: str = "dev"
    current_version: str = ""
    previous_version: str = ""
    status: DeploymentStatus = DeploymentStatus.PENDING
    strategy: str = "rolling"
    replicas: int = 1
    versions: list[DeploymentVersion] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "app_name": self.app_name,
            "environment": self.environment,
            "current_version": self.current_version,
            "previous_version": self.previous_version,
            "status": self.status.value,
            "strategy": self.strategy,
            "replicas": self.replicas,
            "versions": [v.to_dict() for v in self.versions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
        }


class DeploymentManager:
    """Manages application deployments with version tracking.

    Provides CRUD operations, version management, rollback support,
    and deployment history queries.
    """

    def __init__(self) -> None:
        self._deployments: dict[str, Deployment] = {}

    def create_deployment(
        self,
        app_name: str,
        version: str,
        environment: str = "dev",
        image: str = "",
        strategy: str = "rolling",
        replicas: int = 1,
        config: Optional[dict] = None,
    ) -> Deployment:
        """Create a new deployment.

        Args:
            app_name: Name of the application.
            version: Version to deploy (e.g., '1.0.0').
            environment: Target environment.
            image: Container image reference.
            strategy: Deployment strategy (rolling, blue_green, canary).
            replicas: Number of replicas.
            config: Configuration key-value pairs.

        Returns:
            The created Deployment object.
        """
        deployment = Deployment(
            app_name=app_name,
            environment=environment,
            current_version=version,
            status=DeploymentStatus.PENDING,
            strategy=strategy,
            replicas=replicas,
        )

        dep_version = DeploymentVersion(
            version=version,
            image=image,
            config=config or {},
        )
        deployment.versions.append(dep_version)

        self._deployments[deployment.id] = deployment
        return deployment

    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Retrieve a deployment by ID."""
        return self._deployments.get(deployment_id)

    def list_deployments(
        self,
        app_name: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[DeploymentStatus] = None,
    ) -> list[Deployment]:
        """List deployments with optional filtering.

        Args:
            app_name: Filter by application name.
            environment: Filter by environment.
            status: Filter by deployment status.

        Returns:
            List of matching deployments sorted by update time (newest first).
        """
        deployments = list(self._deployments.values())

        if app_name:
            deployments = [d for d in deployments if d.app_name == app_name]
        if environment:
            deployments = [d for d in deployments if d.environment == environment]
        if status:
            deployments = [d for d in deployments if d.status == status]

        return sorted(deployments, key=lambda d: d.updated_at, reverse=True)

    def update_deployment(
        self,
        deployment_id: str,
        version: str,
        image: str = "",
        config: Optional[dict] = None,
    ) -> Optional[Deployment]:
        """Update a deployment to a new version.

        Stores the current version as previous for rollback and
        adds the new version to the version history.

        Args:
            deployment_id: The deployment to update.
            version: The new version to deploy.
            image: New container image reference.
            config: New configuration.

        Returns:
            The updated Deployment, or None if not found.
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        deployment.previous_version = deployment.current_version
        deployment.current_version = version
        deployment.status = DeploymentStatus.IN_PROGRESS
        deployment.updated_at = datetime.utcnow()

        dep_version = DeploymentVersion(
            version=version,
            image=image,
            config=config or {},
        )
        deployment.versions.append(dep_version)

        return deployment

    def complete_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Mark a deployment as successfully completed.

        Args:
            deployment_id: The deployment to complete.

        Returns:
            The updated Deployment, or None if not found.
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        deployment.status = DeploymentStatus.SUCCEEDED
        deployment.completed_at = datetime.utcnow()
        deployment.updated_at = datetime.utcnow()
        return deployment

    def fail_deployment(
        self, deployment_id: str, error_message: str = ""
    ) -> Optional[Deployment]:
        """Mark a deployment as failed.

        Args:
            deployment_id: The deployment that failed.
            error_message: Description of the failure.

        Returns:
            The updated Deployment, or None if not found.
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        deployment.status = DeploymentStatus.FAILED
        deployment.error_message = error_message
        deployment.updated_at = datetime.utcnow()
        return deployment

    def rollback_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Rollback a deployment to its previous version.

        Args:
            deployment_id: The deployment to rollback.

        Returns:
            The updated Deployment, or None if not found or no previous version.
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        if not deployment.previous_version:
            return None

        deployment.current_version, deployment.previous_version = (
            deployment.previous_version,
            deployment.current_version,
        )
        deployment.status = DeploymentStatus.ROLLED_BACK
        deployment.updated_at = datetime.utcnow()
        return deployment

    def cancel_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Cancel a pending or in-progress deployment.

        Args:
            deployment_id: The deployment to cancel.

        Returns:
            The updated Deployment, or None if not found.
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return None

        if deployment.status not in (
            DeploymentStatus.PENDING,
            DeploymentStatus.IN_PROGRESS,
        ):
            return None

        deployment.status = DeploymentStatus.CANCELLED
        deployment.updated_at = datetime.utcnow()
        return deployment

    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a deployment record.

        Args:
            deployment_id: The deployment to delete.

        Returns:
            True if the deployment was found and deleted.
        """
        if deployment_id in self._deployments:
            del self._deployments[deployment_id]
            return True
        return False

    def get_version_history(self, deployment_id: str) -> list[DeploymentVersion]:
        """Get the version history of a deployment.

        Args:
            deployment_id: The deployment ID.

        Returns:
            List of DeploymentVersion objects in chronological order.
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return []
        return deployment.versions
