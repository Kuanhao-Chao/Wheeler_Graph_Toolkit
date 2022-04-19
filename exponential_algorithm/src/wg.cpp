/**
 * @file wg.cpp
 * @author Kuan-Hao Chao
 * Contact: kuanhao.chao@gmail.com
 */

// #define DEBUGPRINT
// #define PERMUTATION

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
#include <chrono>
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
chrono::high_resolution_clock::time_point c_start;
chrono::high_resolution_clock::time_point c_end;

void processOptions(GArgs& args);

int main(int argc, char* argv[]) {
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

    // if (argc == 1 || argc > 2) {
    //     cout << USAGE;
    //     if (argc == 1) {
    //         cerr << "You have to provide the DOT file path." << endl;
    //     }
    //     if (argc > 2) {
    //         cerr << "Invalid inputs. No options should be provided." << endl;
    //     }
    //     exit(0);
    // }

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

    string base_fname = path_name.stem().string();
    g.output_wg_gagie(base_fname);    



    /********************************
    *** Start recognizer exponential algorithm
    ********************************/
    c_start = chrono::high_resolution_clock::now();
    vector<char> I_array;
    vector<char> O_array;
    vector<char> L_array_char;
    vector<char> L_array;
    string file_I = base_fname + "/I.txt";
    string file_O = base_fname + "/O.txt";
    string file_L = base_fname + "/L.txt";

    ifstream ifile_I(file_I);
    filesystem::path path_name_I(file_I);
    ifstream ifile_O(file_O);
    filesystem::path path_name_O(file_O);
    ifstream ifile_L(file_L);
    filesystem::path path_name_L(file_L);
    // vector<string> node1_vec;
    // vector<string> node2_vec;
    // vector<string> node_names;
    // set<string> node_names_set;
    // vector<string> edge_labels;
    // unordered_map<int,int> node_2_ptr_idx;

    int e_n_len = 0;
    int e_len = 0;
    int n_len = 0;
    int sigma_len = 0;
    /********************************
    *** Reading & Parsing I
    ********************************/
    if (ifile_I.is_open()) {
        while(getline(ifile_I, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
#ifdef DEBUGPRINT
            cout << line << endl;
#endif
            e_n_len = line.length();
            for (auto& i : line) {
                I_array.push_back(i);
            }
        }   
        ifile_I.close();
    }

    /********************************
    *** Reading & Parsing O
    ********************************/
    if (ifile_O.is_open()) {
        while(getline(ifile_O, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
#ifdef DEBUGPRINT
            cout << line << endl;
#endif
            for (auto& i : line) {
                O_array.push_back(i);
            }
        }   
        ifile_O.close();
    }

    /********************************
    *** Reading & Parsing L
    ********************************/
    // unordered_map<char, int> sigma_count_map; 
    map<char, int> sigma_count_map; 
    map<char, string> sigma_encode_map; 
    size_t encoding_len;
    int encoding_idx = 0;

    if (ifile_L.is_open()) {
        while(getline(ifile_L, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
#ifdef DEBUGPRINT
            cout << line << endl;
#endif
            e_len = line.length();
            for (auto& i : line) {
                sigma_count_map[i]++;
                L_array_char.push_back(i);
            }
            sigma_len = sigma_count_map.size();
            // for (char i : L_array_char) {
            //     cout << i << endl;
            // }
        }   
        ifile_L.close();
    }

    encoding_len = ceil(log2(sigma_len));
    if (encoding_len == 0) encoding_len = 1;
    string curr_encoding;
    for (auto& i : sigma_count_map) {
        // std::bitset<encoding_len>(encoding_idx);
        curr_encoding = bitset<64>(encoding_idx).to_string();
        sigma_encode_map[i.first] = curr_encoding.substr(64-encoding_len, encoding_len);
        encoding_idx += 1;
    }

#ifdef DEBUGPRINT
    for (auto& i : sigma_encode_map) {
        // std::bitset<encoding_len>(encoding_idx);
        cout << "char    : " << i.first << endl;
        cout << "encoding: " << i.second << endl;
    }
#endif

    for (char i : L_array_char) {
        for (auto& ele : sigma_encode_map[i]) {
            L_array.push_back(ele);
        }
    }

    n_len = e_n_len - e_len;

    cout << "*  |E|: " << e_len << endl;
    cout << "*  |N|: " << n_len << endl;
    cout << "*  |σ|: " << sigma_len << endl;
    cout << "*  σ encoding length: " << encoding_len << endl;
    cout << "*  σ encoding mapping: " << endl;
    for (auto i : sigma_encode_map) {
        cout << "\t" << i.first << ": " << i.second << endl;
    }


    cout << "\n*  |I|: " << I_array.size() << " (" << e_len << " + " << n_len << ")";
    cout << "\n*  I bitvector: " << endl << "\t";
    for_each(I_array.begin(), I_array.end(), [](char v) {cout << v;});

    cout << "\n\n*  |O|: " << O_array.size() << " (" << e_len << " + " << n_len << ")";
    cout << "\n*  O bitvector: " << endl << "\t";
    for_each(O_array.begin(), O_array.end(), [](char v) {cout << v;});

    cout << "\n\n*  |L_char|: " << L_array_char.size() << " (" << e_len << ")";
    cout << "\n*  L vector: " << endl << "\t";
    for_each(L_array_char.begin(), L_array_char.end(), [](char v) {cout << v;});

    cout << "\n\n*  |L|: " << L_array.size() << " (" << e_len << " x " << encoding_len << ")";
    cout << "\n*  L bitvector: " << endl << "\t";
    for_each(L_array.begin(), L_array.end(), [](char v) {cout << v;});


    // int L_zero_count = count(L_array.begin(), L_array.end(), '0');
    // cout << "*  L_zero_count: " << L_zero_count << endl;

    cout << "\n\n*  Total number of iteration times (without filteration): 2^|I| * 2^|O| * 2^|L| (" << pow(2, I_array.size()) << " * " << pow(2, O_array.size()) << " * " << pow(2, L_array.size()) << "): "<< pow(2, I_array.size()) * pow(2, O_array.size()) * pow(2, L_array.size()) << endl;

    vector<char> L_array_char_sorted(L_array_char.size());
#ifdef PERMUTATION
    /**************************
     * Sort the L_array
     **************************/
    partial_sort_copy(begin(L_array_char), end(L_array_char), begin(L_array_char_sorted), end(L_array_char_sorted));

    cout << "Before sorting" << endl;
    for (auto x : L_array_char)
        cout << x << " ";
    cout << endl;
    
    cout << "After sorting" << endl;
    for (auto x : L_array_char_sorted)
        cout << x << " ";
    cout << endl;
#endif

    /**************************
     * Permutate the L_array
     **************************/
    // cout << "Start permutation" << endl;
    // do {
    //     for (char L_ele : L_array_char_sorted) {
    //         cout << L_ele << ' ';
    //     }
    //     cout << endl;
    //     // std::cout << L_array_char[0] << ' ' << L_array_char[1] << ' ' << L_array_char[2] << '\n';
    // } while ( next_permutation(L_array_char_sorted.begin(),L_array_char_sorted.end()) );


    // Iterating the WG
    cout << "\nIterating through 3 bit arrays: " << endl;
    // Bit array I
    bit_array_itr(I_array, O_array, L_array, L_array_char, L_array_char_sorted, e_len, n_len, sigma_len);

    c_end = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::microseconds>(c_end - c_start);
    cout << "Runtime : " << duration.count() << " microseconds" << endl;
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
