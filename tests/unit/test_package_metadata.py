from __future__ import annotations

import nma_pool


def test_package_exposes_version_string() -> None:
    assert isinstance(nma_pool.__version__, str)
    assert nma_pool.__version__
