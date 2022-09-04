#pragma once

#include <iostream>
#include <string>

using namespace std;

class edge {
    private:
        string _label;
        int* _tail;
        int* _prev_tail;
        int* _head;
        int* _prev_head;

        int _tail_name;
        int _head_name;

    public:
        edge(string label, int node_1_name, int* node_1, int node_2_name, int* node_2);
        edge();
        ~edge();
        void print_edge(string offset="");
        void set_node(int a, int b);
        string get_label();
        int* get_tail();
        int* get_head();
        int get_tail_label();
        int get_head_label();
        int get_tail_name();
        int get_head_name();
        string get_tail_name_string();
        string get_head_name_string();
        int string2ascii(string line);
        string ascii2string(int node_name);
        bool operator <(edge& e);
        bool operator <<(edge& e);
        bool operator ==(edge& e);
};