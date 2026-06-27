# A Wheeler-graph pangenome index with native species + position resolution

This is the design log and results for a new pangenome index: query a DNA string, get **every
occurrence as (species, genomic position)**, fast, multi-hit, exact — with the resolution **intrinsic to
the Wheeler index** rather than bolted on. It documents the higher-level view, the ideas proposed and
tried, what each experiment taught, and the recommended algorithm.

## 1. The problem, at a high level

Pangenome indexing = index a set of sequences (here, the species rows of a DNA MSA) so a pattern query
returns all **(species, position)** occurrences — fast and compact. Two axes pull against each other:

- **Resolution** — can you recover *which species* and *which position*?
- **Compactness** — how small is the index (homologous species share a lot)?

The earlier De Bruijn k-mer index (`index/wg_index.py` + `index/locate.py`) is compact but **loses
species resolution in the graph itself**: identical k-mers from many species collapse to **one** node,
so the backward-search range is a set of shared nodes, not occurrences. Species/position had to be
recovered from a **separate** k-mer→position map (the occ-map), and the De Bruijn graph's path-language
is a recombinant **superset** (it accepts strings that occur in no single sequence). We want the
**Wheeler index's own backward-search range to enumerate the occurrences, each natively tagged with
(species, position)**.

### Where resolution comes from (the key insight)

In a Wheeler-graph FM-index, backward search returns a contiguous range `[lo,hi)` of Wheeler-order
nodes. **Locate-resolution = a suffix-sorted Wheeler order + a per-position tag array.** If the Wheeler
order is a **suffix sort** (the multi-string BWT), then `[lo,hi)` is *exactly* the set of occurrences of
P (one entry per occurrence), and a **document array** (which species) + a **sampled suffix array**
(which position) read off every hit. This is intrinsic, exact, and multi-hit. The construction spectrum:

| construction | node = | path-language | species native? | position native? | size |
|---|---|---|---|---|---|
| **trie** | a distinct prefix | **exact** | implicit (subtree) | depth | huge |
| **suffix / multi-string BWT** | a suffix (in sorted order) | **exact** | **document array** | **sampled SA** | O(total length) |
| **RevDet** | (alignment column, char) | recombinant **superset** | column membership (lost on serialize) | column (lost on serialize) | small |
| **De Bruijn** | a (k−1)-mer | recombinant **superset** | merged away | external occ-map only | smallest |

De Bruijn is the most compact but the least resolved; the trie is exact but blows up; **the suffix /
multi-string BWT is the exact construction whose Wheeler range == occurrences**, which is why it is the
recommended core. RevDet (the column automaton) has the right intuition — its node *is* a (column, char),
so position=column and species=membership are natural — but the generator drops the column on DOT
serialization and the path-language is a recombinant superset, so it is membership-only without
augmentation (measured in §4).

### Why this is a *Wheeler graph* (and where the recognizer fits)

The BWT is the canonical Wheeler graph (Gagie–Manzini–Sirén 2017): its nodes are the suffixes in sorted
order, the Wheeler order **is** the suffix-array rank, and the axioms A1/A2/A3 are exactly the
`$`-anchor / `C[]`-block / LF-monotonicity structure of an FM-index. So the suffix order is a Wheeler
order **by theorem**. The recognizer's role (the project's recognition success put to work):

- **Certify on small instances** — emit the suffix graph as a DOT, run `recognizer_linux`, and show it
  is accepted **and** that the recognizer's independently-found Wheeler order is order-isomorphic to our
  suffix-array rank (the theory↔implementation loop, §3).
- **Trust the theorem at scale** — a faithful chrI suffix graph is ~10⁶ nodes, well past the
  recognizer's ~10⁵ practical ceiling (`GENOME_INDEX.md`), so at scale we build the FM-index directly,
  per block.
- **Gate the compacted variants** (§5) — merging suffix states into a smaller graph is *not* guaranteed
  Wheeler, and there the recognizer is the certifier in the loop.

