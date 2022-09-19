/**
 * @file edge.cpp
 * @author Kuan-Hao Chao
 * Contact: kh.chao@cs.jhu.edu
 */

#include <iostream>
#include <string>
#include "edge.hpp"

using namespace std;

edge::edge(int label, int node_1_name, int* node_1, int node_2_name, int* node_2) {
    _label = label;
    _tail_name = node_1_name;
    _tail = node_1;
    _head_name = node_2_name;
    _head = node_2;    

#ifdef DEBUGPRINT
    cout << "_tail: " <<  _tail << endl;
    cout << "_tail label: " <<  *_tail << endl;
    cout << "_tail name: " <<  _tail_name << endl;
    cout << "_head: " <<  _head << endl;
    cout << "_head label: " <<  *_head << endl;
    cout << "_head_name: " <<  _head_name << endl;
#endif
}

edge::edge() {
    _label = 0;
    _tail_name = 0;
    _tail = &_tail_name;
    _head_name = 0;
    _head = &_head_name;    
}

edge::~edge(){}

void edge::print_edge(string offset) {
    cout << offset << "\t       " << "label val: " << _label << "\ttail: " << *_tail << " (" << _newNodeName_2_nodeName[_tail_name]  << ")\t\thead val: " << *_head << " (" << _newNodeName_2_nodeName[_head_name]  << ")" << endl;
    cout << offset << "\t       " << "label ads: " << _label << "\ttail: " << _tail << "\thead ads: " << _head << endl;
}

void edge::set_node(int a, int b) {
    *_tail = a;
    *_head = b;
}

int edge::get_label() {
    return _label;
}

int* edge::get_tail() {
    return _tail;
}

int* edge::get_head() {
    return _head;
}

int edge::get_tail_label() {
    return *_tail;
}

int edge::get_head_label() {
    return *_head;
}
int edge::get_tail_name() {
    return _tail_name;
}
int edge::get_head_name() {
    return _head_name;
}

bool edge::operator <(edge& e) {
    if (*_tail < e.get_tail_label()) {
        return true;
    } else if (*_tail == e.get_tail_label()) {
        if (*_head < e.get_head_label()) {
            return true;
        } else if (*_head == e.get_head_label()) {
            // return true;
            return false;
        } else {
            return false;
        }
    } else {
        return false;
    }
}

bool edge::operator <<(edge& e) {
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
        *_tail == e.get_tail_label() &&
        *_head == e.get_head_label() &&
        _tail == e.get_tail() &&
        _head == e.get_head() &&
        _tail_name == e.get_tail_name() &&
        _head_name == e.get_head_name()
    ) {
        return true;
    } else {
        return false;
    }
}