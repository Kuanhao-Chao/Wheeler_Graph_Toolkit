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

## 3. Recognizer certification (suffix order == a Wheeler order) — *pending (P2)*

## 4. Comparison: resolution × compactness × speed (suffix vs De Bruijn vs RevDet-tagged) — *pending (P3)*

## 5. Compaction: run-length BWT + recognizer-certified merge — *pending (P4)*

## 6. Whole-chrI demo + recommendation — *pending (P5)*
