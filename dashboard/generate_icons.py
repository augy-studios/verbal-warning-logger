"""Run once to generate PNG icons from the SVG source.

Requires: pip install cairosvg
Usage: python3 generate_icons.py
"""
import pathlib

try:
    import cairosvg
except ImportError:
    print("cairosvg not installed. Install it with: pip install cairosvg")
    print("Alternatively, convert public/icons/icon.svg manually to:")
    print("  public/icons/icon-192.png  (192x192)")
    print("  public/icons/icon-512.png  (512x512)")
    raise SystemExit(1)

svg_path = pathlib.Path(__file__).parent / "public" / "icons" / "icon.svg"
svg_data = svg_path.read_bytes()

for size in (192, 512):
    out = svg_path.parent / f"icon-{size}.png"
    cairosvg.svg2png(bytestring=svg_data, write_to=str(out), output_width=size, output_height=size)
    print(f"Generated {out}")
