"""
Unit tests for the AssertionEngine and failure reporting.
"""

import unittest
from framework.assertions import AssertionEngine
from framework.models import (
    ExecutionResult,
    FaultCode,
    SystemState,
    TestCase,
    TestStatus,
)


class TestAssertionEngine(unittest.TestCase):
    """Verify that AssertionEngine detects matches and discrepancies accurately."""

    def setUp(self):
        self.base_case = TestCase(
            id="TC-UNIT-01",
            name="Sample Test Case",
            category="normal",
            description="Unit test verification",
            cli_args=["25.0"],
            expected_exit_code=0,
            expected_state=SystemState.NORMAL,
            expected_fault=FaultCode.NONE,
            expected_temp=25.0,
        )

    def test_perfect_match(self):
        execution = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=0,
            stdout="STATE: NORMAL | TEMP: 25.00 C | FAULT: NONE\n",
            stderr="",
            duration_ms=15.0,
            parsed_state="NORMAL",
            parsed_temp=25.0,
            parsed_fault="NONE",
        )
        result = AssertionEngine.evaluate(self.base_case, execution)
        self.assertEqual(result.status, TestStatus.PASSED)
        self.assertEqual(len(result.failure_reasons), 0)

    def test_exit_code_mismatch(self):
        execution = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=2,  # Expected 0
            stdout="STATE: NORMAL | TEMP: 25.00 C | FAULT: NONE\n",
            stderr="",
            duration_ms=15.0,
            parsed_state="NORMAL",
            parsed_temp=25.0,
            parsed_fault="NONE",
        )
        result = AssertionEngine.evaluate(self.base_case, execution)
        self.assertEqual(result.status, TestStatus.FAILED)
        self.assertTrue(any("Exit code mismatch" in r for r in result.failure_reasons))

    def test_state_mismatch(self):
        execution = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=0,
            stdout="STATE: WARNING | TEMP: 25.00 C | FAULT: NONE\n",
            stderr="",
            duration_ms=15.0,
            parsed_state="WARNING",  # Expected NORMAL
            parsed_temp=25.0,
            parsed_fault="NONE",
        )
        result = AssertionEngine.evaluate(self.base_case, execution)
        self.assertEqual(result.status, TestStatus.FAILED)
        self.assertTrue(any("SystemState mismatch" in r for r in result.failure_reasons))

    def test_fault_code_mismatch(self):
        execution = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=0,
            stdout="STATE: NORMAL | TEMP: 25.00 C | FAULT: OVER_TEMP\n",
            stderr="",
            duration_ms=15.0,
            parsed_state="NORMAL",
            parsed_temp=25.0,
            parsed_fault="OVER_TEMP",  # Expected NONE
        )
        result = AssertionEngine.evaluate(self.base_case, execution)
        self.assertEqual(result.status, TestStatus.FAILED)
        self.assertTrue(any("FaultCode mismatch" in r for r in result.failure_reasons))

    def test_temperature_mismatch(self):
        execution = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=0,
            stdout="STATE: NORMAL | TEMP: 50.00 C | FAULT: NONE\n",
            stderr="",
            duration_ms=15.0,
            parsed_state="NORMAL",
            parsed_temp=50.0,  # Expected 25.0
            parsed_fault="NONE",
        )
        result = AssertionEngine.evaluate(self.base_case, execution)
        self.assertEqual(result.status, TestStatus.FAILED)
        self.assertTrue(any("Temperature mismatch" in r for r in result.failure_reasons))

    def test_unexpected_timeout(self):
        execution = ExecutionResult(
            command=["sensor_controller.exe", "25.0"],
            exit_code=None,
            stdout="",
            stderr="",
            duration_ms=2000.0,
            timed_out=True,
        )
        result = AssertionEngine.evaluate(self.base_case, execution)
        self.assertEqual(result.status, TestStatus.TIMED_OUT)
        self.assertTrue(any("Unexpected timeout" in r for r in result.failure_reasons))

    def test_expected_timeout(self):
        timeout_case = TestCase(
            id="TC-TIME-01",
            name="Expected Timeout Case",
            category="execution_failure",
            description="Process must exceed time bound",
            cli_args=[],
            expect_timeout=True,
        )
        execution = ExecutionResult(
            command=["test_cmd"],
            exit_code=None,
            stdout="",
            stderr="",
            duration_ms=2000.0,
            timed_out=True,
        )
        result = AssertionEngine.evaluate(timeout_case, execution)
        self.assertEqual(result.status, TestStatus.PASSED)


if __name__ == "__main__":
    unittest.main()
