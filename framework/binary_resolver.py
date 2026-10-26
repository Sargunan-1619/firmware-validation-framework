"""
Binary Resolver: Dynamically locates the target C sensor controller executable.
Supports relative paths, environment variable overrides, and cross-platform naming.
Zero external dependencies (os, sys, pathlib).
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def get_candidate_paths(repo_root: Optional[Path] = None) -> List[Path]:
    """
    Generate an ordered list of candidate paths where the target binary may reside.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    exe_names = ["sensor_controller.exe", "sensor_controller"] if sys.platform == "win32" else ["sensor_controller", "sensor_controller.exe"]

    candidates: List[Path] = []

    # 1. Environment variable override
    env_target = os.environ.get("SENSOR_CONTROLLER_BIN")
    if env_target:
        candidates.append(Path(env_target))

    # 2. Relative peer directories (side-by-side git clones)
    peer_dir_names = [
        "sensor-fault-controller",
        "sensor_fault_controller",
        "sensor-controller",
    ]
    for peer in peer_dir_names:
        for name in exe_names:
            candidates.append(repo_root.parent / peer / "build" / name)
            candidates.append(repo_root.parent / peer / name)

    # 3. Inside current repository (if placed locally)
    for name in exe_names:
        candidates.append(repo_root / "build" / name)
        candidates.append(repo_root / name)

    # 4. Known local user scratch location
    scratch_dir = Path.home() / ".gemini" / "antigravity-ide" / "scratch" / "sensor_fault_controller" / "build"
    for name in exe_names:
        candidates.append(scratch_dir / name)

    return candidates


def resolve_target_binary(custom_path: Optional[str] = None, repo_root: Optional[Path] = None) -> Tuple[Path, bool]:
    """
    Resolve the path to the C controller executable.
    
    Args:
        custom_path: Explicit user-specified binary path.
        repo_root: Optional root path of this repository.
        
    Returns:
        Tuple of (resolved_path, exists_boolean).
    """
    if custom_path:
        p = Path(custom_path).resolve()
        return p, p.is_file()

    candidates = get_candidate_paths(repo_root)
    for c in candidates:
        if c.is_file():
            return c.resolve(), True

    # If none found, return the most intuitive relative path
    default_root = repo_root or Path(__file__).resolve().parent.parent
    fallback_name = "sensor_controller.exe" if sys.platform == "win32" else "sensor_controller"
    fallback_path = default_root.parent / "sensor-fault-controller" / "build" / fallback_name
    return fallback_path, False
