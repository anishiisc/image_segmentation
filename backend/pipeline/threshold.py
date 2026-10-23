"""Threshold selection: valley method vs Otsu, with fallback logic."""

import numpy as np
from skimage.filters import threshold_local, threshold_otsu

from backend.config import UNIMODAL_LOCAL_BLOCK_SIZE


def compute_otsu_curve(img: np.ndarray) -> list:
    """Compute between-class variance for all 256 thresholds."""
    h = np.bincount(img.ravel(), minlength=256).astype(np.float64)
    N = img.size
    p = h / N
    curve = []
    for t in range(256):
        w0 = p[:t].sum()
        w1 = p[t:].sum()
        if w0 == 0 or w1 == 0:
            curve.append(0.0)
            continue
        mu0 = np.sum(np.arange(t) * p[:t]) / w0
        mu1 = np.sum(np.arange(t, 256) * p[t:]) / w1
        sigma_b2 = w0 * w1 * (mu0 - mu1) ** 2
        curve.append(float(sigma_b2))
    return curve


def select_threshold(
    img: np.ndarray,
    hist_result: dict,
    bimodality_result: dict,
    manual_threshold: int = None,
) -> dict:
    """
    Select the best threshold based on bimodality verdict.

    Returns:
      valley: int or None
      otsu: int
      chosen: int
      method: str
      reason: str
      local_mask: np.ndarray or None (for unimodal warning)
      otsu_curve: list of 256 floats
    """
    verdict = bimodality_result["verdict"]
    valley = hist_result.get("valley")

    otsu_val = int(threshold_otsu(img))
    otsu_curve = compute_otsu_curve(img)

    # Local threshold for unimodal fallback
    local_mask = None
    use_local_warning = False
    if verdict == "unimodal":
        block = UNIMODAL_LOCAL_BLOCK_SIZE
        local_thresh = threshold_local(img, block_size=block)
        local_mask = (img > local_thresh).astype(np.uint8) * 255
        use_local_warning = True

    if manual_threshold is not None:
        chosen = int(manual_threshold)
        method = "manual"
        reason = f"User manually set threshold to {chosen}."
    elif verdict == "strongly_bimodal" and valley is not None:
        chosen = int(valley)
        method = "valley"
        reason = (
            f"The histogram has a clear bimodal shape (VDR={bimodality_result['vdr']:.2f}). "
            f"The valley between the two peaks at level {chosen} is used as the natural threshold."
        )
    else:
        chosen = otsu_val
        method = "otsu"
        if verdict == "unimodal":
            reason = (
                f"The histogram appears unimodal, so the valley method cannot be applied. "
                f"Otsu's method gives threshold {otsu_val}. "
                f"A local adaptive threshold (block size {UNIMODAL_LOCAL_BLOCK_SIZE}) is also computed as an alternative."
            )
        else:
            reason = (
                f"The histogram is weakly bimodal (VDR={bimodality_result['vdr']:.2f}). "
                f"Otsu's method is preferred over a potentially noisy valley minimum, giving threshold {otsu_val}."
            )

    valley_val = int(valley) if valley is not None else None
    diff = abs(valley_val - otsu_val) if valley_val is not None else None

    return {
        "valley": valley_val,
        "otsu": otsu_val,
        "chosen": chosen,
        "method": method,
        "reason": reason,
        "diff": diff,
        "local_mask": local_mask,
        "otsu_curve": otsu_curve,
        "use_local_warning": use_local_warning,
    }
