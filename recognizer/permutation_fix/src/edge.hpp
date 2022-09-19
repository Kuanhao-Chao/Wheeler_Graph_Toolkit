/**
 * @file edge.hpp
 * @author Kuan-Hao Chao
 * Contact: kh.chao@cs.jhu.edu
 */

#ifndef __EDGE_HPP__
#define __EDGE_HPP__

#pragma once
#include <unordered_map>
#include <iostream>
#include <string>

using namespace std;

extern bool debugMode;
extern bool verbose;
extern bool print_invalid;
extern bool all_valid_WG;
extern unordered_map<string,int> _nodeName_2_newNodeName;
extern unordered_map<int,string> _newNodeName_2_nodeName;

class edge {
    private:
        int _label;
        int* _tail;
        int* _prev_tail;
        int* _head;
        int* _prev_head;

        int _tail_name;
        int _head_name;

    public:
        edge(int label, int node_1_name, int* node_1, int node_2_name, int* node_2);
        edge();
        ~edge();
        void print_edge(string offset="");
        void set_node(int a, int b);
        int get_label();
        int* get_tail();
        int* get_head();
        int get_tail_label();
        int get_head_label();
        int get_tail_name();
        int get_head_name();
        bool operator <(edge& e);
        bool operator <<(edge& e);
        bool operator ==(edge& e);
};

#endif