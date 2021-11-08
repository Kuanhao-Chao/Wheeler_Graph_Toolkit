#define DEBUGPRINT

#include <iostream>
#include <string>
#include "edge.hpp"

using namespace std;

edge::edge(string label, int* node_1, int* node_2) {
    _label = label;
    _head = node_1;
    _tail = node_2;

#ifdef DEBUGPRINT
    cout << "node_1: " <<  node_1 << endl;
    cout << "node_2: " <<  node_2 << endl;
    cout << "_head: " <<  _head << endl;
    cout << "_tail: " <<  _tail << endl;
#endif
}

edge::~edge(){}

void edge::print_edge() {
    cout << "       " << "label val: " << _label << " head: " << *_head << " tail val: " << *_tail << endl;
    cout << "       " << "label ads: " << _label << " head: " << _head << " tail ads: " << _tail << endl;
}

void edge::set_node(int a, int b) {
    *_head = a;
    *_tail = b;
}

string edge::get_label() {
    return _label;
}

int* edge::get_head() {
    return _head;
}

int* edge::get_tail() {
    return _tail;
}