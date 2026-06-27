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

  (index report; `compose_figs.py index`, from plot_index_report.py)
  FIhero.png       -> rfig_hero.png        (§hero  graphical-abstract scorecard)
  FIresolution.png -> rfig_resolution.png  (§4    native species resolution vs De Bruijn / RevDet)
  FImechanism.png  -> rfig_mechanism.png   (§2    how a query resolves species + position)
  FIscale.png      -> rfig_scale.png       (§7    scale / speed / memory, yeast -> human)
  FIquery.png      -> rfig_query.png        (§6    pattern matching: count / locate)
  FIaudit.png      -> rfig_audit.png        (§8    adversarial audit coverage)

Run with the spliceai env python (default = recognizer report; `index` = the index report):
  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/compose_figs.py [index]
"""
import os
import shutil
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
SITE = "/ccb/salz3/kh.chao/Kuanhao-Chao.github.io/src/assets"
REPORT_DIR = os.path.join(SITE, "reports", "wgt-technical-report")
INDEX_REPORT_DIR = os.path.join(SITE, "reports", "wgt-index-technical-report")

REPORT_FIGS = {
    "Fhero.png":         "rfig_hero.png",
    "F2_validation.png": "rfig_validation.png",
    "Flazy_ceiling.png": "rfig_lazy_ceiling.png",
    "Fperformance.png":  "rfig_performance.png",
    "Fmechanism.png":    "rfig_mechanism.png",
    "Fpracticality.png": "rfig_practicality.png",
}

INDEX_FIGS = {
    "FIhero.png":       "rfig_hero.png",
    "FIresolution.png": "rfig_resolution.png",
    "FImechanism.png":  "rfig_mechanism.png",
    "FIscale.png":      "rfig_scale.png",
    "FIquery.png":      "rfig_query.png",
    "FIaudit.png":      "rfig_audit.png",
}


def route(figs, dest, hint):
    os.makedirs(dest, exist_ok=True)
    for src, dst in figs.items():
        sp = os.path.join(SRC, src)
        if not os.path.exists(sp):
            print(f"  !! missing {src} — run {hint} first"); continue
        dp = os.path.join(dest, dst)
        shutil.copyfile(sp, dp)
        print(f"wrote {dp}")
    print("done.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "index":
        route(INDEX_FIGS, INDEX_REPORT_DIR, "plot_index_report.py")
    else:
        route(REPORT_FIGS, REPORT_DIR, "plot_report.py")


if __name__ == "__main__":
    main()
