"""Unit tests for repair/verify_repair.py (the 5 per-output invariants).

Confirms the verifier ACCEPTS a correct repair and CATCHES each way a repair can be wrong:
a non-Wheeler output, a dropped string (language change), and a changed label."""

import _data
import dfa
import minimize as mz
import verify_repair as vr


def test_verify_passes_a_correct_repair(tmp_path):
    b = _data.build(_data.GRAPHS["t_nonwg"])
    inp = str(tmp_path / "in.dot")
    out = str(tmp_path / "out.dot")
    _data.write_dot(_data.GRAPHS["t_nonwg"], inp)
    r = mz.exact(b["T"], b["label_rank"], "size")
    mz.write_repair(b["T"], r["block_of"], out)
    ok, res = vr.verify(inp, out)
    assert ok, res
    assert res["recognizer"] and res["oracle"] and res["strings_preserved"] and res["labels_preserved"]


def test_verify_catches_non_wheeler(tmp_path):
    inp = str(tmp_path / "in.dot")
    bad = str(tmp_path / "bad.dot")
    _data.write_dot(_data.GRAPHS["t_nonwg"], inp)
    _data.write_dot(_data.GRAPHS["t_nonwg"], bad)         # the un-repaired non-WG graph as "output"
    ok, res = vr.verify(inp, bad)
    assert not ok
    assert res["recognizer"] is False


def test_verify_catches_dropped_string(tmp_path):
    inp = str(tmp_path / "in.dot")
    bad = str(tmp_path / "bad.dot")
    _data.write_dot(_data.GRAPHS["t_chain"], inp)         # spells (), x, xx
    _data.write_dot([("a", "b", "x")], bad)               # Wheeler, but spells only (), x
    ok, res = vr.verify(inp, bad)
    assert not ok
    assert res["strings_preserved"] is False


def test_verify_catches_changed_label(tmp_path):
    inp = str(tmp_path / "in.dot")
    bad = str(tmp_path / "bad.dot")
    _data.write_dot(_data.GRAPHS["t_chain"], inp)         # labels {x}
    _data.write_dot([("a", "b", "x"), ("b", "c", "y")], bad)   # introduces label y
    ok, res = vr.verify(inp, bad)
    assert not ok
    assert res["strings_preserved"] is False or res["labels_preserved"] is False
