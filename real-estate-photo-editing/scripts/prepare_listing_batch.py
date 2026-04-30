#!/usr/bin/env python3
"""
prepare_listing_batch.py - thin operator wrapper for listing_edit.py.

Purpose:
- make `real-estate-photo-editing` usable from a folder path without hand-writing JSON
- emit the skill contract bundle under `Codex edited/`
- keep the lower-level per-image engine in `listing_edit.py`
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_VARIANTS = ["listing_clean", "xhs_clean"]


def infer_scene(name: str) -> str | None:
    lower = name.lower()
    pairs = [
        ("bath", "bathroom"),
        ("bed", "bedroom"),
        ("kitchen", "kitchen"),
        ("living", "living_room"),
        ("dining", "dining_area"),
        ("entry", "entry"),
        ("hall", "hallway"),
        ("closet", "detail"),
        ("exterior", "detail"),
    ]
    for marker, scene in pairs:
        if marker in lower:
            return scene
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and run a real-estate-photo-editing batch.")
    parser.add_argument("--input-dir", required=True, help="Folder containing source images.")
    parser.add_argument("--output-dir", default="", help="Defaults to '<input-dir>/Codex edited'.")
    parser.add_argument("--pattern", action="append", default=[], help="Glob(s) to include. Repeatable.")
    parser.add_argument("--variant", action="append", default=[], help="Variant(s) to render. Defaults to listing_clean + xhs_clean.")
    parser.add_argument("--include-edited", action="store_true", help="Include files that already look edited.")
    parser.add_argument("--dry-run", action="store_true", help="Preview matched files and config without running listing_edit.py.")
    return parser


def should_skip(path: Path, include_edited: bool) -> bool:
    if path.suffix.lower() not in IMAGE_EXTS:
        return True
    if not include_edited and "edited" in path.stem.lower():
        return True
    return False


def discover_files(input_dir: Path, patterns: list[str], include_edited: bool) -> list[Path]:
    matches: list[Path] = []
    if patterns:
        for pattern in patterns:
            matches.extend([p for p in input_dir.glob(pattern) if p.is_file() and not should_skip(p, include_edited)])
    else:
        matches.extend([p for p in input_dir.iterdir() if p.is_file() and not should_skip(p, include_edited)])
    unique = sorted({p.resolve(): p for p in matches}.values(), key=lambda p: p.name.lower())
    return unique


def render_markdown_log(batch_index_path: Path, output_root: Path) -> Path:
    data = json.loads(batch_index_path.read_text(encoding="utf-8"))
    lines = [
        "# Listing Edit Log",
        "",
        f"- Source dir: `{data['source_dir']}`",
        f"- Output dir: `{data['output_dir']}`",
        f"- Output layout: `{data.get('output_layout', 'unknown')}`",
        f"- Config: `{data.get('config_path', '')}`",
        f"- Variants: `{', '.join(data.get('variants', []))}`",
        "",
    ]
    for item in data.get("files", []):
        scene = item.get("scene") or "unspecified"
        lines.append(f"## {item['file']}")
        lines.append("")
        lines.append(f"- Scene: `{scene}`")
        for variant_name, variant_meta in item.get("variants", {}).items():
            geo = variant_meta.get("geometry", {})
            angle = geo.get("straighten_angle_deg", 0)
            crop = geo.get("crop") or {}
            lines.append(f"- `{variant_name}` -> `{variant_meta['output']}`")
            lines.append(f"  - straighten: `{angle} deg`")
            if crop:
                lines.append(f"  - crop: `{json.dumps(crop, ensure_ascii=False)}`")
            lines.append(f"  - elapsed: `{variant_meta.get('elapsed_seconds', '?')}s`")
        lines.append("")
    out = output_root / "edit_log.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")
    if not input_dir.is_dir():
        raise SystemExit(f"Input path is not a directory: {input_dir}")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else (input_dir / "Codex edited")
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = args.variant or DEFAULT_VARIANTS
    files = discover_files(input_dir, args.pattern, args.include_edited)
    if not files:
        raise SystemExit("No matching source images found.")

    config = {
        "input_dir": str(input_dir),
        "output_root": str(output_dir),
        "output_layout": "variant_dirs",
        "variants": variants,
        "images": {},
    }
    for path in files:
        entry: dict[str, object] = {}
        scene = infer_scene(path.name)
        if scene:
            entry["scene"] = scene
        config["images"][path.name] = entry

    config_path = output_dir / "listing_edit_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"CONFIG={config_path}")
    print(f"OUTPUT={output_dir}")
    print(f"MATCHED={len(files)}")
    for item in files:
        print(f"- {item.name}")

    if args.dry_run:
        return 0

    script_path = Path(__file__).with_name("listing_edit.py")
    cmd = [sys.executable, str(script_path), "--config", str(config_path)]
    subprocess.run(cmd, check=True)

    batch_index = output_dir / "edit_log" / "batch_index.json"
    if batch_index.exists():
        md_log = render_markdown_log(batch_index, output_dir)
        print(f"EDIT_LOG={md_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
