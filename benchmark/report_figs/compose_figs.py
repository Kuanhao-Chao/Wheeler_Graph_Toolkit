#!/usr/bin/env python
"""Route the six WGT technical-report figures (rendered as single matplotlib figures by
plot_report.py) into the khchao.com site asset tree. No recompositing: each report figure is
already one publication-grade matplotlib figure with shared fonts/DPI, so we just copy it.

  Fhero.png            -> rfig_hero.png          (§3.0  graphical-abstract scorecard)
  F2_validation.png    -> rfig_validation.png    (§3.1  Axis I — validation vs the oracle)
  Flazy_ceiling.png    -> rfig_lazy_ceiling.png  (§3.2  Axis II — THE headline)
  Fperformance.png     -> rfig_performance.png   (§3.3  Axis III — speed/memory/per-type 2x2)
  Fmechanism.png       -> rfig_mechanism.png     (§4    how the speedup works, in depth)
  Fpracticality.png    -> rfig_practicality.png  (§5    practicality + repair)

The draft blog (wgt-verified) keeps its existing assets; it is not part of the report deploy.

Run with the spliceai env python:
  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/compose_figs.py
"""
import os
import shutil

SRC = os.path.dirname(os.path.abspath(__file__))
SITE = "/ccb/salz3/kh.chao/Kuanhao-Chao.github.io/src/assets"
REPORT_DIR = os.path.join(SITE, "reports", "wgt-technical-report")

REPORT_FIGS = {
    "Fhero.png":         "rfig_hero.png",
    "F2_validation.png": "rfig_validation.png",
    "Flazy_ceiling.png": "rfig_lazy_ceiling.png",
    "Fperformance.png":  "rfig_performance.png",
    "Fmechanism.png":    "rfig_mechanism.png",
    "Fpracticality.png": "rfig_practicality.png",
}


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    for src, dst in REPORT_FIGS.items():
        sp = os.path.join(SRC, src)
        if not os.path.exists(sp):
            print(f"  !! missing {src} — run plot_report.py first"); continue
        dp = os.path.join(REPORT_DIR, dst)
        shutil.copyfile(sp, dp)
        print(f"wrote {dp}")
    print("done.")


if __name__ == "__main__":
    main()
