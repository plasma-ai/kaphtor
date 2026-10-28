"""Statistics for the adjudication: Monte Carlo p-values with exact intervals,
empirical likelihoods, AUC, bootstrap, Bayes factor and posterior.

Pure numpy; scipy is used for the beta quantile when available and replaced by
a bisection fallback otherwise, so the package runs without it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

try:  # optional
    from scipy.stats import beta as _beta  # type: ignore
except Exception:  # pragma: no cover
    _beta = None


# ---------------------------------------------------------------------------
# Monte Carlo p-values
# ---------------------------------------------------------------------------

def mc_p(observed: float, null: np.ndarray) -> dict:
    """Davison–Hinkley p = (r+1)/(B+1), one-sided (null >= observed), with
    Clopper–Pearson 95% interval on the exceedance rate and the zero-exceedance
    bound 3/B. Z is descriptive only."""
    null = np.asarray(null, dtype=float)
    B = int(null.size)
    r = int(np.sum(null >= observed))
    p = (r + 1) / (B + 1)
    lo, hi = clopper_pearson(r, B)
    mu = float(null.mean()) if B else float("nan")
    sd = float(null.std(ddof=1)) if B > 1 else float("nan")
    z = (observed - mu) / sd if sd and sd > 0 else float("nan")
    return {"observed": float(observed), "B": B, "r": r, "p": p,
            "p_ci95": [lo, hi], "zero_exceedance_bound": 3.0 / B if B else None,
            "null_mean": mu, "null_sd": sd, "null_max": float(null.max()) if B else None,
            "z_descriptive": z}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else _beta_ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else _beta_ppf(1 - alpha / 2, k + 1, n - k)
    return (lo, hi)


def _beta_ppf(q: float, a: float, b: float) -> float:
    if _beta is None:
        raise RuntimeError("scipy is required for Clopper–Pearson intervals (uv add scipy); "
                           "the former continued-fraction fallback was inaccurate and has been removed")
    return float(_beta.ppf(q, a, b))

def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a,b) by Lentz continued fraction."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _betainc(b, a, 1 - x)
    f, c, d = 1.0, 1.0, 0.0
    for i in range(1, 400):
        m = i // 2
        if i == 1:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1.0 / d if abs(d) > 1e-30 else 1e30
        c = 1.0 + num / c if abs(c) > 1e-30 else 1e30
        cd = c * d
        f *= cd
        if abs(1.0 - cd) < 1e-12:
            break
    return front * (f - 1.0)


# ---------------------------------------------------------------------------
# Empirical likelihoods
# ---------------------------------------------------------------------------

def kde_pdf(samples: np.ndarray, x: float, bandwidth_scale: float = 1.0) -> float:
    """Gaussian KDE density at x with Silverman bandwidth × scale."""
    s = np.asarray(samples, dtype=float)
    n = s.size
    if n == 0:
        return float("nan")
    sd = s.std(ddof=1) if n > 1 else 0.0
    iqr = np.subtract(*np.percentile(s, [75, 25])) if n > 1 else 0.0
    spread = min(sd, iqr / 1.34) if iqr > 0 else sd
    h = 0.9 * spread * n ** (-1 / 5) if spread > 0 else 1e-3
    h *= bandwidth_scale
    z = (x - s) / h
    return float(np.mean(np.exp(-0.5 * z * z)) / (h * math.sqrt(2 * math.pi)))


def likelihood_with_bound(samples: np.ndarray, x: float, bandwidth_scale: float = 1.0) -> dict:
    """KDE likelihood plus the honesty flag: if x exceeds every sample the
    density is extrapolated, and the report must show the 1/(n+1) bound."""
    s = np.asarray(samples, dtype=float)
    n = s.size
    exceeds_all = bool(n and x > s.max())
    return {"pdf": kde_pdf(s, x, bandwidth_scale), "n": int(n),
            "exceeds_all_samples": exceeds_all,
            "tail_bound": 1.0 / (n + 1) if n else None}


# ---------------------------------------------------------------------------
# Discrimination
# ---------------------------------------------------------------------------

def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann–Whitney AUC: P(score_pos > score_neg) + 0.5 P(tie)."""
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (pos.size * neg.size))


