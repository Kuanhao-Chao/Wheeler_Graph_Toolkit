"""Generate the FAITHFUL data file (`tiny.json`) that drives the interactive index visualizations in the
website technical report. The components are pure RENDERERS of this file — no index algorithm is ever
reimplemented in JavaScript. This script imports the REAL index (`index/suffix_index.py`), builds a tiny
ground-truth example, walks the actual `backward_search` step by step, and ASSERTS every output against
brute oracles before writing. If the algorithm ever changes, regenerating either still passes (faithful)
or trips an assert (caught) — mirroring the report's verify-authority discipline.

Run:  ~/miniconda3/envs/myenv/bin/python index/viz/gen_viz_data.py
Emits: index/viz/tiny.json  (provenance copy; also copied to the website at src/data/wgi/tiny.json)
"""
import itertools
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from index.suffix_index import (                       # noqa: E402  (the REAL algorithm = source of truth)
    DNA, dna_code, build_text, build_sa, build_sa_brute, build_bwt, SuffixIndex,
)

SEQS = ["ACGAC", "ACGTC"]      # two short "species" — the tiny worked example
S = 4                          # SA sample rate (rate mode: keeps the full SA for display)
LMAX = 3                       # precompute query traces for every DNA pattern of length 1..LMAX
                               # (<=3 covers the presets + every multi-hit case on a 12-symbol example;
                               #  keeps the query component's client-side trace table small)
PRESETS = ["AC", "ACG", "GTC", "GGG"]   # GGG shows the empty-interval case
SUB = "₀₁₂₃₄₅₆₇₈₉"


def sym_of(code, a):
    """Display symbol for an alphabet code: separators -> $<subscript i>, DNA -> A/C/G/T."""
    if code < a:
        return "$" + "".join(SUB[int(d)] for d in str(code))
    return DNA[code - a]


def cell(idx, code, doc, a):
    """One rendered alphabet cell: symbol, which document, and whether it's a separator."""
    return {"i": idx, "sym": sym_of(code, a), "code": code, "doc": doc,
            "kind": "sep" if code < a else "dna"}


def brute_occurrences(seqs, P):
    """Independent oracle: every (record_idx, local_pos) where P occurs in a sequence (forward)."""
    out = []
    for d, s in enumerate(seqs):
        for p in range(len(s) - len(P) + 1):
            if s[p:p + len(P)] == P:
                out.append((d, p))
    return sorted(out)


