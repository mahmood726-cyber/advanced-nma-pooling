"""Statistical helpers for diagnostics and benchmarks."""

from __future__ import annotations

import math


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def normal_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def two_sided_p_from_z(z: float) -> float:
    return min(1.0, max(0.0, 2.0 * normal_sf(abs(z))))


def chi_square_sf_approx(x: float, df: int) -> float:
    """Approximate chi-square survival function using Wilson-Hilferty."""
    if df <= 0:
        return 1.0
    if x <= 0:
        return 1.0
    ratio = x / float(df)
    z = (
        (ratio ** (1.0 / 3.0)) - (1.0 - (2.0 / (9.0 * df)))
    ) / math.sqrt(2.0 / (9.0 * df))
    return min(1.0, max(0.0, normal_sf(z)))


def chi_square_sf(x: float, df: int) -> float:
    """Exact chi-square survival function via regularized upper incomplete gamma."""
    if df <= 0:
        return 1.0
    if x <= 0:
        return 1.0
    a = 0.5 * float(df)
    xx = 0.5 * float(x)
    return _gammaincc(a, xx)


def _gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x)."""
    if a <= 0 or x < 0:
        raise ValueError("Invalid arguments for gammaincc.")
    if x == 0:
        return 1.0
    if x < a + 1.0:
        p = _gammainc_lower_reg(a, x)
        return min(1.0, max(0.0, 1.0 - p))
    q = _gammainc_upper_reg_cf(a, x)
    return min(1.0, max(0.0, q))


def _gammainc_lower_reg(a: float, x: float) -> float:
    itmax = 512
    eps = 1e-14
    gln = math.lgamma(a)
    ap = a
    summ = 1.0 / a
    delta = summ
    for _ in range(itmax):
        ap += 1.0
        delta *= x / ap
        summ += delta
        if abs(delta) < abs(summ) * eps:
            break
    return summ * math.exp(-x + (a * math.log(x)) - gln)


def _gammainc_upper_reg_cf(a: float, x: float) -> float:
    itmax = 512
    eps = 1e-14
    fpmin = 1e-300
    gln = math.lgamma(a)

    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / max(b, fpmin)
    h = d
    for i in range(1, itmax + 1):
        an = -float(i) * (float(i) - a)
        b += 2.0
        d = (an * d) + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + (an / c)
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return math.exp(-x + (a * math.log(x)) - gln) * h
