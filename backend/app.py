"""FastAPI application: routes, static file serving, CORS."""

import json
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.pipeline.bimodality import compute_bimodality
from backend.pipeline.explain import (
    collect_warnings,
    explain_bimodality,
    explain_histogram,
    explain_input,
    explain_segmentation,
    explain_sharpening,
    explain_threshold,
)
from backend.pipeline.histogram import compute_histogram
from backend.pipeline.io_utils import FileTooLarge, UnsupportedMediaType, decode_image, encode_png_b64
from backend.pipeline.segmentation import segment
from backend.pipeline.sharpen import sharpen
from backend.pipeline.threshold import select_threshold

BASE_DIR = Path(__file__).parent.parent
SAMPLES_DIR = BASE_DIR / "samples"
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Bimodal CV Demo", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:*"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/samples")
def list_samples():
    manifest_path = SAMPLES_DIR / "manifest.json"
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text())


@app.get("/api/samples/{name}")
def get_sample(name: str):
    path = SAMPLES_DIR / name
    if not path.exists() or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp"}:
        raise HTTPException(status_code=404, detail="Sample not found")
    return FileResponse(str(path), media_type="image/png")


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(default=None),
    sample_name: str = Form(default=None),
    smoothing_sigma: float = Form(default=3.0),
    min_prominence_frac: float = Form(default=0.10),
    polarity: str = Form(default="auto"),
    manual_threshold: int = Form(default=None),
    cleanup: bool = Form(default=True),
    sharpen_method: str = Form(default="mask_aware"),
    radius: float = Form(default=1.5),
    amount: float = Form(default=1.0),
    amount_fg: float = Form(default=1.5),
    amount_bg: float = Form(default=0.3),
):
    t0 = time.perf_counter()

    # --- Load image ---
    if sample_name:
        sample_path = SAMPLES_DIR / sample_name
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample '{sample_name}' not found")
        raw_bytes = sample_path.read_bytes()
        filename = sample_name
    elif file:
        raw_bytes = await file.read()
        filename = file.filename or ""
    else:
        raise HTTPException(status_code=422, detail="Provide either 'file' or 'sample_name'")

    try:
        decoded = decode_image(raw_bytes, filename)
    except FileTooLarge as e:
        raise HTTPException(status_code=413, detail=str(e))
    except UnsupportedMediaType as e:
        raise HTTPException(status_code=415, detail=str(e))

    img = decoded["img"]
    h, w = img.shape

    meta = {
        "width": w,
        "height": h,
        "was_colour": decoded["was_colour"],
        "was_rescaled": decoded["was_rescaled"],
        "scale_factor": decoded["scale_factor"],
        "original_size": decoded["original_size"],
    }

    # --- Pipeline ---
    hist = compute_histogram(img, smoothing_sigma, min_prominence_frac)
    bm = compute_bimodality(img, hist)
    thr = select_threshold(img, hist, bm, manual_threshold)
    seg = segment(img, thr, polarity, cleanup)
    fg_mask = seg.pop("_fg_mask", None)
    shp = sharpen(img, sharpen_method, radius, amount, amount_fg, amount_bg, fg_mask)
    sharp_arr = shp.pop("_sharp_arr", None)

    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    meta["elapsed_ms"] = elapsed_ms

    # --- Explanations ---
    explanations = [
        explain_input(meta),
        explain_histogram(hist, smoothing_sigma),
        explain_bimodality(bm),
        explain_threshold(thr),
        explain_segmentation(seg),
        explain_sharpening(shp),
    ]

    warnings = collect_warnings(meta, hist, bm, thr, seg, shp)

    # --- Build response ---
    # Strip internal fields before serialisation
    thr_out = {k: v for k, v in thr.items() if k not in ("local_mask", "otsu_curve")}
    images = {
        "original": encode_png_b64(img),
        "mask": seg.pop("mask_img"),
        "overlay": seg.pop("overlay_img"),
        "foreground": seg.pop("foreground_img"),
        "background": seg.pop("background_img"),
        "contours": seg.pop("contour_img"),
        "detail": shp.pop("detail_img"),
        "sharpened": shp.pop("sharpened_img"),
    }

    return {
        "meta": meta,
        "histogram": {
            "raw": hist["raw"],
            "smoothed": hist["smoothed"],
            "candidates": hist["candidates"],
            "peaks": hist["peaks"],
            "valley": hist["valley"],
            "otsu_curve": thr["otsu_curve"],
        },
        "bimodality": bm,
        "threshold": thr_out,
        "segmentation": seg,
        "sharpening": shp,
        "images": images,
        "explanations": explanations,
        "warnings": warnings,
    }


# Serve frontend as static files
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
