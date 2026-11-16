"""
Shared, editorial chart style for the Kuku content-intelligence case study.
Validated categorical palette (colorblind-checked, light surface). No gradients,
no decorative colour, no emoji. Marks are thin; titles left-aligned; only the
left/bottom spines are drawn; grid is a faint horizontal rule.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

# --- categorical palette, anchored on Kuku's brand crimson (#E41824) ----------
# Red is the brand + "problem" colour; teal is the positive/"good" colour. Kept
# dark enough to stay legible and colourblind-distinct on a white (print) surface.
PALETTE = ["#0a8a74", "#d81f27", "#2b6cb0", "#b8860b", "#b02d6a", "#6b7f14"]
TEAL, VERMILLION, STEEL, GOLD, ROSE, OLIVE = PALETTE
KUKU = VERMILLION  # brand crimson alias

# ink / surface tokens
INK      = "#1f2a2e"   # primary text
SECOND   = "#4a5560"   # secondary text
MUTED    = "#8a9298"   # muted text / axis
GRID     = "#e7e4dd"   # faint gridline
SURFACE  = "#ffffff"
SERIOUS  = VERMILLION  # status: a problem (e.g. the failure spike)
GOODCLR  = TEAL


def apply():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 10.5,
        "text.color": INK,
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.8,
        "axes.labelcolor": SECOND,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "figure.dpi": 140,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


def titled(ax, title, subtitle=None):
    """Left-aligned title + muted subtitle, editorial style."""
    ax.set_title("")
    ax.text(0, 1.10, title, transform=ax.transAxes, fontsize=13.5,
            fontweight="bold", color=INK, ha="left", va="baseline")
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=9.8,
                color=SECOND, ha="left", va="baseline")


def source_note(fig, text, x=0.0, y=-0.02):
    fig.text(x, y, text, fontsize=8, color=MUTED, ha="left", va="top")
