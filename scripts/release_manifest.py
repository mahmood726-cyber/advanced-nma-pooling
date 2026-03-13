"""Generate deterministic release metadata for built distribution artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
        help="Directory containing built release artifacts.",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Release version without a leading 'v', for example '0.1.1'.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated metadata files. Defaults to --dist-dir.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dist_dir = args.dist_dir.resolve()
    output_dir = (args.output_dir or args.dist_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = _collect_artifacts(dist_dir=dist_dir, version=args.version)
    manifest = {
        "package_name": "nma-pool",
        "version": args.version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": _git_commit(dist_dir.parent),
        "artifacts": [_artifact_payload(path) for path in artifacts],
    }

    sha256_path = output_dir / "SHA256SUMS.txt"
    sha256_path.write_text(
        "".join(f"{row['sha256']}  {row['filename']}\n" for row in manifest["artifacts"]),
        encoding="utf-8",
    )

    manifest_path = output_dir / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote release checksums: {sha256_path}")
    print(f"Wrote release manifest: {manifest_path}")
    for row in manifest["artifacts"]:
        print(f"{row['filename']}: sha256={row['sha256']}")
    return 0


def _collect_artifacts(*, dist_dir: Path, version: str) -> list[Path]:
    if not dist_dir.exists():
        raise FileNotFoundError(f"Distribution directory not found: {dist_dir}")

    patterns = (
        f"nma_pool-{version}*.tar.gz",
        f"nma_pool-{version}*.whl",
    )
    artifacts = sorted(
        {
            path.resolve()
            for pattern in patterns
            for path in dist_dir.glob(pattern)
            if path.is_file()
        }
    )
    if not artifacts:
        raise FileNotFoundError(
            f"No distribution artifacts found in {dist_dir} for version {version}."
        )
    return artifacts


def _artifact_payload(path: Path) -> dict[str, Any]:
    return {
        "filename": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(repo_root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    commit = proc.stdout.strip()
    return commit or None


if __name__ == "__main__":
    raise SystemExit(main())