## 2. The core algorithm — the tagged suffix Wheeler index (`index/suffix_index.py`)

Per block, over the same first-`a`, ungapped, cap-`l` rows the De Bruijn graph uses (row `i` = document
`i`):

- **Text:** `T = S_0 sep_0 S_1 sep_1 … S_{a-1} sep_{a-1}` with **distinct** separators `sep_i = i`
  (`0..a-1`), all smaller than DNA (`A=a, C=a+1, G=a+2, T=a+3`). Distinct separators make the
  multi-string BWT's **LF mapping exact** — a *single shared* `$` makes LF cyclic-inconsistent at
  document boundaries (found the hard way: `backward_search` stayed correct but `recover_pos` broke at
  the boundary rows; the fix was per-document separators + a cyclic-rotation suffix sort).
- **Suffix array** (cyclic-rotation, prefix-doubling `O(n log²n)`; a transparent brute sort is the test
  oracle), **BWT** `BWT[i]=T[(SA[i]-1) mod n]`, `C[]` + per-symbol prefix-rank (the `WGIndex` machinery
  reused over the BWT), **document array** `DOC[i]=doc[SA[i]]`, **sampled SA** (rate `s`).
- **`backward_search(P)`** over the BWT on the **forward** sequences (no reverse trick — contrast the De
  Bruijn index). `[lo,hi)` is exactly the occurrences: a DNA pattern never contains a separator, so a
  match can't cross a document boundary.
- **`locate(P)`** → for each `i∈[lo,hi)`: `p=recover_pos(i)` (LF-walk to the nearest sample), `d=doc[p]`,
  `local=p-doc_start[d]`, then `transform(coords[d], local, |P|)` → `{species, src, gstart, gend, strand,
  record_idx, ungapped_pos}`. Multi-hit, exact, any `|P|`.

**Verification (`index/tests/test_suffix_index.py`, all green):** SA/BWT/DOC/C/rank == the brute
reference; `recover_pos == SA` for every sample rate `s` (the LF fix); `locate ==` the independent brute
oracle (`index/locate_oracle`) on toy + real chrI blocks (present/multi-species/multi-hit/absent/
off-alphabet/`|P|` 1..whole-row) and **SA-sample invariant**; forward convention; and every located
**sacCer3** coordinate literally equals the query in the **real chrI genome** (len 230,218 == the MAF
`srcSize`); the − strand transform checked on a synthetic both-strands block.

## 3. Recognizer certification — the suffix order *is* the Wheeler order

`verify/suffix_wheeler_cert.py` exhibits the FM-index as a graph — node `i` (the i-th smallest suffix)
`--LF-->` node `LF(i)` labeled `BWT[i]` — and certifies it three independent ways (gated in
`test_suffix_index.py`):

1. **The SA-rank order satisfies the Wheeler axioms** — `verify/check_order` on `pos = identity`
   (node `i` at position `i`) returns *valid* (A2 = the `C[]` label blocks, A3 = LF monotonic within a
   label class, A1 trivial since LF is a bijection).
2. **Brute force agrees** — `verify/brute_oracle.is_wheeler` (all n! orders) returns Wheeler for n ≤ 9.
3. **The real recognizer independently accepts it** — `recognizer_linux -i -w` returns verdict 1, its
   emitted order is valid, **and it is order-isomorphic to the suffix-array rank** (the recognizer,
   searching the whole ordering space, lands on exactly the SA rank: `recognizer_iso_to_sa_rank = true`).

This closes the theory↔implementation loop: *the suffix order the index uses is precisely the Wheeler
order the recognizer finds.* At genome scale a faithful suffix graph is ~10⁶ nodes ≫ the recognizer's
~10⁵ ceiling, so we build the FM-index directly per block and rely on the theorem (certified on small
instances above). The recognizer is **central** again in §5, where merged graphs are not free Wheeler.

## 4. Comparison: resolution × compactness × speed

