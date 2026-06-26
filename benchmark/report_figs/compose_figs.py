#!/usr/bin/env python
"""Compose the standalone benchmark figures (F1-F11) into clean multi-panel
composites for the khchao.com WGT blog post + technical report.

Each composite normalizes its source PNGs to a common height, lays them out in a
row with white gutters, and prints an (A)/(B)/(C) panel label in a top margin.
Single-panel figures are copied (lightly downscaled) as-is.

Run with the spliceai env python (Pillow 9.5 + matplotlib for the font):
  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/compose_figs.py
"""
import os
import shutil
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager

SRC = os.path.dirname(os.path.abspath(__file__))
SITE = "/ccb/salz3/kh.chao/Kuanhao-Chao.github.io/src/assets"
BLOG_DIR = os.path.join(SITE, "posts", "wgt-verified")
REPORT_DIR = os.path.join(SITE, "reports", "wgt-technical-report")

PANEL_H = 1100          # common panel height (px) before layout
GUTTER = 60             # white gap between panels
MARGIN = 50            # outer margin
LABEL_H = 90            # top strip that holds the (A)/(B) labels
BG = (255, 255, 255)
INK = (20, 20, 20)

_FONT_PATH = font_manager.findfont("DejaVu Sans:bold")


def _font(size):
    return ImageFont.truetype(_FONT_PATH, size)


def _load(name):
    return Image.open(os.path.join(SRC, name)).convert("RGB")


def _resize_h(img, h):
    w = round(img.width * h / img.height)
    return img.resize((w, h), Image.LANCZOS)


def compose_row(sources, out_paths, labels=True):
    """Lay out N source PNGs in a row, normalized to PANEL_H, with (A)/(B) labels."""
    imgs = [_resize_h(_load(s), PANEL_H) for s in sources]
    total_w = sum(im.width for im in imgs) + GUTTER * (len(imgs) - 1) + 2 * MARGIN
    label_strip = LABEL_H if labels else 0
    total_h = PANEL_H + label_strip + 2 * MARGIN
    canvas = Image.new("RGB", (total_w, total_h), BG)
    draw = ImageDraw.Draw(canvas)
    font = _font(64)
    x = MARGIN
    y = MARGIN + label_strip
    for i, im in enumerate(imgs):
        canvas.paste(im, (x, y))
        if labels:
            draw.text((x, MARGIN), f"({chr(65 + i)})", fill=INK, font=font)
        x += im.width + GUTTER
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        canvas.save(p, "PNG")
        print(f"wrote {p}  ({canvas.width}x{canvas.height})")


def copy_single(source, out_paths):
    """Copy a single-panel figure (no recomposition)."""
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        shutil.copyfile(os.path.join(SRC, source), p)
        print(f"wrote {p}  (single)")


# ---- blog composites (4) -------------------------------------------------
compose_row(["F1_false_accepts.png", "F2_verdict_agreement.png"],
            [os.path.join(BLOG_DIR, "fig_correctness.png")])
copy_single("F3_capability.png",
            [os.path.join(BLOG_DIR, "fig_capability.png")])
# blog performance: lead with the mechanism (atoms), then the time it buys (setup/solve split).
copy_single("Fatoms_encoding.png",
            [os.path.join(BLOG_DIR, "fig_performance.png")])
copy_single("F7_setup_solve.png",
            [os.path.join(BLOG_DIR, "fig_setup_solve.png")])
compose_row(["F9_limits_bar.png", "F11_repair_blowup.png"],
            [os.path.join(BLOG_DIR, "fig_scale_repair.png")])

# ---- report composites (clean two-way: v1.0.0 vs current) ----------------
# §3.1 correctness is now a single-panel false-accept bar chart (v1.0.0 vs current).
copy_single("F1_false_accepts.png",
            [os.path.join(REPORT_DIR, "rfig_correctness.png")])
# §3.3 encoding size in atoms (already a 3-panel figure).
copy_single("Fatoms_encoding.png",
            [os.path.join(REPORT_DIR, "rfig_atoms.png")])
# §3.3 -f speed: scatter + ECDF + cactus (v1.0.0 vs current).
compose_row(["F4_f_scatter_cpu.png", "F5_speedup_ecdf_cpu.png", "F6_cactus_cpu.png"],
            [os.path.join(REPORT_DIR, "rfig_f_speed.png")])
# §3.3/§3.4 -f setup/solve split + peak memory (v1.0.0 vs current).
compose_row(["F7_setup_solve.png", "F7b_memory.png"],
            [os.path.join(REPORT_DIR, "rfig_setup_mem.png")])
# §3.5 default-path scalability + §3.9 headline lazy ceiling: both the wall+memory curves (Flazy).
copy_single("Flazy_ceiling.png",
            [os.path.join(REPORT_DIR, "rfig_scalability.png")])
copy_single("Flazy_ceiling.png",
            [os.path.join(REPORT_DIR, "rfig_lazy_ceiling.png")])
# §3.8 per-type -f speedup (single-panel total, v1.0.0 -> current).
copy_single("F12_type_speedup.png",
            [os.path.join(REPORT_DIR, "rfig_type_speedup.png")])
# §3.7 repair, §3.10 MSA→WG practicality (kept as-is).
copy_single("F11_repair_blowup.png",
            [os.path.join(REPORT_DIR, "rfig_repair.png")])
copy_single("F15_msa_practicality.png",
            [os.path.join(REPORT_DIR, "rfig_practicality.png")])

print("done.")
