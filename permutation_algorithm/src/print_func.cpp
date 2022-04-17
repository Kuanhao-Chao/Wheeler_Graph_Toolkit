#include <iostream>
#include "graph.hpp"

using namespace std;

void digraph::print_node(int node_name) {
    cout << "\tnode name: " << this->ascii2string(node_name) << "\t\tnode label val: " << this->get_node_label(node_name)  << endl;
}


void digraph::print_graph(string offset) {
    cout << offset << "\t************************** " << endl; 
    cout << offset << "\t** Print _edge_labels: " << endl; 
    cout << offset << "\t************************** " << endl; 
    cout << offset;

    for (auto& [label, edges] : _edge_label_2_edge) {
        for (auto& edge : edges) {
            cout << "\t   " << edge.get_label() << " ";
        }
    }
    cout << endl;
    cout << offset << "\t************************** " << endl; 
    cout << offset << "\t** Print _edge_label_2_edge: " << endl; 
    cout << offset << "\t************************** " << endl; 
    for (auto& it : _edge_label_2_edge) {
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
            cout << offset << "\t   node name: " << this -> ascii2string(_root_node) << "    node label: " << this -> get_node_label(_root_node) << endl;
        }
    }

    for (auto& [label, edges] : _edge_label_2_edge) {
        cout << offset << "\t** labels: " << label << endl;
        edge pre_edge = edge();
        for (auto& edge : edges) {
            if ((edge.get_head() != pre_edge.get_head())) {
                cout << offset << "\t   node name: " << this -> ascii2string(edge.get_head_name()) << "    node label: " << this -> get_node_label(edge.get_head_name()) << endl;
            }
            pre_edge = edge;
        }
    }
    cout << offset << endl;
}


void digraph::print_edge_label_2_edge_graph() {
    cout << "************************** " << endl; 
    cout << "** Print '_edge_label_2_edge': " << endl;
    cout << "************************** " << endl; 
    for (auto& [edge_label, edges] : _edge_label_2_edge) {
        cout << edge_label << ": " << endl;
        for (auto& edge: edges) {
            cout << edge.get_tail() << ", " << edge.get_head() << endl;
        }
        for (auto& edge: edges) {
            cout << *edge.get_tail() << ", " << *edge.get_head()<< endl;
        }
        cout << endl;
    }
}


void digraph::print_node_2_innodes_graph() {
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
}


void digraph::print_node_2_edgelabel_2_outnodes() {
    // unordered_map<int, map<string, set<int> > > _node_2_edgelabel_2_outnodes;
    for (auto& [node, edgelabel_2_outnodes] : _node_2_edgelabel_2_outnodes) {
        cout << "$$$$$$$ Node: " << this -> ascii2string(node) << endl;
        for (auto& [edgelabel, outnodes] : edgelabel_2_outnodes) {
            cout << "\t$$$$$$$ edge label: " << edgelabel << endl;
            cout << "\t\t$$$$$$$ outnode : ";
            for (auto& outnode: outnodes) {
                cout << this -> ascii2string(outnode) << "  ";
            }
            cout << endl;
        }
    }
}


void digraph::print_node_names_2_node_labels() {
    cout << "************************** " << endl; 
    cout << "** Print node_names_2_node_labels: " << endl;
    cout << "************************** " << endl; 
    if (_root.size() == 0) {
        cout << "\t** There is no root node (indegree == 0) in this graph " << endl;
    } else {
        cout << "\t** Root: " << endl;
        for (auto& _root_node : _root) {
            cout << "\t   node name: " << this -> ascii2string(_root_node) << "    node label: " << this -> get_node_label(_root_node) << endl;
        }
    }

    for (auto& [label, edges] : _edge_label_2_edge) {
        cout << "\t** labels: " << label << endl;
        edge pre_edge = edge();
        for (auto& edge : edges) {
            if ((edge.get_head() != pre_edge.get_head())) {
                cout << "\t   node name: " << this -> ascii2string(edge.get_head_name()) << "    node label: " << this -> get_node_label(edge.get_head_name()) << endl;
            }
            pre_edge = edge;
        }
    }
}


void digraph::print_edge_label_2_next_edge_label() {
    cout << "************************** " << endl; 
    cout << "** Print edge_label_2_next_edge_label: " << endl;
    cout << "************************** " << endl; 
    for (auto& [curr_label, next_label] : _edge_label_2_next_edge_label) {
        cout << "\tCurrent label: " << curr_label << endl;
        cout << "\tNext label: " << next_label << endl;   
    }
}


void digraph::print_wg_result_number() {
    cout << endl;
    cout << "** Number of valid WG: " << _valid_WG_num << endl;
    cout << "** Number of invalid try: " << _invalid_stop_num << endl;
}