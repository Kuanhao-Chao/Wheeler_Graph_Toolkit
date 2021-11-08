#pragma once

#include <iostream>
#include <string>

using namespace std;

class edge {
    private:
        string _label;
        int* _head;
        int* _tail;

    public:
        edge(string label, int* node_1, int* node_2);
        ~edge();
        void print_edge();
        void set_node(int a, int b);
        string get_label();
        int* get_head();
        int* get_tail();
};