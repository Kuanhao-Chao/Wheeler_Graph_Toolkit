#define DEBUGPRINT

#include <iostream>
#include <string>
#include <vector>
#include <regex>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include <queue>
#include "graph.hpp"

using namespace std;

digraph::digraph(vector<int> node_names, int nodes_num, int edges_num) {
    _nodes_num = nodes_num;
    _edges_num = edges_num;
    _node_ptrs = new int[_nodes_num];

    /********************************
    *** Initialize the node indices. 
    ********************************/
    // This number decides the offset.
    int itr_count = 0;
    for(auto node : node_names) {
        _node_2_ptr_idx[node] = itr_count;
        _node_ptrs[_node_2_ptr_idx[node]] = itr_count + 1; 
        itr_count = itr_count+1;
#ifdef DEBUGPRINT
        cout << "* itr_count: " << itr_count << endl;
        cout << "* _node_2_ptr_idx[node]: " << _node_2_ptr_idx[node] << endl;
        cout << "* _node_ptrs[_node_2_ptr_idx[node]]: " << _node_ptrs[_node_2_ptr_idx[node]] << endl;
#endif
    }
}

digraph::~digraph() {
    delete [] _node_ptrs;
}

void digraph::add_edges(vector<int> node1_vec, vector<int> node2_vec, vector<string> edge_labels) {
    /***********************************************
    *** Iterate through all edges and add one by one
    ************************************************/
    for (int i=0; i<_edges_num; i++) {
#ifdef DEBUGPRINT
        cout << "node1_vec[i]: " << node1_vec[i] << "  node2_vec[i]: " << node2_vec[i] << endl;
        cout << "node1_vec[i] idx: " << _node_2_ptr_idx[node1_vec[i]] << "  node2_vec[i] idx: " << _node_2_ptr_idx[node2_vec[i]] << endl;

        cout << "node1_vec[i] wrong: " << &_node_2_ptr_idx[node1_vec[i]] << "  node2_vec[i] wrong: " << &_node_2_ptr_idx[node2_vec[i]] << endl;

        cout << "node1_vec[i] val: " << _node_ptrs[_node_2_ptr_idx[node1_vec[i]]] << "  node2_vec[i] val: " << _node_ptrs[_node_2_ptr_idx[node2_vec[i]]] << endl;
        cout << "node1_vec[i] addr: " << &_node_ptrs[_node_2_ptr_idx[node1_vec[i]]] << "  node2_vec[i] addr: " << &_node_ptrs[_node_2_ptr_idx[node2_vec[i]]] << endl;

        cout << "_node_ptrs[i]: " << _node_ptrs[i] << endl;
#endif
        // Find the outnode vector
        if (_node_2_outnodes.find(node1_vec[i]) == _node_2_outnodes.end()) {
            // Not found
            vector<int> new_outnodes_vc{node2_vec[i]};
            _node_2_outnodes[node1_vec[i]] = new_outnodes_vc;
        } else {
            _node_2_outnodes[node1_vec[i]].push_back(node2_vec[i]);
        }

        // Find the innode vector
        if (_node_2_innodes.find(node2_vec[i]) == _node_2_innodes.end()) {
            // Not found
            vector<int> new_innodes_vc{node1_vec[i]};
            _node_2_innodes[node2_vec[i]] = new_innodes_vc;
        } else {
            _node_2_innodes[node2_vec[i]].push_back(node1_vec[i]);
        }
        
        this -> find_root_node();

        edge e = edge(edge_labels[i], &_node_ptrs[_node_2_ptr_idx[node1_vec[i]]], &_node_ptrs[_node_2_ptr_idx[node2_vec[i]]]);
        
        // Find the label to edge vector
        if (_label_2_edge.find(e.get_label()) == _label_2_edge.end()) {
            // Not found
            vector<edge> new_sub_edge_vc{e};
            _label_2_edge[e.get_label()] = new_sub_edge_vc;
        } else {
            _label_2_edge[e.get_label()].push_back(e);
        }
        // if (find(_edge_labels.begin(), _edge_labels.end(), e.get_label()) != _edge_labels.end()) {
        //     _label_2_edge[e.get_label()].push_back(e);
        // } else {
        // }
        _edges.push_back(e);
    }
}

void digraph::print_graph() {
    cout << "** Print _edge_labels: " << endl; 
    for (edge x : _edges) 
        cout << "   " << x.get_label() << " ";
    cout << endl;
    cout << "** Print _label_2_edge: " << endl; 
    for (auto& it : _label_2_edge) {
        cout << "   >> " << it.first << endl;
        for (auto& it_e : it.second) 
            it_e.print_edge();
    }
    cout << endl;
}

