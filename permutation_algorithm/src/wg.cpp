/**
 * @file wg.cpp
 * @author Kuan-Hao Chao
 * Contact: kuanhao.chao@gmail.com
 */

// #define DEBUGPRINT

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
#include <chrono>
#include "GArgs.h"
#include "edge.hpp"
#include "graph.hpp"

#define VERSION "0.1.0"
#define USAGE "  usage:\n\n\
\trecognizer_p <in.dot> [--version] [-h / --help] [-v / --verbose] [-i / --print_invalid] [-a / --all_valid_WG]\n\n"

using namespace std;

bool valid_wg=true;
bool debugMode=false;
bool verbose=false;
bool print_invalid=false;
bool all_valid_WG = false;
chrono::high_resolution_clock::time_point c_start;
chrono::high_resolution_clock::time_point c_end;

void processOptions(GArgs& args);

int main(int argc, char* argv[]) {

    // c_start = clock();

    c_start = chrono::high_resolution_clock::now();
    (void)argc;
    string line;    

    /********************************
    *** Checking arguments
    ********************************/
    // Check number of arguments.
    string method;
    // bool verbose_mode;

    GArgs args(argc, argv,
	"debug;help;version;verbose;print_invalid;all_valid_WG;"
    "exclude=hviax:n:j:s:D:G:C:S:l:m:o:j:c:f:p:g:P:M:Bb:A:E:F:T:");

	processOptions(args);



    // if (argc == 1 || argc > 6) {
    //     cout << USAGE;
    //     if (argc == 1) {
    //         cerr << "You have to provide the DOT file path." << endl;
    //     }
    //     if (argc > 1) {
    //         cerr << "You are input more than 3 options." << endl;
    //     }
    //     exit(0);
    // }

    // Default options
    // Option 3
    // if (argc <= 5) {
    //     // verbose_mode = false;
    // }
    // if (argc <= 4) {
    //     print_invalid = false;
    // }
    // // Option 2
    // if (argc <= 3) {
    //     !all_valid_WG = true;
    // }
    // // Option 1
    // if (argc <= 2) {
    //     method = "m1";
    // }


    // // Checker for options.
    // if (argc >= 3) {
    //     // Check wg_recognizer_method 'm1' or 'm2'
    //     if (!(strcmp(argv[2], "m1")==0)  &&  !(strcmp(argv[2], "m2")==0)) {
    //         cout << USAGE;
    //         cerr << "wg_recognizer_method must be either 'm1' or 'm2'" << endl;
    //         exit(0);
    //     }
    //     method = argv[2];
    // }
    // if (argc >= 4) {
    //     // Check all_valid_WG 'm1' or 'm2'
    //     if (!(strcmp(argv[3], "!all_valid_WG")==0)  &&  !(strcmp(argv[3], "normal")==0)) {
    //         cout << USAGE;
    //         cerr << "all_valid_WG must be either '!all_valid_WG' or 'normal'" << endl;
    //         exit(0);
    //     }
    //     !all_valid_WG = (strcmp( argv[3], "!all_valid_WG") == 0);
    // } 
    // if (argc >= 5) {
    //     // Check print_invalid 0 or 1
    //     if (!(strcmp(argv[4], "0")==0)  &&  !(strcmp(argv[4], "1")==0)) {
    //         cout << USAGE;
    //         cerr << "print_invalid must be either 0 or 1" << endl;
    //         exit(0);
    //     }
    //     print_invalid = (strcmp( argv[4], "1") == 0);
    // }

    // if (argc >= 6) {
    //     // Check print_invalid 0 or 1
    //     if (!(strcmp(argv[5], "0")==0)  &&  !(strcmp(argv[5], "1")==0)) {
    //         cout << USAGE;
    //         cerr << "print_invalid must be either 0 or 1" << endl;
    //         exit(0);
    //     }
    //     // verbose_mode = (strcmp( argv[5], "1") == 0);
    // }


    string file_extension = filesystem::path(argv[1]).extension();
    if (file_extension != ".dot") {
        cout << USAGE;
        cerr << "Your input is not a DOT file. " << endl;
        return 0;
    }


    ifstream ifile_dot(argv[1]);
    filesystem::path path_name(argv[1]);

    // string method;
    // bool !all_valid_WG;
    // bool print_invalid;

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


    // if (method == "m1") {
    /****************************************
    **** Method 1: do all possible permutation!!!
    *****************************************/

    // Step 1: If after initialization, it is not a WG => it is not a WG.
    g.relabel_initialization();
    // if (!valid_wg) {
    //     g.exit_program();
    //     return -1;
    // }
#ifdef DEBUGPRINT
    g.print_graph();
#endif

    // Step 2: If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
    // valid_wg = 
    g.innodelist_sort_relabel();
    // if (!valid_wg) {
    //     g.exit_program();
    //     return -1;
    // }
#ifdef DEBUGPRINT
    g.print_graph();
#endif

    // Step 3: If after permutation, the number of valid WGs is 0 => it is not a WG.
    g.permutation_start(!all_valid_WG);
    // g.permutation_4_edge_group(g.get_first_edge_label(), !all_valid_WG, print_invalid);
    g.WG_final_check();
    // } else if (method == "m2") {
    //     bool valid_WG = true; 
    //     /****************************************
    //     **** Method 2: sorting by in-node & out-node list!!!
    //     *****************************************/
    //     g.relabel_initialization(print_invalid);
    //     valid_WG = g.WG_checker(print_invalid);
    //     g.print_graph();
    //     // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
    //     g.innodelist_sort_relabel(print_invalid);
    //     valid_WG = g.WG_checker(print_invalid);
    //     g.print_graph();

    //     int counter = 0;
    //     while (valid_WG) {
    //         g.innodelist_sort_relabel(print_invalid);
    //         g.WG_checker(print_invalid);
    //         // If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
    //         g.print_graph();

    //         g.in_out_nodelist_sort_relabel(print_invalid);
    //         g.WG_checker(print_invalid);
    //         counter ++;
    //         if (counter == 50) break;
    //     }
    //     g.print_graph();
    //     // valid_WG_num = g.get_valid_WG_num_2();    
    // }
    return valid_wg;
}


void processOptions(GArgs& args) {

	debugMode=(args.getOpt("debug")!=NULL || args.getOpt('D')!=NULL);

	if (args.getOpt('h') || args.getOpt("help")) {
		fprintf(stdout,"%s",USAGE);
	    exit(0);
	}

	if (args.getOpt("version")) {
	   fprintf(stdout,"%s\n",VERSION);
	   exit(0);
    }

    verbose=(args.getOpt('v')!=NULL || args.getOpt("verbose"));
    if (verbose) {
        fprintf(stderr, "Running recognizer " VERSION ". Command line:\n");
        args.printCmdLine(stderr);
    }

    print_invalid=(args.getOpt('i')!=NULL || args.getOpt("print_invalid"));
    all_valid_WG=(args.getOpt('a')!=NULL || args.getOpt("all_valid_WG"));

    // cout << "debugMode: " << debugMode << endl;
    // cout << "verbose: " << verbose << endl;
    // cout << "print_invalid: " << print_invalid << endl;
    // cout << "all_valid_WG: " << all_valid_WG << endl;
}

