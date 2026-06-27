"""A tagged suffix Wheeler-graph index: native species + position resolution, exact multi-hit locate.

The De Bruijn k-mer index merges identical k-mers across all sequences, so its backward-search range is
a set of *collapsed* nodes (one shared node for a k-mer used by many species) and species/position have
to be recovered from a side table. This index instead uses the **suffix-sorted Wheeler order** (the
multi-string BWT): backward search returns the contiguous range [lo,hi) that is *exactly the
occurrences* of P, and a per-position **document array** (species) + a **sampled suffix array**
(position) read off every hit. Because `$` is the smallest symbol and never appears in a DNA query, a
match can never cross a document boundary, so every occurrence lies within one species — exact.

The suffix order is a Wheeler order by the Gagie-Manzini-Siren theorem (the BWT is the canonical Wheeler
graph); `verify/suffix_wheeler_cert.py` certifies this on small instances with the recognizer and shows
the recognizer's emitted order is the suffix-array rank. At genome scale we build the FM-index directly
(per block) and trust the theorem.

Pure stdlib. Built from the SAME first-`a`, ungapped, cap-`l` content as the De Bruijn graph and the
existing locate, so positions line up with the coords sidecar and the brute oracle.
"""
import bisect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.faithful import _ungap_cap, read_fasta  # noqa: E402
from index.locate import transform                 # noqa: E402  (genomic coord map, ± strand)

# Alphabet (per block of `a` rows): one DISTINCT separator per document, all smaller than DNA, so the
# multi-string BWT's LF mapping is exact (a single shared '$' makes LF cyclic-inconsistent at document
# boundaries). sep_i = i (0..a-1); A=a, C=a+1, G=a+2, T=a+3.  A DNA query never contains a separator, so
# an occurrence can never cross a document boundary -> every hit lies within one species.
DNA = "ACGT"


def dna_code(a):
    return {c: a + i for i, c in enumerate(DNA)}


# --------------------------------------------------------------------------- text + suffix array
def build_text(seqs):
    """seqs (ungapped, upper, ACGT) -> (T, doc, doc_start, a). T = S_0 sep_0 S_1 sep_1 ... ; sep_i = i;
    doc[p] = which row text position p belongs to."""
    a = len(seqs)
    code = dna_code(a)
    T, doc, doc_start = [], [], []
    for i, s in enumerate(seqs):
        doc_start.append(len(T))
        for ch in s:
            T.append(code[ch]); doc.append(i)
        T.append(i)                              # distinct separator sep_i = i
        doc.append(i)
    return T, doc, doc_start, a


def build_sa_brute(T):
    """Transparent reference: cyclic-rotation suffix array (rotation R_p = T[p:]+T[:p])."""
    n = len(T)
    return sorted(range(n), key=lambda p: T[p:] + T[:p])


def build_sa(T):
    """Cyclic-rotation suffix array by prefix doubling, O(n log^2 n) (modular index -> rotations).
    Distinct separators make all rotations distinct, so this is a strict total order == build_sa_brute."""
    n = len(T)
    if n == 0:
        return []
    sa = list(range(n))
    rank = list(T)
    tmp = [0] * n
    k = 1
    while True:
        def key(i):
            return (rank[i], rank[(i + k) % n])   # modular: cyclic rotations
        sa.sort(key=key)
        tmp[sa[0]] = 0
        for a, b in zip(sa, sa[1:]):
            tmp[b] = tmp[a] + (1 if key(a) < key(b) else 0)
        rank = tmp[:]
        if rank[sa[-1]] == n - 1:                 # all ranks distinct -> done
            return sa
        k <<= 1


def build_bwt(T, SA):
    n = len(T)
    return [T[(SA[i] - 1) % n] for i in range(n)]


