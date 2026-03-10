"""Tests for the cloud deployment management system."""

import unittest

from src.deploy.manager import DeploymentManager, DeploymentStatus
from src.deploy.strategies import BlueGreenStrategy, CanaryStrategy, RollingStrategy
from src.deploy.health_checker import HealthChecker, HealthCheckConfig, HealthStatus
from src.environments.env_manager import EnvironmentManager


class TestDeploymentManager(unittest.TestCase):
    """Test deployment CRUD and lifecycle operations."""

    def setUp(self):
        self.mgr = DeploymentManager()

    def test_create_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0", environment="dev")
        self.assertEqual(deploy.app_name, "app")
        self.assertEqual(deploy.current_version, "1.0.0")
        self.assertEqual(deploy.status, DeploymentStatus.PENDING)

    def test_get_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        result = self.mgr.get_deployment(deploy.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, deploy.id)

    def test_get_nonexistent_deployment(self):
        self.assertIsNone(self.mgr.get_deployment("fake"))

    def test_list_deployments(self):
        self.mgr.create_deployment("app1", "1.0.0")
        self.mgr.create_deployment("app2", "1.0.0")
        deployments = self.mgr.list_deployments()
        self.assertEqual(len(deployments), 2)

    def test_list_by_app_name(self):
        self.mgr.create_deployment("app1", "1.0.0")
        self.mgr.create_deployment("app2", "1.0.0")
        deployments = self.mgr.list_deployments(app_name="app1")
        self.assertEqual(len(deployments), 1)

    def test_update_deployment_version(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.mgr.update_deployment(deploy.id, "2.0.0")
        self.assertEqual(deploy.current_version, "2.0.0")
        self.assertEqual(deploy.previous_version, "1.0.0")
        self.assertEqual(len(deploy.versions), 2)

    def test_complete_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.mgr.complete_deployment(deploy.id)
        self.assertEqual(deploy.status, DeploymentStatus.SUCCEEDED)

    def test_fail_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.mgr.fail_deployment(deploy.id, "Out of memory")
        self.assertEqual(deploy.status, DeploymentStatus.FAILED)
        self.assertEqual(deploy.error_message, "Out of memory")

    def test_rollback_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.mgr.update_deployment(deploy.id, "2.0.0")
        self.mgr.rollback_deployment(deploy.id)
        self.assertEqual(deploy.current_version, "1.0.0")
        self.assertEqual(deploy.status, DeploymentStatus.ROLLED_BACK)

    def test_rollback_no_previous_version(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        result = self.mgr.rollback_deployment(deploy.id)
        self.assertIsNone(result)

    def test_cancel_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        result = self.mgr.cancel_deployment(deploy.id)
        self.assertIsNotNone(result)
        self.assertEqual(deploy.status, DeploymentStatus.CANCELLED)

    def test_cancel_completed_fails(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.mgr.complete_deployment(deploy.id)
        result = self.mgr.cancel_deployment(deploy.id)
        self.assertIsNone(result)

    def test_delete_deployment(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.assertTrue(self.mgr.delete_deployment(deploy.id))
        self.assertIsNone(self.mgr.get_deployment(deploy.id))

    def test_version_history(self):
        deploy = self.mgr.create_deployment("app", "1.0.0")
        self.mgr.update_deployment(deploy.id, "1.1.0")
        self.mgr.update_deployment(deploy.id, "1.2.0")
        history = self.mgr.get_version_history(deploy.id)
        self.assertEqual(len(history), 3)


class TestBlueGreenStrategy(unittest.TestCase):
    """Test blue-green deployment strategy."""

    def test_successful_deployment(self):
        bg = BlueGreenStrategy()
        result = bg.execute("app", "1.0.0", health_check_passed=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["active_slot"], "green")

    def test_failed_health_check(self):
        bg = BlueGreenStrategy()
        result = bg.execute("app", "1.0.0", health_check_passed=False)
        self.assertFalse(result["success"])
        self.assertEqual(result["active_slot"], "blue")

    def test_rollback(self):
        bg = BlueGreenStrategy()
        bg.execute("app", "1.0.0")
        result = bg.rollback()
        self.assertTrue(result["success"])
        self.assertEqual(result["active_slot"], "blue")

    def test_steps_recorded(self):
        bg = BlueGreenStrategy()
        result = bg.execute("app", "1.0.0")
        self.assertGreater(len(result["steps"]), 0)


class TestCanaryStrategy(unittest.TestCase):
    """Test canary deployment strategy."""

    def test_successful_deployment(self):
        canary = CanaryStrategy(increments=[25, 50, 100])
        result = canary.execute("app", "1.0.0")
        self.assertTrue(result["success"])
        self.assertEqual(result["current_traffic_pct"], 100)

    def test_failed_deployment(self):
        canary = CanaryStrategy(increments=[10, 25, 50, 100])
        result = canary.execute("app", "1.0.0", failure_at_pct=50)
        self.assertFalse(result["success"])

    def test_custom_increments(self):
        canary = CanaryStrategy(increments=[5, 10, 20, 50, 100])
        result = canary.execute("app", "1.0.0")
        self.assertEqual(len(result["steps"]), 5)


class TestRollingStrategy(unittest.TestCase):
    """Test rolling deployment strategy."""

    def test_successful_deployment(self):
        rolling = RollingStrategy(batch_size=2)
        result = rolling.execute("app", "1.0.0", total_replicas=4)
        self.assertTrue(result["success"])
        self.assertEqual(result["updated_count"], 4)

    def test_failed_deployment(self):
        rolling = RollingStrategy(batch_size=1)
        result = rolling.execute("app", "1.0.0", total_replicas=3, failure_at_batch=2)
        self.assertFalse(result["success"])
        self.assertEqual(result["updated_count"], 1)

    def test_batch_calculation(self):
        rolling = RollingStrategy(batch_size=3)
        result = rolling.execute("app", "1.0.0", total_replicas=7)
        # 7 replicas / batch_size 3 = 3 batches (3+3+1)
        self.assertEqual(len(result["steps"]), 3)


class TestHealthChecker(unittest.TestCase):
    """Test health check monitoring."""

    def setUp(self):
        self.checker = HealthChecker()
        self.deploy_id = "test-deploy"
        self.checker.configure(self.deploy_id)

    def test_initial_status_unknown(self):
        self.assertEqual(self.checker.get_status(self.deploy_id), HealthStatus.UNKNOWN)

    def test_healthy_after_threshold(self):
        config = HealthCheckConfig(healthy_threshold=2)
        self.checker.configure(self.deploy_id, config)
        self.checker.perform_check(self.deploy_id, simulated_healthy=True)
        self.checker.perform_check(self.deploy_id, simulated_healthy=True)
        self.assertEqual(self.checker.get_status(self.deploy_id), HealthStatus.HEALTHY)

    def test_unhealthy_after_threshold(self):
        config = HealthCheckConfig(unhealthy_threshold=2)
        self.checker.configure(self.deploy_id, config)
        self.checker.perform_check(self.deploy_id, simulated_healthy=False)
        self.checker.perform_check(self.deploy_id, simulated_healthy=False)
        self.assertEqual(self.checker.get_status(self.deploy_id), HealthStatus.UNHEALTHY)

    def test_check_history(self):
        self.checker.perform_check(self.deploy_id)
        self.checker.perform_check(self.deploy_id)
        history = self.checker.get_history(self.deploy_id)
        self.assertEqual(len(history), 2)

    def test_remove_deployment(self):
        self.checker.perform_check(self.deploy_id)
        self.checker.remove_deployment(self.deploy_id)
        self.assertEqual(self.checker.get_status(self.deploy_id), HealthStatus.UNKNOWN)


class TestEnvironmentManager(unittest.TestCase):
    """Test environment management."""

    def setUp(self):
        self.env_mgr = EnvironmentManager()
        self.env_mgr.setup_default_environments()

    def test_setup_creates_three_envs(self):
        envs = self.env_mgr.list_environments()
        self.assertEqual(len(envs), 3)

    def test_prod_is_protected(self):
        prod = self.env_mgr.get_environment("prod")
        self.assertTrue(prod.protected)

    def test_dev_has_debug(self):
        dev = self.env_mgr.get_environment("dev")
        self.assertTrue(dev.config.get("debug"))

    def test_promote_dev_to_staging(self):
        result = self.env_mgr.promote("app", "1.0.0", "dev", "staging")
        self.assertTrue(result["success"])

    def test_promote_to_prod_requires_approval(self):
        result = self.env_mgr.promote("app", "1.0.0", "staging", "prod")
        self.assertFalse(result["success"])
        self.assertTrue(result.get("requires_approval"))

    def test_promote_to_prod_with_approval(self):
        result = self.env_mgr.promote("app", "1.0.0", "staging", "prod", approved=True)
        self.assertTrue(result["success"])

    def test_cannot_promote_backwards(self):
        result = self.env_mgr.promote("app", "1.0.0", "prod", "dev")
        self.assertFalse(result["success"])

    def test_update_config_merge(self):
        self.env_mgr.update_config("dev", {"new_key": "value"})
        dev = self.env_mgr.get_environment("dev")
        self.assertIn("new_key", dev.config)
        self.assertIn("debug", dev.config)

    def test_deactivate_environment(self):
        self.env_mgr.deactivate_environment("staging")
        staging = self.env_mgr.get_environment("staging")
        self.assertFalse(staging.active)

    def test_promotion_history(self):
        self.env_mgr.promote("app", "1.0.0", "dev", "staging")
        self.env_mgr.promote("app", "1.0.0", "staging", "prod", approved=True)
        history = self.env_mgr.get_promotion_history()
        self.assertEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
