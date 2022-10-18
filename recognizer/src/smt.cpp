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
        if (lb != ub)
            s.add(distinct(distinct_nodes));
    }

    if (full_range_search) {
        for (auto it1 = _edgeLabel_2_edge.begin(); it1 != _edgeLabel_2_edge.end(); ++it1) {
            for (auto it2 = next(it1); it2 != _edgeLabel_2_edge.end(); ++it2) {
                int l1 = (*it1).first;
                int l2 = (*it2).first;
                vector<edge>& edges1 = (*it1).second;
                vector<edge>& edges2 = (*it2).second;

                for (auto& e1 : edges1) {
                    for (auto& e2 : edges2) {
                        int v1 = e1.get_head_name();
                        int v2 = e2.get_head_name();

                        if (l1 < l2) {
                            s.add(xs[v1] < xs[v2]);
                        } else if (l2 < l1) {
                            s.add(xs[v2] < xs[v1]);
                        } else assert(false);
                    }
                }
            }
        }
    }

    /* Encode edge relations within edge group */
    for (auto& [label, edges] : _edgeLabel_2_edge) {
        for (size_t i = 0; i < edges.size() - 1; ++i) {
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
            int node_order = m.get_const_interp(v).get_numeral_int64();
            *_node_2_ptr_address[_nodeName_2_newNodeName[node_name]] = node_order;
        }  
#ifdef DEBUGPRINT
        cout << "After assigning SMT result" << endl;
        for (auto& [nodename, ptr] : _node_2_ptr_address) {
            cout << ">> Before: " << *ptr << endl;
        }
#endif
        valid_wg = true;
    } else {
        valid_wg = false;
    }
    this -> SMT_WG_final_check();
}
