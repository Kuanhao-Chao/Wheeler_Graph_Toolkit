#include <iostream>
#include <fstream>
#include "z3++.h"

#include "graph.hpp"

using namespace z3;


void digraph::solve_smt() {
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
            expr r_constr = (xs[idx] > lb) && (xs[idx] <= ub);
            s.add(r_constr);
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

    /* NOTE: profile SMT solving time here */
    std::cout << s.check() << '\n';

    model m = s.get_model();

    std::cout << m << "\n";

    // traversing the model
    for (unsigned i = 0; i < m.size(); i++) {
        func_decl v = m[i];
        // this problem contains only constants
        assert(v.arity() == 0); 
        std::cout << v.name() << " = " << m.get_const_interp(v) << "\n";
    }
}

