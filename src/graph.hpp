#pragma once

#include <string>
#include <vector>
#include <regex>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include "edge.hpp"

using namespace std;

/********************************
*** When number of duplicates is large, faster to convert to set and 
*** then dump the data back into a vector.
********************************/
// https://stackoverflow.com/questions/1041620/whats-the-most-efficient-way-to-erase-duplicates-and-sort-a-vector
class digraph {
    private:
        // original node number
        // vector<int> _node_names;
        bool _is_wg = true;
        vector<int> _root;
        int _nodes_num;
        int _edges_num;
        int* _node_ptrs;
        int _valid_WG_num = 0;
        // node to memory address dict in heap
        unordered_map<int,int*> _node_2_ptr_address;
        unordered_map<int,set<int> > _node_2_innodes;
        unordered_map<int,set<int> > _node_2_outnodes;
        // Node -> edge_label -> outnodes
        unordered_map<int, map<string, set<int> > > _node_2_edgelabel_2_outnodes;

        // all edges
        vector<edge> _edges;
        map<string, vector<edge> > _label_2_edge;

        // Still need to think about where to initialize this map. Now: @ add_edges

        // This is only for printing & 
        map<string, vector<int> > _label_2_edgegpnodes;
        map<string, string> _edge_label_2_next_edge_label;

    public:
        digraph(vector<string> node_names, int nodes_num, int edges_num);

        ~digraph();

        void add_edges(vector<string> node1_vec, vector<string> node2_vec, vector<string> edge_labels);

        void print_node(int node_name);
        void print_graph();

        void print_label_2_edge_graph();
        void print_node_2_innodes_graph();
        void print_node_2_outnodes_graph(int node_name);
        void print_node_2_edgelabel_2_outnodes();
        void print_label_2_edgegpnodes();
        void print_node_names_2_node_labels();
        void print_edge_label_2_next_edge_label();


        void relabel_initialization();
        void innodelist_sort_relabel();
        void in_out_nodelist_sort_relabel();


        void relabel_forward(vector<int> &repeat_vec, vector<int> &original_labels, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, vector<int> &prev_num_vec, int &index);

        void relabel_reverse(vector<int> &repeat_vec, vector<int> &original_labels, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, vector<int> &prev_num_vec, int &index);

        void relabel_by_node_name(int node_name, int new_val);
        void relabel_by_node_address(int* node_add, int new_val);

        int  get_node_label(int node_name);
        int* get_node_address(int node_name);
        unordered_map<int,int*> get_node_2_ptr_address();
        
        // map<edge, string> get_edge_2_label();
        vector<edge> get_edges();

        map<string, vector<edge> > get_label_2_edge();
        map<string, vector<int> > get_label_2_edgegpnodes();
        unordered_map<int,set<int> > get_node_2_innodes();
        unordered_map<int,set<int> > get_node_2_outnodes();
        unordered_map<int, map<string, set<int> > > get_node_2_edgelabel_2_outnodes();


        map<string, vector<int> > get_outnodes_labels(int node_name);
        vector<int> get_innodes_labels(string edge_label, int node_name);
        int get_valid_WG_num();
        int get_valid_WG_num_2();

        void one_scan_through_wg_rg(string label);

        void permutation_4_edge_group(string label);
        void permutation_4_sub_edge_group(string &label, vector<int> &prev_num_vec, vector<int> &accum_same_vec, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, int index);

        // void in_edge_group_sort(vector<vector<int> > &edgegp_nodes_innodes, vector<int> &index);
        void in_edge_group_sort(vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index);
        void in_edge_group_pre_label(string label, vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index, int &accum_edgegp_size);

        void in_out_nodelist_repeat_node_sort(vector<int> &nodes_same_label_vec, vector<vector<int> > &nodes_2_innodes, vector<map<string, vector<int> > > &nodes_2_outnodes, vector<int> &index);
        void in_out_nodelist_repeat_node_re_label(vector<int> &nodes_same_label_vec, vector<vector<int> > &nodes_2_innodes, vector<map<string, vector<int> > > &nodes_2_outnodes, vector<int> &index);

        void sort_label_2_edge(string &label);

        string get_first_edge_label();
        string get_next_edge_label(string label);

        bool WG_checker_in_edge_group(string &label);
        bool WG_checker();
        // Find the in degree == 0;
        void find_root_node();
        vector<int> get_root();
        bool get_is_wg();

        void bfs();
        int string2ascii(string line);
        string ascii2string(int node_name);


        void valid_wheeler_graph();
        void invalid_wheeler_graph();
        void invalid_wheeler_graph_exit(string msg, string print_level);
        void output_wg_gagie();
        void output_wg_dot();
};