/**
 * dl_solve.cpp -- native difference-logic / bound-consistency solver for Wheeler recognition.
 *
 * Motivation (from profiling): on the synthetic worst case z3 solves with NEAR-ZERO search (tens of
 * conflicts) but explodes in memory/allocations over the O(E^2) materialized A3 encoding (9.4e12
 * allocations / 1.6 GB at n=1000). After the renaming heuristic, the residual is: a permutation
 * respecting the `_node_ranges` brackets (which already discharge A1 and A2), plus A3 = "within each
 * label group, heads are monotone non-decreasing in tails". This solver decides that residual with a
 * trailed constraint-propagation search in O(V+E) working memory, never materializing O(E^2)
 * constraints. It is a SOUND pre-solver: it returns a verdict only when it can prove it, otherwise 0
 * (undecided) and the caller falls back to z3.
 *
 * solve_dl() returns:  1 = Wheeler (order written to *_node_2_ptr_address[i], WG_checker-validated)
 *                     -1 = not a Wheeler graph (search exhausted with no valid order)
 *                      0 = undecided (decision budget exhausted -> caller uses solve_smt())
 *
 * Soundness:
 *  - Per-node interval domain [lo,hi] always CONTAINS every bracket-respecting Wheeler position for v
 *    (INV). Propagation rules remove only positions no such order can use:
 *      R1 (A3): for two same-label edges, if tail_a is entailed STRICTLY before tail_b
 *               (hi[tail_a] < lo[tail_b]) then A3 forces head_a <= head_b -> tighten both heads.
 *      R3 (all-different): a node fixed to position p forbids p for the other nodes of its bracket
 *               (bound-consistent singleton elimination).
 *    So an empty domain proves non-Wheeler, and the search explores a SUPERSET of all valid orders
 *    (complete: no valid order is pruned).
 *  - Every full (all-singleton) candidate is re-validated by WG_checker() before ACCEPT, so a
 *    propagation/search bug can only cause an unnecessary fallback or a false-reject (both caught by
 *    difftest against the brute oracle) -- never a false-accept.
 *  - The search is exhaustive WITHIN a decision budget; budget exhaustion returns 0 (-> z3), never a
 *    reject, so no verdict can regress relative to the z3 backend.
 */

#include <iostream>
#include <vector>
#include <ctime>
#include <cstdlib>
#include <functional>
#include "graph.hpp"

using namespace std;

extern bool benchmark_mode;
extern bool profile_mode;

// Search budget: number of value assignments (branch decisions) before giving up to z3. Generous --
// the Wheeler-by-construction families decide in far fewer; this only bounds pathological blow-ups.
static const long DL_DECISION_BUDGET = (getenv("DL_BUDGET") ? atol(getenv("DL_BUDGET")) : 20000000L);

