# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

WGT (Wheeler Graph Toolkit) is the research codebase accompanying the bioRxiv paper
"WGT: Tools and algorithms for recognizing, visualizing and generating Wheeler graphs."
It has four parts: a C++ **recognizer** (the core; nicknamed *Wheelie*), Python **generators**
that turn FASTA multiple-sequence alignments into graphs, a Python **visualizer**, and a
**benchmark** harness (which includes a reference implementation of Gibney & Thankachan's
exponential algorithm). A Wheeler graph is an edge-labeled digraph admitting a total node
ordering compatible with edge labels; recognizing one is NP-complete, so the recognizer's job
is to search that ordering efficiently.

## Build & run the recognizer (`recognizer/`)

The canonical build is the top-level `recognizer/Makefile`. Z3 is a git submodule and the SMT
backend links against it statically:

```bash
cd recognizer
git submodule update --init --recursive   # first time only
make z3      # builds Z3, runs `sudo make install` into ./z3 (asks for root password)
make         # builds the recognizer, copies it to recognizer/bin/
```

A prebuilt `recognizer/bin/recognizer` is committed, **but it is a Mach-O arm64 (Apple Silicon
macOS) binary** — it fails with `Exec format error` on this Linux host. On Linux (or any
non-arm64-macOS platform) you must rebuild from source; the committed binary is not a shortcut here.

Run it on a DOT file:

```bash
./bin/recognizer ../data/example/example.dot          # default: SMT (Z3) backend
./bin/recognizer ../data/example/example.dot -s p      # permutation backend instead
```

Key flags (`recognizer/README.md` lists them, but that README is partly stale — see note below):
`-s smt|p` (backend; default is effectively SMT — no `-s` sets the internal solver to `"default"`,
which dispatches to SMT), `-o <dir>` (output dir), `-w` (**gates all on-disk output** — see Output),
`-r` (also write `range.txt`), `-i` (edge labels are integers), `-b` (benchmark mode),
`-e` (exhaustive permutation search — **only takes effect together with `-s p`**; with the default
SMT solver `-e` is ignored), `-f` (full-range search — skip the renaming heuristic and hand the
whole space to the solver; **`-f` always uses SMT and ignores `-s p`**), `-v` (verbose).

The bundled READMEs (`README.md`, `recognizer/README.md`) drifted from the code: they claim version
`0.1.0` (source is `1.0.0`), call the node map `node.dot` (it is `nodes.txt`), and say `-e` sets the
solver to `p` (it does not). Trust the source over the READMEs for behavior.

### macOS / Z3-free build
`recognizer/src/Makefile_macos` is *intended* to build a **permutation-only** binary (`recognizer_p`,
no `smt.cpp`) so you can avoid building Z3, running with `-s p`. Treat this path as unverified:
`wg.cpp`/`graph.cpp` still call `solve_smt()`, which lives only in `smt.cpp`, so the link may fail in
the current source state. Both `recognizer/src/Makefile` and `Makefile_macos` also carry stale paths
from an older layout (a hardcoded conda include dir and `../../../bin` copy targets); prefer the
top-level Makefile, which globs `find src -name '*.cpp'` (so any stray `.cpp` dropped in `src/` gets
compiled in).

### Don't edit the wrong tree
`recognizer/permutation_fix/` and `recognizer/smt/` both exist on disk but are **gitignored scratch**.
`permutation_fix/src/` is a near-complete *second copy* of the recognizer source (an experimental
variant); `recognizer/smt/` holds standalone Python WG-checking prototypes, **not** the C++ SMT
backend. Edit the recognizer in `recognizer/src/` only.

## Recognizer architecture

Everything is built around the `digraph` class (`recognizer/src/graph.hpp`). The class's methods
are split across several `.cpp` files: `graph.cpp` (the algorithm), `smt.cpp` (the Z3 backend),
`get_func.cpp`/`print_func.cpp` (accessors/printers), with `edge.*` (the edge type) and
`GArgs.*`/`GBase.*` (CLI parsing and base utilities, vendored from GCLib). `wg.cpp` is `main`.

`wg.cpp` parses the DOT, builds the `digraph`, then runs a **three-step pipeline**:

1. `relabel_initialization()` — initial constraints; if violated, not a Wheeler graph.
2. `innodelist_sort_relabel()` — the **renaming heuristic**: sorts/relabels nodes and narrows
   each node to a `[lb, ub]` order range (`_node_ranges`). This is what makes recognition fast —
   it shrinks the search space before the solver runs.
3. Solve within those ranges, via one of two interchangeable backends:
   - **SMT** (`solve_smt()` in `smt.cpp`, default): encodes the ordering as a Z3 `QF_IDL`
     problem and asks for a model.
   - **Permutation** (`permutation_start()` in `graph.cpp`, `-s p`): enumerates valid orderings
     per edge-label group with pruning (`WG_checker*`).

`-f` / `full_range_search` bypasses the step-2 range narrowing (step 2 still runs, but its
range-shrinking branches are disabled internally) and forces the SMT backend regardless of `-s`.

### DOT input contract
Input must be a `strict digraph` with edge lines of the form `A -> B [label=x];`. The parser
(`wg.cpp`) strips spaces and matches `(\w+)->(\w+)\[label=(\w+)\];`, so **standalone node
declarations are ignored** — nodes are inferred only from edges, and labels must be single
`\w+` tokens.

