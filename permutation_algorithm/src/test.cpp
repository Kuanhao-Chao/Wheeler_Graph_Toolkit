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
#include <numeric>

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
    // vector<int> vect{ 10, 20, 30 };
    vector<int> a{1, 10, 11, 13, 19, 23, 37, 40, 44};
    vector<int> b{2};
    bool res = a < b;
    cout << res << endl;
    return 0;
}

