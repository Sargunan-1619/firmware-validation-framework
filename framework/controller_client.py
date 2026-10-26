"""
Controller Client: Subprocess abstraction layer for invoking and parsing C firmware executables.
Strictly relies on Python standard library modules (subprocess, time, re, pathlib, typing).
"""

import os
import re
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .models import ExecutionResult


# Regular expression matching the standard C controller output format:
# Example: "STATE: NORMAL | TEMP: 25.00 C | FAULT: NONE"
# Example: "STATE: FAULT | TEMP: INVALID | FAULT: SENSOR_INVALID_DATA"
OUTPUT_PATTERN = re.compile(
    r"STATE:\s+(?P<state>[A-Z_]+)\s+\|\s+TEMP:\s+(?P<temp>[^\s|]+(?:\s+C)?)\s+\|\s+FAULT:\s+(?P<fault>[A-Z_]+)",
    re.MULTILINE
)


class ControllerClient:
    """
    Manages process execution, timeout bounds, and output parsing for the C firmware executable.
    """

    def __init__(self, default_binary_path: Union[str, Path], default_timeout_seconds: float = 2.0):
        """
        Initialize the controller client.
        
        Args:
            default_binary_path: Default absolute or relative path to the compiled executable.
            default_timeout_seconds: Maximum allowed execution duration before SIGKILL / Terminate.
        """
        self.default_binary_path = Path(default_binary_path)
        self.default_timeout_seconds = default_timeout_seconds

    def execute(
        self,
        cli_args: List[str],
        timeout_seconds: Optional[float] = None,
        binary_override: Optional[Union[str, Path]] = None,
    ) -> ExecutionResult:
        """
        Execute the C controller executable as a child process and capture full execution telemetry.
        
        Args:
            cli_args: Command-line arguments to pass to the controller.
            timeout_seconds: Per-execution timeout (defaults to self.default_timeout_seconds).
            binary_override: Optional path override for failure/missing-binary testing.
            
        Returns:
            ExecutionResult containing returncode, stdout, stderr, timing, and parsed telemetry.
        """
        target_path = Path(binary_override) if binary_override else self.default_binary_path
        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds
        
        cmd = [str(target_path)] + [str(arg) for arg in cli_args]

        start_time = time.perf_counter()
        exit_code: Optional[int] = None
        stdout = ""
        stderr = ""
        timed_out = False
        exec_error: Optional[str] = None

        try:
            # Execute child process defensively
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            exit_code = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout or "" if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr or "" if isinstance(exc.stderr, str) else ""
            exec_error = f"Process execution exceeded timeout threshold ({timeout}s)"
            
        except FileNotFoundError as exc:
            exec_error = f"Target binary not found: {target_path} ({exc})"
            
        except PermissionError as exc:
            exec_error = f"Permission denied executing target: {target_path} ({exc})"
            
        except OSError as exc:
            exec_error = f"Operating system error during execution: {exc}"
            
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Parse telemetry fields if process produced formatted stdout
        parsed_state, parsed_temp, parsed_fault = self.parse_telemetry(stdout)

        return ExecutionResult(
            command=cmd,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
            execution_error=exec_error,
            parsed_state=parsed_state,
            parsed_temp=parsed_temp,
            parsed_fault=parsed_fault,
        )

    @staticmethod
    def parse_telemetry(stdout_text: str) -> Tuple[Optional[str], Optional[Union[float, str]], Optional[str]]:
        """
        Extract structured state, temperature, and fault tokens from process stdout.
        
        Returns:
            (state, temp, fault) tuple, or (None, None, None) if pattern doesn't match.
        """
        match = OUTPUT_PATTERN.search(stdout_text)
        if not match:
            return None, None, None

        state = match.group("state")
        raw_temp = match.group("temp").strip()
        fault = match.group("fault")

        parsed_temp: Optional[Union[float, str]] = None
        if raw_temp.endswith(" C"):
            numeric_part = raw_temp[:-2].strip()
            try:
                parsed_temp = float(numeric_part)
            except ValueError:
                parsed_temp = raw_temp
        elif raw_temp == "INVALID":
            parsed_temp = "INVALID"
        else:
            try:
                parsed_temp = float(raw_temp)
            except ValueError:
                parsed_temp = raw_temp

        return state, parsed_temp, fault
