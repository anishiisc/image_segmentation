"""Template-based explanation text for each pipeline stage."""


def _verdict_text(verdict: str) -> str:
    if verdict == "strongly_bimodal":
        return "strongly bimodal — the two intensity populations are well separated"
    elif verdict == "weakly_bimodal":
        return "weakly bimodal — there is some evidence for two populations, but the separation is not clean"
    else:
        return "unimodal — the intensity distribution does not clearly show two separate populations"


def explain_input(meta: dict) -> dict:
    w, h = meta["width"], meta["height"]
    colour_note = (
        " It was converted from colour to grayscale using the standard luminance weights."
        if meta.get("was_colour")
        else ""
    )
    rescale_note = (
        " The 16-bit depth was rescaled to 8-bit using min-max normalisation."
        if meta.get("was_rescaled")
        else ""
    )
    scale_note = (
        f" The image was downscaled by a factor of {meta['scale_factor']:.2f} "
        f"to keep the longest side within {2048} pixels."
        if meta.get("scale_factor", 1.0) < 1.0
        else ""
    )
    summary = f"The image is {w} \u00d7 {h} pixels.{colour_note}{rescale_note}{scale_note}"
    detail = (
        "Images are converted to 8-bit grayscale before analysis. "
        "Colour images use the standard luminance formula (0.299 R + 0.587 G + 0.114 B). "
        "Very large images are downscaled to keep processing fast."
    )
    return {
        "step": "input",
        "title": "Input Image",
        "summary": summary,
        "detail": detail,
        "numbers": {"width": w, "height": h, "was_colour": meta.get("was_colour", False)},
    }


def explain_histogram(hist: dict, smoothing_sigma: float) -> dict:
    peaks = hist["peaks"]
    valley = hist["valley"]
    n_peaks = len(peaks)
    if n_peaks >= 2:
        summary = (
            f"After smoothing with \u03c3={smoothing_sigma}, the histogram has {n_peaks} significant peaks. "
            f"The two strongest sit at grey levels {peaks[0]} and {peaks[1]}, "
            f"with the lowest point between them at {valley}."
        )
    else:
        summary = (
            f"After smoothing with \u03c3={smoothing_sigma}, only {n_peaks} significant peak was found. "
            "The histogram appears unimodal."
        )
    detail = (
        "Raw histograms are jagged because of quantisation noise. "
        "Gaussian smoothing (controlled by \u03c3) reduces spurious peaks so that only real modes are detected. "
        "Peaks are ranked by prominence — how much they stand above the surrounding baseline."
    )
    return {
        "step": "histogram",
        "title": "Intensity Histogram",
        "summary": summary,
        "detail": detail,
        "numbers": {"sigma": smoothing_sigma, "peaks": peaks, "valley": valley},
    }


def explain_bimodality(bm: dict) -> dict:
    vdr = bm["vdr"]
    bc = bm["bc"]
    d = bm["ashman_d"]
    verdict = bm["verdict"]
    gmm_note = (
        " No sharp histogram peaks were found, but the Gaussian mixture model "
        "reveals two overlapping populations — the histogram is broad rather than sharply bimodal."
        if bm.get("gmm_peak_used") else ""
    )
    summary = (
        f"Valley depth ratio is {vdr:.2f}, bimodality coefficient is {bc:.3f} "
        f"(threshold 0.555), and Ashman\u2019s D is {d:.2f} (threshold 2.0). "
        f"Verdict: {_verdict_text(verdict)}.{gmm_note}"
    )
    detail = (
        "Three independent measures are used so students see that \u2018bimodal\u2019 is a quantitative judgement, "
        "not a binary label. The valley depth ratio measures how deep the dip between the two peaks is. "
        "The bimodality coefficient is based on the skewness and kurtosis of the raw pixel intensities. "
        "Ashman\u2019s D measures the separation of a two-Gaussian mixture model fitted to the pixel data."
    )
    return {
        "step": "bimodality",
        "title": "Bimodality Evidence",
        "summary": summary,
        "detail": detail,
        "numbers": {"vdr": vdr, "bc": bc, "ashman_d": d, "verdict": verdict},
    }


