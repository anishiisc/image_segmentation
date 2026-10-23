"""Histogram computation, smoothing, peak and valley detection."""

from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

from backend.config import DEFAULT_MIN_PEAK_DISTANCE, DEFAULT_MIN_PROMINENCE_FRAC, DEFAULT_SMOOTHING_SIGMA


def compute_histogram(
    img: np.ndarray,
    smoothing_sigma: float = DEFAULT_SMOOTHING_SIGMA,
    min_prominence_frac: float = DEFAULT_MIN_PROMINENCE_FRAC,
    min_distance: int = DEFAULT_MIN_PEAK_DISTANCE,
) -> dict:
    """
    Compute and analyse the intensity histogram.

    Returns:
      raw: list of 256 raw counts
      normalised: list of 256 probability mass values
      smoothed: list of 256 smoothed probability mass values
      candidates: list of {level, prominence} for all detected peaks
      peaks: [peak_low, peak_high] or [] if fewer than 2 peaks
      valley: int grey level of the valley (or None)
      is_bimodal_candidate: bool (True if 2+ peaks found)
    """
    h = np.bincount(img.ravel(), minlength=256).astype(np.float64)
    N = img.size
    p = h / N

    if smoothing_sigma > 0:
        p_smooth = gaussian_filter1d(p, sigma=smoothing_sigma)
    else:
        p_smooth = p.copy()

    # Peak detection
    prom_min = min_prominence_frac * float(p_smooth.max())
    peak_indices, props = find_peaks(
        p_smooth,
        prominence=prom_min,
        distance=min_distance,
    )

    prominences = props["prominences"]
    candidates = [
        {"level": int(idx), "prominence": float(prom)}
        for idx, prom in zip(peak_indices, prominences)
    ]
    # Sort by prominence desc, keep top 2
    candidates_sorted = sorted(candidates, key=lambda x: -x["prominence"])
    top2 = candidates_sorted[:2]

    peaks = []
    valley = None
    if len(top2) >= 2:
        levels = sorted([c["level"] for c in top2])
        peak_low, peak_high = levels[0], levels[1]
        peaks = [peak_low, peak_high]
        # Valley is the argmin between the two peaks
        segment = p_smooth[peak_low: peak_high + 1]
        valley = int(np.argmin(segment)) + peak_low

    return {
        "raw": h.tolist(),
        "normalised": p.tolist(),
        "smoothed": p_smooth.tolist(),
        "candidates": candidates,
        "peaks": peaks,
        "valley": valley,
        "is_bimodal_candidate": len(peaks) == 2,
    }