int digraph::solve_dl() {
    clock_t t0 = clock();
    const int n = _nodes_num;
    if (n <= 0) return 0;

    // Interval domains [lo,hi] (positions are 1..n), initialised from the heuristic's brackets
    // (which encode A1 + A2). Nodes the heuristic left unbracketed keep the full range [1,n].
    vector<int> lo(n, 1), hi(n, n);
    // Bracket membership: for R3 we need, per node, the sibling nodes sharing its bracket.
    vector<int> bracket_of(n, -1);
    vector<vector<int>> brackets;
    for (auto& rp_idxs : _node_ranges) {
        int a = rp_idxs.first.first, b = rp_idxs.first.second;
        int bid = (int)brackets.size();
        brackets.push_back({});
        for (int idx : rp_idxs.second) {
            if (idx >= 0 && idx < n) { lo[idx] = a; hi[idx] = b; bracket_of[idx] = bid; brackets[bid].push_back(idx); }
        }
    }

    // Flatten the same-label edge groups into (tail,head) index pairs.
    struct EPair { int t, h; };
    vector<vector<EPair>> groups;
    for (auto& lab_edges : _edgeLabel_2_edge) {
        vector<EPair> g;
        for (edge& e : lab_edges.second) g.push_back({e.get_tail_name(), e.get_head_name()});
        if (!g.empty()) groups.push_back(std::move(g));
    }
    const int NG = (int)groups.size(), NB = (int)brackets.size();

    // Incremental wakeup: node -> the constraint groups it participates in. A domain change re-dirties
    // only the constraints that touch it, so propagation after an assignment costs O(touched), not O(all).
    vector<vector<int>> node_groups(n);
    for (int gi = 0; gi < NG; ++gi)
        for (auto& ep : groups[gi]) { node_groups[ep.t].push_back(gi); node_groups[ep.h].push_back(gi); }
    for (auto& vg : node_groups) { sort(vg.begin(), vg.end()); vg.erase(unique(vg.begin(), vg.end()), vg.end()); }

    vector<char> g_dirty(NG, 0), b_dirty(NB, 0);
    vector<int> g_queue, b_queue;
    bool conflict = false;

    // Trail of domain changes for backtracking: each entry restores a node's full [lo,hi].
    struct TEntry { int idx, old_lo, old_hi; };
    vector<TEntry> trail;
    trail.reserve(4 * n + 64);

    auto wake = [&](int i) {
        for (int gi : node_groups[i]) if (!g_dirty[gi]) { g_dirty[gi] = 1; g_queue.push_back(gi); }
        int bk = bracket_of[i];
        if (bk >= 0 && !b_dirty[bk]) { b_dirty[bk] = 1; b_queue.push_back(bk); }
    };
    auto set_lo = [&](int i, int v) { if (v > lo[i]) { trail.push_back({i, lo[i], hi[i]}); lo[i] = v; if (lo[i] > hi[i]) conflict = true; wake(i); } };
    auto set_hi = [&](int i, int v) { if (v < hi[i]) { trail.push_back({i, lo[i], hi[i]}); hi[i] = v; if (lo[i] > hi[i]) conflict = true; wake(i); } };
    auto undo_to = [&](size_t m) { while (trail.size() > m) { TEntry& e = trail.back(); lo[e.idx] = e.old_lo; hi[e.idx] = e.old_hi; trail.pop_back(); } };
    auto clear_dirty = [&]() { for (int g : g_queue) g_dirty[g] = 0; g_queue.clear(); for (int b : b_queue) b_dirty[b] = 0; b_queue.clear(); };

    // R1: A3 within one same-label group, BOTH directions (head<-tail flow alone starves the search of
    // feedback): tail_a<tail_b (entailed) => head_a<=head_b; head_a>head_b (entailed) => tail_a>=tail_b.
    auto process_group = [&](int gi) {
        auto& g = groups[gi];
        const int m = (int)g.size();
        for (int a = 0; a < m && !conflict; ++a) {
            int ua = g[a].t, va = g[a].h;
            for (int b = 0; b < m; ++b) {
                if (a == b) continue;
                int ub = g[b].t, vb = g[b].h;
                if (hi[ua] < lo[ub]) { set_lo(vb, lo[va]); set_hi(va, hi[vb]); if (conflict) break; }
                if (lo[va] > hi[vb]) { set_lo(ua, lo[ub]); set_hi(ub, hi[ua]); if (conflict) break; }
            }
        }
    };
    // R3: all-different within one bracket (bound-consistent singleton elimination). Brackets are small.
    auto process_bracket = [&](int bi) {
        auto& bk = brackets[bi];
        for (int p : bk) {
            if (lo[p] != hi[p]) continue;
            int val = lo[p];
            for (int q : bk) {
                if (q == p) continue;
                if (lo[q] == val) set_lo(q, val + 1);
                if (hi[q] == val) set_hi(q, val - 1);
                if (conflict) return;
            }
        }
    };

    // Propagate to a fixpoint over the dirty worklist. Returns false on an empty domain.
    auto propagate = [&]() -> bool {
        conflict = false;
        while (!conflict && (!g_queue.empty() || !b_queue.empty())) {
            while (!conflict && !g_queue.empty()) { int gi = g_queue.back(); g_queue.pop_back(); g_dirty[gi] = 0; process_group(gi); }
            while (!conflict && !b_queue.empty()) { int bi = b_queue.back(); b_queue.pop_back(); b_dirty[bi] = 0; process_bracket(bi); }
        }
        if (conflict) { clear_dirty(); return false; }
        return true;
    };
    auto seed_all = [&]() {
        for (int g = 0; g < NG; ++g) if (!g_dirty[g]) { g_dirty[g] = 1; g_queue.push_back(g); }
        for (int b = 0; b < NB; ++b) if (!b_dirty[b]) { b_dirty[b] = 1; b_queue.push_back(b); }
    };

    // Validate a full (all-singleton) assignment: write it and run WG_checker (the accept gate).
    auto validate_full = [&]() -> bool {
        for (int i = 0; i < n; ++i) *_node_2_ptr_address[i] = lo[i];
        vector<char> seen(n + 2, 0);
        for (int i = 0; i < n; ++i) { int v = lo[i]; if (v < 1 || v > n || seen[v]) return false; seen[v] = 1; }
        return this->WG_checker();
    };

    // Initial bracket domains, restored at the start of each restart.
    const vector<int> lo0 = lo, hi0 = hi;

    long decisions = 0;     // global decision count, across restarts (-> z3 fallback when exhausted)
    long branch_nodes = 0;  // total branch expansions, for profiling
    long restarts = 0;
    unsigned rng = 0x9e3779b9u;
    auto nextrand = [&]() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; };

    long node_budget = 0;   // per-restart cap on branch expansions (0 = unlimited)
    long nodes_used = 0;
    bool randomize = false;

    // Tri-state DFS (domains are at a propagation fixpoint on entry):
    //   1 = found a valid order, -1 = subtree EXHAUSTED (proves no order here), 0 = cut off (budget).
    std::function<int()> search = [&]() -> int {
        int pick = -1;
        if (!randomize) {
            // Deterministic pass: leftmost non-singleton (tie: smallest domain). Fills the order
            // left-to-right so A3's tail->head flow fires before heads branch.
            int bestlo = 0x7fffffff, bestd = 0x7fffffff;
            for (int i = 0; i < n; ++i) {
                int d = hi[i] - lo[i];
                if (d <= 0) continue;
                if (lo[i] < bestlo || (lo[i] == bestlo && d < bestd)) { bestlo = lo[i]; bestd = d; pick = i; }
            }
        } else {
            // Randomized pass: random tie-break among the most-constrained (smallest-domain) nodes.
            // No fixed variable order wins on every instance, but each instance IS backtrack-free under
            // SOME order; randomizing across restarts finds one.
            int best = 0x7fffffff, cnt = 0;
            for (int i = 0; i < n; ++i) { int d = hi[i] - lo[i]; if (d > 0 && d < best) best = d; }
            if (best != 0x7fffffff)
                for (int i = 0; i < n; ++i) {
                    int d = hi[i] - lo[i];
                    if (d == best) { if ((nextrand() % (++cnt)) == 0) pick = i; }   // reservoir-sample one
                }
        }
        if (pick == -1) return validate_full() ? 1 : -1;   // all singletons => candidate leaf
        if (node_budget && ++nodes_used > node_budget) return 0;   // restart cutoff
        ++branch_nodes;
        const int sz = hi[pick] - lo[pick] + 1;
        int order[64];
        vector<int> big;
        int* ord = order;
        if (sz > 64) { big.resize(sz); ord = big.data(); }
        for (int k = 0; k < sz; ++k) ord[k] = lo[pick] + k;
        if (randomize) for (int k = sz - 1; k > 0; --k) { int j = nextrand() % (k + 1); int t = ord[k]; ord[k] = ord[j]; ord[j] = t; }
        bool cutoff = false;
        for (int k = 0; k < sz; ++k) {
            int p = ord[k];
            if (++decisions > DL_DECISION_BUDGET) { cutoff = true; break; }
            size_t mark = trail.size();
            set_lo(pick, p); set_hi(pick, p);              // assign pick := p
            bool ok = propagate();                         // incremental; wakes only touched constraints
            int r = ok ? search() : -1;                    // conflict => this value yields no order
            undo_to(mark);
            if (r == 1) return 1;
            if (r == 0) { cutoff = true; break; }          // child cut off -> can't claim exhausted
        }
        return cutoff ? 0 : -1;
    };

    // Geometric restarts: a deterministic pass first (r=0), then randomized descents with doubling node
    // budgets. A restart returning -1 explored its whole tree without ANY cutoff -> definitive (sound
    // UNSAT). Randomized restarts find SAT witnesses on symmetric satisfiable instances where a fixed
    // value order backtracks exponentially. The root propagation is unconditional, so a root conflict
    // is a definitive non-Wheeler verdict.
    int result = 0;
    while (decisions <= DL_DECISION_BUDGET) {
        lo = lo0; hi = hi0; trail.clear(); clear_dirty();
        nodes_used = 0;
        randomize = (restarts > 0);
        node_budget = (restarts == 0) ? 4000L : (4000L << (restarts < 24 ? restarts : 24));
        ++restarts;
        seed_all();
        bool ok = propagate();
        int r = ok ? search() : -1;
        if (r == 1) { result = 1; break; }
        if (r == -1) { result = -1; break; }   // exhausted/root-conflict => definitive
        // r == 0: cut off; grow the budget and restart (unless the global budget is spent).
    }

    if (profile_mode) {
        double dt = (double)(clock() - t0) / CLOCKS_PER_SEC;
        cerr << "PROFILE dl nodes=" << n << " full_range=" << (full_range_search ? 1 : 0)
             << " result=" << result << " restarts=" << restarts << " branch_nodes=" << branch_nodes
             << " decisions=" << decisions << " seconds=" << dt << endl;
    }
    return result;   // 1 = WG (order already written), -1 = not WG, 0 = undecided (-> solve_smt)
}
