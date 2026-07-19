"""Generate the shared transparent optical-glass treatment for profile SVGs."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

TARGETS = [
    ASSETS / "profile-identity-optical.svg",
    ASSETS / "profile-overview-optical.svg",
    ASSETS / "profile-boundary-optical.svg",
    *sorted(ASSETS.glob("repo-card-*.svg")),
    *sorted(ASSETS.glob("contact-card-*.svg")),
]


def dimensions(svg: str) -> tuple[int, int]:
    match = re.search(r'<svg[^>]+width="(\d+)"[^>]+height="(\d+)"', svg)
    if not match:
        raise ValueError("SVG width and height are required")
    return int(match.group(1)), int(match.group(2))


def pane_geometry(width: int, height: int) -> tuple[int, int, int, int, int]:
    if (width, height) == (1000, 264):
        return 18, 18, 964, 228, 34
    margin = 12 if width >= 900 else 8
    x = margin
    y = margin
    pane_width = width - margin * 2
    pane_height = height - margin * 2
    radius = max(16, min(36, round(pane_height * 0.12)))
    return x, y, pane_width, pane_height, radius


def optical_material(width: int, height: int) -> str:
    x, y, pane_width, pane_height, radius = pane_geometry(width, height)
    right = x + pane_width
    bottom = y + pane_height
    inset = 2.2
    side_end = x + pane_width * 0.34
    top_y = y + 0.7
    return f'''  <!-- OPTICAL_GLASS_SYSTEM_START -->
  <defs>
    <clipPath id="glassPaneClip"><rect x="{x}" y="{y}" width="{pane_width}" height="{pane_height}" rx="{radius}"/></clipPath>
    <clipPath id="canvasSafe"><rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="8"/></clipPath>
    <linearGradient id="opticalGlassBody" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".13"/>
      <stop offset=".34" stop-color="#FFFFFF" stop-opacity=".08"/>
      <stop offset=".68" stop-color="#F8FAFC" stop-opacity=".052"/>
      <stop offset="1" stop-color="#F3F4FA" stop-opacity=".032"/>
    </linearGradient>
    <linearGradient id="sideDepth" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#EAF2FF" stop-opacity=".12"/>
      <stop offset=".34" stop-color="#EDF0F8" stop-opacity=".085"/>
      <stop offset=".72" stop-color="#F3F4FA" stop-opacity=".032"/>
      <stop offset="1" stop-color="#F3F4FA" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="ambientLight" cx="16%" cy="3%" r="72%">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".17"/>
      <stop offset=".28" stop-color="#FFFFFF" stop-opacity=".048"/>
      <stop offset=".72" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="lowerShade" x1="0" y1="0" x2="0" y2="1">
      <stop offset=".68" stop-color="#111827" stop-opacity="0"/>
      <stop offset="1" stop-color="#111827" stop-opacity=".052"/>
    </linearGradient>
    <linearGradient id="outerEdge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".82"/>
      <stop offset=".28" stop-color="#FFFFFF" stop-opacity=".48"/>
      <stop offset=".62" stop-color="#FFFFFF" stop-opacity=".22"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity=".13"/>
    </linearGradient>
    <linearGradient id="innerEdge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#EAF2FF" stop-opacity=".34"/>
      <stop offset=".5" stop-color="#FFFFFF" stop-opacity=".17"/>
      <stop offset="1" stop-color="#111827" stop-opacity=".08"/>
    </linearGradient>
    <linearGradient id="chipGlass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".20"/>
      <stop offset=".52" stop-color="#FFFFFF" stop-opacity=".125"/>
      <stop offset="1" stop-color="#EDF0F8" stop-opacity=".09"/>
    </linearGradient>
    <linearGradient id="chipEdge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity=".58"/>
      <stop offset=".5" stop-color="#FFFFFF" stop-opacity=".26"/>
      <stop offset="1" stop-color="#111827" stop-opacity=".12"/>
    </linearGradient>
    <filter id="contactShadow" x="-20%" y="-20%" width="140%" height="150%">
      <feGaussianBlur stdDeviation="6"/>
    </filter>
    <filter id="suspensionShadow" x="-25%" y="-25%" width="150%" height="165%">
      <feGaussianBlur stdDeviation="18"/>
    </filter>
    <filter id="specularSoft" x="-10%" y="-30%" width="120%" height="160%">
      <feGaussianBlur stdDeviation="1.1"/>
    </filter>
  </defs>
  <g aria-hidden="true">
    <g clip-path="url(#canvasSafe)">
      <rect x="{x + 3}" y="{y + 11}" width="{pane_width - 6}" height="{pane_height - 6}" rx="{radius}" fill="none" stroke="#111827" stroke-opacity=".10" stroke-width="5" filter="url(#suspensionShadow)"/>
      <rect x="{x + 2}" y="{y + 5}" width="{pane_width - 4}" height="{pane_height - 4}" rx="{radius}" fill="none" stroke="#111827" stroke-opacity=".15" stroke-width="2" filter="url(#contactShadow)"/>
    </g>
    <rect x="{x}" y="{y}" width="{pane_width}" height="{pane_height}" rx="{radius}" fill="url(#opticalGlassBody)"/>
    <g clip-path="url(#glassPaneClip)">
      <rect x="{x}" y="{y}" width="{side_end - x:.1f}" height="{pane_height}" fill="url(#sideDepth)"/>
      <rect x="{x}" y="{y}" width="{pane_width}" height="{pane_height}" fill="url(#ambientLight)"/>
      <rect x="{x}" y="{y}" width="{pane_width}" height="{pane_height}" fill="url(#lowerShade)"/>
      <path d="M {x + 8} {y + 4} V {bottom - 20}" fill="none" stroke="#1F2937" stroke-opacity=".055" stroke-width="2.2" filter="url(#specularSoft)"/>
    </g>
    <rect x="{x + .7}" y="{y + .7}" width="{pane_width - 1.4}" height="{pane_height - 1.4}" rx="{radius}" fill="none" stroke="url(#outerEdge)" stroke-width="1.55"/>
    <rect x="{x + inset}" y="{y + inset}" width="{pane_width - inset * 2}" height="{pane_height - inset * 2}" rx="{max(1, radius - inset):.1f}" fill="none" stroke="url(#innerEdge)" stroke-width=".9"/>
    <path d="M {x + radius * .62:.1f} {top_y} C {x + pane_width * .18:.1f} {y - .2:.1f}, {x + pane_width * .30:.1f} {y + .2:.1f}, {x + pane_width * .42:.1f} {top_y}" fill="none" stroke="#FFFFFF" stroke-opacity=".82" stroke-width="1.65" stroke-linecap="round" filter="url(#specularSoft)"/>
    <path d="M {x + radius * .34:.1f} {y + radius * .78:.1f} C {x - .2:.1f} {y + pane_height * .22:.1f}, {x + .4:.1f} {y + pane_height * .46:.1f}, {x + 1:.1f} {y + pane_height * .62:.1f}" fill="none" stroke="#FFFFFF" stroke-opacity=".52" stroke-width="1.35" stroke-linecap="round"/>
    <path d="M {right - radius * 1.85:.1f} {top_y} C {right - radius * 1.18:.1f} {y:.1f}, {right - radius * .55:.1f} {y + 2:.1f}, {right - radius * .30:.1f} {y + radius * .38:.1f}" fill="none" stroke="#FFFFFF" stroke-opacity=".68" stroke-width="1.45" stroke-linecap="round" filter="url(#specularSoft)"/>
    <path d="M {right - .9:.1f} {y + pane_height * .28:.1f} V {y + pane_height * .43:.1f}" fill="none" stroke="#FFFFFF" stroke-opacity=".27" stroke-width="1.1" stroke-linecap="round"/>
    <path d="M {x + pane_width * .68:.1f} {bottom - .9:.1f} H {right - radius * .72:.1f}" fill="none" stroke="#FFFFFF" stroke-opacity=".16" stroke-width="1" stroke-linecap="round"/>
    <path d="M {x + pane_width * .79:.1f} {bottom - 2.7:.1f} H {right - radius * .62:.1f} M {right - 2.7:.1f} {y + pane_height * .55:.1f} V {bottom - radius * .70:.1f}" fill="none" stroke="#111827" stroke-opacity=".075" stroke-width="1.05" stroke-linecap="round"/>
    <path d="M {x + 30} {bottom - 2.0:.1f} Q {x + 58} {bottom - 5.0:.1f} {x + 92} {bottom - 2.0:.1f}" fill="none" stroke="#FFFFFF" stroke-opacity=".13" stroke-width="1.2" stroke-linecap="round" filter="url(#specularSoft)"/>
  </g>
  <!-- OPTICAL_GLASS_SYSTEM_END -->
'''


def clean_old_theme(svg: str) -> str:
    svg = re.sub(
        r"\s*<!-- GLASS_PROFILE_THEME -->.*?(?=\s*<title)",
        "\n",
        svg,
        flags=re.DOTALL,
    )
    svg = re.sub(
        r"\s*<!-- OPTICAL_GLASS_SYSTEM_START -->.*?<!-- OPTICAL_GLASS_SYSTEM_END -->\s*",
        "\n",
        svg,
        flags=re.DOTALL,
    )
    svg = re.sub(r'\s*<rect[^>]+class="bg"\s*/>', "", svg)
    svg = re.sub(r'\s*<path d="M 28 5 H \d+"[^>]*/>', "", svg)
    return svg


def restyle(svg: str) -> str:
    svg = re.sub(r"\.bg\{[^}]*\}", ".bg{fill:none;stroke:none}", svg)
    svg = re.sub(
        r"\.card\{[^}]*\}",
        ".card{fill:url(#chipGlass);stroke:url(#chipEdge);stroke-width:1}",
        svg,
    )
    svg = svg.replace("fill:#f7fbff", "fill:#dce9f6;paint-order:stroke;stroke:#111827;stroke-opacity:.92;stroke-width:1.65")
    svg = svg.replace("fill:#afc8e3", "fill:#b7cce0;paint-order:stroke;stroke:#111827;stroke-opacity:.88;stroke-width:1.45")
    svg = re.sub(
        r"fill:#58a6ff(?:;paint-order:stroke;stroke:#07111f;stroke-opacity:\.82;stroke-width:1\.05)*",
        "fill:#58a6ff;paint-order:stroke;stroke:#07111f;stroke-opacity:.82;stroke-width:1.05",
        svg,
    )
    svg = svg.replace("stroke-opacity:.76;stroke-width:1.15", "stroke-opacity:.92;stroke-width:1.65")
    svg = svg.replace("stroke-opacity:.72;stroke-width:1.0", "stroke-opacity:.88;stroke-width:1.45")
    svg = svg.replace("stroke-opacity:.72;stroke-width:.85", "stroke-opacity:.82;stroke-width:1.05")
    svg = svg.replace("fill:#f8fafc;paint-order:stroke", "fill:#dce9f6;paint-order:stroke")
    svg = svg.replace("fill:#dbe6f2;paint-order:stroke", "fill:#b7cce0;paint-order:stroke")
    return svg


def generate_asset(path: Path) -> None:
    svg = clean_old_theme(path.read_text(encoding="utf-8"))
    width, height = dimensions(svg)
    opening = re.search(r"<svg[^>]*>", svg)
    assert opening
    svg = svg[: opening.end()] + "\n" + optical_material(width, height) + svg[opening.end() :]
    path.write_text(restyle(svg).rstrip() + "\n", encoding="utf-8")


def generate_header() -> None:
    width, height = 1000, 264
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Sha-Lai Berends profile header</title>
  <desc id="desc">Business Automation and Data Operations Builder.</desc>
{optical_material(width, height)}
  <g paint-order="stroke" stroke="#111827" stroke-opacity=".92" stroke-width="1.65">
    <text x="54" y="85" fill="#58A6FF" font-family="Consolas,Menlo,monospace" font-size="13" font-weight="700" letter-spacing="2">BERENDSSHALAI // SYSTEMS LAB</text>
    <text x="54" y="145" fill="#DCE9F6" font-family="Arial,Helvetica,sans-serif" font-size="46" font-weight="800">Sha-Lai Berends</text>
    <text x="56" y="183" fill="#DCE9F6" font-family="Arial,Helvetica,sans-serif" font-size="20" font-weight="600">Business Automation &amp; Data Operations Builder</text>
    <text x="56" y="218" fill="#B7CCE0" font-family="Consolas,Menlo,monospace" font-size="12">OPERATIONS -&gt; EXPLICIT RULES -&gt; VALIDATED DATA -&gt; AUDITABLE SYSTEMS</text>
  </g>
  <g aria-hidden="true">
    <circle cx="916" cy="102" r="35" fill="url(#chipGlass)" stroke="url(#chipEdge)"/>
    <path d="M 891 82 Q 916 69 941 82" fill="none" stroke="#FFFFFF" stroke-opacity=".48" stroke-width="1" stroke-linecap="round"/>
  </g>
  <text x="916" y="108" text-anchor="middle" fill="#DCE9F6" paint-order="stroke" stroke="#111827" stroke-opacity=".92" stroke-width="1.45" font-family="Consolas,Menlo,monospace" font-size="13" font-weight="800">SB</text>
</svg>
'''
    (ASSETS / "profile-header-optical.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    for target in TARGETS:
        generate_asset(target)
    generate_header()
    print(f"Generated {len(TARGETS) + 1} optical-glass SVG assets.")


if __name__ == "__main__":
    main()
