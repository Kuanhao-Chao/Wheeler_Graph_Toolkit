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
    def __init__(self, seqs, coords=None, s=8):
        """seqs: ungapped/upper/ACGT rows (row i = document i). coords: per-row coords dicts (optional;
        enables genomic locate). s: SA sample rate (s=1 stores the full SA)."""
        self.coords = coords
        self.s = max(1, s)
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
        self._pref = [[0] * (self.n + 1) for _ in range(self.sigma)]
        for c in range(self.sigma):
            p = self._pref[c]
            for i, x in enumerate(self.BWT):
                p[i + 1] = p[i] + (1 if x == c else 0)
        # document array + sampled SA (sample where text pos % s == 0; pos 0 always sampled)
        self.DOC = [self.doc[self.SA[i]] for i in range(self.n)]
        self.sampled = [(self.SA[i] % self.s == 0) for i in range(self.n)]
        self.sa_val = {i: self.SA[i] for i in range(self.n) if self.sampled[i]}

    def _rank(self, c, i):
        return self._pref[c][i]

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

    def locate(self, P):
        """Every occurrence of P as a hit dict; (species, src, genomic coords, strand) if coords given,
        else (record_idx, ungapped_pos). Exact, multi-hit, any |P|."""
        m = len(P)
        if m == 0:
            return []
        lo, hi = self.backward_search(P)
        hits = []
        for i in range(lo, hi):
            p = self.recover_pos(i)
            d = self.doc[p]
            local = p - self.doc_start[d]
            h = {"record_idx": d, "ungapped_pos": local}
            if self.coords is not None:
                c = self.coords[d]
                gs, ge, st = transform(c, local, m)
                h.update({"species": c["fasta_id"], "src": c["src"],
                          "gstart": gs, "gend": ge, "strand": st})
            hits.append(h)
        return _dedup_sort(hits, genomic=self.coords is not None)

    @classmethod
    def from_fasta(cls, fasta, a=None, l=-1, coords=None, s=8):
        recs = read_fasta(fasta)
        if a is not None:
            recs = recs[:a]
        seqs = [_ungap_cap(seq, l) for _id, seq in recs]
        return cls(seqs, coords=coords, s=s)


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
