#define DEBUGPRINT

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <regex>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include "edge.hpp"
#include "graph.hpp"

using namespace std;

int main(int argc, char* argv[]) {

	// if (args.getOpt("all")) {
    //     all_wg = true;
	// } else {
    //     all_wg = false;
    // }
    // cout << "all_wg: << endl;" << endl;

    (void)argc;
    string line;
    ifstream ifile_dot(argv[1]);
    vector<string> node1_vec;
    vector<string> node2_vec;
    vector<string> node_names;
    set<string> node_names_set;
    vector<string> edge_labels;
    unordered_map<int,int> node_2_ptr_idx;

    if (ifile_dot.is_open()) {
        while(getline(ifile_dot, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
        	line.erase(remove(line.begin(), line.end(), ' '), line.end());

            if (regex_match(line, regex("(.*)(->)(.*)(\\[label=)(.*)(\\];)"))) {
                regex rgx("(\\w+)->(\\w+)\\[label=(\\w+)\\];");
                // regex rgx("(\\w+)->*;");
                smatch match;

                if (regex_search(line, match, rgx)) {
                    string node_1_name = match[1];
                    string node_2_name = match[2];
                    node1_vec.push_back(node_1_name);
                    node2_vec.push_back(node_2_name);
                    node_names_set.insert(node_1_name);
                    node_names_set.insert(node_2_name);
                    edge_labels.push_back(match[3]);
                }
            }
        }   
        ifile_dot.close();
    }
    // copy(node_names_set.begin(), node_names_set.end(), back_inserter(node_names));

    for(unsigned i=0; i<node_names.size(); ++i) node_names_set.insert(node_names[i]);
    node_names.assign(node_names_set.begin(), node_names_set.end());

    int nodes_num = node_names.size();
    int edges_num = edge_labels.size();
    /********************************
    *** Initialize the graph. 
    ********************************/
    digraph g = digraph(node_names, nodes_num, edges_num);
    g.add_edges(node1_vec, node2_vec, edge_labels);

    /********************************
    *** Initialization: relabelling root
    ********************************/
    int root = g.get_root();
    g.relabel_by_node_name(root, 1);

    map<string, vector<edge> > label_2_edge;
    label_2_edge = g.get_label_2_edge();

    bool valid_WG = true;
    g.relabel_initialization();
    valid_WG = g.WG_checker();
    g.print_graph();

    g.innodelist_sort_relabel();
    g.print_graph();

    // valid_WG = g.WG_checker();
    
    // string first_edge_label = g.get_first_edge_label();
    // int valid_WG_num = 0;    
    // if (valid_WG) {
    //     g.permutation_4_edge_group(first_edge_label);
    //     valid_WG_num = g.get_valid_WG_num();
    //     cout << "Number of valid WG: " << valid_WG_num << endl;
    // }


    // if (valid_WG) {
    //     // g.permutation_4_edge_group(first_edge_label);

    //     g.one_scan_through_wg_rg(first_edge_label);
    //     // g.outnodelist_sort_relabel();
    //     g.one_scan_through_wg_rg(g.get_next_edge_label(first_edge_label));
    //     g.one_scan_through_wg_rg(g.get_next_edge_label(g.get_next_edge_label(first_edge_label)));
    // }

    return 0;
}