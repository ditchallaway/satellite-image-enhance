#!/usr/bin/env python3
"""Check optional local capabilities for the public satellite-image-enhance skill."""

from __future__ import annotations

import importlib.util
import shutil
import sys


PACKAGES = ["PIL", "numpy", "cv2"]


def main() -> int:
    print("satellite-image-enhance capability check")
    print(f"python: {sys.version.split()[0]}")

    ok = True
    for package in PACKAGES:
        found = importlib.util.find_spec(package) is not None
        print(f"{package}: {'ok' if found else 'missing'}")
        ok = ok and found

    for binary in ["gdal_translate", "gdalinfo"]:
        path = shutil.which(binary)
        if path:
            print(f"{binary}: optional found at {path}")
        else:
            print(f"{binary}: optional missing")

    if not ok:
        print("Install optional local script dependencies with:")
        print("python -m pip install pillow numpy opencv-python")
        return 1

    print("required local script dependencies: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
