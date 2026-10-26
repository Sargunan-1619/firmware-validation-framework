"""
Unittest adapter: Bridges firmware validation test cases with Python's standard unittest library.
Enables standard test discovery via: python -m unittest
"""

import os
import unittest
from pathlib import Path
from typing import Type

from .assertions import AssertionEngine
from .controller_client import ControllerClient
from .models import TestStatus
from .test_definitions import get_all_test_cases


from .binary_resolver import resolve_target_binary


def _get_target_binary() -> Path:
    """Resolve target binary path from environment, relative repos, or scratch paths."""
    bin_path, _ = resolve_target_binary()
    return bin_path


def make_unittest_class() -> Type[unittest.TestCase]:
    """
    Dynamically generates a unittest.TestCase subclass containing individual test methods
    for each registered firmware validation test case.
    """
    target_binary = _get_target_binary()
    client = ControllerClient(default_binary_path=target_binary, default_timeout_seconds=2.0)
    test_cases = get_all_test_cases()

    methods = {}

    for tc in test_cases:
        # Create a closure binding current test case
        def create_test_method(test_case=tc):
            def test_method(self):
                timeout = test_case.timeout_seconds if test_case.timeout_seconds is not None else 2.0
                execution = client.execute(
                    cli_args=test_case.cli_args,
                    timeout_seconds=timeout,
                    binary_override=test_case.target_override,
                )
                result = AssertionEngine.evaluate(test_case, execution)
                
                if result.status != TestStatus.PASSED:
                    reasons = "\n  - " + "\n  - ".join(result.failure_reasons)
                    self.fail(
                        f"Test {test_case.id} ({test_case.name}) failed with status {result.status.value}:{reasons}\n"
                        f"Command: {' '.join(execution.command)}\n"
                        f"Stdout: {execution.stdout.strip()}\n"
                        f"Stderr: {execution.stderr.strip()}"
                    )
            return test_method

        # Method name format: test_tc_norm_01_nominal_ambient_temperature
        sanitized_name = tc.name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        sanitized_name = "".join(c for c in sanitized_name if c.isalnum() or c == "_")
        method_name = f"test_{tc.id.lower().replace('-', '_')}_{sanitized_name}"
        
        methods[method_name] = create_test_method()

    return type("FirmwareValidationTestCase", (unittest.TestCase,), methods)


# Export the generated TestCase class for unittest discovery
FirmwareValidationTestCase = make_unittest_class()
