#!/usr/bin/env python3
"""
Dashboard Server: Lightweight standard-library HTTP server for the Firmware Validation Framework.
Serves the web dashboard, executes validation suites, and manages live C controller simulations.

Safety & Reliability:
- Strictly bound to localhost (127.0.0.1) by default.
- Strict whitelisting and input sanitization on all simulation parameters.
- Prevents arbitrary command injection and path traversal.
- Uses only Python standard library (http.server, socketserver, json, pathlib, urllib).
"""

import argparse
import json
import os
import platform
import re
import sys
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional, Tuple
from wsgiref.handlers import format_date_time
import time

# Ensure project root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from framework.binary_resolver import resolve_target_binary
from framework.controller_client import ControllerClient
from framework.runner import ValidationRunner
from framework.test_definitions import get_all_test_cases

DASHBOARD_DIR = REPO_ROOT / "dashboard"
REPORT_PATH = REPO_ROOT / "reports" / "validation_report.json"

# Whitelist for simulated status arguments
VALID_STATUS_OPTIONS = {
    "",
    "OK",
    "DISCONNECTED",
    "COMM_TIMEOUT",
    "OUT_OF_BOUNDS",
    "INVALID",
}

# Whitelist for non-numeric temperature tokens
VALID_TEMP_TOKENS = {
    "INVALID",
    "NAN",
    "INF",
    "+INF",
    "-INF",
    "ERROR",
}

# Lock to ensure only one test validation run executes at a time
VALIDATION_LOCK = threading.Lock()


