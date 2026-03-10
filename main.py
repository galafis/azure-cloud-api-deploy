"""Demo script for the Cloud API Deployment Management System.

Demonstrates deployment management with versioning, deployment strategies
(blue-green, canary, rolling), health monitoring, and environment management.
"""

from src.deploy.manager import DeploymentManager
from src.deploy.strategies import BlueGreenStrategy, CanaryStrategy, RollingStrategy
from src.deploy.health_checker import HealthChecker, HealthCheckConfig
from src.environments.env_manager import EnvironmentManager


def print_separator() -> None:
    """Print a visual separator line."""
    print("=" * 60)


def demo_environment_management() -> None:
    """Demonstrate environment setup and promotion."""
    print_separator()
    print("ENVIRONMENT MANAGEMENT DEMO")
    print_separator()

    env_mgr = EnvironmentManager()
    environments = env_mgr.setup_default_environments()

    print("\nEnvironments created:")
    for env in environments:
        protection = " [PROTECTED]" if env.protected else ""
        print(f"  {env.name:10s} - {env.display_name}{protection}")
        print(f"             Replicas: {env.config.get('replicas', 'N/A')}")

    # Promote through environments
    print("\n--- Promotion Workflow ---")
    result = env_mgr.promote("my-api", "1.0.0", "dev", "staging", promoted_by="gabriel")
    print(f"  {result['message']}")

    result = env_mgr.promote("my-api", "1.0.0", "staging", "prod", promoted_by="gabriel")
    print(f"  {result['message']}")

    result = env_mgr.promote("my-api", "1.0.0", "staging", "prod", promoted_by="gabriel", approved=True)
    print(f"  {result['message']}")

    # Show promotion history
    history = env_mgr.get_promotion_history(app_name="my-api")
    print(f"\nPromotion history ({len(history)} records):")
    for record in history:
        print(f"  {record.source_env} -> {record.target_env}: {record.app_name}:{record.version}")
    print()


def demo_deployment_strategies() -> None:
    """Demonstrate different deployment strategies."""
    print_separator()
    print("DEPLOYMENT STRATEGIES DEMO")
    print_separator()

    # Blue-Green
    print("\n--- Blue-Green Strategy ---")
    bg = BlueGreenStrategy()
    result = bg.execute("my-api", "2.0.0", health_check_passed=True)
    print(f"  Result: {result['message']}")
    print(f"  Active slot: {result['active_slot']}")
    for step in result["steps"]:
        print(f"  Step {step['step_number']}: {step['action']} [{step['status']}]")

    # Canary
    print("\n--- Canary Strategy ---")
    canary = CanaryStrategy(increments=[10, 25, 50, 100])
    result = canary.execute("my-api", "2.1.0")
    print(f"  Result: {result['message']}")
    for step in result["steps"]:
        print(f"  Step {step['step_number']}: {step['action']} [{step['status']}]")

    # Canary with failure
    print("\n--- Canary Strategy (with failure) ---")
    canary2 = CanaryStrategy(increments=[10, 25, 50, 100])
    result = canary2.execute("my-api", "2.1.1", failure_at_pct=50)
    print(f"  Result: {result['message']}")

    # Rolling
    print("\n--- Rolling Strategy ---")
    rolling = RollingStrategy(batch_size=2)
    result = rolling.execute("my-api", "2.2.0", total_replicas=6)
    print(f"  Result: {result['message']}")
    for step in result["steps"]:
        print(f"  Step {step['step_number']}: {step['action']} [{step['status']}]")
    print()


def demo_health_monitoring() -> None:
    """Demonstrate health check monitoring."""
    print_separator()
    print("HEALTH CHECK MONITORING DEMO")
    print_separator()

    checker = HealthChecker()
    deploy_id = "deploy-001"

    config = HealthCheckConfig(
        endpoint="/health",
        interval_seconds=10,
        timeout_seconds=5,
        healthy_threshold=3,
        unhealthy_threshold=2,
    )
    checker.configure(deploy_id, config)

    # Simulate health checks
    print("\nPerforming health checks:")
    for i in range(5):
        healthy = i != 3  # Simulate one unhealthy check
        result = checker.perform_check(
            deploy_id, simulated_healthy=healthy, response_time_ms=30.0 + i * 10
        )
        print(f"  Check {i+1}: {result.status.value} ({result.response_time_ms}ms)")

    overall = checker.get_status(deploy_id)
    print(f"\nOverall status: {overall.value}")

    history = checker.get_history(deploy_id, limit=5)
    print(f"Check history: {len(history)} records")
    print()


def demo_deployment_lifecycle() -> None:
    """Demonstrate full deployment lifecycle."""
    print_separator()
    print("DEPLOYMENT LIFECYCLE DEMO")
    print_separator()

    mgr = DeploymentManager()

    # Create deployment
    deploy = mgr.create_deployment(
        app_name="my-api",
        version="1.0.0",
        environment="dev",
        image="myregistry.azurecr.io/my-api:1.0.0",
        strategy="rolling",
        replicas=3,
    )
    print(f"\nDeployment created: {deploy.id[:8]}...")
    print(f"  App: {deploy.app_name}")
    print(f"  Version: {deploy.current_version}")
    print(f"  Environment: {deploy.environment}")

    # Complete deployment
    mgr.complete_deployment(deploy.id)
    print(f"  Status: {deploy.status.value}")

    # Update to new version
    mgr.update_deployment(
        deploy.id,
        version="1.1.0",
        image="myregistry.azurecr.io/my-api:1.1.0",
    )
    print(f"\n  Updated to: {deploy.current_version}")
    print(f"  Previous: {deploy.previous_version}")

    # Rollback
    mgr.rollback_deployment(deploy.id)
    print(f"  After rollback: {deploy.current_version}")
    print(f"  Status: {deploy.status.value}")

    # Version history
    history = mgr.get_version_history(deploy.id)
    print(f"\n  Version history ({len(history)} versions):")
    for ver in history:
        print(f"    {ver.version} - {ver.image}")
    print()


def main() -> None:
    """Run all demo functions."""
    print("\n  CLOUD API DEPLOYMENT MANAGEMENT SYSTEM")
    print("  Sistema de Gerenciamento de Deploy na Nuvem\n")

    demo_environment_management()
    demo_deployment_strategies()
    demo_health_monitoring()
    demo_deployment_lifecycle()

    print_separator()
    print("Demo complete / Demo concluida")
    print_separator()


if __name__ == "__main__":
    main()
