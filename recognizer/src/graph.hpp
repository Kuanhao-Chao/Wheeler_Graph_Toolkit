/**
 * @file graph.hpp
 * @author Kuan-Hao Chao
 * Contact: kh.chao@cs.jhu.edu
 */

#ifndef __GRAPH_HPP__
#define __GRAPH_HPP__

#pragma once
#include <string>
#include <vector>
#include <regex>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include <time.h>
#include "edge.hpp"

using namespace std;

extern const int PERMUTATION_CUTOFF;
extern string dot_full_name;
extern string outDir;
extern bool verbose;
extern bool writeIOL;
extern bool writeRange;
extern bool label_is_int;
extern bool all_valid_WG;
extern bool benchmark_mode;
extern bool exhaustive_search;
extern bool full_range_search;
extern bool valid_wg;
extern clock_t c_start;
extern clock_t c_end;
extern double cpu_time_used;
extern int permutation_counter;
extern unordered_map<string,int> _nodeName_2_newNodeName;
extern unordered_map<int,string> _newNodeName_2_nodeName;

/********************************
*** When number of duplicates is large, faster to convert to set and 
*** then dump the data back into a vector.
********************************/
// https://stackoverflow.com/questions/1041620/whats-the-most-efficient-way-to-erase-duplicates-and-sort-a-vector
class digraph {
    private:
        int _nodeName_mapper_counter = 0;

        string _path_name;
        bool _is_wg = true;
        vector<int> _root;
        int _nodes_num;
        int _edges_num;
        int _labels_num;

        int* _node_ptrs;
        int* _prev_node_ptrs;

        int _valid_WG_num = 0;
        int _invalid_stop_num = 0;
        // node to memory address dict in heap
        unordered_map<int,int*> _node_2_ptr_address;
        unordered_map<int,int*> _prev_node_2_ptr_address;

        unordered_map<int,set<int> > _node_2_innodes;
        // Node -> edgeLabel -> outnodes
        unordered_map<int, map<int, set<int> > > _node_2_edgeLabel_2_outnodes;

        // all edges
        map<int, vector<edge> > _edgeLabel_2_edge;

        // Flatten edges
        // This is only for printing & 
        map<int, int> _edgeLabel_2_next_edgeLabel;

        // [ (lb, ub), [node_names] ]
        vector< pair< pair<int, int>, vector<int> > > _node_ranges;


    public:
        unordered_map<string,int> label_2_newLabel;
        unordered_map<int,string> newLabel_2_label;

        digraph(vector<string> node_names, int nodes_num, int edges_num, string path_name);

        ~digraph();

        void add_edges(vector<string> node1_vec, vector<string> node2_vec, vector<int> edgeLabels);

        void print_node(int node_name);
        void print_graph(string offset="");

        void print_edgeLabel_2_edge_graph();
        void print_node_2_innodes_graph();
        void print_node_2_edgeLabel_2_outnodes();
        void print_node_names_2_node_labels();
        void print_edgeLabel_2_next_edgeLabel();
        void print_wg_result_number();


        void relabel_initialization();
        void innodelist_sort_relabel();
        void in_out_nodelist_sort_relabel();


        void relabel_forward_root(vector<int> &repeat_vec, vector<int> &original_labels);
        void relabel_reverse_root(vector<int> &repeat_vec, vector<int> &original_labels);
        void relabel_forward(vector<int> &repeat_vec, vector<int> &original_labels, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, vector<int> &prev_num_vec, int &index);
        void relabel_reverse(vector<int> &repeat_vec, vector<int> &original_labels, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, vector<int> &prev_num_vec, int &index);

        void relabel_by_node_name(int node_name, int new_val);
        void relabel_init_root_by_node_name(int node_name, int new_val);
        void relabel_node(int* node_add, int new_val);

        int  get_node_label(int node_name);
        int* get_node_address(int node_name);
        unordered_map<int,int*> get_node_2_ptr_address();

        map<int, vector<edge> > get_edgeLabel_2_edge();
        unordered_map<int,set<int> > get_node_2_innodes();
        unordered_map<int, map<int, set<int> > > get_node_2_edgeLabel_2_outnodes();

        vector<int> get_innodes_labels(int edgeLabel, int node_name);
        int get_valid_WG_num();
        int get_invalid_stop_num();
        int get_valid_WG_num_2();

        void permutation_start();
        void permutation_4_edge_group(int label);
        void permutation_4_sub_edge_group(int &label, vector<int> &prev_num_vec, vector<int> &accum_same_vec, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, int index);

        void in_edge_group_sort(vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index);
        void in_edge_group_pre_label(int label, vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index, int &accum_edgegp_size);

        void sort_edgeLabel_2_edge(int &label);
        void sort_edgeLabel_2_edge_by_tail(int &label);

        int get_first_edgeLabel();
        int get_last_edgeLabel();
        int get_next_edgeLabel(int label);

        bool WG_checker_in_edge_group(int label, vector<edge> &edges);
        bool WG_checker();
        void SMT_WG_final_check();
        // Find the in degree == 0;
        void find_root_node();
        vector<int> get_root();
        bool get_is_wg();

        void bfs();
        int get_encoded_nodeName(string line);
        string get_decoded_nodeName(int node_name);

        int get_encoded_label(string label);
        string get_decoded_label(int new_label);

        void valid_wheeler_graph();
        void invalid_wheeler_graph(string msg, bool stop);
        void exit_program(int return_val);
        void output_wg_gagie();

        void solve_smt();
        void permutation_counter_check(int range_size);
};

#endif
