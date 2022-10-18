#pragma once

#include <iostream>
#include <string>

using namespace std;

class edge {
    private:
        string _label;
        int* _head;
        int* _tail;
        int _head_name;
        int _tail_name;

    public:
        edge(string label, int node_1_name, int* node_1, int node_2_name, int* node_2);
        edge();
        ~edge();
        void print_edge(string offset="");
        void set_node(int a, int b);
        string get_label();
        int* get_head();
        int* get_tail();
        int get_head_label();
        int get_tail_label();
        int get_head_name();
        int get_tail_name();
        int string2ascii(string line);
        string ascii2string(int node_name);
        bool operator <(edge& e);
        bool operator ==(edge& e);
};