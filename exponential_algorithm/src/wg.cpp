#include <iostream>
#include <fstream>
#include <filesystem>
#include <map>
#include <bitset>
#include <vector>
#include <cmath>

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
    size_t L_bit_num;
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

    L_bit_num = ceil(log2(sigma_len));
    const size_t encoding_len = L_bit_num;
    string curr_encoding;
    for (auto& i : sigma_count_map) {
        // std::bitset<encoding_len>(encoding_idx);
        curr_encoding = bitset<2>(encoding_idx).to_string();
        sigma_encode_map[i.first] = curr_encoding;
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

    cout << "E length: " << e_len << endl;
    cout << "N length: " << n_len << endl;
    cout << "Signma length: " << sigma_len << endl;
    cout << "Signma encoding length: " << encoding_len << endl;
    cout << "Encoding mapping: " << endl;
    for (auto i : sigma_encode_map) {
        cout << "\t" << i.first << ": " << i.second << endl;
    }


    cout << "\nI bitvector: " << endl;
    for_each(I_array.begin(), I_array.end(), [](char v) {cout << v;});

    cout << "\nO bitvector: " << endl;
    for_each(O_array.begin(), O_array.end(), [](char v) {cout << v;});

    cout << "\nL vector: " << endl;
    for_each(L_array_char.begin(), L_array_char.end(), [](char v) {cout << v;});

    cout << "\nL bitvector: " << endl;
    for_each(L_array.begin(), L_array.end(), [](char v) {cout << v;});


    // Iterating the WG
}   