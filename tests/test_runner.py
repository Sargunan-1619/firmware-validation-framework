"""
Unit tests for ValidationRunner orchestration and exit status contracts.
"""

import tempfile
import unittest
from pathlib import Path

from framework.models import FaultCode, SystemState, TestCase, TestStatus
from framework.runner import ValidationRunner


class TestValidationRunner(unittest.TestCase):
    """Verify runner orchestration, category filtering, and failure detection."""

    def test_runner_detects_deliberate_failure(self):
        # Create a test case that expects an impossible state
        impossible_case = TestCase(
            id="TC-DELIBERATE-FAIL",
            name="Deliberate Failure Expectation",
            category="fault",
            description="Deliberately expecting STATE_NORMAL for an 85.0°C over-temp condition",
            cli_args=["85.0"],
            expected_exit_code=0,  # Controller actually exits 2
            expected_state=SystemState.NORMAL,  # Controller actually outputs FAULT
            expected_fault=FaultCode.NONE,  # Controller actually outputs OVER_TEMP
        )

        from framework.binary_resolver import resolve_target_binary
        target_bin, exists = resolve_target_binary()
        if not exists:
            self.skipTest(f"Target sensor_controller not found at resolved path: {target_bin}")

        runner = ValidationRunner(target_binary=target_bin, default_timeout_seconds=2.0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / "fail_report.json"
            summary = runner.run_tests([impossible_case], report_path=report_file)
            
            self.assertFalse(summary.is_successful)
            self.assertEqual(summary.failed_tests, 1)
            self.assertEqual(summary.passed_tests, 0)
            self.assertEqual(summary.results[0].status, TestStatus.FAILED)
            self.assertTrue(len(summary.results[0].failure_reasons) > 0)
            self.assertTrue(report_file.exists())


if __name__ == "__main__":
    unittest.main()