def main():
    a = len(SEQS)
    code = dna_code(a)
    T, doc, doc_start, _ = build_text(SEQS)
    n = len(T)
    SA = build_sa(T)
    BWT = build_bwt(T, SA)
    idx = SuffixIndex(SEQS, coords=None, s=S, sample="rate")

    # ---- faithfulness asserts: the real index must agree with the brute oracles --------------------
    assert SA == build_sa_brute(T), "prefix-doubling SA != brute rotation sort"
    assert idx.BWT == BWT and idx.SA == SA, "SuffixIndex arrays differ from standalone build"
    DOC = [doc[SA[i]] for i in range(n)]
    assert idx.DOC == DOC, "document array mismatch"

    # ---- shared 'answer key' arrays ----------------------------------------------------------------
    Tcells = [cell(p, T[p], doc[p], a) for p in range(n)]
    bwt_cells = [cell(i, BWT[i], doc[(SA[i] - 1) % n], a) for i in range(n)]
    rotations = []                     # the sorted BWT matrix: one row per sorted cyclic rotation
    for i in range(n):
        p = SA[i]
        rot = [cell(j, T[(p + j) % n], doc[(p + j) % n], a) for j in range(n)]
        rotations.append({"row": i, "saStart": p, "rowDoc": DOC[i],
                          "first": rot[0]["sym"], "last": rot[-1]["sym"], "cells": rot})
    unsorted = []                      # rotations in text order (before the sort)
    for p in range(n):
        rot = [cell(j, T[(p + j) % n], doc[(p + j) % n], a) for j in range(n)]
        unsorted.append({"start": p, "rowDoc": doc[p], "cells": rot})
    sampled_sa = [{"row": i, "sa": SA[i]} for i in range(n) if idx.sampled[i]]
    arrays = {
        "T": Tcells, "SA": SA, "BWT": bwt_cells, "DOC": DOC, "C": idx.C,
        "rotations": rotations, "unsorted": unsorted, "sampledSA": sampled_sa,
    }

    # ---- construction step states (pure render instructions) ---------------------------------------
    seprepr = " < ".join(sym_of(i, a) for i in range(a)) + " < A < C < G < T"
    build = [
        {"id": "msa", "view": "rows", "title": "1 · The alignment block",
         "caption": (f"Two aligned species, alignment gaps stripped: S0 = {SEQS[0]} (blue), "
                     f"S1 = {SEQS[1]} (orange). This is one MSA block."),
         "rows": [{"doc": d, "cells": [sym_of(code[c], a) for c in s]} for d, s in enumerate(SEQS)]},
        {"id": "concat", "view": "linearT", "title": "2 · Concatenate with distinct separators",
         "caption": (f"Join the rows into one text T, each ended by its own distinct separator "
                     f"({seprepr}). The separators are smaller than any DNA base, so a DNA pattern "
                     f"can never cross one."),
         "highlight": [p for p in range(n) if T[p] < a]},
        {"id": "rotate", "view": "unsorted", "title": "3 · Form every cyclic rotation",
         "caption": (f"Write out all {n} cyclic rotations of T (here unsorted). Distinct separators "
                     f"make every rotation unique.")},
        {"id": "sort", "view": "sorted", "title": "4 · Sort the rotations → the BWT matrix",
         "caption": ("Sort the rotations lexicographically. This sorted order IS the Wheeler order "
                     "(Gagie–Manzini–Sirén): the suffix-array rank.")},
        {"id": "extract", "view": "arrays", "title": "5 · Read off the index",
         "caption": ("The last column is the BWT. Each row also yields SA (its text position = "
                     "POSITION), DOC (the species of that position = SPECIES), and a sampled subset "
                     "of SA. These four arrays are the whole index."),
         "show": ["BWT", "SA", "DOC", "sampledSA"]},
    ]

    # ---- query traces: walk the REAL backward_search for every DNA pattern of length 1..LMAX --------
    traces = {}
    for L in range(1, LMAX + 1):
        for tup in itertools.product(DNA, repeat=L):
            P = "".join(tup)
            cs = [code[c] for c in P]
            lo, hi = 0, n
            steps = []
            empty = False
            for k, c in enumerate(reversed(cs)):
                pos_in_P = len(P) - 1 - k
                sym = P[pos_in_P]
                rlo, rhi = idx._rank(c, lo), idx._rank(c, hi)
                nlo, nhi = idx.C[c] + rlo, idx.C[c] + rhi
                matched = P[pos_in_P:]
                if nlo >= nhi:
                    cap = (f"Prepend {sym}: rank({sym},{lo})={rlo}, rank({sym},{hi})={rhi} → "
                           f"interval [{nlo},{nlo}) is empty. “{matched}” does not occur.")
                    steps.append({"i": k, "c": sym, "matched": matched,
                                  "loPrev": lo, "hiPrev": hi, "Cc": idx.C[c],
                                  "rankLo": rlo, "rankHi": rhi, "lo": nlo, "hi": nlo,
                                  "rowsInBand": [], "empty": True, "caption": cap})
                    lo, hi = nlo, nlo
                    empty = True
                    break
                cap = (f"Prepend {sym}: lo = C[{sym}]+rank({sym},{lo}) = {idx.C[c]}+{rlo} = {nlo}; "
                       f"hi = C[{sym}]+rank({sym},{hi}) = {idx.C[c]}+{rhi} = {nhi}. "
                       f"Interval [{nlo},{nhi}) now spells “{matched}”.")
                steps.append({"i": k, "c": sym, "matched": matched,
                              "loPrev": lo, "hiPrev": hi, "Cc": idx.C[c],
                              "rankLo": rlo, "rankHi": rhi, "lo": nlo, "hi": nhi,
                              "rowsInBand": list(range(nlo, nhi)), "empty": False, "caption": cap})
                lo, hi = nlo, nhi
            hits = []
            if not empty:
                for i in range(lo, hi):
                    p = SA[i]; d = doc[p]
                    hits.append({"row": i, "sa": p, "doc": d, "species": f"S{d}",
                                 "localPos": p - doc_start[d]})
            count = 0 if empty else hi - lo

            # ---- assert against the brute oracle + the real index ----
            assert idx.count(P) == count, f"count mismatch for {P}"
            located = sorted((h["record_idx"], h["ungapped_pos"]) for h in idx.locate(P))
            assert located == brute_occurrences(SEQS, P), f"locate != oracle for {P}"
            assert sorted((h["doc"], h["localPos"]) for h in hits) == located, f"viz hits != locate {P}"

            traces[P] = {"pattern": P, "found": not empty, "steps": steps,
                         "final": {"lo": lo if not empty else steps[-1]["lo"],
                                   "hi": hi if not empty else steps[-1]["lo"],
                                   "count": count, "hits": hits}}

    # ---- router schematic numbers (verbatim from the committed benchmark) --------------------------
    rt = json.load(open(os.path.join(ROOT, "data", "suffix_router.json")))
    router = {"blocks": rt["blocks"], "medianSurvivors": int(rt["median_survivors"]),
              "speedup": round(rt["speedup_routed_vs_touchall"]),
              "scanMs": rt["touch_all_ms"], "routedMs": rt["routed_ms"],
              "caption_scan": f"Naive: search every one of {rt['blocks']} blocks for each query.",
              "caption_route": (f"Routed: the global w-mer map lights only the "
                                f"{int(rt['median_survivors'])} candidate block(s) that can contain the "
                                f"pattern — {round(rt['speedup_routed_vs_touchall'])}× faster.")}

    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      text=True).strip()
    except Exception:
        sha = "unknown"

    out = {
        "meta": {"faithful": True, "source_commit": f"wg-genome-index@{sha}",
                 "seqs": SEQS, "a": a, "n": n, "s": S, "sample": "rate", "Lmax": LMAX,
                 "alphabet": [{"sym": sym_of(c, a), "code": c,
                               "kind": "sep" if c < a else "dna", "doc": (c if c < a else None)}
                              for c in range(a + 4)]},
        "arrays": arrays, "build": build,
        "query": {"presets": PRESETS, "Lmax": LMAX, "traces": traces},
        "router": router,
    }

    dst = os.path.join(HERE, "tiny.json")
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"OK: {len(traces)} patterns traced, all asserts passed (faithful=True). wrote {dst}")
    print(f"    seqs={SEQS} n={n} | SA={SA} | presets={PRESETS}")


if __name__ == "__main__":
    main()
