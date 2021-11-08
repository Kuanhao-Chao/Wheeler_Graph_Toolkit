#pragma once

#define DEBUGPRINT

#include <string>
#include <vector>
#include <regex>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include "edge.hpp"

using namespace std;

class digraph {
    private:
        // original node number
        // vector<int> _node_names;
        int _root;
        int _nodes_num;
        int _edges_num;
        int* _node_ptrs;
        // node to memory idx dict in heap
        unordered_map<int,int> _node_2_ptr_idx;
        unordered_map<int,vector<int> > _node_2_innodes;
        unordered_map<int,vector<int> > _node_2_outnodes;
        // all edges
        vector<edge> _edges;
        map<string, vector<edge> > _label_2_edge;

    public:
        digraph(vector<int> node_names, int nodes_num, int edges_num);

        ~digraph();

        void add_edges(vector<int> node1_vec, vector<int> node2_vec, vector<string> edge_labels);

        void print_graph();

        void print_label_2_edge_graph();
        void print_node_2_innodes_graph();
        void print_node_2_outnodes_graph();

        void relabel_by_node_name(int node_name, int new_val);
        void relabel_by_node_address(int* node_add, int new_val);

        int get_node_label(int node_name);

        unordered_map<int,int> get_node_2_ptr_idx();
        
        // map<edge, string> get_edge_2_label();
        vector<edge> get_edges();

        map<string, vector<edge> > get_label_2_edge();
        unordered_map<int,vector<int> > get_node_2_innodes();
        unordered_map<int,vector<int> > get_node_2_outnodes();

        // Find the in degree == 0;
        void find_root_node();
        int get_root();

        void bfs();
};