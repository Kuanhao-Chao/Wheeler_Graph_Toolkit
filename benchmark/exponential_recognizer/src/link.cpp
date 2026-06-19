// #define DEBUGPRINT
#include "link.hpp"
#include <vector>

extern bool debugMode;
extern bool verbose;

/*
 * recognize_wheeler -- honest exponential Wheeler-graph decision procedure.
 *
 * HISTORY: the original bit_array_itr() enumerated abstract I/O/L bitstrings but never received
 * the actual graph (only scalar counts), discarded the L result, had the real L check dead
 * (#ifdef PERMUTATION + commented out), and returned 1 unconditionally -- so EVERY graph within
 * the size cap was reported "Wheeler". This rewrite wires in the real edges and decides correctly.
 *
 * METHOD (exponential, as the paper's baseline intends): enumerate all n! node orderings and test
 * the three Wheeler axioms directly against the input edges. This mirrors the independent oracle
 * verify/brute_oracle.py exactly. A graph is a Wheeler graph iff there is a total order pi on the
 * nodes (pi[i] = position of node i) such that, for edges (u1,v1,a1) and (u2,v2,a2):
 *   (A1) every in-degree-0 node precedes every in-degree-positive node;
 *   (A2) a1 < a2          =>  pi[v1] <  pi[v2];
 *   (A3) a1 == a2 & pi[u1] < pi[u2]  =>  pi[v1] <= pi[v2].
 *
 * Inputs are node-indexed edge arrays (tail/head in 0..n_len-1, label rank in 0..sigma-1).
 * Returns: 1 = Wheeler, 0 = not Wheeler, -1 = over-cap / not enumerated (see WORK_BUDGET).
 *
 * Complexity O(n! * e^2). The whole-space enumeration is gated by a work budget so a degenerate
 * input cannot hang; over-budget graphs return -1 (reported as the benchmark's timeout sentinel).
 */
int recognize_wheeler(int n_len, int e_len,
                      const std::vector<int>& tail,
                      const std::vector<int>& head,
                      const std::vector<int>& lab) {
    // Empty graph (no nodes, no edges) is vacuously a Wheeler graph.
    if (n_len == 0) return 1;

    // --- work-budget cap: refuse graphs too large to enumerate (O(n! * e^2)) ---
    const unsigned long long WORK_BUDGET = 2000000000ULL;   // ~2e9 axiom checks
    unsigned long long fact = 1;                             // n_len! (saturating)
    bool over = false;
    for (int i = 2; i <= n_len; i++) {
        if (fact > WORK_BUDGET / (unsigned long long)i) { over = true; break; }
        fact *= (unsigned long long)i;
    }
    unsigned long long e2 = (unsigned long long)(e_len ? e_len : 1);
    e2 *= e2;
    if (over || fact > WORK_BUDGET / e2) {
        return -1;   // over-cap / undecided
    }

    // --- in-degrees for axiom A1 ---
    std::vector<int> indeg(n_len, 0);
    for (int k = 0; k < e_len; k++) indeg[head[k]]++;
    std::vector<int> zero_in, pos_in;
    for (int i = 0; i < n_len; i++) {
        if (indeg[i] == 0) zero_in.push_back(i);
        else               pos_in.push_back(i);
    }

    // --- enumerate all n! node orderings; perm[i] = position assigned to node i ---
    std::vector<int> perm(n_len);
    for (int i = 0; i < n_len; i++) perm[i] = i;

    do {
        // A1: every in-degree-0 node precedes every in-degree-positive node.
        if (!zero_in.empty() && !pos_in.empty()) {
            int maxZero = -1, minPos = n_len;
            for (int i : zero_in) if (perm[i] > maxZero) maxZero = perm[i];
            for (int i : pos_in)  if (perm[i] < minPos) minPos = perm[i];
            if (maxZero >= minPos) continue;
        }

        // A2 + A3: check every ordered pair of distinct edges.
        bool ok = true;
        for (int i = 0; i < e_len && ok; i++) {
            int v1 = head[i], u1 = tail[i], a1 = lab[i];
            for (int j = 0; j < e_len; j++) {
                if (i == j) continue;
                int v2 = head[j], u2 = tail[j], a2 = lab[j];
                if (a1 < a2) {
                    if (!(perm[v1] < perm[v2])) { ok = false; break; }   // A2
                } else if (a1 == a2) {
                    if (perm[u1] < perm[u2] && !(perm[v1] <= perm[v2])) { ok = false; break; }  // A3
                }
            }
        }
        if (ok) return 1;   // a valid Wheeler order exists
    } while (std::next_permutation(perm.begin(), perm.end()));

    return 0;   // no ordering satisfies the axioms => not a Wheeler graph
}
