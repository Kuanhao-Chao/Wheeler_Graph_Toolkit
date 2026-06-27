"""Q1 gates: the sound w-mer prefilter / global router for the suffix pangenome index.

The prefilter must change NO answer (locate == locate_routed == brute oracle), must be SOUND (every
block that truly contains P survives the prefilter), and must be SELECTIVE (touch far fewer blocks than
the symbol prefilter). Run under python3.
"""
import glob
import json
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index.pangenome_index import PangenomeIndex   # noqa: E402
from index import suffix_index as sx               # noqa: E402
from index import locate_oracle as lor             # noqa: E402
from index.faithful import read_fasta, _ungap_cap  # noqa: E402

FADIR = os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta")
YEAST_FA = sorted(glob.glob(os.path.join(FADIR, "chrI_*.fa")))


@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
def test_prefilter_unchanged_sound_and_selective():
    a, w = 4, 8
    fastas = YEAST_FA[:30]
    pg = PangenomeIndex(fastas, a=a, l=-1, s=4, w=w)
    pg.build_global()
    coords = {fa: json.load(open(fa.replace(".fa", ".coords.json"))) for fa in fastas}

    def oracle_block(fa, P):
        return lor.locate_brute(fa, coords[fa], P, a=a, l=-1)

    def oracle_union(P):
        out = set()
        for fa in fastas:
            out |= oracle_block(fa, P)
        return out

    rng = random.Random(7)
    pats = set()
    for fa in fastas[:12]:
        for _id, s in read_fasta(fa)[:a]:
            u = _ungap_cap(s, -1)
            for m in (3, 6, 8, 12):                       # |P| < w, == w, > w
                if len(u) >= m:
                    pats.add(u[rng.randint(0, len(u) - m):][:m])
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(8, 12))) for _ in range(25)}
    pats |= {"ZZZ"}

    surv_filterable = []                                  # survivors on |P| >= w (prefilter applies)
    for P in pats:
        st = {}
        got = sx.as_tuples(pg.locate(P, _stats=st))
        routed = sx.as_tuples(pg.locate_routed(P))
        truth = oracle_union(P)
        assert got == truth == routed, (P, len(got), len(truth), len(routed))      # NO answer changes
        # SOUNDNESS: every block that truly contains P must survive the prefilter
        for bi, fa in enumerate(fastas):
            if oracle_block(fa, P):
                b = pg.blocks[bi]
                assert pg._survives(b, P, b["idx"]._encode(P)), (fa, P)
        if len(P) >= w:
            surv_filterable.append(st["survivors"])
    # SELECTIVITY: for filterable patterns the prefilter touches a small fraction of all blocks
    import statistics as stat
    assert stat.median(surv_filterable) <= 0.2 * len(fastas)        # median survivors << #blocks


@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
def test_short_pattern_fallback_is_correct():
    # |P| < w cannot be filtered on w-mers -> must fall back and still equal the oracle
    a = 4
    fastas = YEAST_FA[:15]
    pg = PangenomeIndex(fastas, a=a, l=-1, s=4, w=8)
    coords = {fa: json.load(open(fa.replace(".fa", ".coords.json"))) for fa in fastas}
    for P in ("AC", "ACG", "T", "GA"):                    # all shorter than w=8
        got = sx.as_tuples(pg.locate(P))
        truth = set()
        for fa in fastas:
            truth |= lor.locate_brute(fa, coords[fa], P, a=a, l=-1)
        assert got == truth, P
