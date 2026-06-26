"""Phase 2 gate (pipeline): a yeast block De Bruijn graph recognizes as Wheeler and the recognizer
emits a well-formed Gagie I/O/L structure (|I|=|O|=n+E, |L|=E)."""
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from pipeline import msa_to_index as m2i  # noqa: E402
from index import faithful  # noqa: E402

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "*.fa")))
HAVE_REC = os.path.exists(m2i.REC)


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC),
                    reason="needs Phase-1 yeast FASTA + the recognizer binary")
def test_yeast_block_is_wheeler_with_valid_iol(tmp_path):
    fa = YEAST_FA[0]
    r = m2i.process_block(fa, k=4, l=40, a=2, work=str(tmp_path))
    assert r["verdict"] == 1, r          # real yeast De Bruijn block is a Wheeler graph
    assert r["outdir"] and os.path.isdir(r["outdir"])
    I = open(os.path.join(r["outdir"], "I.txt")).read().strip()
    O = open(os.path.join(r["outdir"], "O.txt")).read().strip()
    L = open(os.path.join(r["outdir"], "L.txt")).read().strip()
    gdot = open(os.path.join(r["outdir"], "graph.dot")).read()
    edges, nodes = faithful.parse_dot_edges(gdot)
    n, E = len(nodes), len(edges)
    # Gagie structure dimensions: I and O are n ones interleaved with E zeros; L is one char per edge.
    assert len(I) == n + E and len(O) == n + E, (len(I), len(O), n, E)
    assert I.count("1") == n and O.count("1") == n
    assert len(L) == E, (len(L), E)
    assert set(L) <= set("ACGT$")