# --------------------------------------------------------------------------- the index
class SuffixIndex:
    def __init__(self, seqs, coords=None, s=8, sample="rate"):
        """seqs: ungapped/upper/ACGT rows (row i = document i). coords: per-row coords dicts (optional;
        enables genomic locate). s: SA sample rate. sample: 'rate' (every s-th text position) or 'runs'
        (at BWT run boundaries -> r samples, the r-index compaction; resolution unchanged)."""
        self.coords = coords
        self.s = max(1, s)
        self.sample_mode = sample
        self.T, self.doc, self.doc_start, self.a = build_text(seqs)
        self.code = dna_code(self.a)
        self.n = len(self.T)
        self.SA = build_sa(self.T)
        self.BWT = build_bwt(self.T, self.SA)
        self.sigma = self.a + 4                   # separators 0..a-1 + ACGT
        # C[c] = #symbols < c in T (== in BWT); per-symbol prefix rank over BWT
        cnt = [0] * self.sigma
        for x in self.T:
            cnt[x] += 1
        self.C = [0] * self.sigma
        run = 0
        for c in range(self.sigma):
            self.C[c] = run; run += cnt[c]
        self._build_rank()
        # number of maximal equal-symbol BWT runs (the r-index size measure)
        self.r = 1 if self.n else 0
        for i in range(1, self.n):
            if self.BWT[i] != self.BWT[i - 1]:
                self.r += 1
        # document array + sampled SA. 'rate': text pos % s == 0 (pos 0 always). 'runs': BWT run heads
        # (r samples) -> the r-index compaction; locate is identical, SA storage drops to O(r).
        self.DOC = [self.doc[self.SA[i]] for i in range(self.n)]
        if self.sample_mode == "runs":
            self.sampled = [(i == 0 or self.BWT[i] != self.BWT[i - 1]) for i in range(self.n)]
        else:
            self.sampled = [(self.SA[i] % self.s == 0) for i in range(self.n)]
        self.sa_val = {i: self.SA[i] for i in range(self.n) if self.sampled[i]}
        self.n_samples = len(self.sa_val)
        self._build_phi()
        # SA is a build-time intermediate: no query path uses it (recover_pos uses sa_val, locate_phi
        # uses the toehold + phi). In r-index ('runs') mode we drop it to save n ints/block at genome
        # scale. ('rate' keeps it: the C++-parity default + cheap; ground-truth SA is build_sa(T).)
        if self.sample_mode == "runs":
            self.SA = None

    BLOCK = 64

    def _build_rank(self):
        """Block-rank over BWT: cumulative per-symbol counts every BLOCK symbols (O(sigma*n/BLOCK)),
        vs a dense O(sigma*n) prefix array -- the per-block RAM driver. Mirrors cpp/wg_suffix LabelRank."""
        B, n, sg = self.BLOCK, self.n, self.sigma
        nb = n // B + 1
        self._brank = [[0] * (nb + 1) for _ in range(sg)]
        run = [0] * sg
        for i, x in enumerate(self.BWT):
            if i % B == 0:
                bi = i // B
                for c in range(sg):
                    self._brank[c][bi] = run[c]
            run[x] += 1
        last = (n + B - 1) // B
        for c in range(sg):
            self._brank[c][last] = run[c]

    def _build_phi(self):
        """r-index structures for bounded locate (NO full-SA walk): phi (predecessor + offset over BWT
        run heads) + per-symbol run-tail SA samples for the backward-search toehold. O(r) space."""
        n = self.n
        # phi pairs (SA[i], SA[(i-1) mod n]) at run heads, keyed/sorted by the SA value (text position)
        pairs = sorted((self.SA[i], self.SA[(i - 1) % n]) for i in range(n)
                       if i == 0 or self.BWT[i] != self.BWT[i - 1])
        self._phi_keys = [a for a, _ in pairs]
        self._phi_vals = [b for _, b in pairs]
        # run-tail SA samples grouped by symbol: rows (ascending) + their SA values, for the toehold
        self._tail_rows = {}
        self._tail_sa = {}
        for i in range(n):
            if i == n - 1 or self.BWT[i + 1] != self.BWT[i]:
                c = self.BWT[i]
                self._tail_rows.setdefault(c, []).append(i)
                self._tail_sa.setdefault(c, []).append(self.SA[i])
        self._sa_bottom = self.SA[n - 1] if n else 0     # SA[hi-1] of the full range (a run-tail sample)

    def phi(self, p):
        """phi(p) = SA[(ISA[p]-1) mod n] = text position of the lexicographic predecessor of suffix p,
        via predecessor over run-head samples + linear offset (Gagie-Navarro-Prezza). O(log r)."""
        k = bisect.bisect_right(self._phi_keys, p) - 1   # largest key <= p (k=-1 -> cyclic: last pair)
        return (self._phi_vals[k] + (p - self._phi_keys[k])) % self.n

    def _rank(self, c, i):
        B = self.BLOCK
        b = i // B
        r = self._brank[c][b]
        bwt = self.BWT
        for j in range(b * B, i):
            r += (bwt[j] == c)
        return r

    def lf(self, i):
        c = self.BWT[i]
        return self.C[c] + self._rank(c, i)

    def recover_pos(self, i):
        """Text position SA[i] via the LF walk to the nearest sample (< s steps)."""
        steps = 0
        j = i
        while not self.sampled[j]:
            j = self.lf(j); steps += 1
        return self.sa_val[j] + steps

    def _encode(self, P):
        try:
            return [self.code[c] for c in P.upper()]
        except KeyError:
            return None                         # off-alphabet -> no occurrences

    def backward_search(self, P):
        """SA interval [lo, hi) of suffixes starting with P (FORWARD; no reverse trick)."""
        cs = self._encode(P)
        if not cs:
            return (0, 0)
        lo, hi = 0, self.n
        for c in reversed(cs):                  # right-to-left over P
            lo = self.C[c] + self._rank(c, lo)
            hi = self.C[c] + self._rank(c, hi)
            if lo >= hi:
                return (lo, lo)
        return (lo, hi)

    def count(self, P):
        lo, hi = self.backward_search(P)
        return hi - lo

    def _hit(self, pos, m):
        """Build a hit dict for an occurrence at text position `pos` (length m)."""
        d = self.doc[pos]
        local = pos - self.doc_start[d]
        h = {"record_idx": d, "ungapped_pos": local}
        if self.coords is not None:
            c = self.coords[d]
            gs, ge, st = transform(c, local, m)
            h.update({"species": c["fasta_id"], "src": c["src"],
                      "gstart": gs, "gend": ge, "strand": st})
        return h

    def locate(self, P):
        """Every occurrence of P as a hit dict; (species, src, genomic coords, strand) if coords given,
        else (record_idx, ungapped_pos). Exact, multi-hit, any |P|. Uses the bounded r-index phi-walk
        when sample='runs', else the rate-sampled LF-walk."""
        m = len(P)
        if m == 0:
            return []
        if self.sample_mode == "runs":
            return self.locate_phi(P)
        lo, hi = self.backward_search(P)
        hits = [self._hit(self.recover_pos(i), m) for i in range(lo, hi)]
        return _dedup_sort(hits, genomic=self.coords is not None)

    def _backward_toehold(self, P):
        """Backward search keeping the SA value of the bottom row (the 'toehold'), using only run-tail
        samples (no full SA). Returns (lo, hi, toehold = SA[hi-1]) or (lo, lo, None) if empty."""
        cs = self._encode(P)
        if not cs:
            return (0, 0, None)
        lo, hi = 0, self.n
        p = self._sa_bottom                       # SA[hi-1] of the full range
        for c in reversed(cs):
            nlo = self.C[c] + self._rank(c, lo)
            nhi = self.C[c] + self._rank(c, hi)
            if nlo >= nhi:
                return (nlo, nlo, None)
            if self.BWT[hi - 1] == c:             # the bottom row is itself a c -> it maps to new bottom
                p = (p - 1) % self.n
            else:                                 # else the new bottom comes from the last c-run tail < hi
                rows = self._tail_rows[c]
                k = bisect.bisect_left(rows, hi) - 1
                p = (self._tail_sa[c][k] - 1) % self.n
            lo, hi = nlo, nhi
        return (lo, hi, p)

    def locate_phi(self, P):
        """r-index locate: one toehold (SA[hi-1]) from backward search, then phi to enumerate the rest --
        O(1) predecessor work per occurrence (no unbounded LF walk). Identical result to locate()."""
        m = len(P)
        if m == 0:
            return []
        lo, hi, pos = self._backward_toehold(P)
        if lo >= hi:
            return []
        hits = []
        for _ in range(hi - lo):                  # pos = SA[hi-1], SA[hi-2], ..., SA[lo]
            hits.append(self._hit(pos, m))
            pos = self.phi(pos)
        return _dedup_sort(hits, genomic=self.coords is not None)

    @classmethod
    def from_fasta(cls, fasta, a=None, l=-1, coords=None, s=8, sample="rate"):
        recs = read_fasta(fasta)
        if a is not None:
            recs = recs[:a]
        seqs = [_ungap_cap(seq, l) for _id, seq in recs]
        return cls(seqs, coords=coords, s=s, sample=sample)


def _dedup_sort(hits, genomic):
    if genomic:
        seen, out = set(), []
        for h in sorted(hits, key=lambda h: (h["species"], h["src"], h["gstart"], h["gend"])):
            key = (h["species"], h["src"], h["gstart"], h["gend"], h["strand"])
            if key not in seen:
                seen.add(key); out.append(h)
        return out
    seen, out = set(), []
    for h in sorted(hits, key=lambda h: (h["record_idx"], h["ungapped_pos"])):
        key = (h["record_idx"], h["ungapped_pos"])
        if key not in seen:
            seen.add(key); out.append(h)
    return out


def as_tuples(hits):
    """Genomic occurrence set (species, src, gstart, gend, strand) -- matches locate/locate_oracle."""
    return {(h["species"], h["src"], h["gstart"], h["gend"], h["strand"]) for h in hits}
