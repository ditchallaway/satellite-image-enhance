#!/usr/bin/env python3
"""
prepare_satellite_batch.py - thin operator wrapper for satellite_enhance.py.

Purpose:
- make `satellite-image-enhance` usable from a folder path without hand-writing JSON
- emit the skill contract bundle under `Codex enhanced/`
- keep the lower-level per-image engine in `satellite_enhance.py`
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
DEFAULT_VARIANTS = ["enhance_standard", "enhance_vivid"]


def infer_scene(name: str) -> str | None:
    lower = name.lower()
    pairs = [
        ("urban", "urban"),
        ("city", "urban"),
        ("forest", "forest"),
        ("vegeta", "vegetation"),
        ("agri", "agricultural"),
        ("farm", "agricultural"),
        ("water", "water"),
        ("river", "water"),
        ("lake", "water"),
        ("coast", "coastal"),
        ("shore", "coastal"),
        ("desert", "arid"),
        ("sand", "arid"),
        ("snow", "snow_ice"),
        ("ice", "snow_ice"),
        ("cloud", "cloudy"),
        ("night", "nighttime"),
    ]
    for marker, scene in pairs:
        if marker in lower:
            return scene
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and run a satellite-image-enhance batch.")
    parser.add_argument("--input-dir", required=True, help="Folder containing source images.")
    parser.add_argument("--output-dir", default="", help="Defaults to '<input-dir>/Codex enhanced'.")
    parser.add_argument("--pattern", action="append", default=[], help="Glob(s) to include. Repeatable.")
    parser.add_argument("--variant", action="append", default=[], help="Variant(s) to render. Defaults to enhance_standard + enhance_vivid.")
    parser.add_argument("--include-enhanced", action="store_true", help="Include files that already look enhanced.")
    parser.add_argument("--dry-run", action="store_true", help="Preview matched files and config without running satellite_enhance.py.")
    return parser


def should_skip(path: Path, include_enhanced: bool) -> bool:
    if path.suffix.lower() not in IMAGE_EXTS:
        return True
    if not include_enhanced and "enhanced" in path.stem.lower():
        return True
    return False


def discover_files(input_dir: Path, patterns: list[str], include_enhanced: bool) -> list[Path]:
    matches: list[Path] = []
    if patterns:
        for pattern in patterns:
            matches.extend([p for p in input_dir.glob(pattern) if p.is_file() and not should_skip(p, include_enhanced)])
    else:
        matches.extend([p for p in input_dir.iterdir() if p.is_file() and not should_skip(p, include_enhanced)])
    unique = sorted({p.resolve(): p for p in matches}.values(), key=lambda p: p.name.lower())
    return unique


def render_markdown_log(batch_index_path: Path, output_root: Path) -> Path:
    data = json.loads(batch_index_path.read_text(encoding="utf-8"))
    lines = [
        "# Satellite Enhancement Log",
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
            lines.append(f"- `{variant_name}` -> `{variant_meta['output']}`")
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

    output_dir = Path(args.output_dir).resolve() if args.output_dir else (input_dir / "Codex enhanced")
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = args.variant or DEFAULT_VARIANTS
    files = discover_files(input_dir, args.pattern, args.include_enhanced)
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

    config_path = output_dir / "satellite_enhance_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"CONFIG={config_path}")
    print(f"OUTPUT={output_dir}")
    print(f"MATCHED={len(files)}")
    for item in files:
        print(f"- {item.name}")

    if args.dry_run:
        return 0

    script_path = Path(__file__).with_name("satellite_enhance.py")
    cmd = [sys.executable, str(script_path), "--config", str(config_path)]
    subprocess.run(cmd, check=True)

    batch_index = output_dir / "edit_log" / "batch_index.json"
    if batch_index.exists():
        md_log = render_markdown_log(batch_index, output_dir)
        print(f"EDIT_LOG={md_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
