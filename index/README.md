# `index/` — a queryable FM-index over WGT Wheeler graphs

WGT *recognizes* Wheeler graphs and emits the Gagie–Manzini–Sirén succinct structure (`I.txt`/`O.txt`/
`L.txt`), but nothing in the toolkit ever *queried* it. This module adds the missing layer: an FM-index
with **backward search** over a recognized Wheeler graph, applied to real DNA multiple-sequence
alignments (yeast `sacCer3` multiz, then human). Count/membership is implemented; locate is future work.

## Pipeline (MSA → indexable graph → query)

1. **Acquire** an MSA — `pipeline/yeast_fetch.py` downloads the UCSC `sacCer3` multiz7way MAF and writes
   each alignment block as aligned DNA FASTA (`data/multiseq_alignment/yeast/fasta/`).
2. **Build + recognize** — `pipeline/msa_to_index.py` runs the De Bruijn generator → DOT → recognizer
   `-w`, emitting `out__<stem>/{I,O,L}.txt`, `nodes.txt`, and the Wheeler-order `graph.dot`. Real yeast
   De Bruijn blocks are ~100% Wheeler (k=3/4/5).
3. **Index + query** — `index/wg_index.py` builds the FM-index (from `I/O/L` *or* `graph.dot`) and
   `count(P)` backward-searches it; `index/query.py` is the end-to-end CLI.

```
~/miniconda3/envs/myenv/bin/python index/query.py <block.fa> --pattern CCCACA -k 5 -l 60 -a 2
```

## The succinct structure (recognizer `-w` output)

Nodes are numbered `1..n` in **Wheeler order**. For each node `v` in order:
- **I** = `indeg(v)` zeros then a `1`  (in-edges grouped by head; length `n + E`).
- **O** = `outdeg(v)` zeros then a `1` (out-edges grouped by tail; length `n + E`).
- **L** = `v`'s out-edge labels, sorted ascending, repeated by multiplicity (the out-edge BWT column;
  length `E`).

Example (`data/example/out__example/`): `I=1101001001`, `O=0001011101`, `L=aabba`.

## Query model

`count(P)` returns `(lo, hi, n)`: the half-open range `[lo, hi)` of Wheeler-order nodes reachable by a
walk spelling `P` from any start, and `n = hi - lo`. Backward search: start with all nodes; for each
character `c`, map the current node range through the `c`-edges using `C[c]` (label-count prefix sums) +
`rank` on `L` + the `I`/`O` boundaries (LF-mapping). The Wheeler property guarantees the result is a
contiguous node interval — checked against the brute-force oracle in the tests.

**De Bruijn reverse convention.** This construction builds the graph in reverse from a `$` source, so a
path spells the *reverse* of a sequence. Hence `index/query.py` searches `reverse(P)` by default: a hit
means `P` occurs in the alignment's sequences.

## Verification (all `pytest`, brute-force-gated)

- `test_yeast_fetch.py` — MAF→FASTA parsing on an embedded fixture (no network).
- `test_faithful.py` — the generator builds exactly the transparent reference De Bruijn graph
  (edge-set equality) and the graph decodes its sequences (`reverse(seq)` is spellable).
- `test_pipeline.py` — a real yeast block recognizes as Wheeler with a well-formed `I/O/L`.
- `test_wg_index.py` — `count`/node-range == the brute oracle over present + absent patterns on real
  yeast blocks and random Wheeler graphs; `from_iol` ≡ `from_graph_dot`; a biological end-to-end query.

Run: `~/miniconda3/envs/myenv/bin/python -m pytest index/tests/ -q` (uses an env with Biopython + pytest).

## Deferred (future rounds)

`locate` (map a hit back to sequence/position via sampling), human MSA, repairing non-Wheeler blocks
(`repair/wheelerize.py`) before indexing, and a succinct/C++ (sdsl) port for scale.