def explain_threshold(thr: dict) -> dict:
    T_v = thr["valley"]
    T_o = thr["otsu"]
    chosen = thr["chosen"]
    method = thr["method"]
    reason = thr["reason"]
    diff = thr.get("diff")
    diff_str = f"a difference of {diff} grey levels" if diff is not None else "no valley threshold available"
    summary = (
        f"The valley method gives {'N/A' if T_v is None else T_v} and Otsu gives {T_o} ({diff_str}). "
        f"Threshold {chosen} was chosen using the {method} method."
    )
    detail = (
        "Otsu\u2019s method maximises the between-class variance across all possible thresholds. "
        "The valley method picks the grey level at the lowest point between the two histogram peaks. "
        "When the histogram is cleanly bimodal the valley threshold is more intuitive; "
        "when it is noisy, Otsu is more robust."
    )
    return {
        "step": "threshold",
        "title": "Threshold Selection",
        "summary": summary,
        "detail": detail,
        "numbers": {"valley": T_v, "otsu": T_o, "chosen": chosen, "method": method},
    }


def explain_segmentation(seg: dict) -> dict:
    T = seg["threshold_used"]
    polarity = seg["polarity_used"]
    fg_pct = seg["fg_fraction"] * 100
    n_comp = seg["n_components"]
    mu_fg = seg["mean_fg"]
    mu_bg = seg["mean_bg"]
    above_or_below = "above" if polarity == "bright" else "at or below"
    summary = (
        f"Pixels {above_or_below} {T} were labelled foreground. "
        f"Foreground covers {fg_pct:.1f}% of the image in {n_comp} connected region{'s' if n_comp != 1 else ''}. "
        f"Mean intensity is {mu_fg:.0f} for foreground and {mu_bg:.0f} for background."
    )
    detail = (
        "After thresholding, small isolated regions and holes are removed by morphological opening "
        "and closing, then by area filtering. The polarity rule (auto: the smaller class is foreground) "
        "handles both dark-on-light and light-on-dark images automatically."
    )
    return {
        "step": "segmentation",
        "title": "Segmentation",
        "summary": summary,
        "detail": detail,
        "numbers": {
            "threshold": T,
            "polarity": polarity,
            "fg_pct": round(fg_pct, 1),
            "n_components": n_comp,
            "mean_fg": mu_fg,
            "mean_bg": mu_bg,
        },
    }


def explain_sharpening(shp: dict) -> dict:
    method = shp["method"]
    lv0 = shp["lap_var_before"]
    lv1 = shp["lap_var_after"]
    lv_pct = shp["lap_var_pct"]
    mask_note = (
        " Foreground was sharpened more strongly than background."
        if shp.get("mask_aware")
        else ""
    )
    method_labels = {"unsharp": "Unsharp masking", "laplacian": "Laplacian sharpening", "mask_aware": "Mask-aware unsharp masking"}
    method_label = method_labels.get(method, method)
    summary = (
        f"{method_label} raised the Laplacian variance from {lv0:.0f} to {lv1:.0f} ({lv_pct:+.0f}%).{mask_note}"
    )
    detail = (
        "Unsharp masking subtracts a blurred copy from the original to extract detail, "
        "then adds a scaled version of that detail back. "
        "The Laplacian variance and Tenengrad measure how much high-frequency energy is present \u2014 "
        "both increase when an image becomes sharper. "
        "Mask-aware sharpening applies a stronger boost inside the segmented foreground, "
        "where fine structure matters most, and a lighter touch in the background."
    )
    return {
        "step": "sharpening",
        "title": "Sharpening",
        "summary": summary,
        "detail": detail,
        "numbers": {
            "lap_var_before": lv0,
            "lap_var_after": lv1,
            "lap_var_pct": lv_pct,
            "method": method,
        },
    }


def collect_warnings(
    meta: dict,
    hist: dict,
    bm: dict,
    thr: dict,
    seg: dict,
    shp: dict,
) -> list:
    warnings = []
    if bm["verdict"] == "unimodal":
        warnings.append(
            "The histogram is unimodal. Global thresholding may not give a meaningful result. "
            "Consider using the local adaptive threshold shown in the segmentation step."
        )
    fg_pct = seg["fg_fraction"] * 100
    if fg_pct < 1.0:
        warnings.append(f"Foreground is very small ({fg_pct:.1f}%). The threshold may be too aggressive.")
    if fg_pct > 90.0:
        warnings.append(f"Foreground covers {fg_pct:.1f}% of the image. The threshold may be too permissive.")
    if thr.get("diff") is not None and thr["diff"] > 30:
        warnings.append(
            f"The valley threshold ({thr['valley']}) and Otsu threshold ({thr['otsu']}) "
            f"differ by {thr['diff']} grey levels, which is large. "
            "Inspect the histogram carefully to decide which is more appropriate."
        )
    if shp["lap_var_pct"] > 400:
        warnings.append(
            f"The Laplacian variance increased by {shp['lap_var_pct']:+.0f}%, "
            "which may indicate heavy noise amplification. Consider reducing the sharpening amount."
        )
    return warnings
