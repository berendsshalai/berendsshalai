"""Generate the shared transparent optical-glass treatment for profile SVGs."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

TARGETS = [
    ASSETS / "profile-identity-tech-stack.svg",
    ASSETS / "profile-overview-optical-grey-clean.svg",
    ASSETS / "profile-boundary-optical-grey-clean.svg",
    *sorted(ASSETS.glob("repo-card-*.svg")),
    *sorted(ASSETS.glob("contact-card-*.svg")),
]

DISPLAY_FONT = '"Space Grotesk",Inter,Arial,sans-serif'
BODY_FONT = 'Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif'
MONO_FONT = '"IBM Plex Mono","JetBrains Mono",Consolas,Menlo,monospace'


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
      <stop offset="0" stop-color="#E7F8EC" stop-opacity=".14"/>
      <stop offset=".34" stop-color="#DFF7E7" stop-opacity=".09"/>
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
      <stop offset="0" stop-color="#7EE787" stop-opacity=".46"/>
      <stop offset=".5" stop-color="#FFFFFF" stop-opacity=".17"/>
      <stop offset="1" stop-color="#111827" stop-opacity=".08"/>
    </linearGradient>
    <linearGradient id="chipGlass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#E7F8EC" stop-opacity=".22"/>
      <stop offset=".52" stop-color="#FFFFFF" stop-opacity=".125"/>
      <stop offset="1" stop-color="#DFF7E7" stop-opacity=".09"/>
    </linearGradient>
    <linearGradient id="chipEdge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7EE787" stop-opacity=".62"/>
      <stop offset=".5" stop-color="#FFFFFF" stop-opacity=".26"/>
      <stop offset="1" stop-color="#111827" stop-opacity=".12"/>
    </linearGradient>
    <radialGradient id="emeraldField" cx="58%" cy="48%" r="70%">
      <stop offset="0" stop-color="#3FB950" stop-opacity=".075"/>
      <stop offset=".48" stop-color="#2EA043" stop-opacity=".025"/>
      <stop offset="1" stop-color="#2EA043" stop-opacity="0"/>
    </radialGradient>
    <filter id="contactShadow" x="-20%" y="-20%" width="140%" height="150%">
      <feGaussianBlur stdDeviation="6"/>
    </filter>
    <filter id="suspensionShadow" x="-25%" y="-25%" width="150%" height="165%">
      <feGaussianBlur stdDeviation="18"/>
    </filter>
    <filter id="specularSoft" x="-10%" y="-30%" width="120%" height="160%">
      <feGaussianBlur stdDeviation="1.1"/>
    </filter>
    <filter id="borderRunnerGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.2"/>
    </filter>
    <style>
      .borderRunner{{pointer-events:none}}
      @media (prefers-reduced-motion:reduce){{.borderRunner{{display:none}}}}
    </style>
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
      <rect x="{x}" y="{y}" width="{pane_width}" height="{pane_height}" fill="url(#emeraldField)"/>
      <path d="M {x + 8} {y + 4} V {bottom - 20}" fill="none" stroke="#1F2937" stroke-opacity=".055" stroke-width="2.2" filter="url(#specularSoft)"/>
    </g>
    <rect x="{x + .7}" y="{y + .7}" width="{pane_width - 1.4}" height="{pane_height - 1.4}" rx="{radius}" fill="none" stroke="url(#outerEdge)" stroke-width="1.55"/>
    <rect x="{x + inset}" y="{y + inset}" width="{pane_width - inset * 2}" height="{pane_height - inset * 2}" rx="{max(1, radius - inset):.1f}" fill="none" stroke="url(#innerEdge)" stroke-width=".9"/>
    <rect class="borderRunner" x="{x + 1.4}" y="{y + 1.4}" width="{pane_width - 2.8}" height="{pane_height - 2.8}" rx="{max(1, radius - 1):.1f}" pathLength="100" fill="none" stroke="#3FB950" stroke-opacity=".22" stroke-width="6" stroke-linecap="round" stroke-dasharray="7 93" filter="url(#borderRunnerGlow)">
      <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="9s" repeatCount="indefinite"/>
    </rect>
    <rect class="borderRunner" x="{x + 1.4}" y="{y + 1.4}" width="{pane_width - 2.8}" height="{pane_height - 2.8}" rx="{max(1, radius - 1):.1f}" pathLength="100" fill="none" stroke="#7EE787" stroke-opacity=".78" stroke-width="1.45" stroke-linecap="round" stroke-dasharray="7 93">
      <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="9s" repeatCount="indefinite"/>
    </rect>
    <path d="M {x + 34} {bottom - 18} H {x + pane_width * .38:.1f} M {right - pane_width * .24:.1f} {y + 20} H {right - 34}" fill="none" stroke="#3FB950" stroke-opacity=".24" stroke-width="1"/>
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
    svg = re.sub(
        r"\s*<!-- EMERALD_OBSERVATORY_THEME_START -->.*?<!-- EMERALD_OBSERVATORY_THEME_END -->\s*",
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
    svg = re.sub(
        r";paint-order:stroke;stroke:#[0-9a-f]{6};stroke-opacity:[0-9.]+;stroke-width:[0-9.]+",
        "",
        svg,
        flags=re.IGNORECASE,
    )
    svg = re.sub(r"#58a6ff", "#3fb950", svg, flags=re.IGNORECASE)
    svg = re.sub(r"#b7cce0|#afc8e3|#dbe6f2", "#66707a", svg, flags=re.IGNORECASE)
    svg = re.sub(r"#58636d|#f7fbff|#f8fafc|#dce9f6", "#3a434b", svg, flags=re.IGNORECASE)
    svg = re.sub(
        r'(?:(?:"IBM Plex Mono","JetBrains Mono",)*)Consolas,Menlo,monospace',
        "__OBSERVATORY_MONO__",
        svg,
    )
    svg = re.sub(
        r'(?:(?:"IBM Plex Mono","JetBrains Mono",)*)Consolas,monospace',
        "__OBSERVATORY_MONO__",
        svg,
    )
    svg = svg.replace("__OBSERVATORY_MONO__", MONO_FONT)
    svg = svg.replace("Arial,Helvetica,sans-serif", BODY_FONT)
    svg = re.sub(r"font:800 (\d+)px " + re.escape(BODY_FONT), rf"font:600 \1px {DISPLAY_FONT}", svg)
    svg = re.sub(r"font:700 (\d+)px " + re.escape(BODY_FONT), rf"font:600 \1px {DISPLAY_FONT}", svg)
    svg = re.sub(
        r"\.value\{[^}]*\}",
        f".value{{fill:#3a434b;font:500 14px {BODY_FONT}}}",
        svg,
    )
    svg = svg.replace("with blue field labels", "with GitHub-green telemetry labels")
    observatory_theme = f'''\n  <!-- EMERALD_OBSERVATORY_THEME_START -->
  <style>
    :root{{color-scheme:light dark}}
    .blue,.label,.handle{{fill:#3FB950!important}}
    .ascii{{fill:#2F8F46!important;font-family:{MONO_FONT}}}
    .white,.value,.stackLabel{{fill:#3A434B!important}}
    .muted,.rule{{fill:#66707A!important}}
    @media (prefers-color-scheme:dark){{
      .white,.value,.stackLabel{{fill:#E6EDF3!important}}
      .muted,.rule{{fill:#A8B3BC!important}}
      .ascii{{fill:#7EE787!important}}
      .blue,.label,.handle{{fill:#56D364!important}}
    }}
  </style>
  <!-- EMERALD_OBSERVATORY_THEME_END -->'''
    svg = svg.replace("</svg>", observatory_theme + "\n</svg>")
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
  <style>
    :root{{color-scheme:light dark}}
    .display{{fill:#30363D;font-family:{DISPLAY_FONT}}}
    .body{{fill:#3A434B;font-family:{BODY_FONT}}}
    .telemetry{{fill:#3FB950;font-family:{MONO_FONT}}}
    .quiet{{fill:#66707A;font-family:{MONO_FONT}}}
    @media (prefers-color-scheme:dark){{.display,.body{{fill:#E6EDF3}}.quiet{{fill:#A8B3BC}}.telemetry{{fill:#7EE787}}}}
  </style>
  <g>
    <text x="54" y="143" class="display" font-size="46" font-weight="600" letter-spacing="1">SHA-LAI BERENDS</text>
    <text x="56" y="180" class="body" font-size="19" font-weight="500">Business Automation &amp; Data Operations Builder</text>
    <text x="56" y="218" class="telemetry" font-size="12" font-weight="500" letter-spacing=".8">OPERATIONS -&gt; EXPLICIT RULES -&gt; VALIDATED DATA -&gt; AUDITABLE SYSTEMS</text>
  </g>
  <g aria-hidden="true" fill="none" stroke="#3FB950">
    <circle cx="907" cy="127" r="61" stroke-opacity=".58"/>
    <ellipse cx="907" cy="127" rx="29" ry="61" stroke-opacity=".42"/>
    <ellipse cx="907" cy="127" rx="61" ry="24" stroke-opacity=".42"/>
    <path d="M846 127h122M907 66v122" stroke-opacity=".25"/>
    <circle cx="933" cy="103" r="3" fill="#7EE787" stroke="none"/>
    <circle cx="877" cy="147" r="2.5" fill="#56D364" stroke="none"/>
  </g>
</svg>
'''
    (ASSETS / "profile-header-transparent-v3.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    for target in TARGETS:
        generate_asset(target)
    generate_header()
    print(f"Generated {len(TARGETS) + 1} optical-glass SVG assets.")


if __name__ == "__main__":
    main()