void digraph::print_label_2_edge_graph() {
    cout << "* Print 'label_2_edge': ";
    for (auto& [edge_label, edges] : _label_2_edge) {
        // cout << "edge: " << edge << endl;
        cout << edge_label << ": " << endl;
        for (auto& edge: edges) {
            cout << edge.get_head() << ", " << edge.get_tail() << endl;
        }
        for (auto& edge: edges) {
            cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
        }
        cout << endl;
    }
}

void digraph::print_node_2_innodes_graph() {
    cout << "* Print '_node_2_innodes': " << endl;
    for (auto& [node, innodes] : _node_2_innodes) {
        // cout << "edge: " << edge << endl;
        cout << ">> " << this->get_node_label(node) << ": " << endl;
        for (auto& innode: innodes) {
            cout << "   " << this->get_node_label(innode) << " ";
        }
        cout << endl;
    }
}

void digraph::print_node_2_outnodes_graph() {
    cout << "* Print '_node_2_outnodes': " << endl;
    for (auto& [node, outnodes] : _node_2_outnodes) {
        // cout << "edge: " << edge << endl;
        cout << ">> " << this->get_node_label(node) << ": " << endl;
        for (auto& outnode: outnodes) {
            cout << "   " << this->get_node_label(outnode) << " ";
        }
        cout << endl;
    }
}

void digraph::relabel_by_node_name(int node_name, int new_val) {
#ifdef DEBUGPRINT
    cout << "node_name : " << node_name << endl;
    cout << "&_node_ptrs[_node_2_ptr_idx[node_name]]: " << &_node_ptrs[_node_2_ptr_idx[node_name]] << endl;
    cout << "_node_ptrs[_node_2_ptr_idx[node_name]]: " << _node_ptrs[_node_2_ptr_idx[node_name]] << endl;
    cout << "new_val: " << new_val << endl;
#endif
    _node_ptrs[_node_2_ptr_idx[node_name]] = new_val;
}

void digraph::relabel_by_node_address(int* node_add, int new_val) {
    *node_add = new_val;
}

int digraph::get_node_label(int node_name) {
    return _node_ptrs[_node_2_ptr_idx[node_name]];
}

unordered_map<int,int> digraph::get_node_2_ptr_idx() {
    return _node_2_ptr_idx;
}

vector<edge> digraph::get_edges() {
    return _edges;
}

map<string, vector<edge> > digraph::get_label_2_edge() {
    return _label_2_edge;
}

unordered_map<int,vector<int> > digraph::get_node_2_innodes() {
    return _node_2_innodes;
}

unordered_map<int,vector<int> > digraph::get_node_2_outnodes() {
    return _node_2_outnodes;
}

void digraph::find_root_node() {
    int counter = 0;
    for (auto& [node, ptr_idx] : _node_2_ptr_idx) {
        if (_node_2_innodes.find(node) == _node_2_innodes.end()) {
            // Not found
            counter += 1;
            // cout << "node: " << node << endl;
            _root = node;
        }
        if (counter != 1) {
            _root = int(NULL);
        }
        // cout << ">> " << this->get_node_label(node) << ": " << endl;
        // for (auto& outnode: outnodes) {
        //     cout << "   " << this->get_node_label(outnode) << " ";
        // }
        // cout << endl;
    }   
}

int digraph::get_root() {
    return _root;
}

void digraph::bfs() {
    queue<int> bfsq;
    // enqueue
    unordered_map<int, bool> visited;
    bfsq.push(_root);
    while (!bfsq.empty()) {
        int node = bfsq.front();
        bfsq.pop();

        if (visited[node] != true) {
            visited[node] = true;
            cout << this -> get_node_label(node) << " ";
            for (auto& child : _node_2_outnodes[node]) {
                if (child != node) {
                    bfsq.push(child);
                    // this -> bfs(child);
                }
            }
        }
        // if (visited.find(node) == visited.end()) {
        //     // not found
        //     visited[node] = true;
        //     cout << this -> get_node_label(node)+1 << " ";
        //     for (auto& child : _node_2_outnodes[node]) {
        //         if (child != node) {
        //             bfsq.push(child);
        //             // this -> bfs(child);
        //         }
        //     }
        // }
    }
    // cout << this -> get_node_label(node)+1 << " ";
}

