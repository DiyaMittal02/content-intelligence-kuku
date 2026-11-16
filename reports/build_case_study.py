"""
Render the polished case-study PDF (reports/case_study.pdf) from the real
findings + the rendered figures. Uses DejaVu Sans (same as the charts) for a
consistent, professional look with full glyph support. No gradients, no emoji.
"""
import os
import io
import matplotlib
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from PIL import Image as PILImage

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, "figures")
ASSETS = os.path.join(HERE, "..", "dashboard", "assets")
OUT = os.path.join(HERE, "case_study.pdf")

# --- fonts (match the figures) ---------------------------------------------
_ttf = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(_ttf, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(_ttf, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-It", os.path.join(_ttf, "DejaVuSans-Oblique.ttf")))

INK = colors.HexColor("#1f2a2e")
SECOND = colors.HexColor("#4a5560")
MUTED = colors.HexColor("#8a9298")
TEAL = colors.HexColor("#0a8a74")
KUKU = colors.HexColor("#d81f27")        # Kuku brand crimson (print-legible)
KUKU_DK = colors.HexColor("#b4151c")
VERM = KUKU
LIGHT = colors.HexColor("#f4f2ec")
TILEBG = colors.HexColor("#fbeced")      # faint red tint for stat tiles
WHITE = colors.white


def logo_flowable(side=0.62 * inch):
    """Load the real Kuku FM app icon, re-encode PNG, return a reportlab Image."""
    for cand in ("kuku_fm_logo.png", "kuku_fm_icon.png"):
        p = os.path.join(ASSETS, cand)
        if os.path.exists(p):
            buf = io.BytesIO()
            PILImage.open(p).convert("RGB").save(buf, format="PNG")
            buf.seek(0)
            return Image(buf, width=side, height=side)
    return ""


S = {
    "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=19, leading=23,
                            textColor=INK, spaceAfter=2),
    "htitle": ParagraphStyle("htitle", fontName="DejaVu-Bold", fontSize=18, leading=21,
                             textColor=WHITE, spaceAfter=2),
    "hby": ParagraphStyle("hby", fontName="DejaVu", fontSize=8.8, leading=12,
                          textColor=colors.HexColor("#ffe3e5")),
    "byline": ParagraphStyle("byline", fontName="DejaVu", fontSize=9.5, leading=13,
                             textColor=SECOND),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12.5, leading=15,
                         textColor=KUKU, spaceBefore=12, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.6, leading=13.6,
                          textColor=INK, spaceAfter=5, alignment=TA_LEFT),
    "cap": ParagraphStyle("cap", fontName="DejaVu-It", fontSize=8, leading=10.5,
                         textColor=MUTED, spaceAfter=10),
    "notice": ParagraphStyle("notice", fontName="DejaVu", fontSize=8.3, leading=11.5,
                            textColor=SECOND),
    "th": ParagraphStyle("th", fontName="DejaVu-Bold", fontSize=8.6, leading=11, textColor=INK),
    "td": ParagraphStyle("td", fontName="DejaVu", fontSize=8.6, leading=11, textColor=INK),
    "tilenum": ParagraphStyle("tilenum", fontName="DejaVu-Bold", fontSize=16, leading=18,
                              textColor=KUKU, alignment=TA_CENTER),
    "tilelab": ParagraphStyle("tilelab", fontName="DejaVu", fontSize=7.3, leading=9,
                              textColor=SECOND, alignment=TA_CENTER),
}


def fig(name, caption, width=6.6*inch):
    img = Image(os.path.join(FIG, name))
    img._restrictSize(width, 9*inch)
    return [img, Paragraph(caption, S["cap"])]


