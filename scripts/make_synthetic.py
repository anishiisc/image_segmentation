"""Generate synthetic test images with known ground truth."""

import sys
from pathlib import Path

import cv2
import numpy as np
from skimage import io

out = Path(__file__).parent.parent / "samples"
out.mkdir(exist_ok=True)


def make_bimodal(size=512, bg_level=60, fg_level=190, noise_sigma=15, n_circles=10, seed=42):
    rng = np.random.default_rng(seed)
    img = np.full((size, size), bg_level, dtype=np.float32)
    r = size // 10
    for _ in range(n_circles):
        cx = int(rng.integers(r, size - r))
        cy = int(rng.integers(r, size - r))
        cv2.circle(img, (cx, cy), r, fg_level, -1)
    img += rng.normal(0, noise_sigma, img.shape).astype(np.float32)
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    return np.clip(img, 0, 255).astype(np.uint8)


def make_unimodal(size=512, mean=128, sigma=25, seed=42):
    rng = np.random.default_rng(seed)
    img = rng.normal(mean, sigma, (size, size))
    return np.clip(img, 0, 255).astype(np.uint8)


def make_inverted(size=512):
    """Dark objects on light background."""
    img = make_bimodal(size, bg_level=190, fg_level=60)
    return img


def make_gradient(size=512):
    """Bimodal image with left-to-right illumination ramp (0.5 to 1.0)."""
    base = make_bimodal(size).astype(np.float32)
    ramp = np.linspace(0.5, 1.0, size, dtype=np.float32)
    img = base * ramp[np.newaxis, :]
    return np.clip(img, 0, 255).astype(np.uint8)


images = {
    "synth_bimodal": make_bimodal(),
    "synth_unimodal": make_unimodal(),
    "synth_inverted": make_inverted(),
    "synth_gradient": make_gradient(),
}

for name, img in images.items():
    path = out / f"{name}.png"
    io.imsave(str(path), img, check_contrast=False)
    print(f"  Saved {path}")

print("Synthetic images written.")
