"""A queryable FM-index over a Wheeler graph — the layer WGT was missing.

Consumes the recognizer's succinct output (Gagie I/O/L: per-node in/out-degree bitvectors in Wheeler
order + the out-edge BWT label column) and answers pattern queries by backward search, the operation
the structure was always meant to support but no code in the toolkit performed.

`count(P)` returns `(lo, hi, n)`: the half-open range `[lo, hi)` of Wheeler-order nodes reachable by a
walk spelling P (from any start), and `n = hi - lo` matches.  For a De Bruijn graph of an MSA, a path
spells the reverse of a sequence, so querying reverse(pattern) answers "does the pattern occur in the
alignment, and at how many graph states" (see index/README.md, pipeline/msa_to_index.py).

Two constructors that must agree:
  * `from_iol(dir)`     — load straight from the recognizer's `I.txt`/`O.txt`/`L.txt` (makes the
                          recognizer's own output a live index).
  * `from_graph_dot(p)` — build the same I/O/L from the relabeled Wheeler-order `graph.dot`.

Rank/select are plain prefix arrays (correctness over speed; a succinct/C++ port is future work). The
label total order is the sorted distinct label set; the I/O/L-match test confirms the recognizer uses
the same order, so backward search is consistent with the order the Wheeler axioms were enforced under.
"""
import os


class WGIndex:
    def __init__(self, I_bits, O_bits, L_str):
        self.I = I_bits
        self.O = O_bits
        self.L = L_str
        self.n = I_bits.count("1")
        self.E = len(L_str)
        assert O_bits.count("1") == self.n, "I and O must mark the same node count"
        assert len(I_bits) == self.n + self.E and len(O_bits) == self.n + self.E, "bad I/O length"

        # in-order in-edges grouped by head node (Wheeler order): inedge_node[i] = head of i-th in-edge
        self.inedge_node = [0] * self.E
        ones = z = 0
        for ch in I_bits:
            if ch == "1":
                ones += 1
            else:
                self.inedge_node[z] = ones + 1   # head node is the next '1'-block
                z += 1
        # out_prefix[v] = number of out-edges of nodes 1..v-1  (v in 1..n+1)
        self.out_prefix = [0] * (self.n + 2)
        ones = z = 0
        for ch in O_bits:
            if ch == "1":
                ones += 1
                self.out_prefix[ones + 1] = z       # block for node ones+1 starts after z out-edges
            else:
                z += 1
        self.out_prefix[1] = 0

        # label order + C[] (cumulative count of edges with a strictly-smaller label) + per-label prefix
        self.labels = sorted(set(L_str))
        self.C = {}
        running = 0
        for c in self.labels:
            self.C[c] = running
            running += L_str.count(c)
        # prefix_rank[c][i] = #occurrences of c in L[:i]
        self._pref = {c: [0] * (self.E + 1) for c in self.labels}
        for c in self.labels:
            p = self._pref[c]
            for i, ch in enumerate(L_str):
                p[i + 1] = p[i] + (1 if ch == c else 0)

    # ---------------------------------------------------------------- queries
    def _rank(self, c, i):
        """#occurrences of label c in L[:i]."""
        return self._pref[c][i] if c in self._pref else 0

    def step(self, lo, hi, c):
        """[lo,hi) node range, char c -> head range [a,b) reachable by a c-edge from a tail in [lo,hi)."""
        if c not in self.C or lo >= hi:
            return (lo, lo)
        out_lo = self.out_prefix[lo]
        out_hi = self.out_prefix[hi]
        r_lo = self._rank(c, out_lo)
        r_hi = self._rank(c, out_hi)
        if r_lo == r_hi:
            return (lo, lo)              # empty
        in_lo = self.C[c] + r_lo
        in_hi = self.C[c] + r_hi
        head_lo = self.inedge_node[in_lo]
        head_hi = self.inedge_node[in_hi - 1]
        return (head_lo, head_hi + 1)

    def count(self, pattern):
        """Backward search. Returns (lo, hi, n) — the reachable Wheeler-order node range and its size."""
        lo, hi = 1, self.n + 1
        for c in pattern:
            lo, hi = self.step(lo, hi, c)
            if lo >= hi:
                return (lo, lo, 0)
        return (lo, hi, hi - lo)

    # ---------------------------------------------------------------- constructors
    @classmethod
    def from_iol(cls, outdir):
        rd = lambda f: open(os.path.join(outdir, f)).read().strip()
        return cls(rd("I.txt"), rd("O.txt"), rd("L.txt"))

    @classmethod
    def from_edges(cls, nodes, edges):
        """Build I/O/L from a Wheeler-order edge list (nodes are integers 1..n). Mirrors the
        recognizer's output_wg_gagie ordering: per node, in/out degree zeros + a 1; L = out-edge
        labels sorted ascending, repeated by count."""
        n = max(nodes) if nodes else 0
        indeg = [0] * (n + 1)
        outedges = {v: [] for v in range(1, n + 1)}
        for t, h, lab in edges:
            indeg[h] += 1
            outedges[t].append(lab)
        I = O = ""
        L = []
        for v in range(1, n + 1):
            I += "0" * indeg[v] + "1"
            outs = sorted(outedges[v])              # ascending label order
            O += "0" * len(outs) + "1"
            L.extend(outs)
        return cls(I, O, "".join(L))

    @classmethod
    def from_graph_dot(cls, path):
        from index import oracle
        nodes, edges = oracle.parse_dot(open(path).read())
        return cls.from_edges(nodes, edges)

    def iol(self):
        return self.I, self.O, self.L
