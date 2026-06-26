/**
 * lazy_solve.cpp -- lazy / CEGAR A3 constraint generation for Wheeler recognition.
 *
 * Motivation (from profiling). On the synthetic worst case z3 solves with NEAR-ZERO search (tens of
 * conflicts even at n=1000) but explodes in memory/allocations over the O(E^2) MATERIALIZED A3
 * encoding (902,641 assertions / 5.6 GB on -f at n~850, dying with reason_unknown="Overflow ...
 * vector"). Round 1 (dl_solve.cpp) attacked the SEARCH and lost -- z3's QF_IDL theory propagation is
 * already near-optimal. This file attacks the OTHER wall: the encoding size. It keeps z3's winning
 * CDCL search but never builds the full O(E^2) A3 formula.
 *
 * Why this can work. A3 ("within a label group, heads are monotone non-decreasing in tail order") is a
 * CHAIN constraint. It is O(E^2) only STATICALLY, because the tail order is unknown a priori, forcing
 * an implication for every pair "if tail_i<tail_j then head_i<=head_j". But given a CONCRETE candidate
 * order the tail order is KNOWN, so a violation is forbidden by O(E) consecutive-pair lemmas. So we run
 * a counterexample-guided loop (CEGAR / lazy SMT): assert A1 (brackets) + all-different (+ sparse A2
 * under -f) but NO A3; solve; if the model already satisfies A3 (re-checked in O(E log E)) accept it;
 * otherwise add only the consecutive-pair A3 lemmas the model violates and re-solve. z3's clause
 * learning is preserved across rounds (monotone s.add, never push/pop), so it reuses the search that
 * made Round 0/1 so cheap, while materializing only the A3 pairs that actually bind.
 *
 * solve_smt_lazy() returns:  1 = Wheeler (order written to *_node_2_ptr_address[i], WG_checker-gated)
 *                           -1 = not a Wheeler graph (a SUBSET of the full encoding is already UNSAT)
 *                            0 = undecided (round/abort budget exhausted -> caller falls back to z3)
 *
 * Soundness (invariant INV). At every s.check() the constraint set in `s` is a SUBSET of solve_smt()'s
 * full encoding: identical base (brackets + distinct (+ sparse A2 under -f)) plus a subset of the
 * canonical pairwise A3 lemmas (each added lemma is literally one of smt.cpp's pairwise constraints).
 * Hence Models(s) is a SUPERSET of Models(full).
 *   - No false REJECT. We return -1 only on res==unsat; UNSAT of a superset-of-models subset-of-
 *     constraints means the full set is UNSAT too -> genuinely not a Wheeler graph. unknown / budget
 *     exhaustion return 0 (never -1), so the solver giving up is never reported as non-WG.
 *   - No false ACCEPT. We return 1 only when (a) the model has ZERO A3 violations across all groups
 *     (base gives A1+A2; the detector confirms A3 everywhere) AND (b) WG_checker() re-validates all
 *     three axioms on the written order -- the same accept gate solve_smt() uses (SMT_WG_final_check).
 *   - Termination. The finite universe of A3 pairs is U = sum_l C(E_l,2). Once a pair's lemma is in `s`
 *     every later model satisfies it (distinct positions => strict tails => the implication binds), so
 *     that pair is never flagged again; the `added` set forbids re-adds; <= |U| rounds. In the limit
 *     the set equals the full A3 encoding, so the verdict matches solve_smt() exactly.
 *
 * The `a3_collect_violations` detector below is the lazy counterpart of WG_checker_in_edge_group(): it
 * mirrors that function's sort+consecutive-inversion logic EXACTLY, but is SIDE-EFFECT-FREE -- it sorts
 * a local index array (never the stored _edgeLabel_2_edge vector) and never calls invalid_wheeler_graph
 * / touches _violations -- so the stored group order (and hence the dedup keys) stay stable across the
 * loop, and only the final accept gate mutates state.
 */

#include <iostream>
#include <vector>
#include <ctime>
#include <cstdlib>
#include <algorithm>
#include <numeric>
#include <set>
#include <tuple>
#include "z3++.h"

#include "graph.hpp"

using namespace std;
using namespace z3;

extern bool benchmark_mode;
extern bool profile_mode;

