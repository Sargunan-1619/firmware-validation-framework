"""
Verification script for:
- NORMAL (25.5°C)
- WARNING (60.0°C)
- FAULT (80.0°C)
- INVALID INPUT (INVALID)
Evaluated directly on the compiled C binary and through the Dashboard HTTP API.
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.binary_resolver import resolve_target_binary

def main():
    target_bin, exists = resolve_target_binary()
    print("=" * 80)
    print(f"TARGET CONTROLLER BINARY: {target_bin}")
    print(f"BINARY EXISTS           : {exists}")
    print("=" * 80)

    cases = [
        ("NORMAL (25.5°C)", ["25.5"], {"temperature": "25.5", "status": "OK"}),
        ("WARNING (60.0°C)", ["60.0"], {"temperature": "60.0", "status": "OK"}),
        ("FAULT (80.0°C)", ["80.0"], {"temperature": "80.0", "status": "OK"}),
        ("INVALID INPUT (INVALID)", ["INVALID"], {"temperature": "INVALID", "status": "INVALID"}),
    ]

    for label, args, payload in cases:
        # 1. Direct process execution of C controller
        proc = subprocess.run([str(target_bin)] + args, capture_output=True, text=True)
        
        # 2. Execution through Dashboard Web API
        req = urllib.request.Request(
            "http://127.0.0.1:8080/api/simulate-sensor",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            api_data = json.loads(resp.read().decode())

        print(f"Scenario: {label}")
        print(f"  [Direct C Subprocess] Exit Code: {proc.returncode}")
        print(f"    STDOUT : {proc.stdout.strip()}")
        if proc.stderr:
            print(f"    STDERR : {proc.stderr.strip()}")
        print(f"  [Dashboard HTTP API]  Exit Code: {api_data['exit_code']}")
        print(f"    State  : {api_data['state']}")
        print(f"    Fault  : {api_data['fault']}")
        print(f"    Temp   : {api_data['temperature']}")
        print(f"    STDOUT : {api_data['raw_stdout']}")
        print(f"    Latency: {api_data['duration_ms']} ms")
        print("-" * 80)

    verify_failure_handling(target_bin)


def verify_failure_handling(target_bin):
    print("\n" + "=" * 80)
    print("VERIFYING TEST FAILURE REPORTING & NONZERO EXIT CODES")
    print("=" * 80)

    # 1. Missing executable produces exit code 2
    res_missing = subprocess.run(
        [sys.executable, "validate.py", "--target", "nonexistent_binary.exe"],
        capture_output=True,
        text=True,
    )
    print(f"Missing Binary Exit Code : {res_missing.returncode} (Expected 2)")
    assert res_missing.returncode == 2, f"Expected 2, got {res_missing.returncode}"

    # 2. Deliberate failing test case produces status FAILED and summary is_successful=False
    from framework.models import TestCase, SystemState, FaultCode, TestStatus
    from framework.runner import ValidationRunner

    failing_case = TestCase(
        id="TC-DELIBERATE-FAIL",
        name="Deliberate Failure Expectation",
        category="fault",
        description="Expecting state NORMAL for 85°C when actual is FAULT",
        cli_args=["85.0"],
        expected_exit_code=0,             # actual is 2
        expected_state=SystemState.NORMAL, # actual is FAULT
        expected_fault=FaultCode.NONE,    # actual is OVER_TEMP
    )

    runner = ValidationRunner(target_binary=target_bin)
    summary = runner.run_tests([failing_case])
    
    print(f"Failed Test Status       : {summary.results[0].status.value} (Expected FAILED)")
    print(f"Failure Reasons          : {summary.results[0].failure_reasons}")
    print(f"Summary Is Successful    : {summary.is_successful} (Expected False)")
    print(f"Failed Count             : {summary.failed_tests} (Expected 1)")

    assert summary.results[0].status == TestStatus.FAILED
    assert not summary.is_successful
    assert summary.failed_tests == 1
    print("ALL FAILURE HANDLING ASSERTIONS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
