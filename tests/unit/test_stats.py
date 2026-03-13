from __future__ import annotations

from nma_pool.validation.stats import chi_square_sf


def test_chi_square_sf_known_quantiles() -> None:
    # P(ChiSq_1 >= 3.8415) ~= 0.05
    assert abs(chi_square_sf(3.8415, 1) - 0.05) < 0.002
    # P(ChiSq_2 >= 5.9915) ~= 0.05
    assert abs(chi_square_sf(5.9915, 2) - 0.05) < 0.002
    # P(ChiSq_4 >= 9.4877) ~= 0.05
    assert abs(chi_square_sf(9.4877, 4) - 0.05) < 0.002

