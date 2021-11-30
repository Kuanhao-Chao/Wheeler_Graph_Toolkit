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

    string method = argv[2];
    vector<string> node1_vec;
    vector<string> node2_vec;
    vector<string> node_names;
    set<string> node_names_set;
    vector<string> edge_labels;
    unordered_map<int,int> node_2_ptr_idx;

    if (ifile_dot.is_open()) {
        while(getline(ifile_dot, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
            // cout << line << endl;
        	line.erase(remove(line.begin(), line.end(), ' '), line.end());

            if (regex_match(line, regex("(.*)(->)(.*)(\\[label=)(.*)(\\];)"))) {
                regex rgx("(\\w+)->(\\w+)\\[label=(\\w+)\\];");
                // regex rgx("(\\w+)->*;");
                smatch match;
                cout << line << endl;
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
    cout << "Initialize the graph: " << endl;

    /********************************
    *** Initialization: relabelling root
    ********************************/
    vector<int> root = g.get_root();
    int accum_root_label = 1;
    for (auto& root_node : root) {
        cout << "root_node: " << root_node << endl;
        g.relabel_by_node_name(root_node, accum_root_label);
        accum_root_label += 1;
    }
    cout << "Initialize: relabelling root: " << endl;

    map<string, vector<edge> > label_2_edge;
    label_2_edge = g.get_label_2_edge();
    cout << "get_label_2_edge: " << endl;

    bool valid_WG = true;
    int valid_WG_num = 0;    
    string first_edge_label = g.get_first_edge_label();
    cout << "get_first_edge_label: " << first_edge_label << endl;

    if (method == "m1") {
        /****************************************
        **** Method 1: do all possible permutation!!!
        *****************************************/
        g.relabel_initialization();
        valid_WG = g.WG_checker();
        g.print_graph();
        // If after initialization, it is not a WG => it is not a WG.
        if (!valid_WG) {
            // g.invalid_wheeler_graph_exit("'relabel_initialization' !!!", "graph");
        }
        g.innodelist_sort_relabel();
        valid_WG = g.WG_checker();
        // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
        if (!valid_WG) {
            // g.invalid_wheeler_graph_exit("'innodelist_sort_relabel' !!!", "graph");
        }
        g.print_graph();
        g.permutation_4_edge_group(first_edge_label);
        valid_WG_num = g.get_valid_WG_num();
        g.output_wg_gagie();
    } else if (method == "m2") {
        /****************************************
        **** Method 2: sorting by in-node & out-node list!!!
        *****************************************/
        g.relabel_initialization();
        valid_WG = g.WG_checker();
        if (!valid_WG) {
            g.invalid_wheeler_graph_exit("'relabel_initialization' !!!", "graph");
        }
        g.print_graph();
        g.innodelist_sort_relabel();
        valid_WG = g.WG_checker();
        // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
        if (!valid_WG) {
            g.invalid_wheeler_graph_exit("'innodelist_sort_relabel' !!!", "graph");
        }
        // g.print_graph();

        int counter = 0;
        while (valid_WG) {
            g.innodelist_sort_relabel();
            valid_WG = g.WG_checker();
            // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
            if (!valid_WG) {
                g.invalid_wheeler_graph_exit("'innodelist_sort_relabel' !!!", "graph");
            }
            g.print_graph();

            g.in_out_nodelist_sort_relabel();
            valid_WG = g.WG_checker();
            if (!valid_WG) {
                g.invalid_wheeler_graph_exit("'in_out_nodelist_sort_relabel' !!!", "graph");
            }
            counter ++;
            if (counter == 50) break;
        }
        g.print_graph();
        valid_WG_num = g.get_valid_WG_num_2();    
    }
    cout << "Number of valid WG: " << valid_WG_num << endl;
    return 0;
}