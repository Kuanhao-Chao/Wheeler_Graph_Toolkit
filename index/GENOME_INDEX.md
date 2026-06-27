# Can we build a Wheeler-graph index over the *whole yeast genome* MSA? — feasibility, ceilings, architecture

**Question.** Take the full *Saccharomyces cerevisiae* (`sacCer3`) 7-species multiz alignment (~12.2 Mb,
16 chromosomes + chrM, ~50–60k MAF blocks) and build a *queryable* Wheeler-graph FM-index over it. Is a
**single whole-genome graph** practical? If not, **how big a single graph can each stage of the pipeline
actually handle**, and **what architecture indexes the whole genome**?

This document answers all three from measurement on real chrI data (not estimates): a scaling study
that pins each component's ceiling (`benchmark/genome_index/scaling.py` → `data/genome_scaling.csv`), a
new dependency-free **C++ succinct index** that removes the query/storage bottleneck
(`index/cpp/wg_index.cpp`), a **sharded genome-index architecture** with a verified query router
(`index/genome_index.py`), and a **whole-chromosome demo on chrI** (`benchmark/genome_index/chrI_demo.py`
→ `data/genome_chrI_demo.json`). Every query path is checked against the brute oracle.

## TL;DR

- **A single whole-genome graph at a faithful resolution is NOT practical.** The pipeline's two binding
  stages — the De Bruijn **generator** (pure Python) and the **recognizer** — both top out near **10⁵
  nodes / a few-minute budget** on real yeast De Bruijn graphs. The largest graph we built *and verified*
  end-to-end (generate → recognize → index) is **68,376 nodes / 70,172 edges** (chrI, 200 MAF blocks,
  k=12: generator 62 s, recognizer 168 s). A faithful whole-genome graph is on the order of **10⁷
  k-mers** — ~150× past that ceiling.
- **Two regimes, two honest answers:**
  - **Small-k De Bruijn is *bounded* and trivially feasible, but lossy.** Node count saturates at ≤4ᵏ
    *regardless of genome length* — whole chrI at k=4 is **69 nodes / 262 edges**, identical from 20 to
    992 blocks. A whole-*genome* k=4 graph would likewise be a few hundred nodes. But its path-language
    is a large **superset** of the real sequences (recombinant k-mer membership, not sequence
    membership).
  - **Faithful (large-k) De Bruijn *grows ~linearly* with genome length** — and that is exactly what
    blows past the generator/recognizer ceilings.
- **The index engine is never the single-graph bottleneck.** Both the Python FM-index (`index/wg_index.py`)
  and the new C++ index build and query every graph the recognizer can emit in **well under a tenth of a
  second**. The new C++ index's payoff is at the **aggregate / genome scale** (tens of thousands of
  shards): **~0.03 µs/query vs ~1.85 µs** for Python (≈**58×**), a compact byte-packed footprint, and
  millisecond builds.
- **The practical whole-genome index is *sharded*:** one small Wheeler graph + C++ FM-index **per MAF
  block**, plus a query router (a pattern occurs in the genome iff it occurs in ≥1 shard; the router
  reports which). Sharding sidesteps *both* walls because every shard is tiny. Verified equal to the
  brute oracle on real chrI shards.

## How we grew real graphs (the size knobs)

`scaling.py` concatenates the first *M* consecutive chrI MAF blocks, per species (reference `sacCer3`
plus the next species by coverage; a species absent in a block is gap-filled for that block's width —
a faithful gapped concatenation), into one aligned FASTA, then builds its De Bruijn graph. Two knobs:

- **De Bruijn order k** — the *node* axis. The generator's nodes are the distinct length-k k-mers, so
  node count saturates near **4ᵏ**: small k → a tiny bounded graph; large k → nodes ≈ distinct k-mers ≈
  grows with sequence.
- **Number of blocks M** (sequence length) — the *edge* axis. Edges are distinct k-mer→k-mer
  transitions; at small k both nodes *and* edges saturate, while at large k both grow ~linearly with
  length.

All 992 chrI blocks (~217 kb of reference, essentially the whole chromosome) are available
(`pipeline/yeast_fetch.py`). Each stage runs under `timeout <S> /usr/bin/time -v` so an over-budget
stage is *recorded*, not hung, with its peak RSS captured.

## The measured ceilings (`data/genome_scaling.csv`)

