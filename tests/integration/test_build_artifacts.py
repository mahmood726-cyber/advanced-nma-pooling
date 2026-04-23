from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_built_wheel_contains_cli_entrypoint_and_stan_assets(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_release_artifacts.py",
            "--outdir",
            str(tmp_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr

    wheel_path = next(tmp_path.glob("nma_pool-*.whl"))
    sdist_path = next(tmp_path.glob("nma_pool-*.tar.gz"))
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        assert "nma_pool/models/stan/mlnmr_continuous_fixed.stan" in names
        assert "nma_pool/models/stan/bias_adjusted_normal_fixed.stan" in names
        entry_points_name = next(
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        )
        entry_points = wheel.read(entry_points_name).decode("utf-8")

    assert "nma-pool = nma_pool.cli:main" in entry_points

    manifest_proc = subprocess.run(
        [
            sys.executable,
            "scripts/release_manifest.py",
            "--dist-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path),
            "--version",
            "0.1.1",
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=False,
        capture_output=True,
        text=True,
    )
    assert manifest_proc.returncode == 0, manifest_proc.stderr

    sums_path = tmp_path / "SHA256SUMS.txt"
    manifest_path = tmp_path / "release-manifest.json"
    assert sums_path.exists()
    assert manifest_path.exists()
    sums_text = sums_path.read_text(encoding="utf-8")
    assert wheel_path.name in sums_text
    assert sdist_path.name in sums_text
