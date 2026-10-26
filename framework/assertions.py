"""
Assertion engine for firmware validation.
Performs deterministic comparisons between expected and actual test execution results.
"""

import math
import re
from typing import List, Tuple

from .models import ExecutionResult, TestCase, TestResult, TestStatus


class AssertionEngine:
    """
    Evaluates an ExecutionResult against a TestCase specification and generates
    detailed failure diagnostics.
    """

    @classmethod
    def evaluate(cls, test_case: TestCase, execution: ExecutionResult) -> TestResult:
        """
        Evaluate test execution against expectations.
        
        Returns:
            TestResult containing status (PASSED, FAILED, ERROR, TIMED_OUT) and reasons.
        """
        failure_reasons: List[str] = []

        # 1. Handle Execution / OS Errors (e.g. Missing binary)
        if execution.execution_error:
            # Check if this test specifically expected a missing binary or OS error
            if test_case.target_override and ("Target binary not found" in execution.execution_error or "not found" in execution.execution_error):
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.PASSED,
                    execution=execution,
                    failure_reasons=[],
                    duration_ms=execution.duration_ms,
                )
            return TestResult(
                test_case=test_case,
                status=TestStatus.ERROR,
                execution=execution,
                failure_reasons=[f"Process execution error: {execution.execution_error}"],
                duration_ms=execution.duration_ms,
            )

        # 2. Timeout Validation
        if execution.timed_out:
            if test_case.expect_timeout:
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.PASSED,
                    execution=execution,
                    failure_reasons=[],
                    duration_ms=execution.duration_ms,
                )
            else:
                return TestResult(
                    test_case=test_case,
                    status=TestStatus.TIMED_OUT,
                    execution=execution,
                    failure_reasons=[f"Unexpected timeout: process did not terminate within threshold"],
                    duration_ms=execution.duration_ms,
                )
        elif test_case.expect_timeout:
            failure_reasons.append("Expected process to time out, but it terminated normally.")

        # 3. Exit Code Verification
        if test_case.expected_exit_code is not None:
            if execution.exit_code != test_case.expected_exit_code:
                failure_reasons.append(
                    f"Exit code mismatch: expected {test_case.expected_exit_code}, got {execution.exit_code}"
                )

        # 4. System State Verification
        if test_case.expected_state is not None:
            if execution.parsed_state != test_case.expected_state.value:
                failure_reasons.append(
                    f"SystemState mismatch: expected '{test_case.expected_state.value}', got '{execution.parsed_state}'"
                )

        # 5. Fault Code Verification
        if test_case.expected_fault is not None:
            if execution.parsed_fault != test_case.expected_fault.value:
                failure_reasons.append(
                    f"FaultCode mismatch: expected '{test_case.expected_fault.value}', got '{execution.parsed_fault}'"
                )

        # 6. Temperature Telemetry Verification
        if test_case.expected_temp is not None:
            if test_case.expected_temp == "INVALID":
                if execution.parsed_temp != "INVALID":
                    failure_reasons.append(
                        f"Temperature mismatch: expected 'INVALID', got '{execution.parsed_temp}'"
                    )
            elif isinstance(test_case.expected_temp, (int, float)):
                if isinstance(execution.parsed_temp, (int, float)):
                    if not math.isclose(float(execution.parsed_temp), float(test_case.expected_temp), abs_tol=0.02):
                        failure_reasons.append(
                            f"Temperature mismatch: expected {test_case.expected_temp}°C, got {execution.parsed_temp}°C"
                        )
                else:
                    failure_reasons.append(
                        f"Temperature format mismatch: expected float {test_case.expected_temp}°C, got '{execution.parsed_temp}'"
                    )

        # 7. Stdout Pattern Match
        if test_case.expected_stdout_pattern:
            if not re.search(test_case.expected_stdout_pattern, execution.stdout):
                failure_reasons.append(
                    f"Stdout regex mismatch: pattern '{test_case.expected_stdout_pattern}' not found in '{execution.stdout.strip()}'"
                )

        # 8. Stderr Pattern Match
        if test_case.expected_stderr_pattern:
            if not re.search(test_case.expected_stderr_pattern, execution.stderr):
                failure_reasons.append(
                    f"Stderr regex mismatch: pattern '{test_case.expected_stderr_pattern}' not found in '{execution.stderr.strip()}'"
                )

        status = TestStatus.PASSED if not failure_reasons else TestStatus.FAILED

        return TestResult(
            test_case=test_case,
            status=status,
            execution=execution,
            failure_reasons=failure_reasons,
            duration_ms=execution.duration_ms,
        )