`benchmark/genome_index/resolution_demo.py` over 71 multi-species chrI blocks (a=4, De Bruijn k=8),
653 multi-species queries, ground-truthed by the brute oracle (`data/genome_resolution.json`). Every
suffix query is asserted == the oracle, so the benchmark is also a correctness gate.

| metric | suffix Wheeler index | De Bruijn (k-mer) | RevDet |
|---|---|---|---|
| **native species set correct** (index alone) | **100 %** (653/653) | **0 %** — a shared k-mer is one node, so the range carries no species | superset; column-membership only, dropped on serialize |
| **superset false positives** (recombinants accepted) | **0 / 592** | **592 / 592** (accepts every spliced recombinant) | superset on **71/71** blocks |
| range size == #occurrences | always (range *is* the occurrences) | 12.5 % (range size is uninformative about #occ) | — |
| median nodes / block | 257 | **211** (~1.2× smaller) | **117** (~2.2× smaller) |
| median locate latency | **8.4 µs** | 17 µs (occ-map locate) | — |

**Findings.**
- **Resolution:** the suffix index reports the exact species *set* and positions on **100 %** of
  multi-species queries, natively (its range == the occurrences, the document array reads off species).
  The De Bruijn graph names species on **0 %** — structurally, a k-mer shared by N species is one node,
  so the backward-search range is independent of which/how many species contain P; species only come
  from the external occ-map. This is the resolution loss the user observed, quantified.
- **Fidelity:** De Bruijn accepted **every** recombinant control (592/592) — strings present in *no*
  single species — i.e. its membership is a recombinant superset; the suffix index accepted **none**
  (exact). RevDet is likewise a superset on every multi-species block.
- **Cost:** the suffix index is only ~1.2× larger than De Bruijn (and ~2.2× larger than RevDet) but is
  **exact + resolved**, and its locate is ~2× **faster** than the occ-map. So on yeast the resolution is
  bought cheaply.
- **Is RevDet ideal?** No. It is the most compact, and its node *is* a (column, char) so position and
  species-membership are natural — but the path-language is a recombinant superset (membership only) and
  the column is lost on serialization. It trades exactness for size, the opposite of the goal.

**Recommendation:** the **tagged suffix Wheeler index** is the right construction for native
species+position resolution — exact, multi-hit, faster locate, modest size. De Bruijn remains the choice
when only compact *k-mer presence* is needed and resolution can live outside the index.

## 5. Compaction — run-length BWT (keeps resolution) + a recognizer-certified merge

Two ways to shrink the exact index, both verified (`test_suffix_index.py`; measured over 30 real
4-species chrI blocks):

**Run-length BWT (r-index).** The BWT is stored as `r` maximal equal-symbol runs and the suffix array
is sampled at the `r` run boundaries (`SuffixIndex(sample="runs")`). Locate is **identical** to the full
index (resolution preserved exactly — same answers, verified), with SA-sample storage dropping from `n`
to `r`. On yeast blocks median `r/n ≈ 0.65` (≈1.5× fewer SA samples); the win is modest at the short
block scale and grows with text length / repetitiveness (where the r-index is designed to shine — a
longer homologous concatenation runs far fewer, longer BWT runs). This is the recommended compaction:
**it costs no resolution.**

