"""Environment management for cloud deployments.

Manages multiple deployment environments (development, staging, production)
with environment-specific configurations and promotion workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Environment:
    """Represents a deployment environment.

    Attributes:
        id: Unique environment identifier.
        name: Environment name (e.g., 'dev', 'staging', 'prod').
        display_name: Human-readable environment name.
        description: Environment description.
        config: Environment-specific configuration.
        active: Whether the environment is active.
        protected: Whether the environment requires approval for deployment.
        auto_deploy: Whether deployments are triggered automatically.
        created_at: When the environment was created.
        updated_at: When the environment was last updated.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    display_name: str = ""
    description: str = ""
    config: dict = field(default_factory=dict)
    active: bool = True
    protected: bool = False
    auto_deploy: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "config": self.config,
            "active": self.active,
            "protected": self.protected,
            "auto_deploy": self.auto_deploy,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class PromotionRecord:
    """Records a promotion event between environments.

    Attributes:
        id: Unique record identifier.
        source_env: Source environment name.
        target_env: Target environment name.
        version: Version being promoted.
        app_name: Application being promoted.
        promoted_by: Who initiated the promotion.
        approved: Whether the promotion was approved (for protected envs).
        timestamp: When the promotion occurred.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_env: str = ""
    target_env: str = ""
    version: str = ""
    app_name: str = ""
    promoted_by: str = ""
    approved: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_env": self.source_env,
            "target_env": self.target_env,
            "version": self.version,
            "app_name": self.app_name,
            "promoted_by": self.promoted_by,
            "approved": self.approved,
            "timestamp": self.timestamp.isoformat(),
        }


class EnvironmentManager:
    """Manages deployment environments and promotion workflows.

    Provides CRUD operations for environments, configuration management,
    and promotion tracking between environment stages.
    """

    # Default promotion order
    PROMOTION_ORDER = ["dev", "staging", "prod"]

    def __init__(self) -> None:
        self._environments: dict[str, Environment] = {}
        self._promotions: list[PromotionRecord] = []

    def create_environment(
        self,
        name: str,
        display_name: str = "",
        description: str = "",
        config: Optional[dict] = None,
        protected: bool = False,
        auto_deploy: bool = False,
    ) -> Environment:
        """Create a new environment.

        Args:
            name: Short environment name (e.g., 'dev').
            display_name: Human-readable name.
            description: Environment description.
            config: Environment-specific configuration.
            protected: Whether deployments require approval.
            auto_deploy: Whether to auto-deploy on promotion.

        Returns:
            The created Environment.
        """
        env = Environment(
            name=name,
            display_name=display_name or name.title(),
            description=description,
            config=config or {},
            protected=protected,
            auto_deploy=auto_deploy,
        )
        self._environments[name] = env
        return env

    def get_environment(self, name: str) -> Optional[Environment]:
        """Retrieve an environment by name."""
        return self._environments.get(name)

    def list_environments(self, active_only: bool = True) -> list[Environment]:
        """List all environments.

        Args:
            active_only: If True, only return active environments.

        Returns:
            List of environments, ordered by promotion order.
        """
        envs = list(self._environments.values())
        if active_only:
            envs = [e for e in envs if e.active]

        # Sort by promotion order
        order = {name: i for i, name in enumerate(self.PROMOTION_ORDER)}
        envs.sort(key=lambda e: order.get(e.name, 999))
        return envs

    def update_config(
        self, name: str, config: dict, merge: bool = True
    ) -> Optional[Environment]:
        """Update an environment's configuration.

        Args:
            name: Environment name.
            config: New configuration values.
            merge: If True, merge with existing config. If False, replace.

        Returns:
            The updated Environment, or None if not found.
        """
        env = self._environments.get(name)
        if not env:
            return None

        if merge:
            env.config.update(config)
        else:
            env.config = config

        env.updated_at = datetime.utcnow()
        return env

    def deactivate_environment(self, name: str) -> Optional[Environment]:
        """Deactivate an environment."""
        env = self._environments.get(name)
        if env:
            env.active = False
            env.updated_at = datetime.utcnow()
        return env

    def delete_environment(self, name: str) -> bool:
        """Delete an environment."""
        if name in self._environments:
            del self._environments[name]
            return True
        return False

    def promote(
        self,
        app_name: str,
        version: str,
        source_env: str,
        target_env: str,
        promoted_by: str = "system",
        approved: bool = False,
    ) -> dict:
        """Promote a version from one environment to another.

        Args:
            app_name: The application being promoted.
            version: The version to promote.
            source_env: Source environment name.
            target_env: Target environment name.
            promoted_by: Who initiated the promotion.
            approved: Whether promotion is approved (for protected envs).

        Returns:
            Response dictionary with promotion result.
        """
        source = self._environments.get(source_env)
        target = self._environments.get(target_env)

        if not source:
            return {"success": False, "message": f"Source environment '{source_env}' not found"}
        if not target:
            return {"success": False, "message": f"Target environment '{target_env}' not found"}

        if not target.active:
            return {"success": False, "message": f"Target environment '{target_env}' is not active"}

        # Check if target is protected and requires approval
        if target.protected and not approved:
            return {
                "success": False,
                "message": f"Environment '{target_env}' is protected and requires approval",
                "requires_approval": True,
            }

        # Validate promotion order
        source_order = self.PROMOTION_ORDER.index(source_env) if source_env in self.PROMOTION_ORDER else -1
        target_order = self.PROMOTION_ORDER.index(target_env) if target_env in self.PROMOTION_ORDER else -1

        if source_order >= 0 and target_order >= 0 and target_order < source_order:
            return {
                "success": False,
                "message": f"Cannot promote backwards from '{source_env}' to '{target_env}'",
            }

        # Record promotion
        record = PromotionRecord(
            source_env=source_env,
            target_env=target_env,
            version=version,
            app_name=app_name,
            promoted_by=promoted_by,
            approved=approved or not target.protected,
        )
        self._promotions.append(record)

        return {
            "success": True,
            "message": f"Promoted {app_name}:{version} from {source_env} to {target_env}",
            "promotion": record.to_dict(),
        }

    def get_promotion_history(
        self,
        app_name: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 20,
    ) -> list[PromotionRecord]:
        """Get promotion history with optional filtering.

        Args:
            app_name: Filter by application name.
            environment: Filter by target environment.
            limit: Maximum number of records to return.

        Returns:
            List of PromotionRecord objects.
        """
        records = self._promotions.copy()
        if app_name:
            records = [r for r in records if r.app_name == app_name]
        if environment:
            records = [r for r in records if r.target_env == environment]
        return records[-limit:]

    def setup_default_environments(self) -> list[Environment]:
        """Create default dev/staging/prod environments.

        Returns:
            List of created environments.
        """
        envs = []
        envs.append(
            self.create_environment(
                name="dev",
                display_name="Development",
                description="Development environment for testing",
                config={"debug": True, "log_level": "DEBUG", "replicas": 1},
                auto_deploy=True,
            )
        )
        envs.append(
            self.create_environment(
                name="staging",
                display_name="Staging",
                description="Pre-production environment",
                config={"debug": False, "log_level": "INFO", "replicas": 2},
                protected=False,
            )
        )
        envs.append(
            self.create_environment(
                name="prod",
                display_name="Production",
                description="Production environment",
                config={"debug": False, "log_level": "WARNING", "replicas": 3},
                protected=True,
            )
        )
        return envs
