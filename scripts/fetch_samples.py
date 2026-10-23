"""Populate samples/ with scikit-image built-in images and write manifest.json."""

import json
import sys
from pathlib import Path

import numpy as np
from skimage import data, filters, io, util

out = Path(__file__).parent.parent / "samples"
out.mkdir(exist_ok=True)

items = {
    "coins": (data.coins(), "Coins on a dark background, bimodal"),
    "page": (data.page(), "Scanned text with uneven lighting"),
    "text": (data.text(), "Text on a textured background"),
    "camera": (data.camera(), "Cameraman, not cleanly bimodal"),
    "moon": (data.moon(), "Low contrast, near unimodal"),
    "horse": (util.img_as_ubyte(~data.horse()), "Binary silhouette, ideal bimodal"),
    "blobs": (
        (filters.gaussian(data.binary_blobs(512, rng=1).astype(float), 2) * 255).astype(np.uint8),
        "Synthetic blobs, slightly blurred",
    ),
}

manifest = []
for name, (img, desc) in items.items():
    path = out / f"{name}.png"
    io.imsave(str(path), img, check_contrast=False)
    manifest.append({"name": f"{name}.png", "description": desc})
    print(f"  Saved {path}")

(out / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(f"manifest.json written with {len(manifest)} entries.")