from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """
    HTTP Request Handler managing static dashboard assets and REST API endpoints.
    """

    def __init__(self, *args, target_binary: Optional[Path] = None, **kwargs):
        self.target_binary = target_binary
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def log_message(self, format_str: str, *args: Any) -> None:
        """Custom concise logging format for console visibility."""
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} -> {args[2]}\n")
        sys.stdout.flush()

    def send_json_response(self, data: Dict[str, Any], status: int = 200) -> None:
        """Send formatted JSON payload with appropriate security and CORS headers."""
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, message: str, status: int = 400, details: Optional[Dict[str, Any]] = None) -> None:
        """Send standard JSON error envelope."""
        body = {
            "error": True,
            "status": status,
            "message": message,
            "details": details or {},
        }
        self.send_json_response(body, status=status)

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Route GET requests to API endpoints or static dashboard files."""
        path = self.path.split("?")[0].rstrip("/")
        if not path:
            path = "/"

        if path == "/api/status":
            self.handle_api_status()
        elif path == "/api/report":
            self.handle_api_report()
        elif path == "/api/report/download":
            self.handle_api_report_download()
        else:
            # Serve static files from dashboard directory
            super().do_GET()

    def do_POST(self) -> None:
        """Route POST requests to API endpoints."""
        path = self.path.split("?")[0].rstrip("/")

        if path == "/api/run-validation":
            self.handle_api_run_validation()
        elif path == "/api/simulate-sensor":
            self.handle_api_simulate_sensor()
        else:
            self.send_error_json(f"Endpoint not found: {path}", status=404)

    # ==========================================================================
    # API Endpoint Implementations
    # ==========================================================================

    def handle_api_status(self) -> None:
        """Return server health, resolved binary status, and latest report summary."""
        target_path, exists = resolve_target_binary(
            custom_path=str(self.target_binary) if self.target_binary else None,
            repo_root=REPO_ROOT
        )

        latest_summary = None
        report_exists = REPORT_PATH.is_file()
        if report_exists:
            try:
                with open(REPORT_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    latest_summary = {
                        "timestamp": data.get("metadata", {}).get("timestamp"),
                        "statistics": data.get("statistics", {}),
                        "target_binary": data.get("metadata", {}).get("target_binary"),
                    }
            except Exception as exc:
                latest_summary = {"error": f"Failed reading report: {exc}"}

        status_info = {
            "status": "online",
            "server_time": datetime.now().isoformat(),
            "target_binary": str(target_path),
            "binary_exists": exists,
            "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "python_version": sys.version.split()[0],
            "report_available": report_exists,
            "latest_report": latest_summary,
        }
        self.send_json_response(status_info)

    def handle_api_report(self) -> None:
        """Return the contents of the latest validation report JSON."""
        if not REPORT_PATH.is_file():
            self.send_error_json("No validation report generated yet. Run validation first.", status=404)
            return

        try:
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            self.send_json_response(report_data)
        except Exception as exc:
            self.send_error_json(f"Error reading report: {exc}", status=500)

    def handle_api_report_download(self) -> None:
        """Download the actual validation report file as an attachment."""
        if not REPORT_PATH.is_file():
            self.send_error_json("No validation report available for download.", status=404)
            return

        try:
            with open(REPORT_PATH, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", 'attachment; filename="validation_report.json"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as exc:
            self.send_error_json(f"Error downloading report: {exc}", status=500)

    def handle_api_run_validation(self) -> None:
        """Execute the real test catalog against the target C controller."""
        # Read optional JSON request body
        content_length = int(self.headers.get("Content-Length", 0))
        req_data = {}
        if content_length > 0:
            try:
                body_bytes = self.rfile.read(content_length)
                req_data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                req_data = {}

        suite_filter = req_data.get("suite", "all")

        # Resolve target binary
        target_path, exists = resolve_target_binary(
            custom_path=str(self.target_binary) if self.target_binary else None,
            repo_root=REPO_ROOT
        )

        if not exists:
            self.send_error_json(
                f"Target controller binary not found at '{target_path}'. "
                "Please compile Project 1 first (e.g. run build.ps1 in sensor-fault-controller).",
                status=503,
                details={"target_path": str(target_path)}
            )
            return

        # Acquire validation lock to prevent concurrent test executions
        if not VALIDATION_LOCK.acquire(blocking=False):
            self.send_error_json(
                "Another validation run is currently in progress. Please wait for completion.",
                status=429
            )
            return

        try:
            runner = ValidationRunner(
                target_binary=target_path,
                default_timeout_seconds=2.5,
                verbose=False,
                fail_fast=False,
            )
            all_cases = get_all_test_cases()
            summary = runner.run_tests(
                test_cases=all_cases,
                category_filter=suite_filter,
                report_path=REPORT_PATH,
            )
            self.send_json_response(summary.to_dict())
        except Exception as exc:
            self.send_error_json(f"Validation execution failed: {exc}", status=500)
        finally:
            VALIDATION_LOCK.release()

    def handle_api_simulate_sensor(self) -> None:
        """
        Interactive demonstration: Executes the real compiled C binary with validated inputs.
        Prevents arbitrary command execution and strictly sanitizes all parameters.
        """
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error_json("Missing request body.", status=400)
            return

        try:
            body_bytes = self.rfile.read(content_length)
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception as exc:
            self.send_error_json(f"Malformed JSON body: {exc}", status=400)
            return

        raw_temp = str(payload.get("temperature", "")).strip()
        raw_status = str(payload.get("status", "")).strip().upper()

        if not raw_temp:
            self.send_error_json("Missing required parameter 'temperature'.", status=400)
            return

        # 1. Strict Validation of temperature parameter
        is_token = raw_temp.upper() in VALID_TEMP_TOKENS
        is_float = False
        parsed_float_val = 0.0

        if not is_token:
            try:
                parsed_float_val = float(raw_temp)
                # Bounds check to prevent excessive numerical overflow
                if abs(parsed_float_val) > 100000.0:
                    self.send_error_json("Temperature parameter exceeds physical limits (-100000 to +100000).", status=400)
                    return
                is_float = True
            except ValueError:
                # Check if it matches alphanumeric safe test token (e.g. for testing garbage input)
                if re.match(r"^[a-zA-Z0-9_\-\.\+]{1,32}$", raw_temp):
                    is_token = True
                else:
                    self.send_error_json("Invalid temperature input format. Must be numeric or valid test token.", status=400)
                    return

        # 2. Strict Validation of status parameter
        if raw_status and raw_status not in VALID_STATUS_OPTIONS:
            self.send_error_json(
                f"Invalid status parameter '{raw_status}'. Allowed: {', '.join(sorted(VALID_STATUS_OPTIONS))}",
                status=400
            )
            return

        # 3. Resolve target binary
        target_path, exists = resolve_target_binary(
            custom_path=str(self.target_binary) if self.target_binary else None,
            repo_root=REPO_ROOT
        )

        if not exists:
            self.send_error_json(
                f"Target controller binary not found at '{target_path}'.",
                status=503,
                details={"target_path": str(target_path)}
            )
            return

        # 4. Construct CLI args safely
        cli_args = [raw_temp]
        if raw_status:
            cli_args.append(raw_status)

        # 5. Execute using ControllerClient with timeout guard
        client = ControllerClient(default_binary_path=target_path, default_timeout_seconds=2.0)
        exec_res = client.execute(cli_args=cli_args)

        # Determine human-readable state classification
        state_str = exec_res.parsed_state or ("UNKNOWN" if exec_res.exit_code == 0 else "ERROR")
        fault_str = exec_res.parsed_fault or "NONE"

        response_data = {
            "success": exec_res.execution_error is None and not exec_res.timed_out,
            "command": exec_res.command,
            "exit_code": exec_res.exit_code,
            "state": state_str,
            "fault": fault_str,
            "temperature": exec_res.parsed_temp,
            "raw_stdout": exec_res.stdout.strip(),
            "raw_stderr": exec_res.stderr.strip(),
            "duration_ms": round(exec_res.duration_ms, 2),
            "timed_out": exec_res.timed_out,
            "execution_error": exec_res.execution_error,
            "is_normal": state_str == "NORMAL",
            "is_warning": state_str == "WARNING",
            "is_fault": state_str == "FAULT" or exec_res.exit_code == 2,
            "simulated_telemetry_notice": "Inputs executed directly by compiled C controller in safe user mode."
        }
        self.send_json_response(response_data)


def run_server(host: str = "127.0.0.1", port: int = 8080, target_binary: Optional[str] = None):
    """Start the dashboard HTTP server."""
    target_path = Path(target_binary) if target_binary else None
    handler_factory = lambda *args, **kwargs: DashboardRequestHandler(*args, target_binary=target_path, **kwargs)

    server = ThreadingHTTPServer((host, port), handler_factory)
    print("=" * 80)
    print(" FIRMWARE VALIDATION FRAMEWORK - WEB DASHBOARD ")
    print("=" * 80)
    print(f" Server URL       : http://{host}:{port}")
    resolved_path, exists = resolve_target_binary(custom_path=target_binary, repo_root=REPO_ROOT)
    print(f" Target Binary    : {resolved_path}")
    print(f" Binary Status    : {'AVAILABLE (Found)' if exists else 'NOT FOUND (Check Project 1 build)'}")
    print(f" Root Directory   : {DASHBOARD_DIR}")
    print("-" * 80)
    print(" Press Ctrl+C to stop the dashboard server.")
    print("=" * 80)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Stopping server...")
    finally:
        server.server_close()
        print("[INFO] Server shutdown complete.")


def parse_args():
    default_host = os.environ.get("HOST", "127.0.0.1")
    default_port = int(os.environ.get("PORT", 8080))
    parser = argparse.ArgumentParser(
        description="Launch the Firmware Validation Web Dashboard server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=default_host, help="Host interface to bind (defaults to localhost).")
    parser.add_argument("--port", type=int, default=default_port, help="Port to listen on.")
    parser.add_argument("--target", default=None, help="Explicit path to sensor_controller executable.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_server(host=args.host, port=args.port, target_binary=args.target)
