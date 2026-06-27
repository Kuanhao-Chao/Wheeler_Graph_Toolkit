"""Suffix automaton (DAWG) of the multi-string text -- the compact, EXACT merge of the suffix trie, and
the candidate compact resolved index for the recognizer-certified-merge experiment (P4).

The DAWG recognizes exactly the substrings of T (no recombinant superset, unlike De Bruijn/RevDet),
has <= 2n states (vs n suffixes), and each state carries an `endpos` set -> the positions where that
substring ends -> (document/species, position). So IF the DAWG is a Wheeler graph, it is a *compact
exact resolved* index. Whether a given DAWG is Wheeler is not free -- that is exactly what the
recognizer certifies (the recognizer put central, as the user hoped).

Built over the same multi-string text as index/suffix_index (distinct separators sep_i=i < DNA), so a
DNA pattern's endpos all lie within one document. Pure stdlib.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from index.suffix_index import build_text, dna_code  # noqa: E402
from index.locate import transform                   # noqa: E402


class DAWG:
    def __init__(self, seqs, coords=None):
        self.coords = coords
        self.T, self.doc, self.doc_start, self.a = build_text(seqs)
        self.code = dna_code(self.a)
        self._build(self.T)
        self._propagate_endpos()

    def _build(self, T):
        self.nxt = [dict()]          # transitions: state -> {symbol: state}
        self.link = [-1]
        self.length = [0]
        self.endpos = [set()]        # primary endpos (one per non-clone extend); full set after propagate
        self.is_clone = [False]
        last = 0
        for pos, c in enumerate(T):
            cur = len(self.nxt)
            self.nxt.append(dict()); self.link.append(-1); self.length.append(self.length[last] + 1)
            self.endpos.append({pos}); self.is_clone.append(False)
            p = last
            while p != -1 and c not in self.nxt[p]:
                self.nxt[p][c] = cur; p = self.link[p]
            if p == -1:
                self.link[cur] = 0
            else:
                q = self.nxt[p][c]
                if self.length[p] + 1 == self.length[q]:
                    self.link[cur] = q
                else:
                    clone = len(self.nxt)
                    self.nxt.append(dict(self.nxt[q])); self.link.append(self.link[q])
                    self.length.append(self.length[p] + 1); self.endpos.append(set())
                    self.is_clone.append(True)
                    while p != -1 and self.nxt[p].get(c) == q:
                        self.nxt[p][c] = clone; p = self.link[p]
                    self.link[q] = clone; self.link[cur] = clone
            last = cur
        self.n_states = len(self.nxt)

    def _propagate_endpos(self):
        # full endpos[v] = union of endpos over the suffix-link subtree; propagate by decreasing length
        order = sorted(range(self.n_states), key=lambda v: -self.length[v])
        for v in order:
            lp = self.link[v]
            if lp != -1:
                self.endpos[lp] |= self.endpos[v]

    def _encode(self, P):
        try:
            return [self.code[c] for c in P.upper()]
        except KeyError:
            return None

    def _state_of(self, P):
        cs = self._encode(P)
        if cs is None:
            return None
        v = 0
        for c in cs:
            if c not in self.nxt[v]:
                return None
            v = self.nxt[v][c]
        return v

    def count(self, P):
        v = self._state_of(P)
        return len(self.endpos[v]) if v is not None else 0

    def locate(self, P):
        """Exact occurrences via the state's endpos (no superset). endpos are END positions in T;
        start = end - |P| + 1 ... here we store pos as the index of the LAST char, so start = pos-|P|+1."""
        m = len(P)
        if m == 0:
            return []
        v = self._state_of(P)
        if v is None:
            return []
        hits = []
        for endp in self.endpos[v]:
            start = endp - m + 1
            d = self.doc[start]
            local = start - self.doc_start[d]
            h = {"record_idx": d, "ungapped_pos": local}
            if self.coords is not None:
                c = self.coords[d]
                gs, ge, st = transform(c, local, m)
                h.update({"species": c["fasta_id"], "src": c["src"],
                          "gstart": gs, "gend": ge, "strand": st})
            hits.append(h)
        return hits

    def edges(self):
        """Transition graph: (state, state, symbol_code_str). Nodes 0..n_states-1 (0 = initial)."""
        return [(u, w, str(c)) for u in range(self.n_states) for c, w in self.nxt[u].items()]