def auc_length_matched(pos: np.ndarray, neg: np.ndarray, pos_len: np.ndarray, neg_len: np.ndarray,
                       band: float = 0.5) -> tuple[float, int]:
    """Mann–Whitney AUC over the (pos, neg) pairs whose covariate (mean signs
    per word) differs by at most ``band``; ties credited 0.5. Returns
    (auc, number of contributing pairs); nan when no pair qualifies.
    Refreeze 2026-09-08 (METHOD_REVIEW.md §1: unmatched AUC(language) was a
    word-length meter)."""
    pos, neg = np.asarray(pos, dtype=float), np.asarray(neg, dtype=float)
    pl, nl = np.asarray(pos_len, dtype=float), np.asarray(neg_len, dtype=float)
    if pos.size == 0 or neg.size == 0:
        return float("nan"), 0
    ok = np.abs(pl[:, None] - nl[None, :]) <= band + 1e-12
    n = int(ok.sum())
    if n == 0:
        return float("nan"), 0
    gt = ((pos[:, None] > neg[None, :]) & ok).sum()
    eq = ((pos[:, None] == neg[None, :]) & ok).sum()
    return float((gt + 0.5 * eq) / n), n


def bootstrap_auc_length_matched(pos, neg, pos_len, neg_len, band: float = 0.5,
                                 n_iter: int = 2000, seed: int = 7) -> tuple[float, float]:
    """Percentile bootstrap of auc_length_matched, resampling controls within
    each class (pairs that fall outside the band in a resample are dropped,
    as in the point estimate)."""
    rng = np.random.default_rng(seed)
    pos, neg = np.asarray(pos, dtype=float), np.asarray(neg, dtype=float)
    pl, nl = np.asarray(pos_len, dtype=float), np.asarray(neg_len, dtype=float)
    vals = []
    for _ in range(n_iter):
        i = rng.integers(pos.size, size=pos.size)
        j = rng.integers(neg.size, size=neg.size)
        a, _ = auc_length_matched(pos[i], neg[j], pl[i], nl[j], band)
        if not math.isnan(a):
            vals.append(a)
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def bootstrap_auc(pos: np.ndarray, neg: np.ndarray, n_iter: int = 2000, seed: int = 7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    pos = np.asarray(pos, dtype=float)
    neg = np.asarray(neg, dtype=float)
    vals = []
    for _ in range(n_iter):
        p = rng.choice(pos, size=pos.size, replace=True)
        q = rng.choice(neg, size=neg.size, replace=True)
        vals.append(auc(p, q))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def bootstrap_mean_ci(values: np.ndarray, n_iter: int = 2000, seed: int = 7) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return (float("nan"), float("nan"))
    means = [rng.choice(v, size=v.size, replace=True).mean() for _ in range(n_iter)]
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


# ---------------------------------------------------------------------------
# Bayes factor and posterior
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Posterior:
    prior_h1: float
    bayes_factor: float
    p_h1: float
    p_h0: float


def bayes_factor(lik_h1: float, lik_alts: dict[str, float], weights: dict[str, float]) -> float:
    """BF = p(D|H1) / Σ_k w_k p(D|H_k) with weights renormalized over the
    alternatives actually supplied."""
    keys = [k for k in lik_alts if k in weights and weights[k] > 0]
    wsum = sum(weights[k] for k in keys)
    if wsum <= 0 or lik_h1 <= 0:
        return float("nan")
    denom = sum(weights[k] / wsum * lik_alts[k] for k in keys)
    return float("inf") if denom == 0 else lik_h1 / denom


def posterior(prior_h1: float, bf: float) -> Posterior:
    if math.isnan(bf):
        return Posterior(prior_h1, bf, float("nan"), float("nan"))
    if math.isinf(bf):
        return Posterior(prior_h1, bf, 1.0, 0.0)
    odds = prior_h1 / (1 - prior_h1) * bf
    p1 = odds / (1 + odds)
    return Posterior(prior_h1, bf, p1, 1 - p1)


def posterior_grid(lik_h1: float, lik_alts: dict[str, float],
                   weight_schemes: dict[str, dict[str, float]],
                   priors: tuple[float, ...] = (0.02, 0.05, 0.10, 0.25, 0.50)) -> list[dict]:
    rows = []
    for scheme, w in weight_schemes.items():
        bf = bayes_factor(lik_h1, lik_alts, w)
        for pi in priors:
            po = posterior(pi, bf)
            rows.append({"scheme": scheme, "prior_h1": pi, "log10_bf": math.log10(bf) if bf and not math.isinf(bf) and not math.isnan(bf) else None,
                         "p_h1": po.p_h1, "p_not_h1": po.p_h0})
    return rows


def sensitivity_flag(rows: list[dict], threshold: float = 0.05) -> bool:
    """Red flag: posterior moves less than `threshold` across the prior sweep
    within any single weight scheme (evidence claimed to swamp any prior)."""
    by = {}
    for r in rows:
        by.setdefault(r["scheme"], []).append(r["p_not_h1"])
    return any((max(v) - min(v)) < threshold for v in by.values() if all(isinstance(x, float) and not math.isnan(x) for x in v))
