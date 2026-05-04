#!/usr/bin/env python3
"""
satellite_enhance.py - Per-image satellite imagery enhancer for the satellite-image-enhance skill.

Two variants by default:
  enhance_standard: balanced contrast stretch, mild sharpening, truthful (analysis-leaning)
  enhance_vivid:    stronger contrast and saturation for visual presentation, still geographically accurate

Pipeline per image:
  1. EXIF orientation
  2. Crop (per-image, fraction-based top/right/left/bottom)
  3. Exposure (stops)
  4. Contrast stretch (CLAHE on luminance)
  5. Tone curve (highlights/shadows/whites/blacks)
  6. White balance (gray-world, conservative)
  7. Tint correction
  8. HSL band adjustments (vegetation green, water blue)
  9. Local highlight pullback (cloud/bright region attenuation)
  10. Local shadow lift (dark terrain lifting)
  11. Gentle sharpen

Usage:
  python satellite_enhance.py --config config.json

Config JSON:
{
  "input_dir":   "/absolute/path/to/source-folder",
  "output_root": "/absolute/path/to/source-folder/Codex enhanced",
  "output_layout": "variant_dirs",
  "variants":    ["enhance_standard", "enhance_vivid"],
  "images": {
    "scene_001.jpg": {
      "crop": {"top": 0.05, "right": 0.03},
      "scene": "urban"
    },
    "scene_002.jpg": {
      "crop": {"top": 0.04},
      "boost_contrast": true,
      "reduce_blue": true
    }
  }
}

Optional per-image flags:
  boost_contrast:  true   -> stronger CLAHE contrast
  restrained:      true   -> reduced contrast and sharpening
  reduce_blue:     true   -> stronger blue saturation pullback (reduces water/sky emphasis)
  source_override: PATH   -> use this file as input
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ----------------------------------------------------------------------
# IO
# ----------------------------------------------------------------------

def load_image(path: Path) -> np.ndarray:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return np.asarray(img, dtype=np.uint8)


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------

def crop_image(arr: np.ndarray, *, top=0.0, right=0.0, left=0.0, bottom=0.0) -> np.ndarray:
    h, w = arr.shape[:2]
    t = int(round(h * top))
    b = h - int(round(h * bottom))
    l = int(round(w * left))
    r = w - int(round(w * right))
    return arr[t:b, l:r]


def save_image(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(path, quality=95)


# ----------------------------------------------------------------------
# Tone
# ----------------------------------------------------------------------

def apply_exposure(arr: np.ndarray, stops: float) -> np.ndarray:
    if stops == 0:
        return arr
    gain = 2.0 ** stops
    out = arr.astype(np.float32) * gain
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_clahe(arr: np.ndarray, clip_limit: float = 2.0, tile_grid: int = 8) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) on the L channel."""
    if clip_limit == 0:
        return arr
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    l = clahe.apply(l)
    merged = cv2.merge([l, a, b])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)


def apply_tone_curve(
    arr: np.ndarray,
    highlights: float = 0,
    shadows: float = 0,
    whites: float = 0,
    blacks: float = 0,
) -> np.ndarray:
    """
    Parametric tone curve. All inputs in [-100, 100].
    Acts on luminance via LAB L channel to avoid color shift.
    """
    if highlights == 0 and shadows == 0 and whites == 0 and blacks == 0:
        return arr

    x = np.arange(256, dtype=np.float32) / 255.0
    y = x.copy()

    if shadows:
        s = shadows / 100.0
        mask = np.power(1.0 - x, 2.0)
        y = y + s * mask * 0.30
    if highlights:
        h = highlights / 100.0
        mask = np.power(x, 2.0)
        y = y + h * mask * 0.35
    if whites:
        w = whites / 100.0
        mask = np.power(x, 4.0)
        y = y + w * mask * 0.20
    if blacks:
        b = blacks / 100.0
        mask = np.power(1.0 - x, 4.0)
        y = y + b * mask * 0.20

    y = np.clip(y, 0.0, 1.0)
    lut = (y * 255.0).astype(np.uint8)

    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b_ch = cv2.split(lab)
    l = cv2.LUT(l, lut)
    merged = cv2.merge([l, a, b_ch])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)


# ----------------------------------------------------------------------
# Color
# ----------------------------------------------------------------------

def gray_world_wb(arr: np.ndarray, strength: float = 0.25) -> np.ndarray:
    """Conservative gray-world white balance for spectral neutralization."""
    if strength == 0:
        return arr
    f = arr.astype(np.float32)
    means = f.reshape(-1, 3).mean(axis=0)
    target = means.mean()
    scale = target / np.maximum(means, 1e-6)
    scale = 1.0 + (scale - 1.0) * strength
    return np.clip(f * scale.reshape(1, 1, 3), 0, 255).astype(np.uint8)


