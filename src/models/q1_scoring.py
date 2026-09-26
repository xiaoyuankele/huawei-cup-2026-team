"""CRITIC and fixed-reference weighted-distance TOPSIS for oriented [0, 1] data."""
import numpy as np


def critic_weights(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('CRITIC requires at least two complete observations.')
    sd = x.std(axis=0, ddof=1)
    active = sd > 1e-12
    corr = np.zeros((x.shape[1], x.shape[1]))
    if active.sum() > 1:
        corr[np.ix_(active, active)] = np.corrcoef(x[:, active], rowvar=False)
    np.fill_diagonal(corr, 1.)
    corr = np.clip(corr, -1., 1.)
    information = sd * (1. - corr).sum(axis=1)
    if information.sum() <= 1e-12:
        raise ValueError('All usable information is zero; no automatic fallback.')
    return information / information.sum(), sd, corr, information


def validate(x, w):
    x, w = np.asarray(x, dtype=float), np.asarray(w, dtype=float)
    if x.ndim != 2 or w.shape != (x.shape[1],):
        raise ValueError('Matrix and weight dimensions differ.')
    if not np.isfinite(x).all() or not np.isfinite(w).all():
        raise ValueError('Missing or nonfinite values are not silently imputed.')
    if (x < -1e-12).any() or (x > 1 + 1e-12).any():
        raise ValueError('TOPSIS input must use the fixed [0, 1] scale.')
    if (w < 0).any() or not np.isclose(w.sum(), 1., atol=1e-12):
        raise ValueError('Weights must be nonnegative and sum to one.')
    return x, w


def topsis(x, w):
    """w enters the squared distance ONCE, equivalent to scaling axes by sqrt(w)."""
    x, w = validate(x, w)
    d_plus = np.sqrt(np.square(1. - x) @ w)
    d_minus = np.sqrt(np.square(x) @ w)
    return 100. * d_minus / (d_plus + d_minus), d_plus, d_minus


def weighted_sum(x, w):
    x, w = validate(x, w)
    return 100. * (x @ w)
