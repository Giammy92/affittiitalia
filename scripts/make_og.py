"""Render the social preview image (site/og.png, 1200x630) from the Milano map data."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

ROOT = Path(__file__).resolve().parent.parent
COLORS = ["#fef0d9", "#fdd49e", "#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#990000"]
ND = "#cbd5e0"
INK = "#14213d"
ACCENT = "#e4572e"


def color_for(mid, breaks):
    if mid is None:
        return ND
    i = 0
    while i < len(breaks) and mid >= breaks[i]:
        i += 1
    return COLORS[i]


def main():
    index = json.loads((ROOT / "site/data/index.json").read_text(encoding="utf-8"))
    fc = json.loads((ROOT / "site/data/015146.geojson").read_text(encoding="utf-8"))
    breaks = index["breaks"]
    n_cities = len(index["cities"])

    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor="white")
    ax = fig.add_axes([0.55, 0.05, 0.43, 0.90])
    ax.set_aspect(1 / 0.70)  # cos(45.5°): keeps Milano's proportions
    ax.axis("off")
    for f in fc["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for rings in polys:
            ax.add_patch(MplPolygon(rings[0], closed=True, facecolor=color_for(f["properties"]["loc_mid"], breaks),
                                    edgecolor="white", linewidth=1.2))
    ax.autoscale_view()

    fig.text(0.05, 0.86, "Affitti", fontsize=30, color=INK, fontweight="bold", va="top")
    fig.text(0.05 + 0.118, 0.86, "Italia", fontsize=30, color=ACCENT, fontweight="bold", va="top")
    fig.text(0.05, 0.70, "Quanto costa l'affitto,\nzona per zona", fontsize=34, color=INK,
             fontweight="bold", va="top", linespacing=1.15)
    fig.text(0.05, 0.40, f"Valori ufficiali OMI · Agenzia delle Entrate\n{n_cities} città · cerca un indirizzo · filtra per budget",
             fontsize=15, color="#4a5568", va="top", linespacing=1.5)
    # legend strip
    for i, c in enumerate(COLORS):
        fig.patches.append(plt.Rectangle((0.05 + i * 0.045, 0.17), 0.043, 0.035, color=c, transform=fig.transFigure))
    fig.text(0.05, 0.13, "< 8 €/m²", fontsize=11, color="#718096", va="top")
    fig.text(0.05 + 7 * 0.045, 0.13, "≥ 25 €/m²", fontsize=11, color="#718096", va="top", ha="right")
    fig.text(0.05, 0.07, "giammy92.github.io/affittiitalia", fontsize=13, color=INK, va="top", fontweight="bold")

    out = ROOT / "site" / "og.png"
    fig.savefig(out, dpi=100, facecolor="white")
    print("wrote", out)


if __name__ == "__main__":
    main()
