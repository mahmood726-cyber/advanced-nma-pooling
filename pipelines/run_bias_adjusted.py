"""Run design-stratified bias-adjusted NMA and emit JSON artifact."""

from __future__ import annotations

from pathlib import Path
import sys

# Allow direct script execution without installing the package first.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nma_pool.pipelines.bias_adjusted import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
