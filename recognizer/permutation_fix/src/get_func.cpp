#include <iostream>
#include "graph.hpp"

using namespace std;

int digraph::get_node_label(int node_name) {
    return *_node_2_ptr_address[node_name];
}


int* digraph::get_node_address(int node_name) {
    return _node_2_ptr_address[node_name];
}


unordered_map<int,int*> digraph::get_node_2_ptr_address() {
    return _node_2_ptr_address;
}


map<int, vector<edge> > digraph::get_edgeLabel_2_edge() {
    return _edgeLabel_2_edge;
}


unordered_map<int,set<int> > digraph::get_node_2_innodes() {
    return _node_2_innodes;
}

int digraph::get_valid_WG_num() {
    return _valid_WG_num;
}


int digraph::get_invalid_stop_num() {
    return _invalid_stop_num;
}
