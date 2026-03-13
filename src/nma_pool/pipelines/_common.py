"""Shared helpers for packaged workflow entrypoints."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any


def load_json_object(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a JSON object.")
    return loaded


def write_json_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def cli_command(command: str, *args: str) -> list[str]:
    return [sys.executable, "-m", "nma_pool.cli", command, *args]


def subprocess_env_with_package_path() -> dict[str, str]:
    env = os.environ.copy()
    package_roots: list[str] = []
    seen: set[str] = set()
    for raw in sys.path:
        if not raw:
            continue
        try:
            candidate = Path(raw).resolve()
        except OSError:
            continue
        if not candidate.exists() or not (candidate / "nma_pool").exists():
            continue
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        package_roots.append(key)

    if not package_roots:
        return env

    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        os.pathsep.join([*package_roots, existing])
        if existing
        else os.pathsep.join(package_roots)
    )
    return env
