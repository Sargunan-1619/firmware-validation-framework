"""
Reporting engine for firmware validation.
Provides formatted terminal console output and serializes structured JSON reports.
Uses only the Python standard library (json, pathlib, sys, typing).
"""

import json
from pathlib import Path
from typing import Optional, TextIO
import sys

from .models import TestResult, TestStatus, ValidationSummary


class ConsoleReporter:
    """
    Renders structured, readable test execution results to standard output.
    """

    COLOR_RESET = "\033[0m"
    COLOR_GREEN = "\033[32m"
    COLOR_RED = "\033[31m"
    COLOR_YELLOW = "\033[33m"
    COLOR_CYAN = "\033[36m"
    COLOR_BOLD = "\033[1m"
    COLOR_DIM = "\033[2m"

    @classmethod
    def _use_color(cls, stream: TextIO) -> bool:
        """Determine if terminal stream supports ANSI styling."""
        return hasattr(stream, "isatty") and stream.isatty()

    @classmethod
    def print_header(cls, binary_path: str, suite_filter: Optional[str] = None):
        """Print test run banner."""
        print("=" * 80)
        print(" FIRMWARE AUTOMATED VALIDATION FRAMEWORK ")
        print("=" * 80)
        print(f" Target Executable : {binary_path}")
        if suite_filter:
            print(f" Suite Filter      : {suite_filter.upper()}")
        print("-" * 80)
        print(f"{'TEST ID':<14} {'CATEGORY':<14} {'STATUS':<10} {'TIME (ms)':<10} {'TEST NAME'}")
        print("-" * 80)

    @classmethod
    def print_result_row(cls, result: TestResult, verbose: bool = False):
        """Print a single test result row."""
        status_str = result.status.value
        use_color = cls._use_color(sys.stdout)

        if use_color:
            if result.status == TestStatus.PASSED:
                badge = f"{cls.COLOR_GREEN}[PASS]{cls.COLOR_RESET}"
            elif result.status == TestStatus.FAILED:
                badge = f"{cls.COLOR_RED}[FAIL]{cls.COLOR_RESET}"
            elif result.status == TestStatus.TIMED_OUT:
                badge = f"{cls.COLOR_YELLOW}[TIME]{cls.COLOR_RESET}"
            else:
                badge = f"{cls.COLOR_RED}[ERR ]{cls.COLOR_RESET}"
        else:
            badge = f"[{status_str[:4]}]"

        print(
            f"{result.test_case.id:<14} "
            f"{result.test_case.category:<14} "
            f"{badge:<10} "
            f"{result.duration_ms:>8.2f}  "
            f"{result.test_case.name}"
        )

        if verbose or result.status != TestStatus.PASSED:
            if result.failure_reasons:
                for reason in result.failure_reasons:
                    prefix = "    └── ERROR: " if use_color else "    * "
                    print(f"{prefix}{reason}")
            if verbose:
                cmd_str = " ".join(result.execution.command)
                print(f"        Cmd: {cmd_str}")
                if result.execution.stdout.strip():
                    print(f"        Stdout: {result.execution.stdout.strip()}")
                if result.execution.stderr.strip():
                    print(f"        Stderr: {result.execution.stderr.strip()}")

    @classmethod
    def print_summary(cls, summary: ValidationSummary):
        """Print aggregated run statistics."""
        print("-" * 80)
        use_color = cls._use_color(sys.stdout)
        
        status_label = "ALL TESTS PASSED" if summary.is_successful else "VALIDATION FAILED"
        if use_color:
            color = cls.COLOR_GREEN if summary.is_successful else cls.COLOR_RED
            status_banner = f"{color}{cls.COLOR_BOLD}{status_label}{cls.COLOR_RESET}"
        else:
            status_banner = status_label

        print(f"Result Status : {status_banner}")
        print(
            f"Test Counts   : Total: {summary.total_tests} | "
            f"Passed: {summary.passed_tests} | "
            f"Failed: {summary.failed_tests} | "
            f"Errors: {summary.error_tests} | "
            f"Timeouts: {summary.timed_out_tests}"
        )
        print(f"Pass Rate     : {summary.pass_rate_percent}%")
        print(f"Duration      : {summary.total_duration_ms:.2f} ms")
        print("=" * 80)


class JsonReporter:
    """
    Serializes test run results to standardized JSON format.
    """

    @staticmethod
    def write_report(summary: ValidationSummary, output_path: Union[str, Path]) -> Path:
        """
        Write summary dictionary to formatted JSON file.
        
        Args:
            summary: Aggregated ValidationSummary instance.
            output_path: Target JSON filepath.
            
        Returns:
            Path object to written report.
        """
        path = Path(output_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = summary.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return path