| graph (chrI) | nodes | edges | generator | recognizer | Python idx | C++ idx build | C++ query |
|---|---:|---:|---:|---:|---:|---:|---:|
| k=4, whole chrI (992 blk) | **69** | 262 | 0.6 s | 0.03 s | 0.001 s | 0.15 ms | 0.075 µs |
| k=8, whole chrI (992 blk) | 16,380 | 61,281 | 10.7 s | 33.5 s | 0.05 s | 1.1 ms | 0.10 µs |
| k=12, 80 blk | 16,142 | 16,279 | 3.1 s | 10.4 s | 0.02 s | 0.5 ms | 0.10 µs |
| k=12, 120 blk | 37,345 | 37,932 | 18.3 s | 49.3 s | 0.04 s | 1.0 ms | 0.11 µs |
| **k=12, 200 blk (largest verified)** | **68,376** | **70,172** | **62 s** | **168 s** | **0.07 s** | 8.3 ms | 0.11 µs |
| k=12, 300 blk | 118,306 | 122,841 | 234 s | **timeout (>240 s)** | — | — | — |
| k=12, 500 blk | — | — | **timeout (>600 s)** | — | — | — | — |

**Reading the table.**
- **Recognizer** — the headline single-graph ceiling. It scales super-linearly but is *capable*: 68k
  nodes in 168 s (accepted, Wheeler). It crosses a ~4-minute budget around **~10⁵ nodes** (118k nodes →
  timeout). Peak RSS stayed modest (tens of MB) — it is **time**, not memory, that binds.
- **Generator (pure-Python De Bruijn)** — a *second* wall at essentially the same scale: 234 s at 300
  blocks, **>600 s by 500 blocks**. For a single large graph the generator is as much the bottleneck as
  the recognizer (a C++/streaming constructor would push this out).
- **Python index** — never the bottleneck: 0.07 s to build the 70k-edge index; its per-label prefix
  arrays are O(E·|Σ|) and trivial at any E the recognizer can produce.
- **C++ index** — millisecond builds, ~0.1 µs/query, a few-MB RSS, at every size.

### Why the index is not the single-graph wall (and where the C++ index *does* pay off)

On a *single* graph the recognizer caps the size at ~10⁵ nodes, and at 10⁵ edges either index is
instant. The C++ index matters at the **aggregate**: the whole-genome index is ~50–60k shards, and a
genome-wide query touches them all. Per-query, **C++ ≈ 0.03 µs vs Python ≈ 1.85 µs (≈58×)** — i.e. a
genome-wide pattern is ~**2 ms** (C++ router) vs ~**110 ms** (Python router) across 60k shards, with a
compact byte-packed footprint and millisecond shard builds. The C++ index is what makes the *sharded
genome* index responsive; on one block it is merely convenient.

## Verdict on a single whole-genome graph

**Faithful single whole-genome graph: not practical.** A resolution that distinguishes the actual
sequences (large k, or any construction whose graph grows with the genome) needs ≈10⁷ nodes; the
generate-and-recognize pipeline tops out ~10⁵. That is a ~150× gap, and the recognizer's super-linear
time means closing it is not a matter of a bigger machine.

**Bounded single whole-genome graph (small-k De Bruijn): feasible but lossy.** Because nodes saturate
at ≤4ᵏ, a whole-genome k=4 (or even k=8–10) De Bruijn graph is small enough to recognize and index as
one graph — but it answers *k-mer* membership over a recombinant superset, not *sequence* membership.
Useful as a coarse k-mer presence index; not a faithful pangenome index.

## The practical architecture: a sharded Wheeler-graph genome index

`index/genome_index.py`. Index the genome as **one small Wheeler graph + C++ FM-index per MAF block**
(or per chromosome window), with a query router on top:

```
                MAF blocks (~50–60k)
                      │  per block:
   De Bruijn DOT ──► recognizer -w ──► I/O/L shard ──► C++ wg_index (per-shard FM-index)
                      │
              ShardedGenomeIndex.query(P):
                 P occurs in the genome  ⇔  P occurs in ≥1 shard
                 → report {present, which shards, total node-matches}
```

- **Build** is *embarrassingly parallel* and sidesteps both single-graph walls: each shard is a tiny
  block (tens–hundreds of nodes at small k), so the generator and recognizer run per-block in
  milliseconds–seconds, and shards build independently.
- **Query** is correctness-first here (every shard is asked). At genome scale a per-shard k-mer sketch
  (a Bloom/minimizer prefilter) skips shards that cannot contain P, turning a genome-wide query into a
  handful of shard probes — a standard, orthogonal optimization noted but not needed for correctness.
- **Router correctness is verified**: the C++ router == the Python router == the brute oracle
  (OR over shards of `index/oracle.reachable`) on real chrI shards — present/absent, *which* shards, and
  the total node-match count all agree (`index/tests/test_genome_index.py`).

### Aggregate cost model (extrapolated from measured per-shard numbers)

From the chrI demo below (992 blocks, k=4): **0.29 s build per shard**, **~446 bytes of I/O/L per
shard**, **~49 nodes / 116 edges per shard** on average. The genome is ≈**53× chrI** by length
(12.2 Mb / 0.23 Mb), so:

