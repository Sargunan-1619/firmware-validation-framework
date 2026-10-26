"""
Domain models, enums, and data containers for firmware validation.
Uses only the Python standard library (dataclasses, enum, typing, json).
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Union, Dict, Any


class SystemState(str, Enum):
    """Operational states defined by the C controller state machine."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    FAULT = "FAULT"


class FaultCode(str, Enum):
    """Specific fault identification codes emitted by the C controller."""
    NONE = "NONE"
    OVER_TEMP = "OVER_TEMP"
    SENSOR_UNDER_RANGE = "SENSOR_UNDER_RANGE"
    SENSOR_OVER_RANGE = "SENSOR_OVER_RANGE"
    SENSOR_DISCONNECTED = "SENSOR_DISCONNECTED"
    SENSOR_COMM_ERROR = "SENSOR_COMM_ERROR"
    SENSOR_INVALID_DATA = "SENSOR_INVALID_DATA"


class SensorStatus(str, Enum):
    """Simulated hardware telemetry status flags passed via CLI."""
    OK = "OK"
    DISCONNECTED = "DISCONNECTED"
    COMM_TIMEOUT = "COMM_TIMEOUT"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
    INVALID = "INVALID"


class TestStatus(str, Enum):
    """Evaluation status for a single test case execution."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


@dataclass
class TestCase:
    """
    Specification of a single validation test case.
    
    Attributes:
        id: Unique alphanumeric identifier (e.g. TC-NORM-01)
        name: Short human-readable title
        category: Test suite classification (normal, warning, fault, boundary, invalid, sensor_err, execution)
        description: Comprehensive explanation of test intent and physics/logic under test
        cli_args: Positional arguments to forward to the C controller executable
        expected_exit_code: Expected process return code (0: nominal/warn, 2: fault, 1: CLI error, None: any)
        expected_state: Expected SystemState enum if output parsing is anticipated
        expected_fault: Expected FaultCode enum if output parsing is anticipated
        expected_temp: Expected float value or 'INVALID' or None
        expected_stdout_pattern: Optional regex pattern expected in stdout
        expected_stderr_pattern: Optional regex pattern expected in stderr
        expect_timeout: Set to True if test explicitly expects the controller to hang/timeout
        timeout_seconds: Per-test timeout override (defaults to runner global timeout if None)
        target_override: Optional executable path override (used for testing missing/invalid binaries)
    """
    id: str
    name: str
    category: str
    description: str
    cli_args: List[str] = field(default_factory=list)
    expected_exit_code: Optional[int] = 0
    expected_state: Optional[SystemState] = None
    expected_fault: Optional[FaultCode] = None
    expected_temp: Optional[Union[float, str]] = None
    expected_stdout_pattern: Optional[str] = None
    expected_stderr_pattern: Optional[str] = None
    expect_timeout: bool = False
    timeout_seconds: Optional[float] = None
    target_override: Optional[str] = None


@dataclass
class ExecutionResult:
    """
    Direct low-level outcome of executing a target process.
    """
    command: List[str]
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    execution_error: Optional[str] = None
    parsed_state: Optional[str] = None
    parsed_temp: Optional[Union[float, str]] = None
    parsed_fault: Optional[str] = None


@dataclass
class TestResult:
    """
    High-level validation result comparing expected versus actual outcome.
    """
    test_case: TestCase
    status: TestStatus
    execution: ExecutionResult
    failure_reasons: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to JSON-serializable dictionary."""
        return {
            "id": self.test_case.id,
            "name": self.test_case.name,
            "category": self.test_case.category,
            "description": self.test_case.description,
            "cli_args": self.test_case.cli_args,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 2),
            "failure_reasons": self.failure_reasons,
            "expected": {
                "exit_code": self.test_case.expected_exit_code,
                "state": self.test_case.expected_state.value if self.test_case.expected_state else None,
                "fault": self.test_case.expected_fault.value if self.test_case.expected_fault else None,
                "temp": self.test_case.expected_temp,
                "expect_timeout": self.test_case.expect_timeout,
            },
            "actual": {
                "exit_code": self.execution.exit_code,
                "state": self.execution.parsed_state,
                "fault": self.execution.parsed_fault,
                "temp": self.execution.parsed_temp,
                "timed_out": self.execution.timed_out,
                "execution_error": self.execution.execution_error,
                "stdout": self.execution.stdout.strip(),
                "stderr": self.execution.stderr.strip(),
            }
        }


@dataclass
class ValidationSummary:
    """
    Aggregated summary of an entire test run across all test cases.
    """
    timestamp: str
    target_binary: str
    platform: str
    python_version: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    timed_out_tests: int = 0
    skipped_tests: int = 0
    total_duration_ms: float = 0.0
    results: List[TestResult] = field(default_factory=list)

    @property
    def pass_rate_percent(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return round((self.passed_tests / self.total_tests) * 100.0, 2)

    @property
    def is_successful(self) -> bool:
        return self.failed_tests == 0 and self.error_tests == 0 and self.timed_out_tests == 0

    def to_dict(self) -> Dict[str, Any]:
        """Generate structured JSON-ready representation."""
        return {
            "metadata": {
                "timestamp": self.timestamp,
                "target_binary": self.target_binary,
                "platform": self.platform,
                "python_version": self.python_version,
            },
            "statistics": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "errors": self.error_tests,
                "timed_out": self.timed_out_tests,
                "skipped": self.skipped_tests,
                "pass_rate_percent": self.pass_rate_percent,
                "total_duration_ms": round(self.total_duration_ms, 2),
                "is_successful": self.is_successful,
            },
            "test_results": [r.to_dict() for r in self.results]
        }
