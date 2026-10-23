"""Sharpening: unsharp mask, Laplacian, mask-aware unsharp. Metrics: Laplacian variance, Tenengrad."""

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from backend.config import (
    DEFAULT_AMOUNT,
    DEFAULT_AMOUNT_BG,
    DEFAULT_AMOUNT_FG,
    DEFAULT_LAPLACIAN_C,
    DEFAULT_RADIUS,
    MASK_FEATHER_SIGMA,
)
from backend.pipeline.io_utils import encode_png_b64


def _lap_var(img: np.ndarray) -> float:
    return float(cv2.Laplacian(img.astype(np.float64), cv2.CV_64F).var())


def _tenengrad(img: np.ndarray) -> float:
    gx = cv2.Sobel(img.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    return float(np.mean(gx ** 2 + gy ** 2))


def _unsharp(img: np.ndarray, radius: float, amount: float) -> np.ndarray:
    blurred = cv2.GaussianBlur(img.astype(np.float32), (0, 0), radius)
    detail = img.astype(np.float32) - blurred
    sharp = np.clip(img.astype(np.float32) + amount * detail, 0, 255)
    return sharp.astype(np.uint8), detail


def sharpen(
    img: np.ndarray,
    method: str = "mask_aware",
    radius: float = DEFAULT_RADIUS,
    amount: float = DEFAULT_AMOUNT,
    amount_fg: float = DEFAULT_AMOUNT_FG,
    amount_bg: float = DEFAULT_AMOUNT_BG,
    fg_mask: np.ndarray = None,
    laplacian_c: float = DEFAULT_LAPLACIAN_C,
) -> dict:
    """
    Sharpen the image and return metrics + encoded images.

    Returns:
      method: str
      sharpened_img: base64 PNG
      detail_img: base64 PNG
      lap_var_before: float
      lap_var_after: float
      lap_var_pct: float
      tenengrad_before: float
      tenengrad_after: float
      tenengrad_pct: float
      mask_aware: bool
    """
    lv_before = _lap_var(img)
    tg_before = _tenengrad(img)

    detail_arr = None
    mask_aware = False

    if method == "unsharp":
        sharp, detail_arr = _unsharp(img, radius, amount)

    elif method == "laplacian":
        lap = cv2.Laplacian(img.astype(np.float32), cv2.CV_32F, ksize=3)
        sharp = np.clip(img.astype(np.float32) - laplacian_c * lap, 0, 255).astype(np.uint8)
        detail_arr = np.abs(lap)

    else:  # mask_aware
        mask_aware = True
        if fg_mask is None:
            # Fallback to regular unsharp
            sharp, detail_arr = _unsharp(img, radius, amount)
        else:
            # Feather the mask
            feathered = gaussian_filter(fg_mask.astype(np.float32), sigma=MASK_FEATHER_SIGMA)
            feathered = np.clip(feathered, 0, 1)

            blurred = cv2.GaussianBlur(img.astype(np.float32), (0, 0), radius)
            detail_arr = img.astype(np.float32) - blurred

            # Per-pixel amount blended between fg and bg amounts
            amount_map = feathered * amount_fg + (1 - feathered) * amount_bg
            sharp = np.clip(img.astype(np.float32) + amount_map * detail_arr, 0, 255).astype(np.uint8)

    # Scale detail image for display
    d = detail_arr.astype(np.float32)
    d_min, d_max = d.min(), d.max()
    if d_max > d_min:
        d_display = ((d - d_min) / (d_max - d_min) * 255).astype(np.uint8)
    else:
        d_display = np.zeros_like(img, dtype=np.uint8)

    lv_after = _lap_var(sharp)
    tg_after = _tenengrad(sharp)

    def pct(before, after):
        return round((after - before) / before * 100, 1) if before > 0 else 0.0

    return {
        "method": method,
        "sharpened_img": encode_png_b64(sharp),
        "detail_img": encode_png_b64(d_display),
        "lap_var_before": round(lv_before, 2),
        "lap_var_after": round(lv_after, 2),
        "lap_var_pct": pct(lv_before, lv_after),
        "tenengrad_before": round(tg_before, 2),
        "tenengrad_after": round(tg_after, 2),
        "tenengrad_pct": pct(tg_before, tg_after),
        "mask_aware": mask_aware,
        "_sharp_arr": sharp,  # kept internally; stripped before JSON
    }