| quantity | chrI (measured) | whole genome (extrapolated ≈53×) |
|---|---:|---:|
| shards (Wheeler blocks) | 992 | **~52,600** |
| total nodes / edges | 48,678 / 115,085 | ~2.6 M / ~6.1 M |
| on-disk index (I/O/L) | 432 KB | **~23 MB** |
| build time, single-threaded | 284 s | **~4.2 h** (embarrassingly parallel → minutes on a cluster) |
| genome-wide query, C++ router (per-shard subprocess) | 52 ms/pattern | bounded by #shards (see note) |
| genome-wide query, in-process C++ (0.03 µs/shard) | ~30 µs | ~1.6 ms/pattern with a shard prefilter |

The ~23 MB whole-genome index and parallelizable build are entirely practical; the only number that
looks large — 52 ms/pattern — is **subprocess-spawn overhead** (the demo router shells the C++ binary
once per shard). The actual per-shard query is 0.03 µs; an in-process router (or a k-mer prefilter that
touches only a handful of shards) makes a genome-wide query sub-millisecond.

## Demo: the whole-chrI index, built and queried the feasible way

`benchmark/genome_index/chrI_demo.py` builds the entire chromosome I index as 992 per-block shards (k=4)
and queries it through the **C++ router**, cross-checking a sample against the Python router and the
brute oracle (`data/genome_chrI_demo.json`):

| measurement | value |
|---|---|
| chrI MAF blocks → Wheeler shards | **992 → 992 (100% Wheeler at k=4)**, 0 non-Wheeler, 0 failed |
| build time (single-threaded) | 284 s total, **0.29 s/shard** |
| total nodes / edges (all shards) | 48,678 / 115,085 |
| on-disk index (I/O/L, all shards) | **432 KB** |
| router verification (C++ == Python == oracle) | **0 mismatches / 30 sampled patterns** |

**Queries (and what they reveal about k=4).** Real chrI k-mers were **found 40/40**. Of 42 "absent"
controls, the two **off-alphabet** patterns (`ZZZ`, `QQQQ`) correctly returned **0**, but **40/40 random
DNA 8-mers were also reachable** — every verdict confirmed by the oracle (0 mismatches). This is
limitation #1 made concrete: a **k=4** De Bruijn graph is a *permissive k-mer filter* whose path-language
is a large recombinant **superset**, so almost any short DNA string is "present." It is the right tool to
ask *"could this k-mer occur in the alignment?"* but not *"does this exact sequence occur?"* For
sequence-level fidelity, raise k (at the cost of growing graphs — the ceilings above) or use the
RevDet + Wheeler-NFA repair construction (`index/COMPACT_INDEX.md`), which preserves the sequence set
exactly. The architecture, the per-shard FM-index, and the router are identical regardless of k; only
the construction's fidelity/size trade changes.

## Limitations (stated plainly)

1. **Faithfulness.** De Bruijn (any k) admits recombinant paths — its path-language is a *superset* of
   the input sequences; the index answers "does this k-mer/path occur in the De Bruijn graph of the
   MSA," which is k-mer-level membership, not exact per-sequence membership. (RevDet + Wheeler-NFA repair
   — see `index/COMPACT_INDEX.md` — preserves the sequence set exactly but is larger and was shown not to
   beat small-k De Bruijn on size.)
2. **The generator is pure Python** and is a co-bottleneck with the recognizer for single large graphs.
   A streaming/C++ De Bruijn constructor would move that wall, but the recognizer wall (~10⁵ nodes)
   would then bind alone.
3. **The recognizer wall is *time*, not memory**, and super-linear — recognition is NP-complete; the
   lazy/CEGAR backend is fast on these sparse, near-Wheeler graphs but still scales super-linearly.
4. **Query, not locate.** The index answers count/membership (which Wheeler-order node range). Reporting
   genomic *positions* (locate) needs a suffix-array sample per shard — future work.
5. **The router is verified, not yet prefiltered.** The genome-scale per-shard sketch (to avoid touching
   every shard) is designed but not implemented; the verified path queries all shards.
6. **Scope.** Measured on chrI (sharding generalizes per-block); the whole-genome numbers are
   *extrapolations* from per-shard measurements, clearly labelled as such.

## Reproduce

```bash
# scaling ceilings (resumable; harness-tracked background recommended)
python3 benchmark/genome_index/scaling.py --blocks 20,80,300 --ks 4,8,12 -a 2 --out data/genome_scaling.csv
# C++ index correctness gate (== Python == oracle)
python3 -m pytest index/tests/test_cpp_index.py index/tests/test_genome_index.py -q
# whole-chrI sharded demo (build + query + verify + extrapolate)
python3 benchmark/genome_index/chrI_demo.py -k 4 -a 2 --blocks 0 --out data/genome_chrI_demo.json
```

Cross-interpreter: the De Bruijn generator needs Biopython (`~/miniconda3/envs/myenv/bin/python`); the
index, oracle, router, and C++ binary are pure-stdlib / dependency-free.
