"""Install-safe accessors for packaged model resources."""

from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator


@contextmanager
def stan_model_path(filename: str) -> Iterator[Path]:
    """Yield a filesystem path for a packaged Stan model file."""

    resource = files("nma_pool.models").joinpath("stan", filename)
    if not resource.is_file():
        raise FileNotFoundError(
            f"Stan model file missing from installed package: nma_pool.models/stan/{filename}"
        )
    with as_file(resource) as path:
        yield path
