# Evaluation — correctness, scale, speed, memory of the Wheeler pangenome index (yeast → human)

A full audit + scale/speed/**memory** benchmark of the tagged suffix Wheeler pangenome index (`index/
suffix_index.py`, `pangenome_index.py`) and all the species/position pattern-matching algorithms, on
yeast chrI then the **whole sacCer3 genome** (17 sequences, 44,063 MAF blocks), oriented toward human MSA.

## 1. Correctness — audit-hardened

An adversarial audit (`index/AUDIT.md`, `index/tests/test_audit_*.py`) tested **8 algorithms** against
independent brute oracles over **>4 million** cases. **One degenerate bug** (`DAWG.count("")` →
fixed to 0) and otherwise **robust**: the suffix BWT/SA/LF/φ/toehold, the genomic coordinate transform
(both strands, genome-anchored), the sound w-mer router, the DAWG, the De Bruijn `WGIndex` (2.07M
patterns over 8k graphs), and the C++ port all agree exactly with the oracle. Every benchmark below also
carries a built-in `locate == locate_routed == ∪oracle` gate — **0 mismatches at every scale, including
the full genome** (44,063 blocks, 8,687 reference hits cross-checked against the real chromosomes).

## 2. chrI scale/speed/memory (`data/suffix_chrI_scaling.csv`)

992 blocks; sweep over species count `a` and SA-sample rate `s` (`runs` is the r-index/genome mode):

| sample | a | s | build | peak RSS | in-mem | on-disk | locate | routed | mism |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| rate | 2 | 1 | 3.2 s | 147 MB | 160 MB | 4 MB | 2.94 ms | 0.46 ms | 0 |
| rate | 4 | 1 | 6.0 s | 245 MB | 279 MB | 7 MB | 3.34 ms | 0.86 ms | 0 |
| rate | 4 | 16 | 5.9 s | 198 MB | 215 MB | 4 MB | 4.06 ms | 1.37 ms | 0 |
| rate | 7 | 1 | 8.8 s | 339 MB | 392 MB | 11 MB | 3.88 ms | 1.21 ms | 0 |
| runs | 4 | 4 | 6.0 s | 211 MB | 220 MB | 6 MB | 3.64 ms | 1.04 ms | 0 |

- **`a` (species)** scales build/memory ~linearly (more sequence ⇒ bigger index).
- **`s` (SA-sample rate)** is the size↔speed knob: larger `s` shrinks on-disk (7→4 MB) at the cost of
  slower locate (0.86→1.37 ms). `runs` ≈ `rate` at `s=4` (the r-index samples at BWT run boundaries).
- The **router** touches only ~8–18 of 992 blocks per query (the sound w-mer prefilter); routed locate is
  sub-2 ms.

## 3. Full yeast genome (`data/suffix_genome_scaling.json`) — one index per chromosome, `a=4`, `runs`

| metric | value |
|---|---|
| sequences / blocks / suffix nodes | 17 / **44,063** / 43.4 M |
| build time (single-thread, per-chrom) | **318 s** (≈5.3 min; embarrassingly parallel) |
| peak RSS (largest chromosome, chrIV) | **1.27 GB** (bounds the per-chromosome build) |
| in-memory, all chromosomes held at once | **11.0 GB** |
| **on-disk serialized (arrays)** | **334 MB** (33× smaller than in-mem) |
| routed-locate latency (per-chrom median) | **2.6 ms** |
| **verify mismatches** | **0 / 17 chromosomes** (+ 8,687 reference-genome checks) |

Per-chromosome cost is linear in block count (chrIV: 5,884 blocks, 41 s, 1.43 GB in-mem, 43.5 MB on-disk;
chrM: 318 blocks, 1.1 s). The suffix pangenome index builds **directly from each block FASTA — no De
Bruijn generator, no recognizer** — so the whole genome builds in minutes, not the hours the
generate-and-recognize path needs.

## 4. Memory analysis — where it goes, what binds

The audit-gated Phase-2 fix replaced the dense `O(σ·n)` rank arrays with **block-rank `O(σ·n/64)`** (57×
smaller on a real block) and **drops the full suffix array** in `runs` mode (a build intermediate no
query uses). After that, the per-block rank array is negligible and the **memory-binding structure is the
ROUTER** — the per-block w-mer sets + the global w-mer→blocks map — both linear in genome size. Holding
the whole genome in memory at once is ~11 GB; the **on-disk "arrays" serialization is 334 MB** and loads
without re-sorting suffixes, so the practical architecture is **load-on-demand**: keep the (small) router
in memory, store the 44k block indexes on disk, and load only the candidate blocks a query routes to.

## 5. Human MSA projection (~262× yeast by length)

| quantity | yeast (measured) | human (projected) |
|---|--:|--:|
| blocks | 44,063 | ~11.6 M |
| build, single-core | 318 s | ~23 h (≈minutes parallel) |
| on-disk serialized | 334 MB | **~86 GB** |
| in-memory, all at once | 11 GB | ~2.8 TB |
| routed query | 2.6 ms | ~flat (genome-size-independent) |

**What binds at human scale, and the answer:** holding all block indexes + the router in RAM (~2.8 TB)
is infeasible — so the **on-disk arrays index + load-on-demand router** is required (already enabled by
Phase-2 serialization). On-disk ~86 GB is practical. The router itself (the global w-mer map, linear in
size) is the next compression target — a **minimizer/sketch** would shrink it; that is the recommended
next step before human. Build is embarrassingly parallel (per block / per chromosome).

## 6. Improvements delivered + next steps

Delivered this round (all audit-gated, `locate == oracle` unchanged): **block-rank rank arrays** (57×
smaller), **drop-SA-in-`runs`**, **serialization** (`index/serialize.py`, arrays + rebuild formats),
**a memory probe** (`benchmark/genome_index/memprobe.py`), and the **chrI + full-genome benchmarks**
(`suffix_scaling.py`, `genome_build.py`). Next: a minimizer-sketched router (shrink the in-mem binding
structure), a **load-on-demand genome router** over the on-disk arrays index (the human-scale path), a
C++ port of the r-index φ-locate + the router, and human MSA. See `AUDIT.md`, `PANGENOME_INDEX.md`,
`GENOME_INDEX.md`.

## Reproduce
```bash
~/miniconda3/envs/myenv/bin/python -m pytest index/tests            # audit + serialize + all gates
python3 benchmark/genome_index/suffix_scaling.py --chrom chrI --a 2,4,7 --s 1,4,16 --sample rate
python3 pipeline/yeast_fetch.py --smoke --chrom chrII               # (per chromosome, under myenv)
python3 benchmark/genome_index/genome_build.py --a 4 --s 4          # whole-genome build + measure
```
