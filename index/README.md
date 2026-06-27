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
- `test_cpp_index.py` — the **C++ succinct index** (`cpp/wg_index.cpp`) `count`/range == the Python
  `WGIndex` == the brute oracle on the example, real yeast blocks, and random complete/d-NFA WGs.
- `test_genome_index.py` — the **sharded genome router** (`genome_index.py`): C++ router == Python
  router == oracle (OR over shards) on real chrI shards (present/absent, which shards, total matches).
- `test_locate.py` — **locate** (`locate.py`): query string → exact (species, source, genomic
  coordinate, strand) occurrences == the independent oracle (both strands, multi-hit, `m<K/=K/>K`) and,
  for the reference, == the real sacCer3 genome.

Run: `~/miniconda3/envs/myenv/bin/python -m pytest index/tests/ -q` (uses an env with Biopython + pytest).

## Scaling to a genome (C++ index + sharded architecture)

- **`cpp/wg_index.cpp`** — a dependency-free **C++ succinct FM-index** (no z3/sdsl). Same GMS backward
  search as `wg_index.py`, with compact arrays + a block-rank over `L`; ~0.03 µs/query (≈58× the Python
  index). `make` in `cpp/`, then `wg_index <out__dir> --query P | --queries FILE | --bench`.
- **`genome_index.py`** — a **sharded whole-genome index**: one Wheeler graph + C++ FM-index per MAF
  block, plus a query router (a pattern occurs in the genome iff it occurs in ≥1 shard).
- **`GENOME_INDEX.md`** — the feasibility study: a single whole-genome graph is **not** practical
  (generator + recognizer both cap near ~10⁵ nodes; largest verified single graph = 68k nodes), so the
  genome is indexed **sharded** (whole-chrI demo: 992/992 Wheeler shards, 432 KB, router == oracle).
  `benchmark/genome_index/{scaling.py,chrI_demo.py}` + `data/genome_scaling.csv`, `data/genome_chrI_demo.json`.
- **`LOCATE.md` / `locate.py`** — **locate**: query string → every (species, source, genomic coordinate,
  strand). A forward K-mer inverted index per shard + the Wheeler FM-index as a sound membership
  prefilter; verified == an independent oracle and == the real sacCer3 genome. A global K-mer routing
  index makes locate genome-size-independent (whole-chrI demo: naive vs FM-prefilter vs routed).
  `index/query.py --locate`; `benchmark/genome_index/chrI_locate_demo.py` + `data/genome_chrI_locate.json`.
- **`PANGENOME_INDEX.md` / `suffix_index.py` / `pangenome_index.py`** — a **new index with NATIVE
  species+position resolution**: the tagged suffix Wheeler graph (multi-string BWT + document array +
  sampled SA). Its backward-search range **is** the occurrences, so the species set + positions are read
  off the index itself (the De Bruijn k-mer index can't — it collapses k-mers; 0 % native species,
  recombinant superset). The recognizer certifies the suffix order IS the Wheeler order
  (`verify/suffix_wheeler_cert.py`) and that the compact-exact DAWG (`dawg.py`) is Wheeler. Verified
  exact vs oracle + the real genome. `benchmark/genome_index/{resolution_demo,pangenome_demo}.py`.
  Speed: a sound w-mer **router** (`PangenomeIndex.build_global`/`locate_routed`) makes genome queries
  genome-size-independent (≈167× over touch-all); the **r-index φ-locate** (`SuffixIndex.locate_phi`)
  bounds per-occurrence work; a dependency-free **C++ port** (`cpp/wg_suffix.cpp`, ~18× the Python
  locate) is verified `C++ == Python == oracle` (`tests/test_cpp_suffix.py`).

## Deferred (future rounds)

Human MSA, repairing non-Wheeler blocks (`repair/wheelerize.py`) before indexing, a minimizer/sketch to
compress the locate routing index, suffix-array `locate` from the FM-index itself (no occ map), and an
sdsl wavelet-tree drop-in for large alphabets.
