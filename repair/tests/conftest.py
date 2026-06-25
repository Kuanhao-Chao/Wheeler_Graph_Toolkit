"""pytest setup: put repair/ and verify/ on sys.path so `import dfa, minimize, ...` work, and
expose the shared canonical-graph data/helpers as fixtures."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(ROOT, "verify"), os.path.join(ROOT, "repair"), os.path.dirname(__file__)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402
import _data  # noqa: E402


@pytest.fixture
def graphs():
    return _data.GRAPHS


@pytest.fixture
def expected():
    return _data.EXPECTED


@pytest.fixture
def build():
    return _data.build


@pytest.fixture
def write_dot():
    return _data.write_dot
