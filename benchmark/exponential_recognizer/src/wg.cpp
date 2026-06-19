/**
 * @file wg.cpp
 * @author Kuan-Hao Chao
 * Contact: kuanhao.chao@gmail.com
 */

// #define DEBUGPRINT
// #define PERMUTATION
#define BENCHMARK

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
#include <string>
// #include <chrono>
#include <time.h>
#include "GArgs.h"
#include "edge.hpp"
#include "graph.hpp"
#include "link.cpp"

#define VERSION "0.1.0"

#define USAGE "  usage:\n\n\
\trecognizer_e <in.dot> [--version] [-h / --help] [-v / --verbose]\n\n"

using namespace std;

bool debugMode=false;
bool verbose=false;
// chrono::high_resolution_clock::time_point c_start;
// chrono::high_resolution_clock::time_point c_end;
clock_t c_start, c_end;
double cpu_time_used;

void processOptions(GArgs& args);

int main(int argc, char* argv[]) {
    c_start = clock();
    (void)argc;
    string line;

    /********************************
    *** Dot reader!!
    ********************************/
    /********************************
    *** Checking arguments
    ********************************/
    // Check number of arguments.

    string method;
    bool early_stop;
    bool print_invalid;
    GArgs args(argc, argv,
	"debug;help;version;verbose;"
    "exclude=hvx:n:j:s:D:G:C:S:l:m:o:j:c:f:p:g:P:M:Bb:A:E:F:T:");

	processOptions(args);

    string file_extension = filesystem::path(argv[1]).extension();
    if (file_extension != ".dot") {
        cout << USAGE;
        cerr << "Your input is not a DOT file. " << endl;
        return 0;
    }

    // Default options
    ifstream ifile_dot(argv[1]);
    filesystem::path path_name(argv[1]);
    vector<string> node1_vec;
    vector<string> node2_vec;
    vector<string> node_names;
    set<string> node_names_set;
    vector<string> edge_labels;
    unordered_map<int,int> node_2_ptr_idx;
    map<char, int> sigma_count_map; 
    map<char, string> sigma_encode_map; 
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
                    string edge_label = match[3];
                    node1_vec.push_back(node_1_name);
                    node2_vec.push_back(node_2_name);
                    node_names_set.insert(node_1_name);
                    node_names_set.insert(node_2_name);
                    edge_labels.push_back(match[3]);
                    sigma_count_map[edge_label.at(0)]++;
                }
            }
        }   
        ifile_dot.close();
    }
    node_names.assign(node_names_set.begin(), node_names_set.end());
    int n_len = node_names.size();
    int e_len = edge_labels.size();
    int L_len = 0;

    // Keep per-edge labels in input order BEFORE sorting (the sort below destroys their
    // correspondence with node1_vec/node2_vec).
    vector<string> edge_labels_orig = edge_labels;

    std::sort(edge_labels.begin(), edge_labels.end());
    int sigma_len = std::unique(edge_labels.begin(), edge_labels.end()) - edge_labels.begin();
    int encoding_len = (sigma_len <= 1) ? 1 : (int)ceil(log2(sigma_len));   // guard log2(0/1)
    L_len = e_len * encoding_len;

    // Build node-indexed edge arrays for the decision procedure. DOT "u -> v" => tail=u, head=v
    // (matching the oracle). Label rank = lexicographic order over the distinct label strings,
    // which is exactly the order std::sort produced in edge_labels[0..sigma_len-1].
    unordered_map<string,int> node_idx;
    for (int i = 0; i < n_len; i++) node_idx[node_names[i]] = i;
    map<string,int> labrank_map;
    for (int i = 0; i < sigma_len; i++) labrank_map[edge_labels[i]] = i;
    vector<int> e_tail(e_len), e_head(e_len), e_lab(e_len);
    for (int i = 0; i < e_len; i++) {
        e_tail[i] = node_idx[node1_vec[i]];
        e_head[i] = node_idx[node2_vec[i]];
        e_lab[i]  = labrank_map[edge_labels_orig[i]];
    }

#ifndef BENCHMARK
    string curr_encoding;
    int encoding_idx=0;
    for (auto& i : sigma_count_map) {
        curr_encoding = bitset<64>(encoding_idx).to_string();
        sigma_encode_map[i.first] = curr_encoding.substr(64-encoding_len, encoding_len);
        encoding_idx += 1;
        L_len += sigma_encode_map[i.first].length() * i.second;
    }

    cout << "n_len: " << n_len << endl;
    cout << "e_len: " << e_len << endl;
    cout << "sigma_len: " << sigma_len << endl;
    cout << "L_len: " << L_len << endl << endl;
    cout << "*  |E|: " << e_len << endl;
    cout << "*  |N|: " << n_len << endl;
    cout << "*  |σ|: " << sigma_len << endl;
    cout << "*  σ encoding length: " << encoding_len << endl;
    cout << "*  σ encoding mapping: " << endl;
    for (auto i : sigma_encode_map) {
        cout << "\t" << i.first << ": " << i.second << endl;
    }

    cout << "\n*  |I|: " << e_len + n_len;
    cout << "\n\n*  |O|: " << e_len + n_len;
    cout << "\n\n*  |L|: " << L_len << " (" << e_len << " x " << encoding_len << ")";

    // int L_zero_count = count(L_array.begin(), L_array.end(), '0');
    // cout << "*  L_zero_count: " << L_zero_count << endl;

    cout << "\n\n*  Total number of iteration times (without filteration): 2^|I| * 2^|O| * 2^|L| (" << pow(2, e_len + n_len) << " * " << pow(2, e_len + n_len) << " * " << pow(2, L_len) << "): "<< pow(2, e_len + n_len) * pow(2, e_len + n_len) * pow(2, L_len) << endl;
    // Iterating the WG
    cout << "\nIterating through 3 bit arrays: " << endl;
#endif

    // cout << "n_len: " << n_len << endl;
    // cout << "e_len: " << e_len << endl;
    // cout << "L_len: " << L_len << endl;

    // Decide Wheeler-ness over the actual graph (exponential: enumerate all n! node orderings).
    int result = recognize_wheeler(n_len, e_len, e_tail, e_head, e_lab);

    // cout << "After result: " << result << endl;


    // c_end = chrono::high_resolution_clock::now();
    // auto duration = chrono::duration_cast<chrono::microseconds>(c_end - c_start);
    c_end = clock();
    cpu_time_used = ((double) (c_end - c_start));

#ifdef BENCHMARK
    // Column 1 verdict: 1 = Wheeler graph, 0 = NOT a Wheeler graph, -1 = over-cap / undecided.
    // (Wheeler now codes as 1, matching the main recognizer; the original used 0=WG. Only
    // results/Figure_1/plot_solvers.py consumes this output and it reads column 2 (time) only,
    // so the col1 change breaks no plot.) Real verdicts carry the real CPU time; only the
    // over-cap case keeps the 60000000 sentinel so the cactus plot still treats it as unsolved.
    if (result == 1) {
        cout << 1 << "\t" << to_string(n_len) << "\t" << cpu_time_used << "\t" << path_name << endl;
    } else if (result == 0) {
        cout << 0 << "\t" << to_string(n_len) << "\t" << cpu_time_used << "\t" << path_name << endl;
    } else {
        cout << -1 << "\t" << to_string(0) << "\t" << 60000000 << "\t" << path_name << endl;
    }
#endif
    return 0;
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
}
