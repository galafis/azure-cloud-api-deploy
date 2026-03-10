"""Health check monitoring for deployed applications.

Provides configurable health check probes that simulate
monitoring of application liveness and readiness.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class HealthStatus(Enum):
    """Possible health check result states."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check probe.

    Attributes:
        id: Unique result identifier.
        deployment_id: The deployment being checked.
        status: Health status result.
        response_time_ms: Response time in milliseconds.
        checks: Individual check results.
        timestamp: When the check was performed.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    deployment_id: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    response_time_ms: float = 0.0
    checks: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "deployment_id": self.deployment_id,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "checks": self.checks,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health check probes.

    Attributes:
        endpoint: The health check URL path.
        interval_seconds: Seconds between checks.
        timeout_seconds: Maximum seconds to wait for response.
        healthy_threshold: Consecutive successes required for healthy.
        unhealthy_threshold: Consecutive failures required for unhealthy.
    """

    endpoint: str = "/health"
    interval_seconds: int = 30
    timeout_seconds: int = 5
    healthy_threshold: int = 3
    unhealthy_threshold: int = 3


class HealthChecker:
    """Monitors the health of deployed applications.

    Simulates health check probes and maintains check history
    for each deployment. Supports custom health check configurations.
    """

    def __init__(self) -> None:
        self._configs: dict[str, HealthCheckConfig] = {}
        self._results: dict[str, list[HealthCheckResult]] = {}
        self._status: dict[str, HealthStatus] = {}
        self._consecutive_success: dict[str, int] = {}
        self._consecutive_failure: dict[str, int] = {}

    def configure(
        self,
        deployment_id: str,
        config: Optional[HealthCheckConfig] = None,
    ) -> HealthCheckConfig:
        """Configure health checks for a deployment.

        Args:
            deployment_id: The deployment to configure.
            config: Health check configuration (uses defaults if None).

        Returns:
            The applied HealthCheckConfig.
        """
        cfg = config or HealthCheckConfig()
        self._configs[deployment_id] = cfg
        self._results.setdefault(deployment_id, [])
        self._status[deployment_id] = HealthStatus.UNKNOWN
        self._consecutive_success[deployment_id] = 0
        self._consecutive_failure[deployment_id] = 0
        return cfg

    def perform_check(
        self,
        deployment_id: str,
        simulated_healthy: bool = True,
        response_time_ms: float = 50.0,
        check_details: Optional[dict] = None,
    ) -> HealthCheckResult:
        """Perform a health check probe on a deployment.

        Args:
            deployment_id: The deployment to check.
            simulated_healthy: Whether to simulate a healthy response.
            response_time_ms: Simulated response time.
            check_details: Additional check details.

        Returns:
            The HealthCheckResult.
        """
        config = self._configs.get(deployment_id, HealthCheckConfig())

        # Determine if response is within timeout
        timed_out = response_time_ms > config.timeout_seconds * 1000

        # Build individual check results
        checks = check_details or {}
        checks.setdefault("endpoint_reachable", simulated_healthy and not timed_out)
        checks.setdefault("response_time_ok", not timed_out)

        # Determine status
        if timed_out:
            probe_status = HealthStatus.UNHEALTHY
        elif not simulated_healthy:
            probe_status = HealthStatus.UNHEALTHY
        elif response_time_ms > config.timeout_seconds * 500:
            probe_status = HealthStatus.DEGRADED
        else:
            probe_status = HealthStatus.HEALTHY

        result = HealthCheckResult(
            deployment_id=deployment_id,
            status=probe_status,
            response_time_ms=response_time_ms,
            checks=checks,
        )

        # Update consecutive counters
        if probe_status == HealthStatus.HEALTHY:
            self._consecutive_success[deployment_id] = (
                self._consecutive_success.get(deployment_id, 0) + 1
            )
            self._consecutive_failure[deployment_id] = 0
        else:
            self._consecutive_failure[deployment_id] = (
                self._consecutive_failure.get(deployment_id, 0) + 1
            )
            self._consecutive_success[deployment_id] = 0

        # Update overall status based on thresholds
        successes = self._consecutive_success.get(deployment_id, 0)
        failures = self._consecutive_failure.get(deployment_id, 0)

        if successes >= config.healthy_threshold:
            self._status[deployment_id] = HealthStatus.HEALTHY
        elif failures >= config.unhealthy_threshold:
            self._status[deployment_id] = HealthStatus.UNHEALTHY
        elif probe_status == HealthStatus.DEGRADED:
            self._status[deployment_id] = HealthStatus.DEGRADED

        # Store result
        self._results.setdefault(deployment_id, []).append(result)
        return result

    def get_status(self, deployment_id: str) -> HealthStatus:
        """Get the current health status of a deployment.

        Args:
            deployment_id: The deployment to query.

        Returns:
            The current HealthStatus.
        """
        return self._status.get(deployment_id, HealthStatus.UNKNOWN)

    def get_history(
        self, deployment_id: str, limit: int = 10
    ) -> list[HealthCheckResult]:
        """Get recent health check results for a deployment.

        Args:
            deployment_id: The deployment to query.
            limit: Maximum number of results to return.

        Returns:
            List of recent HealthCheckResult objects.
        """
        results = self._results.get(deployment_id, [])
        return results[-limit:]

    def get_config(self, deployment_id: str) -> Optional[HealthCheckConfig]:
        """Get the health check configuration for a deployment."""
        return self._configs.get(deployment_id)

    def remove_deployment(self, deployment_id: str) -> None:
        """Remove all health check data for a deployment."""
        self._configs.pop(deployment_id, None)
        self._results.pop(deployment_id, None)
        self._status.pop(deployment_id, None)
        self._consecutive_success.pop(deployment_id, None)
        self._consecutive_failure.pop(deployment_id, None)
