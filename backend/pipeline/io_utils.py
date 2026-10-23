"""Input handling: decode upload, convert to grayscale, resize, encode to base64 PNG."""

import base64
import io
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

from backend.config import MAX_LONGEST_SIDE, MAX_UPLOAD_BYTES

ALLOWED_MIME_PREFIXES = {"image/png", "image/jpeg", "image/bmp", "image/tiff", "image/x-tiff"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


class UnsupportedMediaType(Exception):
    pass


class FileTooLarge(Exception):
    pass


def decode_image(data: bytes, filename: str = "") -> dict:
    """
    Decode raw image bytes into a uint8 grayscale numpy array.

    Returns a dict with:
      - img: np.ndarray uint8 grayscale
      - was_colour: bool
      - was_rescaled: bool  (16-bit -> 8-bit)
      - scale_factor: float (1.0 unless downscaled)
      - original_size: (w, h)
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise FileTooLarge(f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")

    ext = ""
    if filename:
        import os
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedMediaType(f"Unsupported file extension: {ext}")

    arr = np.frombuffer(data, np.uint8)
    img_raw = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img_raw is None:
        raise UnsupportedMediaType("Could not decode image. Supported formats: PNG, JPEG, BMP, TIFF")

    was_colour = False
    was_rescaled = False

    # Handle colour images
    if img_raw.ndim == 3:
        was_colour = True
        if img_raw.shape[2] == 4:
            img_raw = cv2.cvtColor(img_raw, cv2.COLOR_BGRA2GRAY)
        else:
            img_raw = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)
    elif img_raw.ndim != 2:
        raise UnsupportedMediaType("Unexpected image dimensions")

    # Handle 16-bit
    if img_raw.dtype == np.uint16:
        was_rescaled = True
        mn, mx = img_raw.min(), img_raw.max()
        if mx > mn:
            img_raw = ((img_raw.astype(np.float32) - mn) / (mx - mn) * 255).astype(np.uint8)
        else:
            img_raw = np.zeros_like(img_raw, dtype=np.uint8)

    img = img_raw.astype(np.uint8)

    h, w = img.shape
    original_size = (w, h)
    scale_factor = 1.0

    # Downscale if too large
    longest = max(h, w)
    if longest > MAX_LONGEST_SIDE:
        scale_factor = MAX_LONGEST_SIDE / longest
        new_w = int(round(w * scale_factor))
        new_h = int(round(h * scale_factor))
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    return {
        "img": img,
        "was_colour": was_colour,
        "was_rescaled": was_rescaled,
        "scale_factor": scale_factor,
        "original_size": original_size,
    }


def encode_png_b64(img: np.ndarray) -> str:
    """Encode a numpy array as a base64 PNG string."""
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    success, buf = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("Failed to encode image as PNG")
    return base64.b64encode(buf.tobytes()).decode("ascii")
