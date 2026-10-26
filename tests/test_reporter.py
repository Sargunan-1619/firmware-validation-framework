"""
Unit tests for report generation and JSON serialization.
"""

import json
import tempfile
import unittest
from pathlib import Path

from framework.models import (
    ExecutionResult,
    FaultCode,
    SystemState,
    TestCase,
    TestResult,
    TestStatus,
    ValidationSummary,
)
from framework.reporter import JsonReporter


class TestReporter(unittest.TestCase):
    """Verify JSON structure and serialization fidelity."""

    def test_json_report_generation(self):
        tc = TestCase(
            id="TC-REP-01",
            name="Report Serialization Test",
            category="normal",
            description="Verify JSON dump",
            cli_args=["25.0"],
            expected_exit_code=0,
            expected_state=SystemState.NORMAL,
            expected_fault=FaultCode.NONE,
            expected_temp=25.0,
        )
        exec_res = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=0,
            stdout="STATE: NORMAL | TEMP: 25.00 C | FAULT: NONE\n",
            stderr="",
            duration_ms=12.5,
            parsed_state="NORMAL",
            parsed_temp=25.0,
            parsed_fault="NONE",
        )
        test_res = TestResult(
            test_case=tc,
            status=TestStatus.PASSED,
            execution=exec_res,
            failure_reasons=[],
            duration_ms=12.5,
        )
        summary = ValidationSummary(
            timestamp="2026-10-26T12:00:00Z",
            target_binary="sensor_controller.exe",
            platform="TestOS",
            python_version="3.14.0",
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            error_tests=0,
            timed_out_tests=0,
            skipped_tests=0,
            total_duration_ms=12.5,
            results=[test_res],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_report.json"
            written = JsonReporter.write_report(summary, out_file)
            self.assertTrue(written.exists())

            with open(written, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertIn("metadata", data)
            self.assertIn("statistics", data)
            self.assertIn("test_results", data)
            self.assertEqual(data["statistics"]["total"], 1)
            self.assertEqual(data["statistics"]["passed"], 1)
            self.assertEqual(data["statistics"]["pass_rate_percent"], 100.0)
            self.assertEqual(len(data["test_results"]), 1)
            self.assertEqual(data["test_results"][0]["id"], "TC-REP-01")


if __name__ == "__main__":
    unittest.main()
