#!/usr/bin/env python3
"""Validate the profile repository-globe assets."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GIF = ROOT / "assets" / "repository-globe.gif"
STATIC = ROOT / "assets" / "repository-globe-static.png"


def main() -> None:
    failures: list[str] = []
    for path in (GIF, STATIC):
        if not path.exists():
            failures.append(f"missing {path.name}")
    if failures:
        raise SystemExit("FAIL: " + "; ".join(failures))

    with Image.open(GIF) as image:
        frames = getattr(image, "n_frames", 1)
        if frames < 80:
            failures.append(f"globe animation has only {frames} frames")
        if image.info.get("loop") != 0:
            failures.append("globe animation does not loop continuously")
        if "transparency" not in image.info:
            failures.append("globe animation has no transparent color")
        width, height = image.size
        if (width, height) != (560, 560):
            failures.append(f"unexpected globe dimensions {width}x{height}")
        if GIF.stat().st_size > 6 * 1024 * 1024:
            failures.append("globe animation exceeds 6 MiB")

    with Image.open(STATIC) as image:
        if image.mode != "RGBA":
            failures.append("static globe fallback is not RGBA")
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] != 0:
            failures.append("static globe background is not transparent")

    if failures:
        raise SystemExit("FAIL: " + "; ".join(failures))
    print(f"PASS: repository globe validated ({frames} frames; {GIF.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
