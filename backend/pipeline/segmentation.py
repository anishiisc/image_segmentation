"""Foreground/background segmentation with morphological cleanup and overlays."""

import cv2
import numpy as np
from skimage.measure import label
from skimage.morphology import remove_small_holes, remove_small_objects

from backend.config import (
    MORPH_KERNEL_SIZE,
    OVERLAY_ALPHA,
    REMOVE_SMALL_HOLES_AREA,
    REMOVE_SMALL_MIN_SIZE,
)
from backend.pipeline.io_utils import encode_png_b64


def segment(
    img: np.ndarray,
    threshold_result: dict,
    polarity: str = "auto",
    cleanup: bool = True,
) -> dict:
    """
    Segment the image into foreground and background.

    Returns:
      polarity_used: str
      fg_fraction: float
      n_components: int
      mean_fg: float
      mean_bg: float
      contrast: float
      mask_img: base64 PNG (white = foreground)
      overlay_img: base64 PNG
      foreground_img: base64 PNG
      background_img: base64 PNG
      contour_img: base64 PNG
    """
    T = threshold_result["chosen"]
    mask_bright = (img > T).astype(bool)

    # Polarity rule
    fg_bright_frac = mask_bright.mean()
    if polarity == "auto":
        # Fewer pixels = foreground
        fg_mask = mask_bright if fg_bright_frac <= 0.5 else ~mask_bright
        polarity_used = "bright" if fg_bright_frac <= 0.5 else "dark"
    elif polarity == "bright":
        fg_mask = mask_bright
        polarity_used = "bright"
    else:  # dark
        fg_mask = ~mask_bright
        polarity_used = "dark"

    # Morphological cleanup
    if cleanup:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE)
        )
        mask_u8 = fg_mask.astype(np.uint8)
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel)
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
        fg_mask = mask_u8.astype(bool)
        fg_mask = remove_small_objects(fg_mask, max_size=REMOVE_SMALL_MIN_SIZE)
        fg_mask = remove_small_holes(fg_mask, max_size=REMOVE_SMALL_HOLES_AREA)

    fg_fraction = float(fg_mask.mean())

    # Connected components
    labeled = label(fg_mask)
    n_components = int(labeled.max())

    # Class statistics
    fg_pixels = img[fg_mask].astype(float)
    bg_pixels = img[~fg_mask].astype(float)
    mean_fg = float(fg_pixels.mean()) if len(fg_pixels) > 0 else 0.0
    mean_bg = float(bg_pixels.mean()) if len(bg_pixels) > 0 else 0.0
    contrast = abs(mean_fg - mean_bg)

    # Build output images
    mask_arr = (fg_mask.astype(np.uint8) * 255)

    # Colour overlay (foreground tinted green at alpha)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    overlay = img_bgr.copy()
    overlay[fg_mask] = (
        (1 - OVERLAY_ALPHA) * overlay[fg_mask].astype(float)
        + OVERLAY_ALPHA * np.array([0, 200, 80], dtype=float)
    ).astype(np.uint8)

    # Foreground only
    fg_only = img.copy()
    fg_only[~fg_mask] = 0

    # Background only
    bg_only = img.copy()
    bg_only[fg_mask] = 0

    # Contour image
    contour_img = img_bgr.copy()
    contours, _ = cv2.findContours(
        fg_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    cv2.drawContours(contour_img, contours, -1, (0, 255, 0), 1)

    return {
        "polarity_used": polarity_used,
        "fg_fraction": round(fg_fraction, 4),
        "n_components": n_components,
        "mean_fg": round(mean_fg, 2),
        "mean_bg": round(mean_bg, 2),
        "contrast": round(contrast, 2),
        "threshold_used": T,
        "mask_img": encode_png_b64(mask_arr),
        "overlay_img": encode_png_b64(overlay),
        "foreground_img": encode_png_b64(fg_only),
        "background_img": encode_png_b64(bg_only),
        "contour_img": encode_png_b64(contour_img),
        "_fg_mask": fg_mask,  # kept for sharpening; stripped before JSON serialisation
    }
