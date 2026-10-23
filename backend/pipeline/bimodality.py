"""Bimodality evidence: VDR, Bimodality Coefficient (Sarle), Ashman's D, GMM fit."""

import numpy as np
from scipy import stats
from sklearn.mixture import GaussianMixture

from backend.config import (
    ASHMAN_D_THRESHOLD,
    BC_THRESHOLD,
    GMM_SUBSAMPLE,
    VDR_THRESHOLD,
)


def compute_bimodality(
    img: np.ndarray,
    hist_result: dict,
) -> dict:
    """
    Compute three bimodality measures and return a verdict.

    Returns:
      vdr: float  Valley Depth Ratio
      bc: float   Bimodality Coefficient (Sarle)
      ashman_d: float  Ashman's D
      verdict: str  'strongly_bimodal' | 'weakly_bimodal' | 'unimodal'
      gmm: dict {means, stds, weights}
    """
    peaks = hist_result["peaks"]
    valley = hist_result["valley"]
    p_smooth = np.array(hist_result["smoothed"])

    # Sample pixels for statistics
    pixels = img.ravel().astype(np.float64)
    if len(pixels) > GMM_SUBSAMPLE:
        rng = np.random.default_rng(42)
        pixels = rng.choice(pixels, size=GMM_SUBSAMPLE, replace=False)

    # --- Bimodality Coefficient (Sarle) ---
    n = len(pixels)
    g = float(stats.skew(pixels))
    k = float(stats.kurtosis(pixels, fisher=True))
    denom = k + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)) if n > 3 else 1.0
    bc = (g ** 2 + 1) / denom if denom != 0 else 0.0

    # --- GMM fit for Ashman's D ---
    gmm = GaussianMixture(n_components=2, random_state=0, max_iter=200)
    gmm.fit(pixels.reshape(-1, 1))
    means = gmm.means_.flatten()
    stds = np.sqrt(gmm.covariances_.flatten())
    weights = gmm.weights_.flatten()
    order = np.argsort(means)
    means, stds, weights = means[order], stds[order], weights[order]

    mu1, mu2 = means[0], means[1]
    s1, s2 = stds[0], stds[1]
    denom_d = np.sqrt(0.5 * (s1 ** 2 + s2 ** 2))
    ashman_d = float(np.sqrt(2) * abs(mu1 - mu2) / denom_d) if denom_d > 0 else 0.0

    # --- Valley Depth Ratio ---
    vdr = 0.0
    if len(peaks) == 2 and valley is not None:
        p_low = p_smooth[peaks[0]]
        p_high = p_smooth[peaks[1]]
        p_valley = p_smooth[valley]
        min_peak = min(p_low, p_high)
        vdr = float(1 - p_valley / min_peak) if min_peak > 0 else 0.0

    # --- Verdict ---
    # When the histogram has no clear peaks, fall back to GMM evidence.
    # A broad bimodal distribution (e.g. coins) may not show sharp histogram
    # peaks but the GMM and Sarle coefficient still detect two populations.
    gmm_peak_used = False
    if len(peaks) < 2:
        gmm_evidence = (bc > BC_THRESHOLD) and (ashman_d > ASHMAN_D_THRESHOLD)
        if gmm_evidence:
            # Use GMM means as surrogate peak positions to compute VDR
            p0 = max(0, int(round(float(mu1))))
            p1 = min(255, int(round(float(mu2))))
            if p1 > p0:
                seg = p_smooth[p0: p1 + 1]
                v_idx = int(np.argmin(seg)) + p0
                p_valley_gmm = p_smooth[v_idx]
                min_peak_gmm = min(p_smooth[p0], p_smooth[p1])
                vdr = float(1 - p_valley_gmm / min_peak_gmm) if min_peak_gmm > 0 else 0.0
            verdict = "weakly_bimodal"
            gmm_peak_used = True
        else:
            verdict = "unimodal"
    else:
        tests_passed = (
            (vdr >= VDR_THRESHOLD) +
            (bc > BC_THRESHOLD) +
            (ashman_d > ASHMAN_D_THRESHOLD)
        )
        if vdr >= VDR_THRESHOLD and tests_passed >= 2:
            verdict = "strongly_bimodal"
        elif tests_passed >= 1:
            verdict = "weakly_bimodal"
        else:
            verdict = "unimodal"

    return {
        "vdr": round(vdr, 4),
        "bc": round(bc, 4),
        "ashman_d": round(float(ashman_d), 4),
        "verdict": verdict,
        "gmm_peak_used": gmm_peak_used,
        "gmm": {
            "means": [round(float(m), 2) for m in means],
            "stds": [round(float(s), 2) for s in stds],
            "weights": [round(float(w), 4) for w in weights],
        },
    }
