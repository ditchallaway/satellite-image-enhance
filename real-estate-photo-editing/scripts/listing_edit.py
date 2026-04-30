#!/usr/bin/env python3
"""
listing_edit.py - Per-image real-estate photo editor for the real-estate-photo-editing skill.

Two variants by default:
  listing_clean: restrained, clean, brighter, truthful (MLS-leaning)
  xhs_clean:     slightly brighter/whiter/polished, still looks real (social-leaning)

Pipeline per image:
  1. EXIF orientation
  2. Crop (per-image, fraction-based top/right/left/bottom)
  3. Exposure (stops)
  4. Tone curve (highlights/shadows/whites/blacks)
  5. White balance (gray-world)
  6. Tint (green removal)
  7. HSL (Yellow/Orange/Blue bands)
  8. Local window highlight pullback (luminance-masked)
  9. Local floor shadow lift (luminance-masked)
  10. Gentle sharpen

Usage:
  python listing_edit.py --config config.json

Config JSON:
{
  "input_dir":   "/absolute/path/to/source-folder",
  "output_root": "/absolute/path/to/source-folder/Codex edited",
  "output_layout": "variant_dirs",
  "variants":    ["listing_clean", "xhs_clean"],
  "images": {
    "IMG_9024.JPG": {
      "crop": {"top": 0.09, "right": 0.04},
      "scene": "living_room"
    },
    "IMG_9025.JPG": {
      "crop": {"top": 0.07},
      "brighten_more": true,
      "reduce_blue": true
    }
  }
}

Optional per-image flags:
  brighten_more:  true   -> +0.08 EV
  restrained:     true   -> -0.05 EV, reduced shadow/floor lift
  reduce_blue:    true   -> stronger blue saturation pullback
  source_override: PATH  -> use this file as input

Output layout:
  variant_dirs (default):
    <output_root>/<variant>/<stem>.jpg
  flat_names:
    <output_root>/<stem>_<variant>.jpg
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
# Hough-based auto-straighten.
# Detect dominant horizontal/vertical lines, weight-average their deviation
# angles, apply a single rotation, then inset-crop the rotation border.
# ----------------------------------------------------------------------

def detect_straighten_angle(arr: np.ndarray) -> tuple[float, float, float]:
    """
    Returns (straighten_angle_deg, hough_h_deg, hough_v_deg).
    `straighten_angle_deg` is the rotation to apply to level the image
    (positive = CCW). Keeps |angle| <= 3.0 to avoid over-rotation.
    """
    h, w = arr.shape[:2]
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 160, apertureSize=3)
    min_len = int(min(h, w) * 0.15)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 360,
        threshold=120, minLineLength=min_len, maxLineGap=12,
    )
    if lines is None or len(lines) == 0:
        return 0.0, 0.0, 0.0

    h_angles = []  # deviations from horizontal
    h_weights = []
    v_angles = []  # deviations from vertical
    v_weights = []
    for line in lines[:, 0]:
        x1, y1, x2, y2 = line
        dx = x2 - x1
        dy = y2 - y1
        length = float(np.hypot(dx, dy))
        if length < 1:
            continue
        ang = np.degrees(np.arctan2(dy, dx))  # -180..180
        # normalize to [-90, 90]
        if ang > 90:
            ang -= 180
        elif ang < -90:
            ang += 180
        if abs(ang) <= 20:
            h_angles.append(ang)
            h_weights.append(length)
        elif abs(abs(ang) - 90) <= 20:
            v_dev = ang - 90 if ang > 0 else ang + 90
            v_angles.append(v_dev)
            v_weights.append(length)

    def _wavg(vals, ws):
        if not vals:
            return 0.0
        return float(np.average(vals, weights=ws))

    h_deg = _wavg(h_angles, h_weights)
    v_deg = _wavg(v_angles, v_weights)

    # Combined estimate: horizontal lines dominate roll; vertical lines
    # confirm. Take weighted mean of the two where counts allow.
    total_h = float(sum(h_weights))
    total_v = float(sum(v_weights))
    total = total_h + total_v
    if total < 1:
        roll = 0.0
    else:
        roll = (h_deg * total_h + v_deg * total_v) / total

    # Clamp: truthful listing photo edits should rarely need more than
    # about 3 degrees. Bigger values are usually furniture edges.
    # are usually Hough picking up furniture edges.
    roll = float(np.clip(roll, -3.0, 3.0))
    return roll, h_deg, v_deg


def rotate_and_inset(arr: np.ndarray, angle_deg: float, inset_ratio: float = 0.04) -> np.ndarray:
    """Rotate CCW by `angle_deg`, then crop `inset_ratio` from all sides to
    remove the rotation border. No resize: preserves resolution."""
    if abs(angle_deg) < 0.05:
        return arr
    h, w = arr.shape[:2]
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    rotated = cv2.warpAffine(arr, M, (w, h),
                             flags=cv2.INTER_LANCZOS4,
                             borderMode=cv2.BORDER_REPLICATE)
    t = int(round(h * inset_ratio))
    l = int(round(w * inset_ratio))
    return rotated[t:h - t, l:w - l]


def save_image(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(path, quality=95)


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


# ----------------------------------------------------------------------
# Tone
# ----------------------------------------------------------------------

def apply_exposure(arr: np.ndarray, stops: float) -> np.ndarray:
    if stops == 0:
        return arr
    gain = 2.0 ** stops
    out = arr.astype(np.float32) * gain
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_tone_curve(
    arr: np.ndarray,
    highlights: float = 0,
    shadows: float = 0,
    whites: float = 0,
    blacks: float = 0,
) -> np.ndarray:
    """
    Lightroom-style parametric tone curve. All inputs in [-100, 100].
    Acts on luminance via LAB L channel to avoid color shift.
    """
    if highlights == 0 and shadows == 0 and whites == 0 and blacks == 0:
        return arr

    # Build a 256-entry LUT on [0,1]
    x = np.arange(256, dtype=np.float32) / 255.0
    y = x.copy()

    if shadows:
        s = shadows / 100.0
        mask = np.power(1.0 - x, 2.0)    # strongest at x=0
        y = y + s * mask * 0.30          # was 0.45; too aggressive on phone-JPG blocks
    if highlights:
        h = highlights / 100.0
        mask = np.power(x, 2.0)          # strongest at x=1
        y = y + h * mask * 0.35
    if whites:
        w = whites / 100.0
        mask = np.power(x, 4.0)          # very top only
        y = y + w * mask * 0.20
    if blacks:
        b = blacks / 100.0
        mask = np.power(1.0 - x, 4.0)    # very bottom only
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

def gray_world_wb(arr: np.ndarray, strength: float = 0.40) -> np.ndarray:
    if strength == 0:
        return arr
    f = arr.astype(np.float32)
    means = f.reshape(-1, 3).mean(axis=0)
    target = means.mean()
    scale = target / np.maximum(means, 1e-6)
    scale = 1.0 + (scale - 1.0) * strength
    return np.clip(f * scale.reshape(1, 1, 3), 0, 255).astype(np.uint8)


def apply_tint(arr: np.ndarray, tint: float) -> np.ndarray:
    """Positive tint removes green (shifts toward magenta)."""
    if tint == 0:
        return arr
    out = arr.astype(np.float32)
    out[:, :, 1] -= tint * 0.35  # subtract from G channel
    return np.clip(out, 0, 255).astype(np.uint8)


def _smooth_mask_in_range(h: np.ndarray, h_lo: float, h_hi: float, feather: float = 3.0) -> np.ndarray:
    """Smooth 0..1 mask for H values inside [h_lo, h_hi] with linear feather."""
    # H in OpenCV: 0..179
    m = np.zeros_like(h, dtype=np.float32)
    inside = (h >= h_lo) & (h <= h_hi)
    m[inside] = 1.0
    # feather
    lo_edge = (h >= h_lo - feather) & (h < h_lo)
    hi_edge = (h > h_hi) & (h <= h_hi + feather)
    m[lo_edge] = (h[lo_edge] - (h_lo - feather)) / feather
    m[hi_edge] = ((h_hi + feather) - h[hi_edge]) / feather
    return m


def apply_hsl(
    arr: np.ndarray,
    yellow_sat_delta: float = 0,
    yellow_lum_delta: float = 0,
    orange_sat_delta: float = 0,
    orange_lum_delta: float = 0,
    blue_sat_delta: float = 0,
    blue_lum_delta: float = 0,
) -> np.ndarray:
    if all(x == 0 for x in [yellow_sat_delta, yellow_lum_delta,
                            orange_sat_delta, orange_lum_delta,
                            blue_sat_delta,   blue_lum_delta]):
        return arr

    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # OpenCV H ranges (0..179): yellow about 20-35, orange about 10-20,
    # blue about 95-130.
    y_mask = _smooth_mask_in_range(h, 20, 35)
    o_mask = _smooth_mask_in_range(h, 10, 20)
    b_mask = _smooth_mask_in_range(h, 95, 130)

    s = s + yellow_sat_delta * y_mask + orange_sat_delta * o_mask + blue_sat_delta * b_mask
    v = v + yellow_lum_delta * y_mask + orange_lum_delta * o_mask + blue_lum_delta * b_mask

    hsv[:, :, 1] = np.clip(s, 0, 255)
    hsv[:, :, 2] = np.clip(v, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


# ----------------------------------------------------------------------
# Local
# ----------------------------------------------------------------------

def local_highlight_pullback(arr: np.ndarray, amount: float = -20) -> np.ndarray:
    """
    Pull back very bright regions (windows). amount in [-100, 0].
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


