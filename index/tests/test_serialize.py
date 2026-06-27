"""Gate for index/serialize.py: a loaded index answers identically to a freshly built one (both formats,
both sample modes), == the brute oracle, for SuffixIndex and PangenomeIndex."""
import glob
import json
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from index.suffix_index import SuffixIndex, as_tuples       # noqa: E402
from index import serialize as ser                          # noqa: E402
from index import locate_oracle as lor                      # noqa: E402
from index.faithful import read_fasta, _ungap_cap           # noqa: E402

YEAST_FA = sorted(glob.glob(os.path.join(ROOT, "data", "multiseq_alignment", "yeast", "fasta", "chrI_*.fa")))


def _pairs(hits):
    return {(h["record_idx"], h["ungapped_pos"]) for h in hits}


@pytest.mark.parametrize("sample", ["rate", "runs"])
@pytest.mark.parametrize("fmt", ["arrays", "rebuild"])
def test_roundtrip_synthetic(sample, fmt):
    rng = random.Random(hash((sample, fmt)) & 0xffff)
    for _ in range(60):
        seqs = ["".join(rng.choice("ACGT") for _ in range(rng.randint(0, 16)))
                for _ in range(rng.randint(1, 5))]
        if sum(map(len, seqs)) == 0:
            continue
        idx = SuffixIndex(seqs, s=4, sample=sample)
        back = ser.loads(ser.dumps(idx, fmt))
        # arrays format must reproduce the SA-derived fields exactly
        if fmt == "arrays":
            assert (back.BWT, back.DOC, back.doc_start, back.sa_val, back._phi_keys, back._phi_vals) == \
                   (idx.BWT, idx.DOC, idx.doc_start, idx.sa_val, idx._phi_keys, idx._phi_vals)
        pats = {u[a:a + m] for u in seqs for m in (1, 3, 5) for a in range(len(u) - m + 1)}
        pats |= {"Z", "ACGT", ""}
        for P in pats:
            assert _pairs(back.locate(P)) == _pairs(idx.locate(P))
            assert back.count(P) == idx.count(P)


@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
@pytest.mark.parametrize("sample", ["rate", "runs"])
@pytest.mark.parametrize("fmt", ["arrays", "rebuild"])
def test_roundtrip_real_block_vs_oracle(sample, fmt, tmp_path):
    fa = YEAST_FA[3]
    coords = json.load(open(fa.replace(".fa", ".coords.json")))
    idx = SuffixIndex.from_fasta(fa, a=4, l=-1, coords=coords, s=4, sample=sample)
    path = os.path.join(str(tmp_path), f"idx_{sample}_{fmt}.bin")
    ser.save(idx, path, fmt)
    back = ser.load(path)
    us = [_ungap_cap(s, -1) for _id, s in read_fasta(fa)[:4]]
    rng = random.Random(7)
    pats = set()
    for u in us:
        for m in (4, 8, 12):
            if len(u) >= m:
                pats.add(u[rng.randint(0, len(u) - m):][:m])
    pats |= {"".join(rng.choice("ACGT") for _ in range(6)) for _ in range(15)} | {"NNN"}
    for P in pats:
        assert as_tuples(back.locate(P)) == as_tuples(idx.locate(P)) == lor.locate_brute(fa, coords, P, a=4, l=-1)


@pytest.mark.skipif(not YEAST_FA, reason="needs yeast FASTA")
def test_pangenome_roundtrip(tmp_path):
    from index.pangenome_index import PangenomeIndex
    fastas = YEAST_FA[:20]
    pg = PangenomeIndex(fastas, a=4, l=-1, s=4, w=8)
    path = os.path.join(str(tmp_path), "pg.bin")
    ser.save_pangenome(pg, path, fmt="arrays")
    back = ser.load_pangenome(path)
    assert len(back.blocks) == len(pg.blocks)
    coords = {fa: json.load(open(fa.replace(".fa", ".coords.json"))) for fa in fastas}
    rng = random.Random(3)
    pats = set()
    for fa in fastas[:8]:
        for _id, s in read_fasta(fa)[:4]:
            u = _ungap_cap(s, -1)
            if len(u) >= 8:
                pats.add(u[rng.randint(0, len(u) - 6):][:6])
    pats |= {"".join(rng.choice("ACGT") for _ in range(6)) for _ in range(10)}
    back.build_global()
    for P in pats:
        truth = set()
        for fa in fastas:
            truth |= lor.locate_brute(fa, coords[fa], P, a=4, l=-1)
        assert as_tuples(back.locate(P)) == as_tuples(pg.locate(P)) == truth
        assert as_tuples(back.locate_routed(P)) == truth