### Output
**A successful run writes no files by default** — it only prints `(v) It is a wheeler graph!!`
(preceded by `solved by SMT` / `solved by permutation` / `Decided after propagation`, depending on
the path). `-w` is what gates the on-disk structure: with `-w`, files land in
`<outDir>/out__<dotstem>/` (default `outDir` is `./`): `I.txt`, `O.txt`, `L.txt` (Gagie et al.'s
succinct WG structure), `nodes.txt` (old→new node-label mapping), and `graph.dot` (relabeled, sorted
graph). `range.txt` is separate: it is written by `-r` during step 2, *before* the final solve, so it
can exist even for a graph the solver later rejects. A non-Wheeler graph produces no output and the
program halts (exit `-1`; a valid WG exits `1`). The committed `data/example/out__example/` was
generated with `-w -r`, so it is not what a default run produces.

## Generators (`generator/`)

**Five git-tracked** Python generators produce DOT graphs (two more dirs,
`MultiSeqWG_generator/` and `PrefixSortedGraph/`, exist on disk but are **gitignored, incomplete
WIP** — `PrefixSortedGraph`'s prefix-doubling step is a no-op stub and its `Run_Fasta_2_Dot.sh`
calls a script that doesn't exist; `MultiSeqWG_generator` is a recognizer-coupled multi-step
pipeline with stale `../../` paths. Ignore both unless you're reviving them.)

The four FASTA-based generators — `DeBruijnGraph_generator`, `DeBruijnGraph_generator_noncollapse`,
`RevDetGraph_generator`, `Trie_generator` — **require Biopython** (`Bio`), parse args with
`getopt` (not argparse), and each imports a sibling `node.py`, so **run them from inside their own
directory**. They batch-convert FASTA trees under `data/multiseq_alignment/` into DOT under
`data/graph/` via `Run_Fasta_2_Dot.sh` — *except* `Trie_generator`, which has no such script, and
the `noncollapse` one, whose script has its python call commented out. Several scripts carry a
hardcoded macOS conda shebang, so invoke them through an explicit `python`/`python3`, never `./`.

```bash
cd generator/DeBruijnGraph_generator
python DeBruijnGraph_generator.py -o out.dot -k <kmer> -l <seqLen> -a <alnNum> input.fasta
```

Flags differ per generator: only `DeBruijnGraph_generator` takes `-k`; `RevDetGraph_generator` and
`Trie_generator` take just `-o/-l/-a`. The FASTA path is a positional argument.

`generator/Random_generator/` (`gen_complete_WG.py`, `gen_d-nfa_WG.py`) synthesizes random valid
Wheeler graphs and uses **only the standard library** (argparse here). Both require `-n/-e/-l`
and `assert` edge-count feasibility, so infeasible parameters abort with an `AssertionError`.

## Visualizer (`visualizer/`)

`visualizer.py` (needs **NetworkX + matplotlib**) draws a recognizer-output `graph.dot` in the
bipartite representation:

```bash
cd visualizer
python3 visualizer.py ../data/example/out__example/graph.dot       # opens an interactive window
python3 visualizer.py -o out.png ../data/example/out__example/graph.dot   # saves a PNG instead
```

It expects **integer node labels**, so it only works on the recognizer's relabeled `graph.dot`,
not on arbitrary input DOT. Without `-o` it calls `plt.show()`; with `-o` it saves a PNG (the
path must include a directory component or the existence check fails).

## Benchmarking (`benchmark/`)

`benchmark/exponential_recognizer/` is the exponential baseline (Gibney & Thankachan); build it
with `make` in its `src/` to get `recognizer_e`. Both binaries emit the same **four
whitespace-separated columns** — *is-Wheeler*, *node count*, *time*, *input path* — but the
mechanism and encoding differ:

- The **main** recognizer emits them in benchmark mode via the runtime `-b` flag; column 1 is `1`
  for a Wheeler graph, `-1` otherwise.
- The **exponential** baseline has **no `-b` flag** — it always prints the columns (compile-time
  `#define BENCHMARK`), and its column 1 is `0` for a Wheeler graph, `-1` otherwise.

So column 1 is not a clean boolean (1/-1 vs 0/-1, with `-1` also doubling as the timeout sentinel
the wrappers append), and the time column is `clock()` CPU ticks (numerically ≈ µs on Linux, but
CPU not wall time). The `run_*.sh` scripts under `benchmark/unit_test/` wrap each call in a
`timeout` — **duration varies by experiment** (`15s`/`30s`/`500s`/`1000s`, not a uniform 500s) and
exit 124 appends a synthetic timeout row. The unit_test tree is organized by comparison axis
(`GT_vs_WGT`, `SMT_vs_RHSMT`, `RHPer_vs_RHSMT`), with a large legacy `prev/` subtree that is not
part of the current pipeline. The `benchmark/results/Figure_*/plot_*.py` scripts turn results into
the paper's figures — they need **matplotlib + numpy, and several also need pandas**.

## Data (`data/`)

`data/multiseq_alignment/` holds source FASTA MSAs (input to generators), plus the Ensembl
data-retrieval scripts under `Ensembl_REST/` and `Genes/` that produced them; `data/example/` is a
small worked example. `data/graph/` is more than "generated DOT": alongside ~11.5k `.dot` files it
holds recognizer **output** dirs and per-experiment **`create_exp.sh`** regeneration scripts — these
scripts (with their explicit `-n/-e/-l` or `-k/-l/-a` parameters) are the authoritative record of
how the paper's benchmark graphs were generated.

The `doc/`, `proof/`, `slides/`, and `.vscode/` directories exist locally but are **gitignored**
(reports, the NP-completeness proof, talk slides, editor settings). The repo is MIT licensed and has
**no Cursor/Copilot rule files** — this CLAUDE.md is the only assistant-guidance file.
