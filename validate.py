#!/usr/bin/env python3
"""
Firmware Validation CLI Entrypoint.
Automated test runner and verification suite for embedded sensor controllers.
Uses only the Python standard library (argparse, sys, os, pathlib).
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from framework.binary_resolver import resolve_target_binary
from framework.models import TestCase
from framework.runner import ValidationRunner
from framework.test_definitions import get_all_test_cases


DEFAULT_REPORT_PATH = SCRIPT_DIR / "reports" / "validation_report.json"


def parse_args():
    default_bin, _ = resolve_target_binary(repo_root=SCRIPT_DIR)
    parser = argparse.ArgumentParser(
        description="Firmware Validation Framework: Automated test suite runner for C sensor controllers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-t", "--target",
        dest="target_binary",
        default=str(default_bin),
        help="Path to the compiled sensor controller executable under test.",
    )
    parser.add_argument(
        "-s", "--suite",
        dest="suite_filter",
        default="all",
        choices=["all", "normal", "warning", "fault", "boundary", "invalid_input", "sensor_error", "execution_failure"],
        help="Select a specific test suite category to execute.",
    )
    parser.add_argument(
        "-r", "--report",
        dest="report_path",
        default=str(DEFAULT_REPORT_PATH),
        help="Destination path for writing the structured JSON validation report.",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=2.0,
        help="Execution timeout per test case in seconds.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Display verbose output including full command invocations and raw stdout/stderr.",
    )
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop test execution immediately upon the first failure.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered test cases and exit without executing.",
    )
    return parser.parse_args()


def list_test_cases(test_cases):
    print("=" * 80)
    print(" REGISTERED TEST CASES")
    print("=" * 80)
    print(f"{'ID':<14} {'CATEGORY':<16} {'NAME'}")
    print("-" * 80)
    for tc in test_cases:
        print(f"{tc.id:<14} {tc.category:<16} {tc.name}")
    print("-" * 80)
    print(f"Total: {len(test_cases)} test cases registered.")
    print("=" * 80)


def main():
    args = parse_args()
    test_cases = get_all_test_cases()

    if args.list:
        list_test_cases(test_cases)
        return 0

    target_path = Path(args.target_binary)
    if not target_path.exists():
        print(f"[FATAL ERROR] Target controller binary not found at: {target_path}", file=sys.stderr)
        print("Please compile Project 1 first or specify --target <path>", file=sys.stderr)
        return 2

    runner = ValidationRunner(
        target_binary=target_path,
        default_timeout_seconds=args.timeout,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
    )

    summary = runner.run_tests(
        test_cases=test_cases,
        category_filter=args.suite_filter,
        report_path=args.report_path,
    )

    # Return nonzero code if any tests failed or had errors
    if summary.is_successful:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
