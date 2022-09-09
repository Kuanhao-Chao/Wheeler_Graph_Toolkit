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

#define VERSION "0.1.0"
#define USAGE "  usage:\n\n\
\trecognizer_p <in.dot> [-o / --outDir] [--version] [-h / --help] [-v / --verbose] [-s / --solver <smt / p>] [-w / --writeIOL] [-r / --writeRange] [-i / --print_invalid] [-b / --benchmark]\n\n"

using namespace std;

const int PERMUTATION_CUTOFF = 50;

string outDir;
bool valid_wg=true;
bool debugMode=false;
bool verbose=false;
string solver="p"; // Default solver: p
bool writeIOL=false;
bool writeRange=false;
bool print_invalid=false;
bool benchmark_mode=false;
int permutation_counter=1;
clock_t c_start, c_end;
double cpu_time_used;

unordered_map<string,int> _nodeName_2_newNodeName;
unordered_map<int,string> _newNodeName_2_nodeName;

void processOptions(GArgs& args);

int main(int argc, char* argv[]) {

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
	"debug;help;version;outDir=;verbose;solver=;writeIOL;writeRange;print_invalid;"
    "exclude=hvpwribs:");

	processOptions(args);
    string file_extension = filesystem::path(argv[1]).extension();
    if (file_extension != ".dot") {
        cout << USAGE;
        cerr << "Your input is not a DOT file. " << endl;
        return 0;
    }

    ifstream ifile_dot(argv[1]);
    filesystem::path path_name(argv[1]);

    vector<string> node1_vec;
    vector<string> node2_vec;
    vector<string> node_names;
    set<string> node_names_set;
    vector<string> edgeLabels;
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
                    edgeLabels.push_back(match[3]);
                    // cout << "match[3]: " << match[3] << endl;
                }
            }
        }   
        ifile_dot.close();
    }
    node_names.assign(node_names_set.begin(), node_names_set.end());

    int nodes_num = node_names.size();
    int edges_num = edgeLabels.size();

    /********************************
    *** Initialize the graph. 
    ********************************/
    digraph g = digraph(node_names, nodes_num, edges_num, path_name.stem());
    g.add_edges(node1_vec, node2_vec, edgeLabels);

#ifdef DEBUGPRINT
        string label = g.get_first_edgeLabel();
        while(label != "" ) {
            g.sort_edgeLabel_2_edge(label);
            label = g.get_next_edgeLabel(label);
        }
        g.print_graph();
#endif


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
    if (!solver.compare("p") || (!solver.compare("default") && permutation_counter < PERMUTATION_CUTOFF)) {
        g.permutation_start();
    } else {
        g.solve_smt();
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
    print_invalid = (args.getOpt('i')!=NULL || args.getOpt("print_invalid"));
    benchmark_mode = (args.getOpt('b')!=NULL || args.getOpt("benchmark"));

#ifdef DEBUGPRINT
    cout << "debugMode: " << debugMode << endl;
    cout << "outDir: " << outDir << endl;
    cout << "verbose: " << verbose << endl;
    cout << "writeIOL: " << writeIOL << endl;
    cout << "writeRange: " << writeRange << endl;
    cout << "print_invalid: " << print_invalid << endl;
#endif
}