def build():
    doc = SimpleDocTemplate(OUT, pagesize=LETTER,
                            leftMargin=0.8*inch, rightMargin=0.8*inch,
                            topMargin=0.7*inch, bottomMargin=0.6*inch,
                            title="Micro-drama & Audio Content Intelligence — Kuku")
    E = []

    # --- branded cover band (Kuku red + real app icon) ---------------------
    head_txt = [Paragraph("Micro-drama &amp; Audio Content Intelligence", S["htitle"]),
                Paragraph("A product-analytics case study modelled on Kuku (Kuku FM audio "
                          "+ Kuku TV micro-dramas) &nbsp;·&nbsp; Diya Mittal, ex-Product "
                          "Analyst intern at Pocket FM (Scout) &nbsp;·&nbsp; November 2026",
                          S["hby"])]
    logo = logo_flowable()
    band = Table([[logo, head_txt]], colWidths=[0.95 * inch, 5.95 * inch])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), KUKU),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 12), ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    E.append(band)
    E.append(Spacer(1, 10))

    # --- headline-stat strip ----------------------------------------------
    def tile(num, lab):
        return [Paragraph(num, S["tilenum"]), Paragraph(lab, S["tilelab"])]
    tiles = Table([[tile("4.9%", "subscribe rate<br/>(synthetic funnel)"),
                    tile("+7.1pp", "later-paywall A/B lift<br/>(synthetic)"),
                    tile("~24%", "of real reviews cite<br/>payments &amp; autopay"),
                    tile("1,200", "real Play Store<br/>reviews analysed")]],
                   colWidths=[1.725 * inch] * 4)
    tiles.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TILEBG),
        ("LINEABOVE", (0, 0), (-1, 0), 2, KUKU),
        ("INNERGRID", (0, 0), (-1, -1), 6, WHITE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    E.append(tiles)
    E.append(Spacer(1, 12))

    notice = Table([[Paragraph(
        "<b>Synthetic data notice.</b> Product metrics below (funnel, retention, revenue, the "
        "A/B test) come from a reproducible <b>synthetic</b> dataset and are not Kuku's real "
        "numbers. The Voice-of-customer section uses <b>real public Play Store reviews</b> and is "
        "labelled as such. The two kinds of evidence are kept separate throughout.",
        S["notice"])]], colWidths=[6.9*inch])
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, VERM),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    E.append(notice)
    E.append(Spacer(1, 10))

    E.append(Paragraph("The problem", S["h2"]))
    E.append(Paragraph(
        "Micro-drama and audio apps live or die on <b>early retention and paywall conversion</b>. "
        "For a Kuku-shaped product I asked: where do new users drop out between install and a paid "
        "subscription, and how much of that is the content versus the paywall? I modelled a realistic "
        "funnel on synthetic data and triangulated it against real Play Store review themes.", S["body"]))

    E.append(Paragraph("Evidence — simulated analytics (synthetic data)", S["h2"]))
    E.append(Paragraph(
        "Of 50,000 synthetic signups, 99% play an episode but only <b>47% activate</b> (3+ episodes in "
        "72 hours), and just <b>4.9% subscribe</b>. The two leaks that matter are activation and the "
        "paywall.", S["body"]))
    E += fig("fig_funnel.png", "Figure 1. Activation-to-subscription funnel (synthetic).")
    E.append(Paragraph(
        "Retention depends sharply on genre. Thrillers and horror win day 1 with a strong first-episode "
        "hook but decay fastest, so their D30 is near zero; drama and romance start lower but hold far "
        "better. A high-hook title needs episodic cliff-hangers to convert its day-1 advantage into a "
        "month-long habit.", S["body"]))
    E += fig("fig_retention_genre.png", "Figure 2. D1 vs D30 retention by genre of first watched title (synthetic).")
    E.append(Paragraph(
        "Inside a series, the single biggest drop is <b>at the paywall episode (a 77% step-drop versus "
        "~25% at other early episodes)</b> — so it is the wall, not the content, that loses users. A "
        "simulated A/B test moving the paywall from episode 6 to episode 8 lifts the subscribe rate "
        "among wall-reachers from 25.1% to 32.3% (<b>+7.1pp, 95% CI ±2.5pp</b>), at the cost of two free "
        "episodes.", S["body"]))
    E += fig("fig_paywall_cliff.png", "Figure 3. Episode survival by paywall position (synthetic).")
    E += fig("fig_payment_spike.png", "Figure 4. A simulated one-week UPI payment-failure incident (synthetic).")

    E.append(Paragraph("Evidence — observed public feedback (real reviews)", S["h2"]))
    E.append(Paragraph(
        "I collected 1,200 real public Play Store reviews (600 each for Kuku FM and Kuku TV, India, "
        "Aug–Nov 2026; usernames discarded) and tagged them with transparent keyword rules. The reviews "
        "are self-selected and strongly polarised, so I read the <i>themes</i>, not the average star. The "
        "single largest complaint is <b>payments and autopay (~24% of reviews, average 1.2 stars)</b>: an "
        "unexpected trial-to-subscription charge and hard cancellation. This lands on exactly the paywall "
        "and payment steps the synthetic funnel flags.", S["body"]))
    E += fig("fig_review_themes.png", "Figure 5. Most-discussed review themes (real public reviews; red = avg rating below 2.5).")

    E.append(Paragraph("Recommendations", S["h2"]))
    rec = [[Paragraph("#", S["th"]), Paragraph("Recommendation", S["th"]),
            Paragraph("Why", S["th"]), Paragraph("Experiment", S["th"])],
           [Paragraph("1", S["td"]),
            Paragraph("Move the micro-drama paywall from ep 6 to ep 8 for high-hook genres.", S["td"]),
            Paragraph("Synthetic readout: +7.1pp subscribe among wall-reachers.", S["td"]),
            Paragraph("A/B; primary metric paywall→subscribe; guardrail ARPPU &amp; total revenue.", S["td"])],
           [Paragraph("2", S["td"]),
            Paragraph("Make the trial-to-paid moment explicit (price, consent, one-tap cancel) and add UPI-failure retry.", S["td"]),
            Paragraph("Payments is the #1 real complaint; a simulated failure week visibly dents conversion.", S["td"]),
            Paragraph("Pre/post + holdout; primary metric payment success &amp; refund rate.", S["td"])],
           [Paragraph("3", S["td"]),
            Paragraph("Genre-aware retention: cliff-hanger notifications for high-hook genres.", S["td"]),
            Paragraph("High D1 / low D30 genres leak the month after a strong start.", S["td"]),
            Paragraph("A/B on notification cadence; primary metric D7 retention.", S["td"])]]
    t = Table(rec, colWidths=[0.3*inch, 2.5*inch, 2.0*inch, 2.1*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TILEBG),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, KUKU),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#e0ddd5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    E.append(t)
    E.append(Spacer(1, 8))

    E.append(Paragraph("What I'd do next", S["h2"]))
    E.append(Paragraph(
        "Instrument the real paywall and payment funnel to confirm the cliff; size the ep6→ep8 revenue "
        "trade-off on real ARPPU; connect each review theme to a funnel step with event-level tagging; "
        "and track the payments theme across app versions to see whether fixes land.", S["body"]))
    E.append(Spacer(1, 4))
    E.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0ddd5")))
    E.append(Paragraph(
        "Every insight is tagged as observed public feedback, simulated analytical result, product "
        "hypothesis, or validation needed. Synthetic figures are never presented as Kuku's real "
        "performance. Method, sample size and collection date for the reviews are in the repository.",
        S["cap"]))

    doc.build(E)
    print("Wrote", OUT)


if __name__ == "__main__":
    build()
