/**
 * @file wg.cpp
 * @author Kuan-Hao Chao
 * Contact: kh.chao@cs.jhu.edu
 */

// #define DEBUGPRINT

#include <iostream>
#include <fstream>
#include <filesystem>
#include <string>
#include <cstring>
#include <vector>
#include <regex>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include <ctime>
// Change to chrono
#include "GArgs.h"
#include "edge.hpp"
#include "graph.hpp"

#define VERSION "1.0.0"
#define USAGE "  usage:\n\n\
\trecognizer_p <in.dot> [-o / --outDir] [--version] [-h / --help] [-v / --verbose] [-s / --solver <smt / p>] [-w / --writeIOL] [-r / --writeRange] [-i / --label_is_int] [-b / --benchmark] [-e / --exhaustive_search] [-f / --full_range_search] \n\n"


const char* banner = "==========================================\n"
"Fast algorithm to recognize Wheeler Graphs\n"
"==========================================\n\n"
"██╗    ██╗ ██████╗████████╗\n"
"██║    ██║██╔════╝╚══██╔══╝\n"
"██║ █╗ ██║██║  ███╗  ██║   \n"
"██║███╗██║██║   ██║  ██║   \n"
"╚███╔███╔╝╚██████╔╝  ██║   \n"
" ╚══╝╚══╝  ╚═════╝   ╚═╝   \n";

using namespace std;

const int PERMUTATION_CUTOFF = 50;

string outDir;
string dot_full_name;
bool valid_wg = true;
bool debugMode = false;
bool verbose = false;
string solver = "smt"; // Default solver: p
bool writeIOL = false;
bool writeRange = false;
bool label_is_int = false;
bool benchmark_mode = false;
bool exhaustive_search = false;
bool full_range_search = false;
int permutation_counter = 1;
clock_t c_start, c_end;
double cpu_time_used;

unordered_map<string,int> _nodeName_2_newNodeName;
unordered_map<int,string> _newNodeName_2_nodeName;

void processOptions(GArgs& args);

int main(int argc, char* argv[]) {
    cout << banner << endl;
    c_start = clock();
    (void)argc;
    string line;    

    /********************************
    *** Checking arguments
    ********************************/
    // Check number of arguments.
    string method;
    // bool verbose_mode;

    GArgs args(argc, argv,
	"debug;help;version;outDir=;verbose;solver=;writeIOL;writeRange;print_invalid;exhaustive_search;label_is_int;benchmark;full_range_search;"
    "exclude=hvpwriebfs:o:");

	processOptions(args);
    cout << "dot_full_name: " << dot_full_name << endl;
    string file_extension = filesystem::path(dot_full_name).extension();
    if (file_extension != ".dot") {
        cout << USAGE;
        cerr << "Your input is not a DOT file. " << endl;
        return 0;
    }

    ifstream ifile_dot(dot_full_name);
    filesystem::path path_name(dot_full_name);
    vector<string> node1_vec;
    vector<string> node2_vec;
    vector<string> node_names;
    set<string> node_names_set;
    vector<string> edge_labels;
    vector<int> new_edge_labels;
    unordered_map<int,int> node_2_ptr_idx;
    // dot_full_name = argv[1];

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
                    string label = match[3];
                    node1_vec.push_back(node_1_name);
                    node2_vec.push_back(node_2_name);
                    node_names_set.insert(node_1_name);
                    node_names_set.insert(node_2_name); 
                    edge_labels.push_back(label);
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
    
    /********************************
    *** Creating the label mapping
    ********************************/
    if (label_is_int) {
        set<int> s;
        for( unsigned i = 0; i < edge_labels.size(); i++ ) s.insert( stoi(edge_labels[i]) );
        int new_label = 0;
        for (auto itr : s) {
            g.label_2_newLabel[to_string(itr)] = new_label;
            g.newLabel_2_label[new_label] = to_string(itr);
            new_label ++;
        } 
    } else {
        set<string> s;
        for( unsigned i = 0; i < edge_labels.size(); i++ ) s.insert( edge_labels[i] );
        int new_label = 0;
        for (auto itr : s) {
            g.label_2_newLabel[itr] = new_label;
            g.newLabel_2_label[new_label] = itr;
            new_label ++;
        } 
    }
    for (int i=0; i<edge_labels.size(); i++) {
        new_edge_labels.push_back(g.label_2_newLabel[edge_labels[i]]);
    }
    g.add_edges(node1_vec, node2_vec, new_edge_labels);

    /********************************
    *** Step 1: If after initialization, it is not a WG => it is not a WG.
    ********************************/
    g.relabel_initialization();
#ifdef DEBUGPRINT
    g.print_graph();
#endif

    /********************************
    *** Step 2: If after innodelist sorting & relabelling, it is not a WG => it is not a WG.
    ********************************/
    g.innodelist_sort_relabel();
#ifdef DEBUGPRINT
    g.print_graph();
#endif

    /********************************
    *** Step 3: If after permutation, the number of valid WGs is 0 => it is not a WG.
    ********************************/
    if (full_range_search) {
        g.solve_smt();
    } else {
        if (!solver.compare("default") || !solver.compare("smt")) {
            g.solve_smt();
        } else if (!solver.compare("p") || (permutation_counter < PERMUTATION_CUTOFF) || exhaustive_search) {
            g.permutation_start();
            if (exhaustive_search) {
                if (!benchmark_mode) cout << "(v) It is a wheeler graph!!" << endl;
                g.exit_program(1);
            }
        }
    }
    return valid_wg;
}

void processOptions(GArgs& args) {

	debugMode = (args.getOpt("debug")!=NULL || args.getOpt('D')!=NULL);

    char* s = args.getOpt("outDir");
    if (s == NULL) {
        s=args.getOpt('o');
    }
    if (s == NULL) {
        outDir = "./";
    } else {
        outDir = s;
        if (outDir.back() != '/') {
            outDir += '/';
        }
    }

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

    s = args.getOpt("solver");
    if (s == NULL) {
        s = args.getOpt('s');
    }
    if (s == NULL) {
        solver = "default";
    } else {
        if (strcmp(s, "smt")==0 || strcmp(s, "p")==0) solver = s;
        else solver = "default";
    }

    writeIOL = (args.getOpt('w')!=NULL || args.getOpt("writeIOL"));
    writeRange = (args.getOpt('r')!=NULL || args.getOpt("writeRange"));
    label_is_int = (args.getOpt('i')!=NULL || args.getOpt("label_is_int"));
    benchmark_mode = (args.getOpt('b')!=NULL || args.getOpt("benchmark"));
    exhaustive_search = (args.getOpt('e')!=NULL || args.getOpt("exhaustive_search"));
    full_range_search = (args.getOpt('f')!=NULL || args.getOpt("full_range_search"));

#ifdef DEBUGPRINT
    cout << "debugMode: " << debugMode << endl;
    cout << "outDir: " << outDir << endl;
    cout << "verbose: " << verbose << endl;
    cout << "writeIOL: " << writeIOL << endl;
    cout << "writeRange: " << writeRange << endl;
    cout << "label_is_int: " << label_is_int << endl;
    cout << "exhaustive_search: " << exhaustive_search << endl;
    cout << "full_range_search: " << full_range_search << endl;
    cout << "solver: " << solver << endl;
#endif
    args.startNonOpt();
    if (args.getNonOptCount()==0) {
		fprintf(stdout,"%s",USAGE);
        cout << "\n[ERROR] no input provided!\n" << endl;
        exit(1);
    }
    // const char* ifn=NULL;
    dot_full_name=args.nextNonOpt();
}
