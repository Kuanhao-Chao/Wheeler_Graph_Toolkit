/**
 * @file smt.cpp
 * @author Pei-Wei
 * Contact: pwchen@berkeley.edu
 */

#include <iostream>
#include <fstream>
#include <ctime>
#include <cassert>
#include "z3++.h"

#include "graph.hpp"

using namespace z3;

extern bool benchmark_mode;

void digraph::solve_smt() {
    clock_t start = clock();
    context c;

    /* Create variables */
    expr_vector xs(c);
    for (int i = 0; i < _nodes_num; ++i)
        xs.push_back(c.int_const(get_decoded_nodeName(i).c_str()));

    solver s(c, "QF_IDL");

    vector<int> fixed(_nodes_num, 0);
    /* Encode node ranges and distinct constraint */
    for (auto& [range_pair, node_indices] : _node_ranges) {
        int lb = range_pair.first;
        int ub = range_pair.second;
        assert(node_indices.size() == ub - lb + 1);
        expr_vector distinct_nodes(c);
        for (int& idx : node_indices) {
            expr constr(c);
            if (lb == ub) {
                constr = (xs[idx] == ub);
                fixed[idx] = ub;
            }
            else
                constr = (xs[idx] >= lb) && (xs[idx] <= ub);
            s.add(constr);
            distinct_nodes.push_back(xs[idx]);
        }
        // Guard: z3::distinct() asserts (SIGABRT) on an empty vector, and a singleton group needs
        // no distinctness constraint. A degenerate graph can yield an empty range group -- e.g.
        // running `-f` on a 0-node input previously crashed here.
        if (lb != ub && distinct_nodes.size() > 1)
            s.add(distinct(distinct_nodes));
    }

    if (full_range_search) {
        // Cross-group axiom A2: every head of a smaller label must order before every head of a
        // larger label. The old encoding added this for ALL O(E^2) edge pairs across label groups.
        // Sparse equivalent (O(E + L)): per non-empty label group l (iterating _edgeLabel_2_edge in
        // ascending label order) introduce a [lo_l, hi_l] window bracketing the order of all of l's
        // edge HEADS, then chain consecutive groups with a STRICT gap.
        //   per head e in l:  xs[head(e)] in [lo_l, hi_l];   well-formed: lo_l <= hi_l
        //   chain (l ascending):  prev_hi < lo_cur   (strict, matching WG_checker's reject-on->=)
        // Equisatisfiable with the all-pairs form: the node vars xs are unchanged (lo/hi are
        // auxiliary). (a) a model of all-pairs gives one here via hi_l=max, lo_l=min head order in l;
        // (b) a model here satisfies all-pairs since for i<j, a<=hi_i < ... < lo_j <=b via the chain
        // (>=1 strict step) => a<b. All constraints are integer difference constraints (QF_IDL).
        // Aux names use a '#' prefix, which cannot collide with DOT node names (\w+ tokens).
        bool have_prev = false;
        expr prev_hi(c);
        int group_idx = 0;
        for (auto it = _edgeLabel_2_edge.begin(); it != _edgeLabel_2_edge.end(); ++it) {
            vector<edge>& edges = it->second;
            if (edges.empty()) continue;   // defensive; map keys always have >=1 edge

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

    /* Encode edge relations within edge group */
    for (auto& [label, edges] : _edgeLabel_2_edge) {
        // `i + 1 < size()` instead of `i < size()-1` to avoid size_t underflow on an empty group.
        for (size_t i = 0; i + 1 < edges.size(); ++i) {
            for (size_t j = i+1; j < edges.size(); ++j) {
                edge& ei = edges[i];
                edge& ej = edges[j];
                int ui = ei.get_tail_name();
                int vi = ei.get_head_name();
                int uj = ej.get_tail_name();
                int vj = ej.get_head_name();
                if (fixed[ui] && fixed[uj] && fixed[vi] && fixed[vj])
                    continue;
                else if (fixed[ui] && fixed[uj]) {
                    if (fixed[ui] < fixed[uj])
                        s.add(xs[vi] <= xs[vj]);
                    else if (fixed[ui] > fixed[uj])
                        s.add(xs[vi] >= xs[vj]);
                } 
                else if (fixed[vi] && fixed[vj]) {
                    if (fixed[vi] < fixed[vj])
                        s.add(xs[ui] <= xs[uj]);
                    else if (fixed[vi] > fixed[vj])
                        s.add(xs[ui] >= xs[uj]);
                }
                else {
                    expr constr1 = implies(xs[ui] < xs[uj], xs[vi] <= xs[vj]);
                    expr constr2 = implies(xs[ui] > xs[uj], xs[vi] >= xs[vj]);
                    s.add(constr1 && constr2);
                }
            }
        }
    }
    clock_t end = clock();
    double elapsed = (double) (end-start) / CLOCKS_PER_SEC;

    if (!benchmark_mode) {
        cout << "SMT Setup: " << elapsed << " seconds\n";
    }

#ifdef DEBUGPRINT
    ofstream out("tmp.smt2");
    out << s.to_smt2();
    out.close();
#endif

    /* NOTE: profile SMT solving time here */
    start = clock();
    auto res = s.check();
    end = clock();
    elapsed = (double) (end-start) / CLOCKS_PER_SEC;

    if (!benchmark_mode) {
        cout << "SMT Solve: " << elapsed << " seconds\n";
    }

    if (res == sat) {
        model m = s.get_model();
#ifdef DEBUGPRINT
        // traversing the model
        for (unsigned i = 0; i < m.size(); i++) {
            func_decl v = m[i];
            // this problem contains only constants
            assert(v.arity() == 0); 
            std::cout << v.name() << " = " << m.get_const_interp(v) << "\n";
        }
#endif

#ifdef DEBUGPRINT
        cout << "Before assigning SMT result" << endl;
        for (auto& [nodename, ptr] : _node_2_ptr_address) {
            cout << ">> Before: " << *ptr << endl;
        }
#endif
        for (unsigned i = 0; i < m.size(); i++) {
            func_decl v = m[i];
            string node_name = v.name().str();
            // Skip auxiliary boundary vars (#lo_/#hi_ from the sparse cross-group encoding): they
            // are not graph nodes. _nodeName_2_newNodeName[node_name] on a missing key would
            // operator[]-INSERT a default id 0 and clobber the real node whose id is 0, corrupting
            // the recovered order (and making SMT_WG_final_check reject a valid Wheeler graph).
            auto nn = _nodeName_2_newNodeName.find(node_name);
            if (nn == _nodeName_2_newNodeName.end()) continue;
            int node_order = m.get_const_interp(v).get_numeral_int64();
            *_node_2_ptr_address[nn->second] = node_order;
        }
#ifdef DEBUGPRINT
        cout << "After assigning SMT result" << endl;
        for (auto& [nodename, ptr] : _node_2_ptr_address) {
            cout << ">> Before: " << *ptr << endl;
        }
#endif
        valid_wg = true;
        this -> SMT_WG_final_check();
    } else if (res == unsat) {
        // Proof that no Wheeler ordering exists -- a genuine NOT-a-Wheeler-graph verdict.
        valid_wg = false;
        this -> invalid_wheeler_graph("SMT returned unsat: no valid Wheeler ordering exists", true);
    } else {
        // z3 returned UNKNOWN: the solver could not decide this instance (e.g. a very large -f
        // encoding it cannot search, even though a model exists). unknown != unsat -- the old code's
        // `else { valid_wg = false; }` reported "not a Wheeler graph" here, a FALSE REJECT (confirmed:
        // such instances are SAT once a witness order is fixed). Report UNDECIDED instead (column 1 =
        // 0, exit 0) so the recognizer never claims a Wheeler graph is non-Wheeler just because the
        // solver gave up. Use the default backend (heuristic range-narrowing) to decide such graphs.
        valid_wg = false;
        if (!benchmark_mode)
            cout << "(?) Undecided: SMT solver returned unknown (instance too hard for -f)" << endl;
        this -> exit_program(0);
    }
}
