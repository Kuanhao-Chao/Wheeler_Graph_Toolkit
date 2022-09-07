/**
 * @file print_func.cpp
 * @author Kuan-Hao Chao
 * Contact: kh.chao@cs.jhu.edu
 */

#include <iostream>
#include "graph.hpp"

using namespace std;

// #define PRINTER

void digraph::print_node(int node_name) {
#ifdef DEBUGPRINT
    cout << "\tnode name: " << this->get_decoded_nodeName(node_name) << "\t\tnode label val: " << this->get_node_label(node_name)  << endl;
#endif
}


void digraph::print_graph(string offset) {

// #ifdef PRINTER
    cout << offset << "\t************************** " << endl; 
    cout << offset << "\t** Print _edgeLabels: " << endl; 
    cout << offset << "\t************************** " << endl; 
    cout << offset;

    for (auto& [label, edges] : _edgeLabel_2_edge) {
        for (auto& edge : edges) {
            cout << "\t   " << edge.get_label() << " ";
        }
    }
    cout << endl;
    cout << offset << "\t************************** " << endl; 
    cout << offset << "\t** Print _edgeLabel_2_edge: " << endl; 
    cout << offset << "\t************************** " << endl; 
    for (auto& it : _edgeLabel_2_edge) {
        cout << offset << "\t   >> " << it.first << endl;
        for (auto& it_e : it.second) 
            it_e.print_edge(offset);
    }
    cout << offset << endl;

    cout << offset << "\t************************** " << endl; 
    cout << offset << "\t** Print node_names_2_node_labels: " << endl;
    cout << offset << "\t************************** " << endl; 
    if (_root.size() == 0) {
        cout << offset << "\t** There is no root node (indegree == 0) in this graph " << endl;
    } else {
        cout << offset << "\t** Root: " << endl;
        for (auto& _root_node : _root) {
            cout << offset << "\t   node name: " << this -> get_decoded_nodeName(_root_node) << "    node label: " << this -> get_node_label(_root_node) << endl;
        }
    }

    for (auto& [label, edges] : _edgeLabel_2_edge) {
        cout << offset << "\t** labels: " << label << endl;
        edge pre_edge = edge();
        for (auto& edge : edges) {
            if ((edge.get_head() != pre_edge.get_head())) {
                cout << offset << "\t   node name: " << this -> get_decoded_nodeName(edge.get_head_name()) << "    node label: " << this -> get_node_label(edge.get_head_name()) << endl;
            }
            pre_edge = edge;
        }
    }
    cout << offset << endl;
// #endif
}


void digraph::print_edgeLabel_2_edge_graph() {
#ifdef PRINTER
    cout << "************************** " << endl; 
    cout << "** Print '_edgeLabel_2_edge': " << endl;
    cout << "************************** " << endl; 
    for (auto& [edgeLabel, edges] : _edgeLabel_2_edge) {
        cout << edgeLabel << ": " << endl;
        for (auto& edge: edges) {
            cout << edge.get_tail() << ", " << edge.get_head() << endl;
        }
        for (auto& edge: edges) {
            cout << *edge.get_tail() << ", " << *edge.get_head()<< endl;
        }
        cout << endl;
    }
#endif
}


void digraph::print_node_2_innodes_graph() {
#ifdef PRINTER
    cout << "************************** " << endl; 
    cout << "** Print '_node_2_innodes': " << endl;
    cout << "************************** " << endl; 
    for (auto& [node, innodes] : _node_2_innodes) {
        cout << "** " << this->get_node_label(node) << ": " << endl;
        for (auto& innode: innodes) {
            cout << "   " << this->get_node_label(innode) << " ";
        }
        cout << endl;
    }
#endif
}


void digraph::print_node_2_edgeLabel_2_outnodes() {
#ifdef PRINTER
    // unordered_map<int, map<string, set<int> > > _node_2_edgeLabel_2_outnodes;
    for (auto& [node, edgelabel_2_outnodes] : _node_2_edgeLabel_2_outnodes) {
        cout << "$$$$$$$ Node: " << this -> get_decoded_nodeName(node) << endl;
        for (auto& [edgelabel, outnodes] : edgelabel_2_outnodes) {
            cout << "\t$$$$$$$ edge label: " << edgelabel << endl;
            cout << "\t\t$$$$$$$ outnode : ";
            for (auto& outnode: outnodes) {
                cout << this -> get_decoded_nodeName(outnode) << "  ";
            }
            cout << endl;
        }
    }
#endif
}


void digraph::print_node_names_2_node_labels() {
#ifdef PRINTER
    cout << "************************** " << endl; 
    cout << "** Print node_names_2_node_labels: " << endl;
    cout << "************************** " << endl; 
    if (_root.size() == 0) {
        cout << "\t** There is no root node (indegree == 0) in this graph " << endl;
    } else {
        cout << "\t** Root: " << endl;
        for (auto& _root_node : _root) {
            cout << "\t   node name: " << this -> get_decoded_nodeName(_root_node) << "    node label: " << this -> get_node_label(_root_node) << endl;
        }
    }

    for (auto& [label, edges] : _edgeLabel_2_edge) {
        cout << "\t** labels: " << label << endl;
        edge pre_edge = edge();
        for (auto& edge : edges) {
            if ((edge.get_head() != pre_edge.get_head())) {
                cout << "\t   node name: " << this -> get_decoded_nodeName(edge.get_head_name()) << "    node label: " << this -> get_node_label(edge.get_head_name()) << endl;
            }
            pre_edge = edge;
        }
    }
#endif
}


void digraph::print_edgeLabel_2_next_edgeLabel() {
#ifdef PRINTER
    cout << "************************** " << endl; 
    cout << "** Print edgeLabel_2_next_edgeLabel: " << endl;
    cout << "************************** " << endl; 
    for (auto& [curr_label, next_label] : _edgeLabel_2_next_edgeLabel) {
        cout << "\tCurrent label: " << curr_label << endl;
        cout << "\tNext label: " << next_label << endl;   
    }
#endif
}


void digraph::print_wg_result_number() {
// #ifdef PRINTER
    cout << endl;
    cout << "** Number of valid WG: " << _valid_WG_num << endl;
    cout << "** Number of invalid try: " << _invalid_stop_num << endl;
// #endif
}