**Recognizer-certified merge — the suffix automaton (DAWG).** The DAWG (`index/dawg.py`) is the compact
*exact* merge of the suffix trie: it recognizes **exactly** the substrings (no recombinant superset,
unlike De Bruijn/RevDet), has ≤2n states, and each state's `endpos` set gives the (species, position)
hits. Whether a given DAWG is a Wheeler graph is **not** free — so the recognizer is put central to
certify it. Finding: the DAWG was **recognized Wheeler on 30/30 (and 40/40 earlier) blocks**, and its
`locate` is exact (== oracle). So the merge genuinely yields a *compact, exact, resolved Wheeler graph*
— a positive, recognizer-enabled result. **But it does not pay off on size here:** the DAWG has ~1.6×
**more** nodes (median 442 vs the suffix-array graph's 276) and a larger `endpos` locate payload than
the suffix-array index, because the suffix automaton sits between `n` and `2n` states while the
suffix-array Wheeler graph is exactly `n`. So on this data the suffix-array index is already at the
compact end of the *exact-resolution* frontier; the DAWG is an equally-exact alternative, not a smaller
one.

**Verdict:** keep the suffix-array tagged Wheeler index as the exact resolved core; compress it with the
**run-length BWT** (resolution-free). The DAWG is a clean illustration that the recognizer can certify
nontrivial compact-exact Wheeler graphs, but it is not smaller than the suffix-array graph for these
inputs.

## 6. Whole-chrI demo + recommendation

`index/pangenome_index.py` shards the suffix index per MAF block (no recognizer at build time — the
order is Wheeler by theorem, §3); a genome query unions the per-block locates behind a cheap per-block
symbol prefilter. `benchmark/genome_index/pangenome_demo.py` over **all 992 chrI blocks**
(`data/genome_pangenome.json`):

| measurement | value |
|---|---|
| blocks / build | 992 / **5.4 s** (5.5 ms per block) |
| total suffix nodes / SA samples | 820,487 / 205,377 |
| query latency | **7.7 ms / pattern** (all blocks, symbol prefilter) |
| verification (sample vs oracle union + real genome) | **0 mismatches / 30 patterns**, 124 sacCer3 genome checks |
| biological example | `CATTACCC` → **9 occurrences across 4 species** (sacCer3, sacKud, sacMik, sacPar), each with its genomic coordinate |

Every query returns the exact (species, genomic coordinate, strand) of every occurrence, multi-hit,
**natively** — the species come from the index's own document array, not a side table — and each sacCer3
hit is verified against the real chromosome. (Random short controls that happen to occur are reported as
the real occurrences they are; only truly-absent / off-alphabet strings return nothing — there is no
recombinant superset.)

## 7. Recommendation & what we learned

- **The new algorithm:** a **tagged suffix Wheeler-graph index** — the multi-string BWT with a document
  array (species) and a sampled suffix array (position). Backward search returns the exact occurrence
  interval; the tags read off (species, position). This is the construction whose Wheeler range *is* the
  occurrences, giving **native, exact, multi-hit species+position resolution** — what the De Bruijn
  k-mer index could not (it collapses k-mers, 0 % native species, and accepts a recombinant superset).
- **The recognizer was genuinely useful:** it independently finds exactly the suffix-array rank as the
  Wheeler order (certifying the construction), and it certifies that the compact-exact DAWG is Wheeler.
- **What we tried and learned:** RevDet (the user's candidate) is compact but a membership-only
  recombinant superset with the column lost on serialization — *not* ideal for resolution. The
  run-length BWT compresses the index with **zero** resolution loss (the right compaction). The
  suffix-automaton merge yields an equally-exact Wheeler graph but is *not* smaller than the
  suffix-array graph, so the suffix-array index already sits at the compact end of the exact-resolution
  frontier.
- **Cost honestly stated:** the suffix index is ~1.2× larger than the small-k De Bruijn graph and is
  O(text length) per block, so it is sharded per block (as the De Bruijn genome index is); it is the
  right tool when you need *which species, where*, and the De Bruijn graph remains the choice for compact
  k-mer *presence* alone.

### Reproduce
```bash
~/miniconda3/envs/myenv/bin/python -m pytest index/tests/test_suffix_index.py -q   # all gates
python3 verify/suffix_wheeler_cert.py ACGACG ACGTAC                                 # recognizer cert
python3 benchmark/genome_index/resolution_demo.py -a 4 --kdb 8 --limit 80           # suffix vs De Bruijn
python3 benchmark/genome_index/pangenome_demo.py -a 4 -s 4 --blocks 0               # whole-chrI demo
```
