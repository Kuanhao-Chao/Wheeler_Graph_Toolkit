#include <iostream>
#include <string>
#include "edge.hpp"

using namespace std;

edge::edge(string label, int node_1_name, int* node_1, int node_2_name, int* node_2) {
    _label = label;
    _head_name = node_1_name;
    _head = node_1;
    _tail_name = node_2_name;
    _tail = node_2;    

#ifdef DEBUGPRINT
    cout << "_head: " <<  _head << endl;
    cout << "_head label: " <<  *_head << endl;
    cout << "_head name: " <<  _head_name << endl;
    cout << "_tail: " <<  _tail << endl;
    cout << "_tail label: " <<  *_tail << endl;
    cout << "_tail_name: " <<  _tail_name << endl;
#endif
}

edge::edge() {
    _label = "";
    _head_name = 0;
    _head = &_head_name;
    _tail_name = 0;
    _tail = &_tail_name;    
}

edge::~edge(){}

void edge::print_edge(string offset) {
    cout << offset << "\t       " << "label val: " << _label << "\thead: " << *_head << " (" << this->ascii2string(_head_name)  << ")\t\ttail val: " << *_tail << " (" << this->ascii2string(_tail_name)  << ")" << endl;
    cout << offset << "\t       " << "label ads: " << _label << "\thead: " << _head << "\ttail ads: " << _tail << endl;
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

int edge::get_head_label() {
    return *_head;
}

int edge::get_tail_label() {
    return *_tail;
}
int edge::get_head_name() {
    return _head_name;
}
int edge::get_tail_name() {
    return _tail_name;
}

bool edge::operator <(edge& e) {
    if (*_head < e.get_head_label()) {
        return true;
    } else if (*_head == e.get_head_label()) {
        if (*_tail < e.get_tail_label()) {
            return true;
        } else if (*_tail == e.get_tail_label()) {
            // return true;
            return false;
        } else {
            return false;
        }
    } else {
        return false;
    }
}

bool edge::operator ==(edge& e) {
    if (
        *_head == e.get_head_label() &&
        *_tail == e.get_tail_label() &&
        _head == e.get_head() &&
        _tail == e.get_tail() &&
        _head_name == e.get_head_name() &&
        _tail_name == e.get_tail_name()
    ) {
        return true;
    } else {
        return false;
    }
}

int edge::string2ascii(string line) {
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

string edge::ascii2string(int node_name) {
    int tmp = 0;
    string str = to_string(node_name);
    int len = str.length();
    string str_converted = "";
    for (int i=0; i<len; i++) {
        tmp = tmp*10 + (str[i] - '0');
        if (tmp >= 32 && tmp <= 122) {
            // Convert num to char
            char ch = (char)tmp;
            // Reset num to 0
            tmp = 0;
            str_converted = str_converted + ch;
        }
    }
    return str_converted;
}