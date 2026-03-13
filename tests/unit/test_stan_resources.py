from __future__ import annotations

import pytest

from nma_pool.models.resources import stan_model_path


def test_stan_model_path_resolves_packaged_models() -> None:
    with stan_model_path("mlnmr_continuous_fixed.stan") as path:
        assert path.name == "mlnmr_continuous_fixed.stan"
        assert path.exists()
        assert "parameters" in path.read_text(encoding="utf-8")


def test_stan_model_path_rejects_missing_model() -> None:
    with pytest.raises(FileNotFoundError, match="missing-model\\.stan"):
        with stan_model_path("missing-model.stan"):
            pass