static long lazy_env_long(const char* k, long def) { const char* v = getenv(k); return v ? atol(v) : def; }
static double lazy_env_double(const char* k, double def) { const char* v = getenv(k); return v ? atof(v) : def; }

// Side-effect-free A3 violation collector for ONE label group, evaluated on the CURRENT candidate order
// (positions live in _node_ptrs, read via edge::get_*_label()). Sorts a LOCAL index permutation by
// (tail position, head position) -- identical key to edge::operator< / sort_edgeLabel_2_edge -- and
// appends each consecutive HEAD INVERSION as a (group-local index p, c) pair, where p precedes c in the
// sorted order but has the strictly larger head position. Returns true iff any violation was found.
// Does NOT reorder `edges` (the caller's stored vector) and has no other side effects.
bool digraph::a3_collect_violations(int /*label*/, vector<edge>& edges, vector<pair<int,int>>& out) {
    const int m = (int)edges.size();
    if (m < 2) return false;
    vector<int> idx(m);
    std::iota(idx.begin(), idx.end(), 0);
    std::sort(idx.begin(), idx.end(), [&](int a, int b) {
        int ta = edges[a].get_tail_label(), tb = edges[b].get_tail_label();
        if (ta != tb) return ta < tb;
        return edges[a].get_head_label() < edges[b].get_head_label();
    });
    bool any = false;
    for (int k = 1; k < m; ++k) {
        int p = idx[k - 1], cc = idx[k];
        // Same key as WG_checker_in_edge_group: after the (tail,head) sort, tails are non-decreasing; a
        // head that drops below its predecessor is an A3 break. Equal-tail edges are head-ascending here,
        // so they never spuriously trip -- matching the pairwise encoding's "same tail => no constraint".
        if (edges[cc].get_head_label() < edges[p].get_head_label()) {
            out.push_back({p, cc});
            any = true;
        }
    }
    return any;
}

