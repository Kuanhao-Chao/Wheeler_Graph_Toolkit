#define DEBUGPRINT

#include <iostream>
#include <fstream>
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

int string2ascii(string line)
{
    string s_join;
    for (int i = 0; i < line.length(); i++) {
        int x = int(line.at(i));
        if (x >= 32 && x <= 122) {
            // Concatenate strings
            s_join = s_join + to_string(x);
        } 
    }
    int c = stoi(s_join);
    // cout << c << endl;
    // cout << &c << endl;
    return c;
}

void ascii2string(int) {

}


int main(int argc, char* argv[]) {

    // std::vector<int> v{1, 2, 3};

    // for (int x : v)
    //     cout << x << " ";

    (void)argc;
    string line;
    ifstream ifile_dot(argv[1]);
    vector<int> node1_vec;
    vector<int> node2_vec;
    vector<int> node_names;
    set<int> node_names_set;
    vector<string> edge_labels;
    unordered_map<int,int> node_2_ptr_idx;

    if (ifile_dot.is_open()) {
        while(getline(ifile_dot, line)) {
            // Example from: https://www.codegrepper.com/code-examples/cpp/remove+all+spaces+from+string+c%2B%2B
        	line.erase(remove(line.begin(), line.end(), ' '), line.end());

            if (regex_match(line, regex("(.*)(->)(.*)(\\[label=)(.*)(\\];)"))) {
                regex rgx("(\\w+)->(\\w+)\\[label=(\\w+)\\];");
                // regex rgx("(\\w+)->*;");
                smatch match;

                if (regex_search(line, match, rgx)) {
                    int node_1_name = string2ascii(match[1]);
                    int node_2_name = string2ascii(match[2]);
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
    copy(node_names_set.begin(), node_names_set.end(), back_inserter(node_names));

    int nodes_num = node_names.size();
    int edges_num = edge_labels.size();
    /********************************
    *** Initialize the graph. 
    ********************************/
    digraph g = digraph(node_names, nodes_num, edges_num);
    g.add_edges(node1_vec, node2_vec, edge_labels);

    g.print_graph();

    // edge_label list is sorted => because I use map
    // map<string, vector<edge> > label_2_edge;
    // label_2_edge = g.get_label_2_edge();
    g.print_label_2_edge_graph();

    // unordered_map<int, vector<int> > node_2_innodes;
    // node_2_innodes = g.get_node_2_innodes();
    g.print_node_2_innodes_graph();

    // unordered_map<int, vector<int> > node_2_outnodes;
    // node_2_outnodes = g.get_node_2_outnodes();
    g.print_node_2_outnodes_graph();

    // g.relabel_by_node_name(node_names[2], 20);
    // g.relabel_by_node_name(node_names[2], 20);
    // g.relabel_by_node_name(node_names[3], 20);

    // g.print_graph();
    int root = g.get_root();
    g.relabel_by_node_name(root, 1);

    map<string, vector<edge> > label_2_edge;
    label_2_edge = g.get_label_2_edge();
    cout << "* Print 'label_2_edge': ";

    int accum_label = 1;
    for (auto& [edge_label, edges] : label_2_edge) {
        // cout << "edge: " << edge << endl;
        cout << edge_label << ": " << endl;
        accum_label = accum_label + edges.size();
        for (auto& edge: edges) {
            g.relabel_by_node_address(edge.get_tail(), accum_label);
        }
        // for (auto& edge: edges) {
        //     cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
        // }
        cout << endl;
    }
    g.print_graph();


    g.bfs();

    return 0;
}