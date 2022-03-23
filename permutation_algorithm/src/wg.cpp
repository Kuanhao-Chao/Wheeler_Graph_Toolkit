/**
 * @file wg.cpp
 * @author Kuan-Hao Chao
 * Contact: kuanhao.chao@gmail.com
 */

#define DEBUGPRINT

#include <iostream>
#include <fstream>
#include <filesystem>
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
    (void)argc;
    string line;
    string usage = " usage:\n\n\
    recognizer <in.dot> [wg_recognizer_method ('m1' or 'm2')] [stop_condition ('early_stop' or 'normal')] [print_invalid (0 or 1)] \n\n";

    /********************************
    *** Checking arguments
    ********************************/
    // Check number of arguments.
    string method;
    bool early_stop;
    bool print_invalid;

    if (argc == 1 || argc > 5) {
        cout << usage;
        if (argc == 1) {
            cerr << "You have to provide the DOT file path." << endl;
        }
        if (argc > 1) {
            cerr << "You are input more than 3 options." << endl;
        }
        exit(0);
    }

    // Default options
    // Option 3
    if (argc <= 4) {
        print_invalid = false;
    }
    // Option 2
    if (argc <= 3) {
        early_stop = true;
    }
    // Option 1
    if (argc <= 2) {
        method = "m1";
    }

    // Checker for options.
    if (argc >= 3) {
        // Check wg_recognizer_method 'm1' or 'm2'
        if (!(strcmp(argv[2], "m1")==0)  &&  !(strcmp(argv[2], "m2")==0)) {
            cout << usage;
            cerr << "wg_recognizer_method must be either 'm1' or 'm2'" << endl;
            exit(0);
        }
        method = argv[2];
    }
    if (argc >= 4) {
        // Check stop_condition 'm1' or 'm2'
        if (!(strcmp(argv[3], "early_stop")==0)  &&  !(strcmp(argv[3], "normal")==0)) {
            cout << usage;
            cerr << "stop_condition must be either 'early_stop' or 'normal'" << endl;
            exit(0);
        }
        early_stop = (strcmp( argv[3], "early_stop") == 0);
    } 
    if (argc == 5) {
        // Check print_invalid 0 or 1
        if (!(strcmp(argv[4], "0")==0)  &&  !(strcmp(argv[4], "1")==0)) {
            cout << usage;
            cerr << "print_invalid must be either 0 or 1" << endl;
            exit(0);
        }
        print_invalid = (strcmp( argv[4], "1") == 0);
    }
    

    ifstream ifile_dot(argv[1]);
    filesystem::path path_name(argv[1]);

    // string method;
    // bool early_stop;
    // bool print_invalid;
    cout << "method: " << method << endl; 
    cout << "early_stop: " << early_stop << endl; 
    cout << "print_invalid: " << print_invalid << endl; 

    vector<string> node1_vec;
    vector<string> node2_vec;
    vector<string> node_names;
    set<string> node_names_set;
    vector<string> edge_labels;
    unordered_map<int,int> node_2_ptr_idx;

    /********************************
    *** Reading & Parsing DOT
    ********************************/
    if (ifile_dot.is_open()) {
        while(getline(ifile_dot, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
        	line.erase(remove(line.begin(), line.end(), ' '), line.end());
            if (regex_match(line, regex("(.*)(->)(.*)(\\[label=)(.*)(\\];)"))) {
                regex rgx("(\\w+)->(\\w+)\\[label=(\\w+)\\];");
                smatch match;
                // cout << line << endl;
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
    node_names.assign(node_names_set.begin(), node_names_set.end());

    int nodes_num = node_names.size();
    int edges_num = edge_labels.size();

    /********************************
    *** Initialize the graph. 
    ********************************/
    digraph g = digraph(node_names, nodes_num, edges_num, path_name.stem());
    g.add_edges(node1_vec, node2_vec, edge_labels);

// #ifdef DEBUGPRINT
//         string label = g.get_first_edge_label();
//         while(label != "" ) {
//             g.sort_edge_label_2_edge(label);
//             label = g.get_next_edge_label(label);
//         }
//         g.print_graph();
// #endif

    if (method == "m1") {
        /****************************************
        **** Method 1: do all possible permutation!!!
        *****************************************/

        // Step 1: If after initialization, it is not a WG => it is not a WG.
        g.relabel_initialization(print_invalid);
#ifdef DEBUGPRINT
        g.print_graph();
#endif

        // Step 2: If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
        g.innodelist_sort_relabel(print_invalid);
#ifdef DEBUGPRINT
        g.print_graph();
#endif

        // Step 3: If after permutation, the number of valid WGs is 0 => it is not a WG.
        g.permutation_start(early_stop, print_invalid);
        // g.permutation_4_edge_group(g.get_first_edge_label(), early_stop, print_invalid);
        g.WG_final_check();
    } else if (method == "m2") {
        bool valid_WG = true; 
        /****************************************
        **** Method 2: sorting by in-node & out-node list!!!
        *****************************************/
        g.relabel_initialization(print_invalid);
        valid_WG = g.WG_checker(print_invalid);
        g.print_graph();
        // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
        g.innodelist_sort_relabel(print_invalid);
        valid_WG = g.WG_checker(print_invalid);
        g.print_graph();

        int counter = 0;
        while (valid_WG) {
            g.innodelist_sort_relabel(print_invalid);
            g.WG_checker(print_invalid);
            // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
            g.print_graph();

            g.in_out_nodelist_sort_relabel(print_invalid);
            g.WG_checker(print_invalid);
            counter ++;
            if (counter == 50) break;
        }
        g.print_graph();
        // valid_WG_num = g.get_valid_WG_num_2();    
    }
    return 0;
}