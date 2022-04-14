#include <iostream>
#include <fstream>
#include <filesystem>
#include <map>
#include <bitset>
#include <vector>
#include <cmath>
#include "link.cpp"

// #define DEBUGPRINT
using namespace std;

int main(int argc, char* argv[]) {
    (void)argc;
    string line;
    string usage = " usage:\n\n\
    recognizer <wg_dir/> \n\n";

    /********************************
    *** Checking arguments
    ********************************/
    // Check number of arguments.
    string method;
    bool early_stop;
    bool print_invalid;

    if (argc == 1 || argc > 2) {
        cout << usage;
        if (argc == 1) {
            cerr << "You have to provide the path to a wheeler graph directory." << endl;
        }
        if (argc > 1) {
            cerr << "You are input invalid option." << endl;
        }
        exit(0);
    }


    vector<char> I_array;
    vector<char> O_array;
    vector<char> L_array_char;
    vector<char> L_array;
    string file_I = string(argv[1]) + "/I.txt";
    string file_O = string(argv[1]) + "/O.txt";
    string file_L = string(argv[1]) + "/L.txt";

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

    cout << "|E|: " << e_len << endl;
    cout << "|N|: " << n_len << endl;
    cout << "|σ|: " << sigma_len << endl;
    cout << "σ encoding length: " << encoding_len << endl;
    cout << "σ encoding mapping: " << endl;
    for (auto i : sigma_encode_map) {
        cout << "\t" << i.first << ": " << i.second << endl;
    }


    cout << "\n|I|: " << I_array.size() << " (" << e_len << " + " << n_len << ")";
    cout << "\nI bitvector: " << endl;
    for_each(I_array.begin(), I_array.end(), [](char v) {cout << v;});

    cout << "\n|O|: " << O_array.size() << " (" << e_len << " + " << n_len << ")";
    cout << "\nO bitvector: " << endl;
    for_each(O_array.begin(), O_array.end(), [](char v) {cout << v;});

    cout << "\n|L_char|: " << L_array_char.size() << " (" << e_len << ")";
    cout << "\nL vector: " << endl;
    for_each(L_array_char.begin(), L_array_char.end(), [](char v) {cout << v;});

    cout << "\n|L|: " << L_array.size() << " (" << e_len << " x " << encoding_len << ")";
    cout << "\nL bitvector: " << endl;
    for_each(L_array.begin(), L_array.end(), [](char v) {cout << v;});


    int L_zero_count = count(L_array.begin(), L_array.end(), '0');
    cout << "L_zero_count: " << L_zero_count << endl;


    vector<char> L_array_char_sorted(L_array_char.size());
    partial_sort_copy(begin(L_array_char), end(L_array_char), begin(L_array_char_sorted), end(L_array_char_sorted));

    /**************************
     * Sort the L_array
     **************************/
    cout << "Before sorting" << endl;
    for (auto x : L_array_char)
        cout << x << " ";
    cout << endl;
    
    cout << "After sorting" << endl;
    for (auto x : L_array_char_sorted)
        cout << x << " ";
    cout << endl;

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
    // for (int i_idx = 0; i_idx < pow(2, I_array.size()); i_idx++) {
    //     cout << i_idx << endl;
    //     string I_itr_encoding = bitset<100>(i_idx).to_string();
    //     cout << I_itr_encoding.substr(100-I_array.size(), I_array.size()) << endl;

    //     // // Bit array O
    //     // for (int o_idx = 0; o_idx < O_array.size(); o_idx++) {
    //     //     cout << o_idx << endl;

    //     //     // Bit array L
    //     //     for (int l_idx = 0; l_idx < L_array.size(); l_idx++) {
    //     //         cout << l_idx << endl;
    //     //     }
    //     // }

    // }
}   