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
        if frames < 48:
            failures.append(f"globe animation has only {frames} frames")
        if image.info.get("loop") != 0:
            failures.append("globe animation does not loop continuously")
        if "transparency" not in image.info:
            failures.append("globe animation has no transparent background")
        width, height = image.size
        if (width, height) != (560, 560):
            failures.append(f"unexpected globe dimensions {width}x{height}")
        if GIF.stat().st_size > 12 * 1024 * 1024:
            failures.append("globe animation exceeds 12 MiB")

    with Image.open(STATIC) as image:
        if image.mode != "RGBA":
            failures.append(f"unexpected static globe mode {image.mode}")
        else:
            alpha = image.getchannel("A")
            extrema = alpha.getextrema()
            corners = [
                alpha.getpixel((0, 0)),
                alpha.getpixel((image.width - 1, 0)),
                alpha.getpixel((0, image.height - 1)),
                alpha.getpixel((image.width - 1, image.height - 1)),
            ]
            if extrema != (0, 255):
                failures.append(f"static globe alpha range is {extrema}, expected (0, 255)")
            if any(corners):
                failures.append("static globe corners are not fully transparent")

    if failures:
        raise SystemExit("FAIL: " + "; ".join(failures))
    print(f"PASS: repository globe validated ({frames} frames; {GIF.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
