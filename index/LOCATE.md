# Locate: query a string → which species, which genomic position

The membership index (`index/wg_index.py`, `index/genome_index.py`) answers *"does P occur?"*. **Locate**
answers the biological question: *given a DNA string P, which species does it come from and where, for
every occurrence?* This module (`index/locate.py`) adds exact, verified locate on top of the sharded
Wheeler k-mer index, and shows it is fast enough to be practical genome-wide.

```
$ python index/query.py data/.../chrI_blk00000_s6.fa --pattern CCACACCA -k 8 -l 100000 -a 2 --locate
locate: 'CCACACCA' -> 2 occurrence(s)
     sacCer3  sacCer3.chrI  26-34 (+)  [block offset 20]
     sacCer3  sacCer3.chrI  38-46 (+)  [block offset 32]
```

## Why locate needs more than the graph

The De Bruijn graph **collapses** k-mers and admits **recombinant paths** — its path-language is a
*superset* of the sequences, so `count(P)>0` does **not** prove P occurs contiguously, and a node (a
(k−1)-mer) can occur at many positions in many species. So locate cannot be read off the graph topology;
it needs occurrence positions, verified against the actual sequences.

## The algorithm (exact, correctness-first)

Per shard (one MAF block) we build, by **one forward scan** of the same ungapped/capped first-`a` records
the De Bruijn graph was built from:
- `occ`: **K-mer → [(record_idx, ungapped_pos)]** (K = k−1) — a forward inverted index (lists, never
  deduped: a K-mer repeating in a record gives several positions);
- the per-record genomic coordinates from the `<stem>.coords.json` sidecar (recovered from the MAF).

`locate_shard(P)`:
1. **FM prefilter** — the shard's Wheeler FM-index `count(reverse(P))`. It is *sound* (every real
   substring of an indexed sequence ⇒ count>0, by the De Bruijn round-trip property), so `count==0`
   safely **skips** the shard. This is the only place the reverse convention is used.
2. **Candidates** — `occ[P[:K]]` if `|P|≥K`; else a direct scan of the short shard sequences.
3. **Verify** — char-compare `seq[pos:pos+|P|] == P` (kills the recombinant-superset false positives).
   Only verified hits are emitted ⇒ **exact** for any `|P| < , = , or > K`.

**Coordinate transform** (ungapped offset `pos`, length `m`; 0-based half-open on the source's + strand):
- `+` strand: `gstart = start + pos`, `gend = start + pos + m` (P is literally there);
- `−` strand (UCSC): `gstart = srcSize − (start+pos+m)`, `gend = srcSize − (start+pos)` (the + strand
  holds `revcomp(P)` over `[gstart,gend)`).

`GenomeLocateIndex.locate(P)` runs this across all shards (the `count==0` skip is the speed lever),
dedups the exact genomic tuple `(species, src, gstart, gend, strand)`, and sorts.

## Three ways to locate, and which is fast (`benchmark/genome_index/chrI_locate_demo.py`)

Over the **whole chrI** index (k=8 ⇒ K=7; **992/992 Wheeler shards**, 0 non-Wheeler), the same query mix
(present K-mers of length `m<K/=K/>K`, absent, off-alphabet) was located three ways — **all three agree
on every query (0 mismatches)**:

| method | what it does | median latency | speedup vs naive |
|---|---|---:|---:|
| **naive** | scan every position of every sequence (linear in genome length) | **43.8 ms** | 1× |
| **FM-prefilter router** | per-shard Wheeler FM membership skips shards, then occ + verify | **7.2 ms** | **6.1×** |
| **routed K-mer index** | one global K-mer→sites lookup, then verify (genome-size-independent) | **0.021 ms** | **2,048×** |

The **FM-prefilter** speedup is roughly constant (it still probes every shard, just cheaply — median 7.5
of 992 shards survive); the **routed** index is *genome-size-independent* (one dict lookup yields the few
candidate sites), so its speedup **grows with genome size**: the routed speedup was **614×** over 60
chrI blocks and **2,048×** over all 992 — naive scales linearly with the genome, routed stays flat. The
Wheeler FM-index remains the validated membership layer (and handles arbitrary-length patterns); the
global K-mer index is the locate accelerator, built from the same per-shard occ maps.

Build + size (whole chrI, single-threaded): shards 330 s (embarrassingly parallel), locate index 1.5 s;
the routing index holds **16,368 distinct 7-mers / 318,129 occurrence entries**. Biological example:
the 7-mer `GCAACCG` locates to **16 occurrences** across species; every sacCer3 hit is verified against
the real chromosome.

## Verification (every path brute-force-gated)

- **Independent oracle** `index/locate_oracle.py` — direct substring scan with its *own* inlined ungap/cap
  and *own* coordinate transform (no shared code with `locate.py`). `test_locate.py`: `locate ==
  locate_brute` over present (incl. multi-hit), absent, off-alphabet, `m<K/=K/>K`, on the example, real
  chrI blocks, and a **synthetic block with hand-computed coordinates exercising both + and − strands**.
- **Routed == FM-prefilter == oracle** across real chrI shards.
- **Real-genome cross-check** — fetch the actual sacCer3 chrI (length 230,218 == the MAF `srcSize`) and
  assert every located `(sacCer3, gstart..gend)` literally equals P in the real chromosome.
- **Consistency** — `occ` keys == the De Bruijn (k−1)-mer set (minus `$`); the filename reference start ==
  `coords[0].start`; (uncapped) ungapped row length == the MAF `size`.

## Limitations

1. **K-mer granularity / fidelity.** Locate is exact for the indexed content, but that content is the
   first-`a`, capped, ungapped block sequences; the selectivity of the FM prefilter is set by k (at small
   k the De Bruijn superset is permissive and the prefilter prunes little — use a selective k, e.g. 8+).
2. **Needs the coords sidecar** (`<stem>.coords.json`, emitted by `yeast_fetch`) for genomic coordinates;
   without it, only (species, block, ungapped offset) is available.
3. **Strand:** + and − are handled (UCSC convention); the − transform is unit-tested on a synthetic block
   and the + path is cross-checked against the real reference genome (the other species' genomes are not
   fetched).
4. **Routing index size** grows with the number of distinct K-mers; a minimizer/sketch is the natural
   next compression. `locate` reports per-occurrence records; full suffix-array `locate` over the graph
   (positions from the FM-index itself, no occ map) remains future work.

## Reproduce

```bash
# emit coords sidecars (once) + fetch the reference genome
~/miniconda3/envs/myenv/bin/python pipeline/yeast_fetch.py --parse data/.../chrI.maf --out data/.../fasta
~/miniconda3/envs/myenv/bin/python -c "from pipeline.yeast_fetch import fetch_genome; fetch_genome('chrI')"
# gates (locate == oracle == genome) ; selective-k locate demo (naive vs FM vs routed)
~/miniconda3/envs/myenv/bin/python -m pytest index/tests/test_locate.py -q
python3 benchmark/genome_index/chrI_locate_demo.py -k 8 -a 2 --blocks 0 --out data/genome_chrI_locate.json
```
