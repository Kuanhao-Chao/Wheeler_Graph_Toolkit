# `repair/` — turning a non-Wheeler graph into a Wheeler graph

Phase 5 of the verification/repair effort. Goal: given a graph that is **not** a Wheeler graph,
produce one that **is**, under a chosen invariant. The first milestone targets the case the
pangenomics setting cares about: **acyclic graphs, preserving the represented path-strings.**

## `wheelerize.py` — string-preserving repair for DAGs (trie unfolding)

For a DAG, it unfolds the graph into the **trie of its path-strings** (the label strings of paths
from source nodes, prefix-closed). Key facts:

- A trie is **always a Wheeler graph** (order nodes by the co-lex order of their unique incoming
  string — all three Wheeler axioms then hold). So this **always succeeds for a DAG**.
- It preserves the **set of path-strings** exactly.

```bash
python3 repair/wheelerize.py input.dot -o repaired.dot      # string labels
python3 repair/wheelerize.py input.dot -o repaired.dot --int   # integer labels
```

Every run self-verifies three ways: (1) the recognizer accepts the output as Wheeler; (2) the brute
oracle accepts it (when small); (3) the output's path-string set equals the input's.

### Semantics & caveats (important)

- "Preserve stored paths" here means **preserve the set of path-strings** (the represented
  language of source-paths). It does **not** preserve node identity or path *multiplicity*: nodes
  that spell the same string get merged, so the output can be *smaller* than the input (avg ~0.87×
  on random DAGs) as well as larger (up to ~2.4×). Worst case is exponential, but typical DAGs are
  modest.
- **Cyclic graphs are out of scope** (unfolding is infinite). The tool detects cycles and stops;
  the chosen fallback there is lossy **edge-edit** repair (minimum deletions/relabelings), which is
  not yet implemented.
- This first version is **not minimal** — it does not minimize the number of node splits. Minimal /
  optimal node-splitting (e.g. via subset-DFA minimization while staying Wheeler, or a Z3
  optimization) is future work (plan Phase 5.2/5.3).

## `test_wheelerize.py` — at-scale validation

Generates random DAGs (a mix of Wheeler and non-Wheeler), wheelerizes each, and asserts every one
becomes a verified Wheeler graph with strings preserved.

```bash
python3 repair/test_wheelerize.py --n 600 --max-n 7
```

Latest run: 509 DAGs (308 already Wheeler, 201 repaired), **0 failures**.

## Roadmap (remaining)

- Lossy edge-edit fallback for cyclic / non-DAG inputs (min deletions/relabelings + report).
- Minimal node-splitting (don't merge/over-split): split only where the recognizer/`WG_checker`
  reports a conflict, reusing the `-x`/violation API (`recognizer/src` `get_violations()`).
- Exact optimal repair via Z3 `optimize` (MaxSAT) for small graphs.