def local_shadow_lift(arr: np.ndarray, amount: float = +15) -> np.ndarray:
    """
    Lift only *very dark* floor/corner regions (below L=0.30). Mask is heavily
    blurred and attenuated so walls-in-shadow (L about 0.35-0.55) are NOT touched,
    which is where phone-JPG block noise lives and gets visibly amplified.
    """
    if amount == 0:
        return arr
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l_f = l.astype(np.float32) / 255.0
    # Only regions darker than L=0.30 (very dark floors, corners)
    mask = np.clip((0.30 - l_f) / 0.20, 0, 1)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=40)
    l_f = l_f + (amount / 100.0) * 0.60 * mask   # conservative attenuation
    l = np.clip(l_f * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)


def gentle_sharpen(arr: np.ndarray, amount: float = 0.10) -> np.ndarray:
    """
    Edge-gated unsharp: only sharpen where there is real edge energy.
    Avoids amplifying JPG-block edges on flat walls/floor gradients.
    """
    if amount == 0:
        return arr
    f = arr.astype(np.float32)
    blurred = cv2.GaussianBlur(f, (0, 0), sigmaX=1.0)
    # Edge-gate: Sobel magnitude on luma
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    gate = np.clip(mag / 40.0, 0, 1)  # 0 on flat, 1 on strong edge
    gate = cv2.GaussianBlur(gate, (0, 0), sigmaX=1.5)
    gate3 = np.stack([gate] * 3, axis=-1)
    sharpened = cv2.addWeighted(f, 1.0 + amount, blurred, -amount, 0)
    out = f + (sharpened - f) * gate3
    return np.clip(out, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------
# Variants
# ----------------------------------------------------------------------

VARIANT_PRESETS = {
    # Restrained-tuned presets. See learning_from_codex_listing_photo.md:
    # "applied restrained XHS polish lift / applied slight extra neutral-white
    # polish for social posts" - target observation: a slightly polished handheld photo,
    # not a filtered/edited look.
    "listing_clean": dict(
        exposure=0.15, highlights=-22, shadows=+10, whites=+4, blacks=-4,
        wb_strength=0.30, tint=3,
        yellow_sat_delta=-8,  yellow_lum_delta=+5,
        orange_sat_delta=-4,  orange_lum_delta=+3,
        blue_sat_delta_default=-2,
        blue_sat_delta_reduce=-8,
        window_pullback=-18, floor_lift=+5, sharpen=0.04,
    ),
    "xhs_clean": dict(
        # v5: dropped Exposure from 0.26 to 0.15, Shadows from +22 to +12,
        # Whites from +10 to +5. Also HSL halved. This matches the
        # restrained handheld-listing observation.
        exposure=0.15, highlights=-20, shadows=+12, whites=+5, blacks=-4,
        wb_strength=0.32, tint=4,
        yellow_sat_delta=-10, yellow_lum_delta=+6,
        orange_sat_delta=-5,  orange_lum_delta=+4,
        blue_sat_delta_default=-3,
        blue_sat_delta_reduce=-10,
        window_pullback=-18, floor_lift=+6, sharpen=0.05,
    ),
}


def process_one(arr: np.ndarray, img_cfg: dict, variant: str, geo_out: dict) -> np.ndarray:
    p = VARIANT_PRESETS[variant].copy()

    # --- Per-image overrides ---
    exposure = p["exposure"]
    shadows = p["shadows"]
    floor_lift = p["floor_lift"]

    if img_cfg.get("brighten_more"):
        exposure += 0.05      # smaller nudge than before
        shadows += 3
        floor_lift += 3
    if img_cfg.get("restrained"):
        exposure -= 0.04
        shadows -= 3
        floor_lift -= 3

    blue_sat_delta = p["blue_sat_delta_reduce"] if img_cfg.get("reduce_blue") else p["blue_sat_delta_default"]

    # --- Step 2: Hough-based auto-straighten + inset crop ---
    roll, h_deg, v_deg = detect_straighten_angle(arr)
    inset = float(img_cfg.get("inset_ratio", 0.04))
    if abs(roll) >= 0.05:
        arr = rotate_and_inset(arr, roll, inset_ratio=inset)
    geo_out["straighten_angle_deg"] = round(roll, 2)
    geo_out["hough_horizontal_deg"] = round(h_deg, 2)
    geo_out["hough_vertical_deg"] = round(v_deg, 2)
    geo_out["inset_ratio"] = inset if abs(roll) >= 0.05 else 0.0

    # --- Per-image crop ---
    c = img_cfg.get("crop", {})
    arr = crop_image(
        arr,
        top=c.get("top", 0.0),
        right=c.get("right", 0.0),
        left=c.get("left", 0.0),
        bottom=c.get("bottom", 0.0),
    )
    geo_out["crop"] = c

    # Pipeline
    # NOTE: Do NOT pre-denoise. cv2.edgePreservingFilter / bilateral on phone
    # JPGs turns flat walls into cartoon/watercolor swirls. Keep original
    # texture, just stay restrained on shadows/whites.

    arr = apply_exposure(arr, exposure)
    arr = apply_tone_curve(
        arr, highlights=p["highlights"], shadows=shadows,
        whites=p["whites"], blacks=p["blacks"],
    )
    arr = gray_world_wb(arr, p["wb_strength"])
    arr = apply_tint(arr, p["tint"])
    arr = apply_hsl(
        arr,
        yellow_sat_delta=p["yellow_sat_delta"], yellow_lum_delta=p["yellow_lum_delta"],
        orange_sat_delta=p["orange_sat_delta"], orange_lum_delta=p["orange_lum_delta"],
        blue_sat_delta=blue_sat_delta,
    )
    arr = local_highlight_pullback(arr, p["window_pullback"])
    arr = local_shadow_lift(arr, floor_lift)
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
    variants = cfg.get("variants", ["listing_clean", "xhs_clean"])
    if output_layout not in {"variant_dirs", "flat_names"}:
        raise SystemExit(f"Unsupported output_layout: {output_layout}")

    # JSON edit log: structured, one per image plus batch index.
    edit_log_dir = output_root / "edit_log"
    edit_log_dir.mkdir(parents=True, exist_ok=True)
    copied_config = output_root / "listing_edit_config.json"
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
            geo_out: dict = {}
            result = process_one(base_arr.copy(), img_cfg, variant, geo_out)
            stem = Path(fname).stem
            if output_layout == "flat_names":
                out = output_root / f"{stem}_{variant}.jpg"
            else:
                out = output_root / variant / f"{stem}.jpg"
            save_image(result, out)
            elapsed = round(_time.monotonic() - t0, 2)
            per_file_log["variants"][variant] = {
                "output": str(out),
                "geometry": geo_out,
                "elapsed_seconds": elapsed,
            }
            print(f"SAVED={out} ({elapsed}s)")

        # Per-image JSON
        per_file_log_path = edit_log_dir / f"{Path(fname).stem}.json"
        per_file_log_path.write_text(
            json.dumps(per_file_log, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        batch["files"].append(per_file_log)

    # Batch index
    (edit_log_dir / "batch_index.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"BATCH_INDEX={edit_log_dir / 'batch_index.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
