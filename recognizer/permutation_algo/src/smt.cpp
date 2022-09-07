#include <iostream>
#include <fstream>
#include <ctime>
#include "z3++.h"

#include "graph.hpp"

using namespace z3;

void digraph::solve_smt() {
    clock_t start = clock();
    context c;

    /* Create variables */
    expr_vector xs(c);
    for (int i = 0; i < _nodes_num; ++i)
        xs.push_back(c.int_const(get_decoded_nodeName(i).c_str()));

    solver s(c, "QF_IDL");

    /* Encode node ranges and distinct constraint */
    for (auto& [range_pair, node_indices] : _node_ranges) {
        int lb = range_pair.first;
        int ub = range_pair.second;
        expr_vector distinct_nodes(c);
        for (int& idx : node_indices) {
            expr constr(c);
            if (lb + 1 == ub)
                constr = (xs[idx] == ub);
            else
                constr = (xs[idx] > lb) && (xs[idx] <= ub);
            s.add(constr);
            distinct_nodes.push_back(xs[idx]);
        }
        s.add(distinct(distinct_nodes));
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
                expr constr1 = implies(xs[ui] < xs[uj], xs[vi] <= xs[vj]);
                expr constr2 = implies(xs[ui] > xs[uj], xs[vi] >= xs[vj]);
                s.add(constr1 && constr2);
            }
        }
    }
    clock_t end = clock();
    double elapsed = (double) (end-start) / CLOCKS_PER_SEC;
    cout << "SMT Setup: " << elapsed << " seconds\n";

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
    cout << "SMT Solve: " << elapsed << " seconds\n";

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
        _valid_WG_num += 1;
    }
}

