"""Regression pins: exact optima for the canonical graphs must not silently drift."""

import pytest

import _data
import minimize as mz
import brute_oracle as bo

NAMES = list(_data.GRAPHS)


@pytest.mark.parametrize("name", NAMES)
def test_pinned_optima(name):
    b = _data.build(_data.GRAPHS[name])
    T, rank = b["T"], b["label_rank"]
    exp = _data.EXPECTED[name]
    assert T.n == exp["trie"], "trie size drifted"
    assert mz.exact(T, rank, "size")["nodes"] == exp["min_size"], "min-size drifted"
    re = mz.exact(T, rank, "edits")
    assert re["nodes"] == exp["min_edits"], "min-edits nodes drifted"
    assert re["edits"] == exp["edits"], "min-edits (#splits) drifted"
    assert bo.is_wheeler(b["nodes"], b["edges"], rank) == exp["wg"], "WG verdict drifted"


def test_classic_nonwg_needs_one_split():
    # the canonical 4-node conflict: exactly one node duplication makes it Wheeler
    b = _data.build(_data.GRAPHS["t_nonwg"])
    assert mz.exact(b["T"], b["label_rank"], "edits")["edits"] == 1


def test_diamond_min_size_below_input_via_cross_origin_merge():
    # min-size (4) is below the trie (5): the two leaves merge (cross-origin) -- but NOT to 3,
    # because that re-creates the A2 conflict. Guards the subtle "minimal DFA can be non-Wheeler".
    b = _data.build(_data.GRAPHS["diamond"])
    T, rank = b["T"], b["label_rank"]
    assert T.n == 5
    assert mz.exact(T, rank, "size")["nodes"] == 4
