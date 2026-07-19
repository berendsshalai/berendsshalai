"""Validate transparent, self-contained optical-glass profile SVG assets."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TARGETS = [
    ASSETS / "profile-header-optical-grey-clean.svg",
    ASSETS / "profile-identity-optical-grey-clean.svg",
    ASSETS / "profile-overview-optical-grey-clean.svg",
    ASSETS / "profile-boundary-optical-grey-clean.svg",
    *sorted(ASSETS.glob("repo-card-*.svg")),
    *sorted(ASSETS.glob("contact-card-*.svg")),
]

PROHIBITED = {
    "<image": "embedded image element",
    "data:image/": "base64 or data image",
    "foreignObject": "embedded HTML",
    "backdrop-filter": "unsupported backdrop filtering",
    "GLASS_PROFILE_THEME": "obsolete raster glass theme",
    "paint-order:stroke": "text outline paint order",
}


def validate_svg(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")
    document = None
    try:
        document = ET.fromstring(text)
    except ET.ParseError as error:
        issues.append(f"invalid XML: {error}")
    for token, label in PROHIBITED.items():
        if token.lower() in text.lower():
            issues.append(label)
    root = re.search(r'<svg[^>]+width="(\d+)"[^>]+height="(\d+)"', text)
    if not root:
        issues.append("missing numeric dimensions")
        return issues
    width, height = map(int, root.groups())
    if document is not None:
        for element in document.iter():
            if element.tag.rsplit("}", 1)[-1] == "text" and ("stroke" in element.attrib or "filter" in element.attrib):
                issues.append("outlined or filtered text element")
                break
        for element in document.iter():
            if element.tag.rsplit("}", 1)[-1] != "rect":
                continue
            attributes = element.attrib
            if (
                attributes.get("x", "0") == "0"
                and attributes.get("y", "0") == "0"
                and attributes.get("width") == str(width)
                and attributes.get("height") == str(height)
            ):
                issues.append("full-canvas rectangle")
                break
    if "OPTICAL_GLASS_SYSTEM_START" not in text:
        issues.append("missing shared optical material")
    return issues


def validate_render(path: Path) -> list[str]:
    issues: list[str] = []
    with Image.open(path).convert("RGBA") as image:
        corners = ((0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1))
        alpha = [image.getpixel(point)[3] for point in corners]
    if alpha != [0, 0, 0, 0]:
        issues.append(f"corner alpha is not zero: {alpha}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rendered-dir", type=Path)
    args = parser.parse_args()
    failures: dict[str, list[str]] = {}
    for target in TARGETS:
        issues = validate_svg(target)
        if args.rendered_dir:
            rendered = args.rendered_dir / f"{target.stem}.png"
            if not rendered.exists():
                issues.append("missing rendered PNG")
            else:
                issues.extend(validate_render(rendered))
        if issues:
            failures[target.name] = issues
    if failures:
        for name, issues in failures.items():
            print(f"FAIL {name}: {', '.join(issues)}")
        raise SystemExit(1)
    summary = (
        f"PASS: {len(TARGETS)}/{len(TARGETS)} SVG assets; "
        "0 prohibited elements; 0 full-canvas rectangles; "
        f"{len(TARGETS)}/{len(TARGETS)} shared optical materials"
    )
    if args.rendered_dir:
        summary += f"; {len(TARGETS) * 4}/{len(TARGETS) * 4} canvas-corner alpha values equal 0"
    print(summary + ".")


if __name__ == "__main__":
    main()
