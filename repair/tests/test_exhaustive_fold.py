"""Unit tests for repair/exhaustive_fold.py (the independent brute-force optimum)."""

import pytest

import _data
import exhaustive_fold as ex
import minimize as mz


def _bell(n):
    row = [1]
    for _ in range(n):
        nxt = [row[-1]]
        for v in row:
            nxt.append(nxt[-1] + v)
        row = nxt
    return row[0]


@pytest.mark.parametrize("n", [0, 1, 2, 3, 4, 5])
def test_set_partitions_count_and_validity(n):
    items = list(range(n))
    parts = list(ex.set_partitions(items))
    assert len(parts) == _bell(n)
    for p in parts:
        flat = [x for blk in p for x in blk]
        assert sorted(flat) == items                 # every partition covers all items, disjointly


@pytest.mark.parametrize("name", list(_data.GRAPHS))
def test_exhaustive_equals_exact_and_expected(name):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    if T.n > 9:
        pytest.skip("trie too big for the brute-force oracle")
    xs, _ = ex.min_size(T, rank)
    xe, xee, _, _ = ex.min_edits(T, rank)
    exp = _data.EXPECTED[name]
    assert xs == exp["min_size"] == mz.exact(T, rank, "size")["nodes"]
    assert xe == exp["min_edits"] == mz.exact(T, rank, "edits")["nodes"]
    assert xee == exp["edits"]


def test_within_class_partitions_respect_classes():
    # all yielded partitions must keep each class's nodes splittable only within the class
    b = _data.build(_data.GRAPHS["diamond"])
    T = b["T"]
    import dfa
    cls, _ = dfa.nerode_classes(T)
    for block_of in ex.within_class_partitions(cls, T.n):
        # two nodes sharing a block must share a class
        for i in range(T.n):
            for j in range(T.n):
                if block_of[i] == block_of[j]:
                    assert cls[i] == cls[j]
