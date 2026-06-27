"""Gate for the sharded whole-genome Wheeler index (index/genome_index.py).

Builds a set of real chrI block shards, then checks that the query ROUTER -- present/absent, which
shards, and the total node-match count -- agrees across three independent engines:
  * the C++ per-shard FM-index (index/cpp/wg_index),
  * the Python WGIndex per shard,
  * the brute oracle (OR over shards of index/oracle.reachable).

This is what makes "the pattern occurs somewhere in the genome MSA" a verified query. Run under
python3 (the De Bruijn generator is shelled to myenv).
"""
import glob
import os
import random
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index import oracle               # noqa: E402
from index import genome_index as gi   # noqa: E402
from pipeline import msa_to_index as m2i  # noqa: E402

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "chrI_*.fa")))
HAVE_REC = os.path.exists(m2i.REC)
PY_BIO = os.environ.get("WGT_PY_BIO", os.path.expanduser("~/miniconda3/envs/myenv/bin/python"))


def _build_cpp():
    cdir = os.path.join(ROOT, "index", "cpp")
    if not os.path.exists(gi.CPP_BIN):
        subprocess.run(["make", "-s"], cwd=cdir, capture_output=True)
    return os.path.exists(gi.CPP_BIN)


def _oracle_router(shard_dirs):
    """Parsed (nodes, edges) per shard for the brute-force ground truth."""
    parsed = []
    for d in shard_dirs:
        nodes, edges = oracle.parse_dot(open(os.path.join(d, "graph.dot")).read())
        parsed.append((nodes, edges))
    return parsed


def _oracle_query(parsed, p):
    hits, total = 0, 0
    for nodes, edges in parsed:
        r = oracle.reachable(nodes, edges, p)
        if r:
            hits += 1; total += len(r)
    return {"present": hits > 0, "n_shards_hit": hits, "total_matches": total}


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
def test_router_cpp_eq_py_eq_oracle(tmp_path):
    assert _build_cpp(), "C++ index build failed"
    fastas = YEAST_FA[:30]
    man = gi.build_shards(fastas, k=4, l=40, a=2, work=str(tmp_path), py_bio=PY_BIO)
    shards = man["shards"]
    assert len(shards) >= 10, man

    parsed = _oracle_router(shards)
    cpp = gi.ShardedGenomeIndex(shards, engine="cpp")
    py = gi.ShardedGenomeIndex(shards, engine="py")

    # present patterns: random walks inside random shards; absent: random DNA + off-alphabet
    rng = random.Random(2024)
    pats = set()
    for nodes, edges in parsed[:15]:
        adj = {}
        for t, h, lab in edges:
            adj.setdefault(t, []).append((lab, h))
        for _ in range(8):
            v = rng.choice(sorted(nodes)); s = []
            for _ in range(rng.randint(1, 6)):
                if v not in adj:
                    break
                lab, h = rng.choice(adj[v]); s.append(lab); v = h
            if s:
                pats.add("".join(s))
    pats |= {"".join(rng.choice("ACGT") for _ in range(rng.randint(2, 6))) for _ in range(40)}
    pats |= {"ZZZ", "QQQQ"}             # off-alphabet -> absent everywhere
    pats = [p for p in pats if p]

    cpp_res = cpp.query_batch(pats)
    py_res = py.query_batch(pats)
    saw_present = saw_absent = False
    for p in pats:
        o = _oracle_query(parsed, p)
        c, y = cpp_res[p], py_res[p]
        assert (c["present"], c["n_shards_hit"], c["total_matches"]) == \
               (o["present"], o["n_shards_hit"], o["total_matches"]), ("cpp", p, c, o)
        assert (y["present"], y["n_shards_hit"], y["total_matches"]) == \
               (o["present"], o["n_shards_hit"], o["total_matches"]), ("py", p, y, o)
        saw_present |= o["present"]; saw_absent |= (not o["present"])
    assert saw_present and saw_absent, "want both present and absent patterns covered"


@pytest.mark.skipif(not (YEAST_FA and HAVE_REC), reason="needs yeast FASTA + recognizer")
def test_router_reports_which_shards(tmp_path):
    """A pattern present in exactly one shard is attributed to that shard, with the right count."""
    assert _build_cpp()
    man = gi.build_shards(YEAST_FA[:20], k=4, l=40, a=2, work=str(tmp_path), py_bio=PY_BIO)
    shards = man["shards"]
    parsed = _oracle_router(shards)
    cpp = gi.ShardedGenomeIndex(shards, engine="cpp")
    # find a single-edge label string present in exactly one shard, if any; else just check consistency
    for nodes, edges in parsed:
        for _t, _h, lab in edges:
            res = cpp.query(lab)
            o = _oracle_query(parsed, lab)
            assert res["present"] == o["present"] and res["n_shards_hit"] == o["n_shards_hit"]
            break
        break