def apply_tint(arr: np.ndarray, tint: float) -> np.ndarray:
    """Positive tint removes green cast (atmospheric haze correction)."""
    if tint == 0:
        return arr
    out = arr.astype(np.float32)
    out[:, :, 1] -= tint * 0.35
    return np.clip(out, 0, 255).astype(np.uint8)


def _smooth_mask_in_range(h: np.ndarray, h_lo: float, h_hi: float, feather: float = 3.0) -> np.ndarray:
    """Smooth 0..1 mask for H values inside [h_lo, h_hi] with linear feather."""
    m = np.zeros_like(h, dtype=np.float32)
    inside = (h >= h_lo) & (h <= h_hi)
    m[inside] = 1.0
    lo_edge = (h >= h_lo - feather) & (h < h_lo)
    hi_edge = (h > h_hi) & (h <= h_hi + feather)
    m[lo_edge] = (h[lo_edge] - (h_lo - feather)) / feather
    m[hi_edge] = ((h_hi + feather) - h[hi_edge]) / feather
    return m


def apply_hsl(
    arr: np.ndarray,
    green_sat_delta: float = 0,
    green_lum_delta: float = 0,
    blue_sat_delta: float = 0,
    blue_lum_delta: float = 0,
) -> np.ndarray:
    """Adjust vegetation (green) and water/sky (blue) HSL channels."""
    if all(x == 0 for x in [green_sat_delta, green_lum_delta, blue_sat_delta, blue_lum_delta]):
        return arr

    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # OpenCV H ranges (0..179): green about 35-85, blue about 95-130.
    g_mask = _smooth_mask_in_range(h, 35, 85)
    b_mask = _smooth_mask_in_range(h, 95, 130)

    s = s + green_sat_delta * g_mask + blue_sat_delta * b_mask
    v = v + green_lum_delta * g_mask + blue_lum_delta * b_mask

    hsv[:, :, 1] = np.clip(s, 0, 255)
    hsv[:, :, 2] = np.clip(v, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


# ----------------------------------------------------------------------
# Local
# ----------------------------------------------------------------------

def local_highlight_pullback(arr: np.ndarray, amount: float = -15) -> np.ndarray:
    """
    Pull back very bright regions (clouds, snow, salt flats). amount in [-100, 0].
    Uses a soft luminance mask over L > ~0.80.
    """
    if amount == 0:
        return arr
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l_f = l.astype(np.float32) / 255.0
    mask = np.clip((l_f - 0.78) / 0.20, 0, 1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=12)
    l_f = l_f + (amount / 100.0) * mask
    l = np.clip(l_f * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)


def local_shadow_lift(arr: np.ndarray, amount: float = +12) -> np.ndarray:
    """
    Lift only very dark terrain regions (below L=0.25). Reveals shadow detail
    in valleys, forests, and urban canyons without over-brightening mid-tones.
    """
    if amount == 0:
        return arr
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l_f = l.astype(np.float32) / 255.0
    mask = np.clip((0.25 - l_f) / 0.20, 0, 1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=40)
    l_f = l_f + (amount / 100.0) * 0.55 * mask
    l = np.clip(l_f * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)


def gentle_sharpen(arr: np.ndarray, amount: float = 0.12) -> np.ndarray:
    """
    Edge-gated unsharp: sharpen only where there is real edge energy.
    Avoids amplifying compression artifacts on homogeneous terrain.
    """
    if amount == 0:
        return arr
    f = arr.astype(np.float32)
    blurred = cv2.GaussianBlur(f, (0, 0), sigmaX=1.0)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    gate = np.clip(mag / 40.0, 0, 1)
    gate = cv2.GaussianBlur(gate, (0, 0), sigmaX=1.5)
    gate3 = np.stack([gate] * 3, axis=-1)
    sharpened = cv2.addWeighted(f, 1.0 + amount, blurred, -amount, 0)
    out = f + (sharpened - f) * gate3
    return np.clip(out, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------
# Variants
# ----------------------------------------------------------------------

VARIANT_PRESETS = {
    "enhance_standard": dict(
        # Balanced enhancement: modest contrast stretch, light sharpening.
        # Preserves spectral relationships for analysis.
        exposure=0.08, clahe_clip=1.5, highlights=-15, shadows=+8, whites=+3, blacks=-3,
        wb_strength=0.25, tint=2,
        green_sat_delta=+5, green_lum_delta=+3,
        blue_sat_delta_default=-2,
        blue_sat_delta_reduce=-8,
        cloud_pullback=-15, shadow_lift=+10, sharpen=0.08,
    ),
    "enhance_vivid": dict(
        # Stronger contrast and saturation for visual presentation.
        # Still geographically accurate; no invented features.
        exposure=0.10, clahe_clip=2.5, highlights=-20, shadows=+12, whites=+5, blacks=-4,
        wb_strength=0.30, tint=3,
        green_sat_delta=+10, green_lum_delta=+5,
        blue_sat_delta_default=-3,
        blue_sat_delta_reduce=-12,
        cloud_pullback=-18, shadow_lift=+14, sharpen=0.14,
    ),
}


def process_one(arr: np.ndarray, img_cfg: dict, variant: str) -> np.ndarray:
    p = VARIANT_PRESETS[variant].copy()

    exposure = p["exposure"]
    clahe_clip = p["clahe_clip"]
    shadows = p["shadows"]
    shadow_lift = p["shadow_lift"]

    if img_cfg.get("boost_contrast"):
        clahe_clip += 0.8
        shadows += 4
    if img_cfg.get("restrained"):
        exposure -= 0.04
        clahe_clip = max(clahe_clip - 0.5, 0.5)
        shadows -= 3
        shadow_lift -= 4

    blue_sat_delta = (
        p["blue_sat_delta_reduce"] if img_cfg.get("reduce_blue") else p["blue_sat_delta_default"]
    )

    # Per-image crop
    c = img_cfg.get("crop", {})
    arr = crop_image(
        arr,
        top=c.get("top", 0.0),
        right=c.get("right", 0.0),
        left=c.get("left", 0.0),
        bottom=c.get("bottom", 0.0),
    )

    arr = apply_exposure(arr, exposure)
    arr = apply_clahe(arr, clip_limit=clahe_clip)
    arr = apply_tone_curve(
        arr, highlights=p["highlights"], shadows=shadows,
        whites=p["whites"], blacks=p["blacks"],
    )
    arr = gray_world_wb(arr, p["wb_strength"])
    arr = apply_tint(arr, p["tint"])
    arr = apply_hsl(
        arr,
        green_sat_delta=p["green_sat_delta"], green_lum_delta=p["green_lum_delta"],
        blue_sat_delta=blue_sat_delta,
    )
    arr = local_highlight_pullback(arr, p["cloud_pullback"])
    arr = local_shadow_lift(arr, shadow_lift)
    arr = gentle_sharpen(arr, p["sharpen"])
    return arr


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> int:
    import time as _time
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to JSON config.")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    input_dir = Path(cfg["input_dir"])
    output_root = Path(cfg["output_root"])
    output_layout = str(cfg.get("output_layout") or "variant_dirs").strip().lower()
    variants = cfg.get("variants", ["enhance_standard", "enhance_vivid"])
    if output_layout not in {"variant_dirs", "flat_names"}:
        raise SystemExit(f"Unsupported output_layout: {output_layout}")

    edit_log_dir = output_root / "edit_log"
    edit_log_dir.mkdir(parents=True, exist_ok=True)
    copied_config = output_root / "satellite_enhance_config.json"
    copied_config.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    batch = {
        "source_dir": str(input_dir),
        "output_dir": str(output_root),
        "output_layout": output_layout,
        "config_path": str(copied_config),
        "variants": variants,
        "files": [],
    }

    for fname, img_cfg in cfg["images"].items():
        override = img_cfg.get("source_override")
        src = Path(override) if override else (input_dir / fname)

        if not src.exists():
            print(f"WARN: missing {src}, skipping")
            continue

        base_arr = load_image(src)
        per_file_log = {
            "file": fname,
            "scene": img_cfg.get("scene"),
            "variants": {},
        }
        for variant in variants:
            t0 = _time.monotonic()
            result = process_one(base_arr.copy(), img_cfg, variant)
            stem = Path(fname).stem
            if output_layout == "flat_names":
                out = output_root / f"{stem}_{variant}.jpg"
            else:
                out = output_root / variant / f"{stem}.jpg"
            save_image(result, out)
            elapsed = round(_time.monotonic() - t0, 2)
            per_file_log["variants"][variant] = {
                "output": str(out),
                "elapsed_seconds": elapsed,
            }
            print(f"SAVED={out} ({elapsed}s)")

        per_file_log_path = edit_log_dir / f"{Path(fname).stem}.json"
        per_file_log_path.write_text(
            json.dumps(per_file_log, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        batch["files"].append(per_file_log)

    (edit_log_dir / "batch_index.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"BATCH_INDEX={edit_log_dir / 'batch_index.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
