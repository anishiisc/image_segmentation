# Bimodal Histogram Segmentation & Sharpening Demo

An interactive, step-by-step computer vision tutorial built with FastAPI and vanilla JavaScript. The app walks through the full image analysis pipeline — from histogram analysis to segmentation to sharpening — with live controls and explanations at every stage.

**Dr. Anish Roychowdhury · Generative AI Architect & Educator**

---

## What It Does

The demo runs a complete CV pipeline on a selected grayscale image and displays every stage as an interactive card:

| Step | What you see |
|---|---|
| 1. Input Image | Original image with dimensions, pixel count, colour mode |
| 2. Intensity Histogram | Raw + smoothed histogram, peak detection, Otsu variance curve |
| 3. Bimodality Evidence | Valley Depth Ratio, Bimodality Coefficient, Ashman's D — colour-coded gauges |
| 4. Threshold Selection | Valley vs Otsu threshold comparison, with reason for the choice |
| 5. Segmentation | Binary mask, overlay, foreground/background isolation, contours |
| 6. Sharpening | Drag before/after slider, detail layer, sharpness metrics table |

All controls (smoothing sigma, prominence, threshold override, polarity, sharpening method/strength) re-run the pipeline instantly.

---

## Tutorial Images

Six curated images cover the full range of bimodality scenarios:

| Image | Concept demonstrated |
|---|---|
| Synthetic Bimodal | Designed blobs — perfect, clean bimodality |
| Binary Silhouette (horse) | Pure black-and-white — maximum bimodality |
| Coins | Real-world strongly bimodal |
| Cameraman | Classic CV benchmark — weakly bimodal |
| Moon Surface | Low contrast — near-unimodal |
| Pure Unimodal (synthetic) | Gaussian noise — single-peaked histogram |

---

## Project Structure

```
cvdemo/
├── backend/
│   ├── app.py               # FastAPI routes
│   ├── config.py            # Default parameters
│   ├── schemas.py           # Pydantic models
│   └── pipeline/
│       ├── histogram.py     # Gaussian smoothing, peak & valley detection
│       ├── bimodality.py    # VDR, Bimodality Coefficient, Ashman's D, GMM
│       ├── threshold.py     # Valley vs Otsu selection
│       ├── segmentation.py  # Morphological cleanup, overlays, contours
│       ├── sharpen.py       # Unsharp mask, Laplacian, mask-aware sharpening
│       ├── explain.py       # Natural-language explanation templates
│       └── io_utils.py      # Image decode / encode helpers
├── frontend/
│   ├── index.html           # Single-page layout
│   ├── app.js               # Rendering, charts, before/after slider
│   └── styles.css           # Light/dark theme, responsive grid
├── samples/
│   ├── manifest.json        # Sample image metadata
│   └── *.png                # Tutorial images
├── scripts/
│   └── make_synthetic.py    # Generates synthetic bimodal/unimodal images
└── requirements.txt
```

---

## Quickstart

**1. Clone the repo**
```bash
git clone https://github.com/anishiisc/image_segmentation.git
cd image_segmentation
```

**2. Create a virtual environment and install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Start the server**
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

**4. Open in your browser**
```
http://localhost:8000
```

Click any tutorial image in the sidebar to run the full pipeline instantly.

---

## Key Concepts

**Bimodality** — An image is bimodal when its pixel intensities form two distinct clusters (e.g. dark background, bright foreground). Three independent measures are used:
- **Valley Depth Ratio (VDR)** — depth of the dip between histogram peaks (≥ 0.5 = pass)
- **Bimodality Coefficient (BC)** — Sarle's statistic based on skewness and kurtosis (> 0.555 = pass)
- **Ashman's D** — separation of a two-Gaussian mixture model (> 2.0 = pass)

**Threshold selection** — When the histogram is strongly bimodal, the natural valley between peaks is used. Otherwise Otsu's method (maximising between-class variance) is preferred.

**Mask-aware sharpening** — The default sharpening mode applies a stronger boost inside the segmented foreground and a lighter touch in the background, enhancing object detail without amplifying background noise.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/api/samples` | List available tutorial images |
| GET | `/api/samples/{name}` | Serve a sample image file |
| POST | `/api/analyze` | Run the full pipeline, returns JSON + base64 images |

The `/api/analyze` endpoint accepts `multipart/form-data` with parameters: `sample_name`, `smoothing_sigma`, `min_prominence_frac`, `polarity`, `manual_threshold`, `cleanup`, `sharpen_method`, `radius`, `amount`, `amount_fg`, `amount_bg`.

---

## Requirements

- Python 3.10+
- FastAPI, Uvicorn
- OpenCV (`opencv-python-headless`)
- scikit-image, scikit-learn, scipy, numpy
- Chart.js (loaded via CDN in the browser)
