// #define DEBUGPRINT
#include "link.hpp"

extern bool debugMode;
extern bool verbose;
// extern chrono::high_resolution_clock::time_point c_start;
// extern chrono::high_resolution_clock::time_point c_end;

int bit_array_itr(int e_len, int n_len, int sigma_len, int L_len) {
    int I_len = e_len + n_len;
    int O_len = e_len + n_len;
    /***********************
    * Iterating I array
    ************************/    
    int pow_I_len = pow(2, I_len);
    int pow_O_len = pow(2, O_len);

    // cout <<  "pow(2, I_len): " << pow_I_len << endl;
    // cout <<  "pow(2, O_len): " << pow_O_len << endl;
    if (pow(2, I_len) > 10000 || pow(2, O_len) > 10000) {
        return -1;
    }

    for (int i_idx = 0; i_idx < pow(2, I_len); i_idx++) {
        // cout <<  "I: " << i_idx << endl;
        string I_itr_encoding = bitset<100>(i_idx).to_string();
        I_itr_encoding = I_itr_encoding.substr(100-I_len, I_len);
        int I_zero_count = count(I_itr_encoding.begin(), I_itr_encoding.end(), '0');

        
        /***********************
        * WG checking condition (I).
        ************************/
        // 1. 0 count must be e_len
        if (I_zero_count != e_len) {
            continue;
        }
        // 2. Last bit must be 1.
        if (I_itr_encoding.back() == '0') {
            continue;
        }
        // 3. nodes with in-degree 0 precede those with positive in-degree
        char prev_char = ' ';
        bool in_degree_invalid = false;
        for (auto& I_ele : I_itr_encoding) {
            if (prev_char == '1' && I_ele == '1') {
                in_degree_invalid = true;
                break;
            }
            prev_char = I_ele;
        }
        if (in_degree_invalid) {
            continue;
        }

        if (verbose) {
            cout << "I_zero_count: " << I_zero_count << endl;         
            for (auto& I_ele : I_itr_encoding) {
                if (I_ele == '0') {
                    cout << I_ele;
                }
            }
            cout << endl << endl;   
        }



        /***********************
        * Iterating O array
        ************************/
        for (int o_idx = 0; o_idx < pow(2, O_len); o_idx++) {
            // cout << "O: " <<  o_idx << endl;
            string O_itr_encoding = bitset<100>(o_idx).to_string();
            O_itr_encoding = O_itr_encoding.substr(100-O_len, O_len);
            int O_zero_count = count(O_itr_encoding.begin(), O_itr_encoding.end(), '0');

            /***********************
            * WG checking condition (O).
            ************************/
            // 1. 0 count must be e_len
            if (O_zero_count != e_len) {
                continue;
            }
            // 2. Last bit must be 1.
            if (O_itr_encoding.back() == '0') {
                continue;
            }

            if (verbose) {

                cout << "O_zero_count: " << O_zero_count << endl;         
                for (auto& O_ele : O_itr_encoding) {
                    // if (O_ele == '0') {
                        cout << O_ele;
                    // }
                }
                cout << endl;
            }

            /***********************
            * Iterating L array
            ************************/
            for (int l_idx = 0; l_idx < pow(2, e_len*sigma_len); l_idx++) {
                // cout << "O: " <<  o_idx << endl;
                string L_itr_encoding = bitset<100>(l_idx).to_string();
                L_itr_encoding = L_itr_encoding.substr(100-L_len, L_len);
                if (verbose) {
                    cout << L_itr_encoding << endl;
                }
                int L_zero_count = count(L_itr_encoding.begin(), L_itr_encoding.end(), '0');
            }
            
#ifdef PERMUTATION
            /**************************
             * Permutate the L_array
             **************************/
            // cout << "Start permutation" << endl;
            // do {
            //     /***********************
            //     * WG checking condition (L).
            //     ************************/
            //     // The string is increasing in each O chunk.
            //     int chunk_start = 0;
            //     int chunk_end = 0;
            //     int one_counter = 0;
            //     for (int i=0; i<O_itr_encoding.size(); i++) {
            //         // cout << "i idx: " << i << " "<< O_itr_encoding[i] << endl;
            //         if (O_itr_encoding[i] == '1') {
            //             chunk_end = i;
            //             cout << "(" << chunk_start << ", " << chunk_end << ")" << endl;
            //             for (int j=chunk_start-one_counter; j<chunk_end-one_counter; j++) {
            //                 // cout << "j: " << j << endl;
            //                 cout << L_array_char_sorted[j];
            //             }
            //             cout << " ";

            //             chunk_start = i+1;
          

            //     // for (char L_ele : L_array_char_sorted) {
            //     //     cout << L_ele << ' ';
            //     // }
            //     // cout << endl;
            //             one_counter ++;
            //         }
            //     }

            //     // for (char L_ele : L_array_char_sorted) {
            //     //     cout << L_ele << ' ';
            //     // }
            //     // cout << endl;
            //     // std::cout << L_array_char[0] << ' ' << L_array_char[1] << ' ' << L_array_char[2] << '\n';
            // } while ( next_permutation(L_array_char_sorted.begin(),L_array_char_sorted.end()) );
#endif
        }
    }
    return 1;
}

