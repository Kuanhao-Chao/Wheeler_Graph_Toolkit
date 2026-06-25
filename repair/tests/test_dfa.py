"""Unit tests for repair/dfa.py (determinize, classes, quotient, helpers)."""

import pytest

import _data
import dfa
from wheelerize import is_acyclic

NAMES = list(_data.GRAPHS)


@pytest.mark.parametrize("name", NAMES)
def test_trie_size(name):
    assert _data.build(_data.GRAPHS[name])["T"].n == _data.EXPECTED[name]["trie"]


@pytest.mark.parametrize("name", NAMES)
def test_class_counts(name):
    T = _data.build(_data.GRAPHS[name])["T"]
    assert dfa.nerode_classes(T)[1] == _data.EXPECTED[name]["nerode"]
    assert dfa.origin_classes(T)[1] == _data.EXPECTED[name]["origin"]


@pytest.mark.parametrize("name", NAMES)
def test_is_deterministic(name):
    b = _data.build(_data.GRAPHS[name])
    assert dfa.is_deterministic(b["out_adj"]) == _data.EXPECTED[name]["det"]


@pytest.mark.parametrize("name", NAMES)
def test_trie_preserves_language_and_labels(name):
    b = _data.build(_data.GRAPHS[name])
    T = b["T"]
    _, bedges, qs, qadj = dfa.quotient(T, list(range(T.n)))
    L_in = dfa.path_strings(b["sources"], b["out_adj"])
    assert dfa.path_strings(qs, qadj) == L_in            # trie spells exactly the input language
    out_labels = {a for (_, _, a) in bedges}
    in_labels = dfa.label_set(b["edges"])
    assert out_labels <= in_labels and (out_labels == in_labels or len(L_in) <= 1)


@pytest.mark.parametrize("name", NAMES)
def test_minimal_dfa_preserves_language_and_is_dag(name):
    b = _data.build(_data.GRAPHS[name])
    T = b["T"]
    cls, _ = dfa.nerode_classes(T)
    blocks, bedges, ms, madj = dfa.quotient(T, cls)
    assert dfa.path_strings(ms, madj) == dfa.path_strings(b["sources"], b["out_adj"])
    mnodes = sorted({x for e in bedges for x in (e[0], e[1])} | set(blocks))
    assert is_acyclic(mnodes, madj)                       # minimal DFA of a finite language is a DAG


def test_quotient_dedups_parallel_edges():
    T = _data.build(_data.GRAPHS["parallel_dup"])["T"]
    _, bedges, _, _ = dfa.quotient(T, list(range(T.n)))
    assert len(bedges) == len(set(bedges))


def test_empty_graph_is_single_root():
    T = dfa.determinize([], {})
    assert T.n == 1 and not T.edges


def test_origin_singletons_for_deterministic():
    # a deterministic input has singleton origin sets => #origin classes == #input nodes
    b = _data.build(_data.GRAPHS["t_chain"])
    assert dfa.origin_classes(b["T"])[1] == len(b["nodes"])