int digraph::solve_smt_lazy() {
    clock_t t0 = clock();
    const int n = _nodes_num;
    if (n <= 0) return 0;   // degenerate input -> let the caller fall back to solve_smt()

    context c;

    /* One integer position var per node, named by node id (matches smt.cpp). */
    expr_vector xs(c);
    for (int i = 0; i < n; ++i)
        xs.push_back(c.int_const(get_decoded_nodeName(i).c_str()));

    solver s(c, "QF_IDL");

    /* ---- BASE ENCODING = A1 brackets + all-different (verbatim copy of smt.cpp:34-55). NO A3. ---- */
    vector<int> fixed(n, 0);
    for (auto& [range_pair, node_indices] : _node_ranges) {
        int lb = range_pair.first;
        int ub = range_pair.second;
        expr_vector distinct_nodes(c);
        for (int& idx : node_indices) {
            expr constr(c);
            if (lb == ub) {
                constr = (xs[idx] == ub);
                fixed[idx] = ub;
            } else
                constr = (xs[idx] >= lb) && (xs[idx] <= ub);
            s.add(constr);
            distinct_nodes.push_back(xs[idx]);
        }
        if (lb != ub && distinct_nodes.size() > 1)
            s.add(distinct(distinct_nodes));
    }

    /* ---- BASE ENCODING = sparse cross-group A2 under -f (verbatim copy of smt.cpp:57-92). NO A3. ---- */
    if (full_range_search) {
        bool have_prev = false;
        expr prev_hi(c);
        int group_idx = 0;
        for (auto it = _edgeLabel_2_edge.begin(); it != _edgeLabel_2_edge.end(); ++it) {
            vector<edge>& edges = it->second;
            if (edges.empty()) continue;

            expr lo = c.int_const(("#lo_" + to_string(group_idx)).c_str());
            expr hi = c.int_const(("#hi_" + to_string(group_idx)).c_str());
            ++group_idx;

            for (auto& e : edges) {
                int v = e.get_head_name();
                s.add(xs[v] >= lo);
                s.add(xs[v] <= hi);
            }
            s.add(lo <= hi);

            if (have_prev) s.add(prev_hi < lo);
            prev_hi = hi;
            have_prev = true;
        }
    }
    /* NOTE: A3 is deliberately omitted here -- it is generated lazily from counterexamples below. */

    /* Finite A3-pair universe (for the convergence signal + the degeneration abort). */
    long pair_universe = 0;
    for (auto& [lab, edges] : _edgeLabel_2_edge) {
        long mm = (long)edges.size();
        pair_universe += mm * (mm - 1) / 2;
    }

    // Safety budgets. ROUND_BUDGET is a hard cap on refinement rounds; ABORT_FRAC trips when the lazy
    // encoding degenerates toward the full O(E^2) one (e.g. symmetric/dense families) -- at that point a
    // single full solve_smt() is better than continuing to pay per-round solve overhead, so we give up to
    // the caller's fallback. Both are env-tunable for the benchmark.
    const long ROUND_BUDGET = lazy_env_long("WGT_LAZY_ROUNDS", 1L << 30);
    const double ABORT_FRAC = lazy_env_double("WGT_LAZY_ABORT_FRAC", 0.6);

    set<tuple<int, int, int>> added;   // dedup key: (label, min group-local idx, max group-local idx)
    long rounds = 0, materialized_a3 = 0;
    int verdict = 0;

    while (true) {
        ++rounds;
        check_result res = s.check();
        if (res == unsat) { verdict = -1; break; }    // subset UNSAT => full UNSAT => genuinely non-WG
        if (res == unknown) { verdict = 0; break; }    // solver gave up -> fall back (never a verdict)

        /* Extract the model into _node_ptrs (same #-aux filter as smt.cpp:277-288). */
        model md = s.get_model();
        for (unsigned i = 0; i < md.size(); ++i) {
            func_decl v = md[i];
            auto nn = _nodeName_2_newNodeName.find(v.name().str());
            if (nn == _nodeName_2_newNodeName.end()) continue;   // skip #lo_/#hi_ aux vars
            *_node_2_ptr_address[nn->second] = md.get_const_interp(v).get_numeral_int64();
        }

        /* Detect A3 violations on this candidate order; batch the new consecutive-pair lemmas. */
        bool any = false;
        for (auto& [lab, edges] : _edgeLabel_2_edge) {
            if (edges.size() < 2) continue;
            vector<pair<int, int>> viol;
            if (!a3_collect_violations(lab, edges, viol)) continue;
            any = true;
            for (auto& pr : viol) {
                int p = pr.first, cc = pr.second;
                int lo_i = (p < cc) ? p : cc, hi_i = (p < cc) ? cc : p;
                if (!added.insert(make_tuple(lab, lo_i, hi_i)).second) continue;   // already materialized
                edge& ea = edges[p];
                edge& eb = edges[cc];
                int ua = ea.get_tail_name(), va = ea.get_head_name();
                int ub = eb.get_tail_name(), vb = eb.get_head_name();
                // Canonical pairwise A3 lemma -- a literal subset of smt.cpp:191-193. Globally sound, so
                // we add it permanently (monotone) and keep z3's learned clauses across rounds.
                s.add(implies(xs[ua] < xs[ub], xs[va] <= xs[vb]) &&
                      implies(xs[ua] > xs[ub], xs[va] >= xs[vb]));
                ++materialized_a3;
            }
        }

        if (!any) {
            // The model satisfies A1 + A2 + A3 everywhere -> a genuine Wheeler order. Double-gate with
            // WG_checker() (the identical accept gate solve_smt() uses) before accepting.
            valid_wg = true;
            if (this->WG_checker()) { verdict = 1; break; }
            verdict = 0; break;   // unreachable in theory; if it happens, fall back rather than accept
        }

        if (rounds > ROUND_BUDGET ||
            (pair_universe > 0 && (double)materialized_a3 > ABORT_FRAC * (double)pair_universe)) {
            verdict = 0; break;   // degenerating / over budget -> caller falls back to solve_smt()
        }
    }

    if (profile_mode) {
        double dt = (double)(clock() - t0) / CLOCKS_PER_SEC;
        cerr << "PROFILE lazy nodes=" << n
             << " full_range=" << (full_range_search ? 1 : 0)
             << " rounds=" << rounds
             << " materialized_a3=" << materialized_a3
             << " pair_universe=" << pair_universe
             << " assertions=" << s.assertions().size()
             << " result=" << (verdict == 1 ? "sat" : verdict == -1 ? "unsat" : "undecided")
             << " seconds=" << dt << endl;
    }
    return verdict;   // 1 = WG (order already written), -1 = not WG, 0 = undecided (-> solve_smt)
}
