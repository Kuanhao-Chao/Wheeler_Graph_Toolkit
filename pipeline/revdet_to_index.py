"""Compact-index pipeline: RevDet column automaton -> minimal Wheeler-repair -> FM-index.

RevDet graphs are a candidate *compact* alternative to the De Bruijn graph for indexing an MSA: a DAG
whose paths spell the sequences forward, but ~1% Wheeler. This driver makes a RevDet graph Wheeler with
the existing minimal lossless repair (`repair/minimize.py refine`, min-size = smallest deterministic
Wheeler graph preserving the path-string set) and indexes the result (`index/wg_index.py`). Because
RevDet spells forward, queries need no reversal (unlike the De Bruijn index).

Run under **python3** (needs z3 for repair); the RevDet generator is shelled out to a Biopython python.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "repair"))

import dfa                      # noqa: E402  repair/dfa.py
import minimize as mz          # noqa: E402  repair/minimize.py
import brute_oracle as bo      # noqa: E402  verify/brute_oracle.py (on minimize's path)
from pipeline import msa_to_index as m2i   # noqa: E402  reuse recognize()
from index.wg_index import WGIndex         # noqa: E402

PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))
REVDET_DIR = os.path.join(ROOT, "generator", "RevDetGraph_generator")
REVDET_PY = os.path.join(REVDET_DIR, "RevDetGraph_generator.py")


def build_revdet_dot(fasta, l, a, out_dot):
    r = subprocess.run([PY_BIO, REVDET_PY, "-o", os.path.abspath(out_dot), "-l", str(l), "-a", str(a),
                        os.path.abspath(fasta)],
                       cwd=REVDET_DIR, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(out_dot):
        raise RuntimeError(f"RevDet generator failed on {fasta}: {r.stderr.strip()[:300]}")
    return out_dot


def repair_to_wheeler(revdet_dot, out_dot, mode="size", method="refine", trie_cap=200000):
    """Minimal lossless repair of a (non-Wheeler) RevDet DAG. Returns a record dict; raises on cyclic.
    On trie blow-up past trie_cap, returns record with trie_nodes=None and ok=False (the limit)."""
    nodes, sources, out_adj, edges = dfa.build_graph(revdet_dot)
    rec = {"in_nodes": len(nodes), "in_edges": len(edges), "acyclic": dfa.is_acyclic(nodes, out_adj)}
    if not rec["acyclic"]:
        raise ValueError("RevDet graph is cyclic (unexpected) — out of scope for lossless repair")
    label_rank = bo.rank_labels(edges, False)
    try:
        T = dfa.determinize(sources, out_adj, max_nodes=trie_cap)
    except RuntimeError as e:                 # path-string trie blow-up past the cap
        rec.update({"trie_nodes": None, "blowup": True, "detail": str(e)[:120], "ok": False})
        return rec
    r = mz.repair(T, label_rank, mode, method)
    mz.write_repair(T, r["block_of"], out_dot)
    rec.update({"trie_nodes": T.n, "blowup": False, "rep_nodes": r["nodes"],
                "edits": r.get("edits"), "out_dot": out_dot, "ok": True})
    return rec


def process_block(fasta, l, a, work, method="refine", trie_cap=200000):
    """RevDet -> (recognize; repair if needed) -> recognize -w -> index. Returns a record + the index."""
    stem = os.path.splitext(os.path.basename(fasta))[0]
    os.makedirs(work, exist_ok=True)
    revdet_dot = build_revdet_dot(fasta, l, a, os.path.join(work, stem + ".revdet.dot"))
    base = m2i.recognize(revdet_dot, work, write=False)            # is RevDet already Wheeler?
    rec = {"fasta": os.path.basename(fasta), "l": l, "a": a, "revdet_dot": revdet_dot,
           "revdet_wheeler": base["verdict"] == 1, "revdet_nodes": base["nodes"]}

    if base["verdict"] == 1:
        to_index, rec["repaired"] = revdet_dot, False
    else:
        rp = repair_to_wheeler(revdet_dot, os.path.join(work, stem + ".repaired.dot"),
                               method=method, trie_cap=trie_cap)
        rec.update({"trie_nodes": rp["trie_nodes"], "rep_nodes": rp.get("rep_nodes"),
                    "edits": rp.get("edits"), "repaired": True})
        if not rp["ok"]:
            rec.update({"ok": False, "reason": "trie_blowup"})
            return rec, None
        to_index = rp["out_dot"]

    res = m2i.recognize(to_index, work, write=True)               # Wheeler-order graph.dot + I/O/L
    if res["verdict"] != 1 or not res["outdir"]:
        rec.update({"ok": False, "reason": f"repaired-not-wheeler({res['verdict']})"})
        return rec, None
    idx = WGIndex.from_iol(res["outdir"])
    rec.update({"ok": True, "outdir": res["outdir"], "wheeler_nodes": idx.n, "wheeler_edges": idx.E,
                "to_index_dot": to_index})
    return rec, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fasta")
    ap.add_argument("-l", type=int, default=40)
    ap.add_argument("-a", type=int, default=2)
    ap.add_argument("--method", default="refine")
    ap.add_argument("--work", default="/tmp/revdet_idx")
    ap.add_argument("--query", help="DNA pattern to search (forward; RevDet spells forward)")
    args = ap.parse_args()
    rec, idx = process_block(args.fasta, args.l, args.a, args.work, method=args.method)
    print(f"{rec['fasta']}: RevDet {rec.get('revdet_nodes')}n (Wheeler={rec['revdet_wheeler']})"
          + (f" -> trie {rec.get('trie_nodes')}n -> repaired {rec.get('rep_nodes')}n" if rec["repaired"] else "")
          + (f" -> indexed {rec.get('wheeler_nodes')}n/{rec.get('wheeler_edges')}e" if rec.get("ok") else
             f"  [FAILED: {rec.get('reason')}]"))
    if idx and args.query:
        lo, hi, n = idx.count(args.query.upper())
        print(f"  query {args.query!r}: {'FOUND ' + str(n) + ' node(s) in [' + str(lo) + ',' + str(hi) + ')' if n else 'not found'}")


if __name__ == "__main__":
    main()
