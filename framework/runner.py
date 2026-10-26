"""
Test Runner: Execution orchestration engine for firmware validation test suites.
Uses only the Python standard library.
"""

from datetime import datetime, timezone
import platform
import sys
import time
from pathlib import Path
from typing import List, Optional, Union

from .assertions import AssertionEngine
from .controller_client import ControllerClient
from .models import (
    TestCase,
    TestResult,
    TestStatus,
    ValidationSummary,
)
from .reporter import ConsoleReporter, JsonReporter


class ValidationRunner:
    """
    Executes a test catalog against a target firmware controller binary.
    """

    def __init__(
        self,
        target_binary: Union[str, Path],
        default_timeout_seconds: float = 2.0,
        verbose: bool = False,
        fail_fast: bool = False,
    ):
        self.target_binary = Path(target_binary)
        self.default_timeout_seconds = default_timeout_seconds
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.client = ControllerClient(
            default_binary_path=self.target_binary,
            default_timeout_seconds=self.default_timeout_seconds,
        )

    def run_tests(
        self,
        test_cases: List[TestCase],
        category_filter: Optional[str] = None,
        report_path: Optional[Union[str, Path]] = None,
    ) -> ValidationSummary:
        """
        Execute the specified test cases and return the aggregated summary.
        
        Args:
            test_cases: List of TestCase specifications.
            category_filter: Optional category name to restrict execution (e.g. 'normal', 'boundary').
            report_path: Optional file path where JSON report will be saved.
            
        Returns:
            ValidationSummary containing complete results and metrics.
        """
        filtered_cases = test_cases
        if category_filter and category_filter.lower() != "all":
            selected = category_filter.lower()
            filtered_cases = [tc for tc in test_cases if tc.category.lower() == selected]

        ConsoleReporter.print_header(str(self.target_binary), category_filter)

        results: List[TestResult] = []
        passed_count = 0
        failed_count = 0
        error_count = 0
        timeout_count = 0
        skipped_count = len(test_cases) - len(filtered_cases)

        run_start = time.perf_counter()

        for tc in filtered_cases:
            timeout = tc.timeout_seconds if tc.timeout_seconds is not None else self.default_timeout_seconds
            execution = self.client.execute(
                cli_args=tc.cli_args,
                timeout_seconds=timeout,
                binary_override=tc.target_override,
            )

            result = AssertionEngine.evaluate(tc, execution)
            results.append(result)

            if result.status == TestStatus.PASSED:
                passed_count += 1
            elif result.status == TestStatus.FAILED:
                failed_count += 1
            elif result.status == TestStatus.TIMED_OUT:
                timeout_count += 1
            elif result.status == TestStatus.ERROR:
                error_count += 1

            ConsoleReporter.print_result_row(result, verbose=self.verbose)

            if self.fail_fast and result.status != TestStatus.PASSED:
                print(f"\n[FAIL-FAST] Halting execution early due to failure on test {tc.id}.")
                break

        total_duration_ms = (time.perf_counter() - run_start) * 1000.0

        summary = ValidationSummary(
            timestamp=datetime.now(timezone.utc).isoformat(),
            target_binary=str(self.target_binary),
            platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
            python_version=sys.version.split()[0],
            total_tests=len(filtered_cases),
            passed_tests=passed_count,
            failed_tests=failed_count,
            error_tests=error_count,
            timed_out_tests=timeout_count,
            skipped_tests=skipped_count,
            total_duration_ms=total_duration_ms,
            results=results,
        )

        ConsoleReporter.print_summary(summary)

        if report_path:
            written_file = JsonReporter.write_report(summary, report_path)
            print(f"JSON validation report saved to: {written_file}")

        return summary
