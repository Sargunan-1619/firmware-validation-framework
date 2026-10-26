"""
Unit tests for ControllerClient parsing and process handling.
"""

import sys
import unittest
from pathlib import Path

from framework.controller_client import ControllerClient


class TestControllerClient(unittest.TestCase):
    """Verify stdout parsing and execution safety."""

    def test_parse_telemetry_nominal(self):
        line = "STATE: NORMAL | TEMP: 25.00 C | FAULT: NONE"
        state, temp, fault = ControllerClient.parse_telemetry(line)
        self.assertEqual(state, "NORMAL")
        self.assertAlmostEqual(temp, 25.0, places=2)
        self.assertEqual(fault, "NONE")

    def test_parse_telemetry_warning(self):
        line = "STATE: WARNING | TEMP: 65.50 C | FAULT: NONE"
        state, temp, fault = ControllerClient.parse_telemetry(line)
        self.assertEqual(state, "WARNING")
        self.assertAlmostEqual(temp, 65.5, places=2)
        self.assertEqual(fault, "NONE")

    def test_parse_telemetry_fault_over_temp(self):
        line = "STATE: FAULT | TEMP: 85.00 C | FAULT: OVER_TEMP"
        state, temp, fault = ControllerClient.parse_telemetry(line)
        self.assertEqual(state, "FAULT")
        self.assertAlmostEqual(temp, 85.0, places=2)
        self.assertEqual(fault, "OVER_TEMP")

    def test_parse_telemetry_invalid_data(self):
        line = "STATE: FAULT | TEMP: INVALID | FAULT: SENSOR_INVALID_DATA"
        state, temp, fault = ControllerClient.parse_telemetry(line)
        self.assertEqual(state, "FAULT")
        self.assertEqual(temp, "INVALID")
        self.assertEqual(fault, "SENSOR_INVALID_DATA")

    def test_parse_telemetry_unmatched(self):
        line = "Usage: sensor_controller <temp> [status]"
        state, temp, fault = ControllerClient.parse_telemetry(line)
        self.assertIsNone(state)
        self.assertIsNone(temp)
        self.assertIsNone(fault)

    def test_missing_binary_execution(self):
        client = ControllerClient("nonexistent_binary_xyz_123.exe")
        result = client.execute(cli_args=["25.0"])
        self.assertIsNotNone(result.execution_error)
        self.assertIn("not found", result.execution_error.lower())
        self.assertIsNone(result.exit_code)

    def test_process_timeout_handling(self):
        # Execute a Python sleep command that exceeds 0.2s timeout
        py_exec = sys.executable
        client = ControllerClient(py_exec, default_timeout_seconds=0.2)
        result = client.execute(cli_args=["-c", "import time; time.sleep(1.0)"])
        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.execution_error)
        self.assertIn("timeout", result.execution_error.lower())


if __name__ == "__main__":
    unittest.main()
