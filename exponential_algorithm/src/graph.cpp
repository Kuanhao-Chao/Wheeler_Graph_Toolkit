/**
 * @file graph.cpp
 * @author Kuan-Hao Chao
 * Contact: kuanhao.chao@gmail.com
 */

// #define DEBUGPRINT

#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <string>
#include <vector>
#include <regex>
#include <numeric>
#include <map>
#include <unordered_map>
#include <set>
#include <new>
#include <queue>
#include "graph.hpp"

using namespace std;

digraph::digraph(vector<string> node_names, int nodes_num, int edges_num, string path_name) {
    _nodes_num = nodes_num;
    _edges_num = edges_num;
    _node_ptrs = new int[_nodes_num];
    _path_name = path_name;

    /********************************
    *** Initialize the node indices. 
    ********************************/
    // This number decides the offset.
    int itr_count = 0;
    for(auto node : node_names) {
        _node_2_ptr_address[this->string2ascii(node)] = &_node_ptrs[itr_count];
        _node_ptrs[itr_count] = itr_count + 1; 
        itr_count = itr_count+1;
#ifdef DEBUGPRINT
        cout << "** itr_count: " << itr_count-1 << endl;
        cout << "** _node_2_ptr_address[node]: " << _node_2_ptr_address[this->string2ascii(node)] << endl;
        cout << "** _node_ptrs[itr_count]: " << _node_ptrs[itr_count-1] << endl;
#endif
    }
}


digraph::~digraph() {
    delete [] _node_ptrs;
}


void digraph::add_edges(vector<string> node1_vec, vector<string> node2_vec, vector<string> edge_labels) {
    /***********************************************
    *** Iterate through all edges and add one by one
    ************************************************/
#ifdef DEBUGPRINT
    cout << "* Initialize the graph: " << endl;
#endif
    // This is a temporary variable storing node group set.
    map<string, set<int> > label_2_node_group_set;
    for (int i=0; i<_edges_num; i++) {
        int node_1_name = this->string2ascii(node1_vec[i]);
        int node_2_name = this->string2ascii(node2_vec[i]);
#ifdef DEBUGPRINT
        cout << "node1_vec[i]: " << node_1_name << "  node2_vec[i]: " << node_2_name << endl;
        cout << "node1_vec[i] addr: " << _node_2_ptr_address[node_1_name] << "  node2_vec[i] addr: " << _node_2_ptr_address[node_2_name] << endl;
        cout << "node1_vec[i] label: " << *_node_2_ptr_address[node_1_name] << "  node2_vec[i] label: " << *_node_2_ptr_address[node_2_name] << endl;
        cout << "_node_ptrs[i]: " << _node_ptrs[i] << endl;
#endif

        if (_node_2_edgelabel_2_outnodes.find(node_1_name) == _node_2_edgelabel_2_outnodes.end()) {
            // Not found the node key.
            map<string, set<int> > edgelabel_2_outnodes;
            _node_2_edgelabel_2_outnodes[node_1_name] = edgelabel_2_outnodes; 
            for (auto& edge_label : edge_labels) {
                set<int> outnodes{};
                _node_2_edgelabel_2_outnodes[node_1_name][edge_label] = outnodes;
            }
        } 
        _node_2_edgelabel_2_outnodes[node_1_name][edge_labels[i]].insert(node_2_name);

        // Find the innode vector
        if (_node_2_innodes.find(node_2_name) == _node_2_innodes.end()) {
            // Not found
            set<int> new_innodes_vc{node_1_name};
            _node_2_innodes[node_2_name] = new_innodes_vc;
        } else {
            _node_2_innodes[node_2_name].insert(node_1_name);
        }
        edge e = edge(edge_labels[i], node_1_name, this->get_node_address(node_1_name), node_2_name, this->get_node_address(node_2_name));
        // Find the label to edge vector & calculate node group set.
        if (_edge_label_2_edge.find(e.get_label()) == _edge_label_2_edge.end()) {
            // Not found
            vector<edge> new_sub_edge_vc{e};
            _edge_label_2_edge[e.get_label()] = new_sub_edge_vc;
        } else {
            _edge_label_2_edge[e.get_label()].push_back(e);
        }
    }
    this -> find_root_node();
    // calculate number of nodes in each node group set.
    string prev_label = "";
    for (auto& [label, edges] : _edge_label_2_edge ) {
        if (prev_label != "") {
            _edge_label_2_next_edge_label[prev_label] = label;
        }
        prev_label = label;
    }
}


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
            if ((edge.get_tail() != pre_edge.get_tail())) {
                cout << offset << "\t   node name: " << this -> ascii2string(edge.get_tail_name()) << "    node label: " << this -> get_node_label(edge.get_tail_name()) << endl;
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
            cout << edge.get_head() << ", " << edge.get_tail() << endl;
        }
        for (auto& edge: edges) {
            cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
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
            if ((edge.get_tail() != pre_edge.get_tail())) {
                cout << "\t   node name: " << this -> ascii2string(edge.get_tail_name()) << "    node label: " << this -> get_node_label(edge.get_tail_name()) << endl;
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


void digraph::relabel_initialization(bool print_invalid) {
    // root has already added.
#ifdef DEBUGPRINT
    cout << "************************** " << endl; 
    cout << "** Relabelling initialization: " << endl;
    cout << "************************** " << endl; 
#endif

    // Relabel roots
    for (auto& root_node : _root) {
        // Relabel roots with the biggest possible
        this -> relabel_by_node_name(root_node, _root.size());
    }

    // Relabel all edge group nodes
    int accum_label= _root.size();
    for (auto& [edge_label, edges] : _edge_label_2_edge) {
        set<int> edgenodes_set;
        for (auto& edge : edges) {
            edgenodes_set.insert(edge.get_tail_name());
        }
        // Relabel the node with the largest possible value in the edge group.
        accum_label = accum_label + edgenodes_set.size();
        for (auto& edge: edges) {
            this -> relabel_by_node_address(edge.get_tail(), accum_label);
        }
    }

    bool WG_valid = true;
    WG_valid = this -> WG_checker(print_invalid);
    if (!WG_valid) {
        // Invalid graph!!! Terminate the program.
        cout << "XX After initialization, it is not a wheeler graph." << endl;
        this -> exit_program();
    }
}


void digraph::innodelist_sort_relabel(bool print_invalid) {
#ifdef DEBUGPRINT
    cout << "************************** " << endl; 
    cout << "** Sort & Pre-relabel nodes in same edge group: " << endl;
    cout << "************************** " << endl; 
#endif
    int accum_edgegp_size = 0;
    for (auto& [label, edges] : _edge_label_2_edge) {
#ifdef DEBUGPRINT
        cout << "****** LABEL: " << label << endl;
#endif
        vector<int> edgegp_nodes;
        vector<vector<int> > edgegp_node_2_innodes_vec;

        for (auto& edge : edges) {
#ifdef DEBUGPRINT
            edge.print_edge();
#endif
            if (find(edgegp_nodes.begin(), edgegp_nodes.end(), edge.get_tail_name()) == edgegp_nodes.end()) {
                // The node has not been added into the map yet! 
                edgegp_nodes.push_back(edge.get_tail_name());
                edgegp_node_2_innodes_vec.push_back(this->get_innodes_labels(label, edge.get_tail_name()));
            }
        }
        /********************************
        *** Sorting nodes by in-node list (sort `edgegp_node_2_innodes` map by values).
        ********************************/
        vector<int> index(edgegp_nodes.size(), 0);
        this->in_edge_group_sort(edgegp_nodes, edgegp_node_2_innodes_vec, index, print_invalid);

        /********************************
        *** Get the new pre-label list
        ***      When there is a tie, label nodes with the **smallest**.
        ********************************/
        this->in_edge_group_pre_label(label, edgegp_nodes, edgegp_node_2_innodes_vec, index, accum_edgegp_size);
        accum_edgegp_size += edgegp_nodes.size();
    }
    bool WG_valid = true;
    WG_valid = this -> WG_checker(print_invalid);
    if (!WG_valid) {
        // Invalid graph !! Terminate the program.
        cout << "XX After sorting by innode-list and relabelling, it is not a wheeler graph" << endl;
        this -> WG_final_check();
        this -> exit_program();
    }
}


void digraph::in_out_nodelist_sort_relabel(bool print_invalid) {
#ifdef DEBUGPRINT
    cout << "************************** " << endl; 
    cout << "** Sort & relabel nodes by in_out_node-list : " << endl;
    cout << "************************** " << endl; 
#endif  
    for (auto& [label, edges] : _edge_label_2_edge) {
        set<int> nodes_same_label_set;
        vector<int> nodes_same_label_vec;
        vector<vector<int> > nodes_2_innodes;
        vector<map<string, vector<int> > > nodes_2_outnodes;
        int prev_num = edges.begin()->get_tail_label();

        vector<edge>::iterator edge_itv = edges.begin();
        do{
            if (edge_itv != edges.end()) {
#ifdef DEBUGPRINT
                edge_itv->print_edge();
                cout << "Current edge.get_tail_label(): " << edge_itv->get_tail_label() << endl;
                cout << "Previous prev_num: " << prev_num << endl;
#endif
                if (prev_num == edge_itv->get_tail_label()) {
                    nodes_same_label_set.insert(edge_itv->get_tail_name());
                } else if (prev_num != edge_itv->get_tail_label()) {
                    if (nodes_same_label_set.size() != 1) {
                        /********************************
                        *** Process the repeat node vector first
                        ********************************/
                        for (auto& node : nodes_same_label_set) {
                            nodes_same_label_vec.push_back(node);
                            nodes_2_innodes.push_back(this->get_innodes_labels(label, node));
                            nodes_2_outnodes.push_back(this->get_outnodes_labels(node));
                        }
                        /********************************
                        *** Sorting nodes by in- & out-node list (sort `_node_2_edgelabel_2_outnodes` unordered_map by values).
                        ********************************/
                        vector<int> index(nodes_same_label_set.size(), 0);
                        this -> in_out_nodelist_repeat_node_sort(nodes_same_label_vec, nodes_2_innodes, nodes_2_outnodes, index, print_invalid);
                        /********************************
                        *** Get the new pre-label list
                        ***      When there is a tie, label nodes with the smallest.
                        ********************************/
                        // this -> in_out_nodelist_repeat_node_re_label(nodes_same_label_vec, nodes_2_innodes, nodes_2_outnodes, index);
                    }
                    /********************************
                    *** Restart another repeat node vector finding
                    ********************************/
                    nodes_same_label_set.clear();
                    nodes_same_label_vec.clear();
                    nodes_2_outnodes.clear();
                    /********************************
                    *** Need to insert one in the beginning!!!!
                    ********************************/
                    nodes_same_label_set.insert(edge_itv->get_tail_name());
                }
                prev_num = edge_itv->get_tail_label();
            }
        } while (edge_itv++ != edges.end());
        if (nodes_same_label_set.size() != 1) {
            /********************************
            *** Process the repeat node vector
            ********************************/
            for (auto& node : nodes_same_label_set) {
                nodes_same_label_vec.push_back(node);
                nodes_2_innodes.push_back(this->get_innodes_labels(label, node));
                nodes_2_outnodes.push_back(this->get_outnodes_labels(node));
            }
            /********************************
            *** Sorting nodes by out-node list (sort `_node_2_edgelabel_2_outnodes` unordered_map by values).
            ********************************/
            vector<int> index(nodes_same_label_set.size(), 0);
            this -> in_out_nodelist_repeat_node_sort(nodes_same_label_vec, nodes_2_innodes, nodes_2_outnodes, index, print_invalid);
            /********************************
            *** Get the new pre-label list
            ***      When there is a tie, label nodes with the smallest.
            ********************************/
            // this -> in_out_nodelist_repeat_node_re_label(nodes_same_label_vec, nodes_2_innodes, nodes_2_outnodes, index);
        }
        /********************************
        *** Restart another repeat node vector finding
        ********************************/
        nodes_same_label_set.clear();
        nodes_same_label_vec.clear();
        nodes_2_outnodes.clear();
    }
}


void digraph::relabel_forward_root(vector<int> &repeat_vec, vector<int> &original_labels) {
#ifdef DEBUGPRINT
    cout << "\t......................................." << endl;
    cout << "\t..... Before relabelling root !!!!!!!! ....." << endl;
    cout << "\t......................................." << endl;
    this -> print_graph();
#endif
    for (int i = 0; i < repeat_vec.size(); i++) {
        original_labels.push_back(this->get_node_label(_root[i]));
        this -> relabel_by_node_name(_root[i], repeat_vec[i]);
#ifdef DEBUGPRINT
        cout << repeat_vec[i] << ", ";
#endif
    }
#ifdef DEBUGPRINT
    cout << endl;
    cout << "\t......................................." << endl;
    cout << "\t..... End relabelling root !!!!!!!! ........" << endl;
    cout << "\t......................................." << endl;
    this -> print_graph();
#endif   
}


void digraph::relabel_reverse_root(vector<int> &repeat_vec, vector<int> &original_labels) {
    /************************
    ** reverse-relabel back before starting another label try.
    ************************/
#ifdef DEBUGPRINT
    cout << "\t............................................" << endl;
    cout << "\t..... Before relabelling back root !!!!!!!! ....." << endl;
    cout << "\t............................................" << endl;
    this -> print_graph();
#endif
    for (int i = 0; i < repeat_vec.size(); i++) {
        this -> relabel_by_node_name(_root[i], original_labels[i]);
    }
#ifdef DEBUGPRINT
    cout << "\t............................................" << endl;
    cout << "\t..... End of relabelling back root !!!!!!!! ....." << endl;
    cout << "\t............................................" << endl;
    this -> print_graph();        
#endif
}


void digraph::relabel_forward(vector<int> &repeat_vec, vector<int> &original_labels, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, vector<int> &prev_num_vec, int &index) {
#ifdef DEBUGPRINT
    cout << "\t......................................." << endl;
    cout << "\t..... Before relabelling !!!!!!!! ....." << endl;
    cout << "\t......................................." << endl;
    this -> print_graph();
#endif
    for (int i = 0; i < repeat_vec.size(); i++) {
        original_labels.push_back(*nodes_2_relabelled_nodes_vec[prev_num_vec[index]][i]);
        this -> relabel_by_node_address(nodes_2_relabelled_nodes_vec[prev_num_vec[index]][i], repeat_vec[i]);
#ifdef DEBUGPRINT
        cout << repeat_vec[i] << ", ";
#endif
    }
#ifdef DEBUGPRINT
    cout << endl;
    cout << "\t......................................." << endl;
    cout << "\t..... End relabelling !!!!!!!! ........" << endl;
    cout << "\t......................................." << endl;
    this -> print_graph();
#endif   
}


void digraph::relabel_reverse(vector<int> &repeat_vec, vector<int> &original_labels, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, vector<int> &prev_num_vec, int &index) {
    /************************
    ** reverse-relabel back before starting another label try.
    ************************/
#ifdef DEBUGPRINT
    cout << "\t............................................" << endl;
    cout << "\t..... Before relabelling back !!!!!!!! ....." << endl;
    cout << "\t............................................" << endl;
    this -> print_graph();
#endif
    for (int i = 0; i < repeat_vec.size(); i++) {
        this -> relabel_by_node_address(nodes_2_relabelled_nodes_vec[prev_num_vec[index]][i], original_labels[i]);
    }
#ifdef DEBUGPRINT
    cout << "\t............................................" << endl;
    cout << "\t..... End of relabelling back !!!!!!!! ....." << endl;
    cout << "\t............................................" << endl;
    this -> print_graph();        
#endif
}


void digraph::relabel_by_node_name(int node_name, int new_val) {
#ifdef DEBUGPRINT
    cout << "node_name : " << node_name << endl;
    cout << "_node_2_ptr_address[node_name]: " << _node_2_ptr_address[node_name] << endl;
    cout << "*_node_2_ptr_address[node_name]: " << *_node_2_ptr_address[node_name] << endl;
    cout << "new_val: " << new_val << endl;
#endif
    *_node_2_ptr_address[node_name] = new_val;
}


void digraph::relabel_by_node_address(int* node_add, int new_val) {
    *node_add = new_val;
}


int digraph::get_node_label(int node_name) {
    return *_node_2_ptr_address[node_name];
}


int* digraph::get_node_address(int node_name) {
    return _node_2_ptr_address[node_name];
}


unordered_map<int,int*> digraph::get_node_2_ptr_address() {
    return _node_2_ptr_address;
}


map<string, vector<edge> > digraph::get_edge_label_2_edge() {
    return _edge_label_2_edge;
}


unordered_map<int,set<int> > digraph::get_node_2_innodes() {
    return _node_2_innodes;
}


map<string, vector<int> > digraph::get_outnodes_labels(int node_name) {
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "*** get_outnodes_labels =>  node_name: " << this->ascii2string(node_name) << "  "<< this -> get_node_label(node_name) << endl;
    cout << "*********************************" << endl;
#endif
    map<string, vector<int> > outnodes_label_ls;
    for (auto& pair : _node_2_edgelabel_2_outnodes[node_name]) {
        auto edgelabel = pair.first;
        auto outnodes_set = pair.second;
        vector<int> outnodes_vec(outnodes_set.size());
        transform(outnodes_set.begin(), outnodes_set.end(), outnodes_vec.begin(), 
                [this] (int a) {return get_node_label(a); });
        sort(outnodes_vec.begin(), outnodes_vec.end());
        outnodes_label_ls[edgelabel] = outnodes_vec;
    }
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "Starting of out_node_list: " << endl;
    for (auto& [edgelabel, outnodes] : outnodes_label_ls) {
        cout << "\tedgelabel: " << edgelabel << " " << endl << "\t\toutnode: ";
        for (auto& outnode : outnodes) {
            cout << outnode << ",  ";
        }
        cout << endl;
    }
    cout << "End of out_node_list " << endl;
    cout << "*********************************" << endl;
#endif
    return outnodes_label_ls;
}


vector<int> digraph::get_innodes_labels(string edge_label, int node_name) {
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "*** get_innodes_labels =>  node_name: "  << this->ascii2string(node_name) << "  "<< this -> get_node_label(node_name) << endl;
    cout << "*********************************" << endl;
#endif
    vector<int> innodes_label_ls;
    set<int*> innodes_address_set;
    for (auto& edge : _edge_label_2_edge[edge_label]) {
        if (edge.get_tail_name() == node_name) {
            if (innodes_address_set.find(edge.get_head()) == innodes_address_set.end()) {
#ifdef DEBUGPRINT
                cout << "edge.get_head(): " << edge.get_head() << endl; 
#endif
                innodes_address_set.insert(edge.get_head());
                innodes_label_ls.push_back(edge.get_head_label());
            }
        }
    }
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "Starting of in_node_list: " ;
    for (auto& node_label : innodes_label_ls) {
        cout << node_label << " ";
    }
    cout << "End of in_node_list " << endl;
    cout << "*********************************" << endl;
#endif
    return innodes_label_ls;
}


int digraph::get_valid_WG_num() {
    return _valid_WG_num;
}


int digraph::get_invalid_stop_num() {
    return _invalid_stop_num;
}


int digraph::get_valid_WG_num_2() {
    _valid_WG_num = 1;
    for (auto& [label, edges] : _edge_label_2_edge) {
        set<int*> node_with_same_label;
        int prev_node_label = edges.front().get_tail_label();
        for (auto& edge : edges) {
#ifdef DEBUGPRINT
            edge.print_edge();
#endif
            if (edge.get_tail_label() == prev_node_label) {
                node_with_same_label.insert(edge.get_tail());
#ifdef DEBUGPRINT
                cout << "Same !" << endl;
#endif
            } else {
#ifdef DEBUGPRINT
                cout << "node_with_same_label.size(): " << node_with_same_label.size() << endl;
#endif
                for (int i = 1; i <= node_with_same_label.size(); i++) {
                    _valid_WG_num *= i;
#ifdef DEBUGPRINT
                    cout << "i: " << i << endl;
                    cout << "_valid_WG_num: " << _valid_WG_num << endl;
#endif
                }
                node_with_same_label.clear();
                node_with_same_label.insert(edge.get_tail());
#ifdef DEBUGPRINT
                cout << "Not same !" << endl;
#endif
            }
        }
#ifdef DEBUGPRINT
        cout << "node_with_same_label.size(): " << node_with_same_label.size() << endl;
#endif
        for (int i = 1; i <= node_with_same_label.size(); i++) {
            _valid_WG_num *= i;
#ifdef DEBUGPRINT
            cout << "i: " << i << endl;
            cout << "_valid_WG_num: " << _valid_WG_num << endl;
#endif
        }
        node_with_same_label.clear();
#ifdef DEBUGPRINT
        cout << "End!!!!" << endl;
#endif
    }
    return _valid_WG_num;
}


void digraph::one_scan_through_wg_rg(string label) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `one_scan_through_wg_rg` " << endl;
    cout << "****   Label: " << label << endl;
    cout << "***************************" << endl;
#endif  
    int start_node_label = 0;
    int end_node_label = 0;
    int prev_num = 0;
    int* prev_address = &prev_num; // This is just initialization to a random address.
    int accum_same = 1;

    vector<edge>::iterator itv_1 = _edge_label_2_edge[label].begin();

    start_node_label = itv_1 -> get_tail_label();
    end_node_label = prev(_edge_label_2_edge[label].end()) -> get_tail_label();
#ifdef DEBUGPRINT
    cout << "start_node_label: " << start_node_label << endl;
    cout << "end_node_label: " << end_node_label << endl;
#endif  

    vector<edge>::iterator itv = _edge_label_2_edge[label].begin();
    vector<edge> smaller_gp;
    vector<edge> same_gp;
    vector<edge> bigger_gp;

    do{
        if (itv != _edge_label_2_edge[label].end()) {
#ifdef DEBUGPRINT
            itv -> print_edge();
#endif  
            if (itv -> get_head_label() < start_node_label) {
                smaller_gp.push_back(*itv);
#ifdef DEBUGPRINT
                cout << "Smaller group" << endl;
#endif  
            } else if (itv -> get_head_label() >= start_node_label && itv -> get_head_label() <= end_node_label) {
                same_gp.push_back(*itv);
#ifdef DEBUGPRINT
                cout << "Same group" << endl;
#endif  
            } else if (itv -> get_head_label() > end_node_label) {
                bigger_gp.push_back(*itv);
#ifdef DEBUGPRINT
                cout << "Bigger group" << endl;
#endif  
            }
        }
    } while (itv++ != _edge_label_2_edge[label].end());
#ifdef DEBUGPRINT
    cout << "** >> smaller_gp: " << endl;
    cout << "** >> same_gp: " << endl;;
    cout << "** >> bigger_gp: " << endl;
#endif  
}

void digraph::permutation_start(bool early_stop, bool print_invalid) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `permutation_start` " << endl;
    cout << "***************************" << endl;
#endif
    vector<int> repeat_vec(_root.size());
    iota (std::begin(repeat_vec), std::end(repeat_vec), 1);
    // Start _root permutation.
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `permutation_4_root` " << endl;
    cout << "***************************" << endl;
#endif
    do {
        vector<int> original_labels;
        // Relabel & try the new permutation.
        this -> relabel_forward_root(repeat_vec, original_labels);
        this -> permutation_4_edge_group(this -> get_first_edge_label(), early_stop, print_invalid);
        // Relabel back before trying another permutation.
        this -> relabel_reverse_root(repeat_vec, original_labels);
    } while(std::next_permutation(repeat_vec.begin(), repeat_vec.end()));
}

void digraph::permutation_4_edge_group(string label, bool early_stop, bool print_invalid) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `permutation_4_edge_group` " << endl;
    cout << "****   Label: " << label << endl;
    cout << "***************************" << endl;
#endif
    int prev_num = 0;
    int* prev_address = &prev_num; // This is just initialization to a random address.
    int accum_same = 1;
    vector<int> prev_num_vec;
    vector<int> accum_same_vec;
    map<int, vector<int*> > nodes_2_relabelled_nodes_vec;

    vector<edge>::iterator itv = _edge_label_2_edge[label].begin();
    vector<int*> relabelled_nodes_vec;
    do{
        if (itv != _edge_label_2_edge[label].end()) {
            if (prev_num == itv->get_tail_label() &&  prev_address == itv->get_tail()) {
#ifdef DEBUGPRINT
                cout << "They are the same node. No accumulation." << endl;
#endif
            } else if (prev_num == itv->get_tail_label() &&  prev_address != itv->get_tail()) {
                if (relabelled_nodes_vec.size() == 0) {
                    relabelled_nodes_vec.push_back(prev(itv)->get_tail());
                }
#ifdef DEBUGPRINT
                cout << "Same" << endl;
#endif
                accum_same += 1;
                relabelled_nodes_vec.push_back(itv->get_tail());
            } else if (prev_num!=0 && accum_same!=1) {
                prev_num_vec.push_back(prev_num);
                accum_same_vec.push_back(accum_same);
                nodes_2_relabelled_nodes_vec[prev_num] = relabelled_nodes_vec;
#ifdef DEBUGPRINT
                cout << "****&&  `permutation_4_edge_group` " << endl;
                for (auto& x:relabelled_nodes_vec) {
                    cout << x << " ";
                }
                cout << endl;
#endif
                accum_same = 1;
                relabelled_nodes_vec.clear();
            }
#ifdef DEBUGPRINT
            cout << "**** prev_num: " << prev_num << endl;
            cout << "**** accum_same: " << accum_same << endl;
            cout << "**** relabelled_nodes_vec.size(): " << relabelled_nodes_vec.size() << endl;
            cout << "itv->get_tail_label(): " << itv->get_tail_label() << endl;
#endif
            prev_num = itv->get_tail_label();
            prev_address = itv->get_tail();
        }
    } while (itv++ != _edge_label_2_edge[label].end());
    if (prev_num!=0 && accum_same!=1) {
        prev_num_vec.push_back(prev_num);
        accum_same_vec.push_back(accum_same);
        nodes_2_relabelled_nodes_vec[prev_num] = relabelled_nodes_vec;
        accum_same = 1;
        relabelled_nodes_vec.clear();
    }
#ifdef DEBUGPRINT
    cout << ">>>>>>> prev_num_vec.size(): " << prev_num_vec.size() << endl;
    cout << ">>>>>>> accum_same_vec.size(): " << accum_same_vec.size() << endl;
#endif
    this -> permutation_4_sub_edge_group(label, prev_num_vec, accum_same_vec, nodes_2_relabelled_nodes_vec, 0, early_stop, print_invalid);
}


void digraph::permutation_4_sub_edge_group(string &label, vector<int> &prev_num_vec, vector<int> &accum_same_vec, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, int index, bool early_stop, bool print_invalid) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****   Entry to  'permutation_4_sub_edge_group' !!!!!! " << endl;
    cout << "****   label: " << label << "  index: " << index << endl;
    cout << "****  `permutation_4_sub_edge_group` " << endl;
    cout << "***************************" << endl;
    cout << "prev_num_vec.size(): " << prev_num_vec.size() << endl;
    cout << "accum_same_vec.size(): " << accum_same_vec.size() << endl;
#endif
    if (index < prev_num_vec.size() && index < accum_same_vec.size()) {
        vector<int> repeat_vec(accum_same_vec[index]);
        iota (std::begin(repeat_vec), std::end(repeat_vec), prev_num_vec[index]);
#ifdef DEBUGPRINT
        cout << "prev_num_vec[index]: " << prev_num_vec[index] << endl;
        cout << "accum_same_vec[index]: " << accum_same_vec[index] << endl;
        cout << "nodes_2_relabelled_nodes_vec[prev_num_vec[index]]: " << nodes_2_relabelled_nodes_vec[prev_num_vec[index]].size() << endl;
#endif
        do {
            vector<int> original_labels;
            // Relabel & try the new permutation.
            this -> relabel_forward(repeat_vec, original_labels, nodes_2_relabelled_nodes_vec, prev_num_vec, index);
            bool WG_valid = true;
            WG_valid = this -> WG_checker_in_edge_group(label, _edge_label_2_edge[label], print_invalid);
#ifdef DEBUGPRINT
            cout << "$$$$$ WG_valid : " << WG_valid << endl;
#endif
            if (WG_valid) {
                this -> permutation_4_sub_edge_group(label, prev_num_vec, accum_same_vec, nodes_2_relabelled_nodes_vec, index+1, early_stop, print_invalid);
            }
            // Relabel back before trying another permutation.
            this -> relabel_reverse(repeat_vec, original_labels, nodes_2_relabelled_nodes_vec, prev_num_vec, index);
        } while(std::next_permutation(repeat_vec.begin(), repeat_vec.end()));
    } else {
#ifdef DEBUGPRINT
        cout << "There is no more permutation in 'permutation_4_edge_group' label " << label << endl;
#endif
        if (this -> get_next_edge_label(label)  != "" ) {
#ifdef DEBUGPRINT
            cout << "Move on to the next edge group label: " << this -> get_next_edge_label(label) << endl;
#endif
            this -> permutation_4_edge_group(this -> get_next_edge_label(label), early_stop, print_invalid);            
        } else if (this -> get_next_edge_label(label)  == ""  ) {
#ifdef DEBUGPRINT
            cout << "This is the end of all edge groups!!!! " << this -> get_next_edge_label(label) << endl;
#endif

            bool WG_valid = true;
            WG_valid = this -> WG_checker(print_invalid);
            if (WG_valid) {
                this -> valid_wheeler_graph(early_stop);
            } else {
                // Print the invalid graph!!!
                this -> invalid_wheeler_graph("Wrong", print_invalid, false);
            }
        }
    }
#ifdef DEBUGPRINT
    cout << "****End of  'permutation_4_sub_edge_group' !!!!!! " << endl;
    cout << "****   label: " << label << "  index: " << index << endl;
    cout << "************************************" << endl;
    cout << endl << endl;
#endif
}


void digraph::in_edge_group_sort(vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index, bool print_invalid) {
    for (int i = 0 ; i != index.size() ; i++) {
        index[i] = i;
    }
    sort(index.begin(), index.end(),
        [&](const int& a, const int& b) {
            if (edgegp_node_2_innodes_vec[a] < edgegp_node_2_innodes_vec[b]) {
                if (edgegp_node_2_innodes_vec[b].front() < edgegp_node_2_innodes_vec[a].back()) {
                    this -> invalid_wheeler_graph("'in_edge_group_sort'!!!", print_invalid, true);
                }
            } else if (edgegp_node_2_innodes_vec[a] > edgegp_node_2_innodes_vec[b]) {
                if (edgegp_node_2_innodes_vec[a].front() < edgegp_node_2_innodes_vec[b].back()) {
            
            cout << "edgegp_nodes[a]: " << this -> ascii2string(edgegp_nodes[a]) << endl;
            cout << "edgegp_label: " << this -> get_node_label(edgegp_nodes[a]) << endl;
            cout << "edgegp_node_2_innodes_vec[a]: " << endl;
            for (auto& aa : edgegp_node_2_innodes_vec[a]) {
                cout << aa << " ";
            }
            cout << endl;
            cout << "edgegp_nodes[b]: " << this -> ascii2string(edgegp_nodes[b]) << endl;
            cout << "edgegp_label: " << this -> get_node_label(edgegp_nodes[b]) << endl;
            cout << "edgegp_node_2_innodes_vec[b]: " << endl;
            for (auto& bb : edgegp_node_2_innodes_vec[b]) {
                cout << bb << " ";
            }
            cout << endl;
                    this -> invalid_wheeler_graph("'in_edge_group_sort'!!!", print_invalid, true);
                }
            }
#ifdef DEBUGPRINT
            cout << "edgegp_nodes[a]: " << this -> ascii2string(edgegp_nodes[a]) << endl;
            cout << "edgegp_node_2_innodes_vec[a]: " << endl;
            for (auto& aa : edgegp_node_2_innodes_vec[a]) {
                cout << aa << " ";
            }
            cout << endl;
            cout << "edgegp_nodes[b]: " << this -> ascii2string(edgegp_nodes[b]) << endl;
            cout << "edgegp_node_2_innodes_vec[b]: " << endl;
            for (auto& bb : edgegp_node_2_innodes_vec[b]) {
                cout << b << " ";
            }
            cout << endl;
#endif
            return (edgegp_node_2_innodes_vec[a] < edgegp_node_2_innodes_vec[b]);
        }
    );
}


void digraph::in_edge_group_pre_label(string label, vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index, int &accum_edgegp_size) {
    vector<int> prev {};
    int prev_relabel_num = 0;
    for (int i = 0; i < edgegp_nodes.size(); i++) {
        int relabel_num = 0;
        if (prev == edgegp_node_2_innodes_vec[index[i]]) {
            relabel_num = prev_relabel_num;
#ifdef DEBUGPRINT
            cout << "SAME!!!!" << endl;
            cout << "** Repeat label!!!  " << endl;
            for (auto& x : prev) {
                cout << x << ", ";
            }
            cout << endl;
#endif
        } else if (prev != edgegp_node_2_innodes_vec[index[i]]) {
#ifdef DEBUGPRINT
            cout << "DIFFERENT!!!!" << endl;
#endif
            relabel_num = i + accum_edgegp_size + 1 + _root.size();
            prev_relabel_num = relabel_num;
        }
#ifdef DEBUGPRINT
        cout << "index: " << index[i] << "\tnew_label: " << relabel_num << "\t edgegp_nodes: " << this -> ascii2string(edgegp_nodes[i]);

        cout << "\toriginal: ";
        for (auto& edgegp_node_innode : edgegp_node_2_innodes_vec[i]) {
            cout << edgegp_node_innode << "  ";
        }
        cout << "\t edgegp_nodes: " << this -> ascii2string(edgegp_nodes[index[i]]) << "\tordered: ";
        for (auto& edgegp_node_innode : edgegp_node_2_innodes_vec[index[i]]) {
            cout << edgegp_node_innode << "  ";
        }
        cout << endl;
#endif
        this -> relabel_by_node_name(edgegp_nodes[index[i]], relabel_num);
        prev = edgegp_node_2_innodes_vec[index[i]];
    }
}


void digraph::in_out_nodelist_repeat_node_sort(vector<int> &nodes_same_label_vec, vector<vector<int> > &nodes_2_innodes, vector<map<string, vector<int> > > &nodes_2_outnodes, vector<int> &index, bool print_invalid) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** in_out_nodelist_repeat_node_sort " << endl;
    cout << "***************************" << endl;
#endif
    for (int i = 0 ; i != index.size() ; i++) {
        index[i] = i;
        cout << this -> get_node_label(nodes_same_label_vec[i]) << " (" << this -> ascii2string(nodes_same_label_vec[i]) << ")  ";
    }

#ifdef DEBUGPRINT
    cout << endl;
    cout << "$$$$$$$ Number of repeat nodes with different addresses: " << index.size() << "  " << nodes_same_label_vec.size() << "  " << nodes_2_outnodes.size() << endl;
    cout << "&&&&&&&& Before sorting (nodes_2_innodes)!!!!" << endl;
    for (int i = 0; i < index.size(); i++) {
        cout << this -> get_node_label(nodes_same_label_vec[i]) << " (" << this -> ascii2string(nodes_same_label_vec[i]) << ")  " << endl << "\t";
        for (auto& innode : nodes_2_innodes[i]) {
            cout << innode << ",  ";
        }
    cout << endl;
    }
    cout << "&&&&&&&& Before sorting (nodes_2_outnodes)!!!!" << endl;
    for (int i = 0; i < index.size(); i++) {
        cout << this -> get_node_label(nodes_same_label_vec[i]) << " (" << this -> ascii2string(nodes_same_label_vec[i]) << ")  " << endl;
        for (auto& [edgelabel, outnodes] : nodes_2_outnodes[i]) {
            cout << "\t>>(($$$$$$$ edge label: " << edgelabel << endl;
            cout << "\t\t>>(($$$$$$$ outnode : ";
            for (auto& outnode: outnodes) {
                cout << outnode << ",  ";
            }
            cout << endl;
        }
    }
#endif

    // Now I need to check & sort!!! _node_2_edgelabel_2_outnodes[node]; (type: map<string, set<int> >)
    sort(index.begin(), index.end(),
        [&](const int& a, const int& b) {
            bool final_cmp = false; // false -> do not swap;  true -> swap
            bool a_bigger_entry = false;
            bool b_bigger_entry = false;
            // for (auto& [edgelabel, outnodes] : nodes_2_outnodes[a]) {
            for (auto& pair : _edge_label_2_edge) {
                // Check order is consistant among all labels.
                auto edgelabel = pair.first;
                // convert set to vector
#ifdef DEBUGPRINT
                cout << "  edgelabel: " << edgelabel << endl;
                cout << "  a: " << a << endl;
                cout << "  b: " << b << endl;
                cout << "nodes_2_innodes[a].size(): " << nodes_2_innodes[a].size() << endl;
                cout << "nodes_2_innodes[b].size(): " << nodes_2_innodes[b].size() << endl;
                cout << "nodes_2_outnodes[a][edgelabel].size(): " << nodes_2_outnodes[a][edgelabel].size() << endl;
                cout << "nodes_2_outnodes[b][edgelabel].size(): " << nodes_2_outnodes[b][edgelabel].size() << endl;   
#endif


                // In-node list won't be empty because only at most 1 node can have indegree zero.
                if (nodes_2_innodes[a] < nodes_2_innodes[b]) {
#ifdef DEBUGPRINT
                    cout << "\t\t\t\tnodes_2_innodes[b] is bigger" << endl;
#endif
                    if (nodes_2_innodes[b].front() < nodes_2_innodes[a].back()) {
                        this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", print_invalid, true);
                    }
                    b_bigger_entry = true;
                    final_cmp = true;
                } else if (nodes_2_innodes[a] > nodes_2_innodes[b]) {
#ifdef DEBUGPRINT
                    cout << "\t\t\t\tnodes_2_innodes[a] is bigger" << endl;
#endif
                    if (nodes_2_innodes[a].front() < nodes_2_innodes[b].back()) {
                        this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", print_invalid, true);
                    }
                    a_bigger_entry = true;
                    final_cmp = false;
                } else if (nodes_2_innodes[a] == nodes_2_innodes[b]) {
#ifdef DEBUGPRINT
                    cout << "\t\t\t\tnodes_2_innodes[a] == nodes_2_innodes[b] bigger" << endl;
#endif
                }

                if (nodes_2_outnodes[a][edgelabel].empty() && nodes_2_outnodes[b][edgelabel].empty()) {
                    // Cannot decide the order. 'a_bigger_entry', 'b_bigger_entry' remain the same
                    // Don't swap order 
#ifdef DEBUGPRINT
                    cout << "\t\t\tBoth nodes_2_outnodes[a][edgelabel] and nodes_2_outnodes[b][edgelabel] are empty." << endl;
#endif
                } else if (nodes_2_outnodes[a][edgelabel].empty() && !nodes_2_outnodes[b][edgelabel].empty()) {
                    // Cannot decide the order. 'a_bigger_entry', 'b_bigger_entry' remain the same
                    // Don't swap order
#ifdef DEBUGPRINT
                    cout << "\t\t\tnodes_2_outnodes[a][edgelabel] is empty but nodes_2_outnodes[b][edgelabel] is not empty." << endl;
#endif
                } else if (!nodes_2_outnodes[a][edgelabel].empty() && nodes_2_outnodes[b][edgelabel].empty()) {
                    // Cannot decide the order. 'a_bigger_entry', 'b_bigger_entry' remain the same
                    // Don't swap order
#ifdef DEBUGPRINT
                    cout << "\t\t\tnodes_2_outnodes[a][edgelabel] is not empty but nodes_2_outnodes[b][edgelabel] is empty." << endl;
#endif
                } else if (!nodes_2_outnodes[a][edgelabel].empty() && !nodes_2_outnodes[b][edgelabel].empty()) {
                    // Can decide the order!!
                    // swap order if nodes_2_outnodes[a][edgelabel] < nodes_2_outnodes[b][edgelabel].
#ifdef DEBUGPRINT
                    cout << "\t\t\tBoth nodes_2_outnodes[a][edgelabel] and nodes_2_outnodes[b][edgelabel] are not empty." << endl;
#endif
                    // These are invalid situation.
                    if (nodes_2_outnodes[a][edgelabel] < nodes_2_outnodes[b][edgelabel]) {
#ifdef DEBUGPRINT
                        cout << "\t\t\t\tnodes_2_outnodes[b][edgelabel] is bigger" << endl;
#endif
                        if (nodes_2_outnodes[b][edgelabel].front() < nodes_2_outnodes[a][edgelabel].back()) {
                            this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", print_invalid, true);
                        }
                        b_bigger_entry = true;
                        final_cmp = true;
                    } else if (nodes_2_outnodes[a][edgelabel] > nodes_2_outnodes[b][edgelabel]) {
#ifdef DEBUGPRINT
                        cout << "\t\t\t\tnodes_2_outnodes[a][edgelabel] is bigger" << endl;
#endif
                        if (nodes_2_outnodes[a][edgelabel].front() < nodes_2_outnodes[b][edgelabel].back()) {
                            this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", print_invalid, true);
                        }
                        a_bigger_entry = true;
                        final_cmp = false;
                    } else if (nodes_2_outnodes[a][edgelabel] == nodes_2_outnodes[b][edgelabel]) {
                        // Their in-node lists are same => Do not change their order.
#ifdef DEBUGPRINT
                        cout << "\t\t\t\tnodes_2_outnodes[a][edgelabel] == nodes_2_outnodes[b][edgelabel] bigger" << endl;
#endif
                    }
                }
                if (a_bigger_entry && b_bigger_entry) {
                    this -> invalid_wheeler_graph("Wrong!! The vector comparisons in different edge labels have to be in consistant order.", print_invalid, true);
                }
#ifdef DEBUGPRINT
                cout << "Checkpoint 0-1" << endl;
                cout << "a_bigger_entry: " << a_bigger_entry << endl;
                cout << "b_bigger_entry: " << b_bigger_entry << endl;
#endif
                // Check vectors are consistent
                // Smallest node vs biggest next in two groups.
            }
            if ((a_bigger_entry && !b_bigger_entry) || (!a_bigger_entry && b_bigger_entry)) {
                return final_cmp;
                // return false;
            } 
            if (!a_bigger_entry && !b_bigger_entry) {
                return false;
                // return true;
            }
            return false;
            // return true;
        }
    );

#ifdef DEBUGPRINT
    cout << "&&&&&&&& After sorting (nodes_2_innodes)!!!!" << endl;
    for (int i = 0; i < index.size(); i++) {
        cout << this -> get_node_label(nodes_same_label_vec[index[i]]) << " (" << this -> ascii2string(nodes_same_label_vec[index[i]]) << ")  " << endl << "\t";
        for (auto& innode : nodes_2_innodes[index[i]]) {
            cout << innode << ",  ";
        }
    cout << endl;
    }

    cout << "&&&&&&&& After sorting (nodes_2_outnodes)!!!!" << endl;
    for (int i = 0; i < index.size(); i++) {
        // cout << "index[i]: " << index[i] << endl;
        cout << this -> get_node_label(nodes_same_label_vec[index[i]]) << " (" << this -> ascii2string(nodes_same_label_vec[index[i]]) << ")  " << endl;
        for (auto& [edgelabel, outnodes] : nodes_2_outnodes[index[i]]) {
            cout << "\t>>(($$$$$$$ edge label: " << edgelabel << endl;
            cout << "\t\t>>(($$$$$$$ outnode : ";
            for (auto& outnode: outnodes) {
                cout << outnode << ",  ";
            }
            cout << endl;
        }
    }
#endif
}


void digraph::in_out_nodelist_repeat_node_re_label(vector<int> &nodes_same_label_vec, vector<vector<int> > &nodes_2_innodes, vector<map<string, vector<int> > > &nodes_2_outnodes, vector<int> &index) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** in_out_nodelist_repeat_node_re_label " << endl;
    cout << "***************************" << endl;
#endif
    vector<int> innode_prev{};
    map<string, vector<int> > outnode_prev{};
    // all nodes have the same label in `nodes_same_label_vec`.
    int original_label = this->get_node_label(nodes_same_label_vec.front());
    int prev_relabel_num = original_label;

    for (int i = 0; i < nodes_same_label_vec.size(); i++) {
        int relabel_num = 0;
        // Change the condition!!! When we cannot determine their order.!!!!!!!!!!!!
        bool no_order = true;
        for (auto& pair : _edge_label_2_edge) {
            // Check we cannot determine the order in all edge_label.
            auto edgelabel = pair.first;
            if (innode_prev == nodes_2_innodes[i]) {
                no_order = true;
            } else {
                no_order = false;
            }
            if (nodes_2_outnodes[index[i]][edgelabel].empty() || outnode_prev[edgelabel].empty()) {
                // Cannot decide the order. 'a_bigger_entry', 'b_bigger_entry' remain the same
#ifdef DEBUGPRINT
                cout << "\t\t\tnodes_2_outnodes[index[i]][edgelabel] or outnode_prev[edgelabel] are empty." << endl;
#endif
                no_order = no_order && true;
            } else if (!nodes_2_outnodes[index[i]][edgelabel].empty() && !outnode_prev[edgelabel].empty()) {
#ifdef DEBUGPRINT
                cout << "\t\t\tBoth nodes_2_outnodes[index[i]][edgelabel] and outnode_prev[edgelabel] are not empty." << endl;
#endif
                if (nodes_2_outnodes[index[i]][edgelabel] == outnode_prev[edgelabel]) {
                    no_order = no_order && true;
                } else {
                    // We can determine the order between `nodes_2_outnodes[index[i]][edgelabel]` and `v_previous`.
                    no_order = false;
                }
            }
            if (!no_order) {
                break;
            }
        }

        if (no_order) {
            relabel_num = prev_relabel_num;
#ifdef DEBUGPRINT
            cout << "\t** No order!!! Use the same label " << endl;
            cout << "\t**** Current !!!!" << endl;
            for (auto& [edgelabel, outnodes] : nodes_2_outnodes[index[i]]) {
                cout << "\t>>(($$$$$$$ edge label: " << edgelabel << endl;
                cout << "\t\t>>(($$$$$$$ outnode : ";
                for (auto& outnode: outnodes) {
                    cout << this -> ascii2string(outnode) << " (" << this -> get_node_label(outnode) << ")   ";
                }
                cout << endl;
            }
            cout << "\t**** outnode_Previous !!!!" << endl;
            for (auto& [edgelabel, outnodes] : outnode_prev) {
                cout << "\t>>(($$$$$$$ edge label: " << edgelabel << endl;
                cout << "\t\t>>(($$$$$$$ outnode : ";
                for (auto& outnode: outnodes) {
                    cout << this -> ascii2string(outnode) << " (" << this -> get_node_label(outnode) << ")   ";
                }
                cout << endl;
            }
#endif
        } else {
            // Change the relabelling condition!!!!!!!!!
                        // relabel_num = i + accum_edgegp_size + 2;!!!!
            relabel_num = i + original_label;
            prev_relabel_num = relabel_num;
        }
#ifdef DEBUGPRINT
        cout << ">>>>>>>> index: " << index[i] << "\tnew_label: " << relabel_num << "\t nodes_same_label_vec: " << this -> ascii2string(nodes_same_label_vec[index[i]]);
#endif
        this -> relabel_by_node_name(nodes_same_label_vec[index[i]], relabel_num);
        innode_prev = nodes_2_innodes[index[i]];
        outnode_prev = nodes_2_outnodes[index[i]];
    }
}


void digraph::sort_edge_label_2_edge(string &label) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** sort_edge_label_2_edge " << endl;
    cout << "***************************" << endl;

    cout << "&&& label: " << label << endl;
    cout << "Before sorting ... "  << endl;
    for (auto& edge: _edge_label_2_edge[label]) {
        cout << edge.get_head() << ", " << edge.get_tail() << endl;
    }
    for (auto& edge: _edge_label_2_edge[label]) {
        cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
    }
#endif

    sort(_edge_label_2_edge[label].begin(), _edge_label_2_edge[label].end(),
        [&](edge& e1, edge& e2) {
            return (e1 < e2);
        }
    );

#ifdef DEBUGPRINT
    cout << "After sorting ... "  << endl;
    for (auto& edge: _edge_label_2_edge[label]) {
        cout << edge.get_head() << ", " << edge.get_tail() << endl;
    }
    for (auto& edge: _edge_label_2_edge[label]) {
        cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
    }
#endif
}


string digraph::get_first_edge_label() {
    return _edge_label_2_edge.begin()->first;
}


string digraph::get_last_edge_label() {
    return (--_edge_label_2_edge.end())->first;
}


string digraph::get_next_edge_label(string label) {
    if (_edge_label_2_next_edge_label.find(label) != _edge_label_2_next_edge_label.end()) {
        return _edge_label_2_next_edge_label[label];
    } else {
#ifdef DEBUGPRINT
        cout << "The label " << label << " is the last edge label in the graph." << endl;
#endif
        return "";
    }
}


bool digraph::WG_checker_in_edge_group(string label, vector<edge> &edges, bool print_invalid) {
    string msg;
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `WG_checker_in_edge_group` " << endl;
    cout << "***************************" << endl;
#endif
    this -> sort_edge_label_2_edge(label);
    bool WG_valid = true;
    vector<edge>::iterator edge;
    for (edge = edges.begin(); edge != edges.end(); edge++) {
        if (edge != edges.begin()) {
            if (edge->get_head_label() < prev(edge)->get_head_label()) {
                WG_valid = false; 
                msg = "In the same edge group, the head of the current edge (" + to_string(edge->get_head_label()) + ") has to be bigger or equal to the head of the previous edge (" + to_string(prev(edge)->get_head_label()) + ").";
                if (print_invalid) {
                    cout << endl << endl << endl;
                    cout << "=================================================================" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    cout << "XXXXX After sorting, the invalid edges: XXXXX" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    prev(edge) -> print_edge();
                    edge -> print_edge();
                }
                this -> invalid_wheeler_graph(msg, print_invalid, false);
                break;
            } 
            if (edge->get_tail_label() < prev(edge)->get_tail_label()) {
                WG_valid = false; 
                msg = "In the same edge group, the tail of the current edge (" + to_string(edge->get_tail_label()) + ") has to be bigger or equal to the tail of the previous edge (" + to_string(prev(edge)->get_tail_label()) + ")." ;
                if (print_invalid) {
                    cout << endl << endl << endl;
                    cout << "=================================================================" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    cout << "XXXXX After sorting, the invalid edges: XXXXX" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    prev(edge) -> print_edge();
                    edge -> print_edge();
                }
                this -> invalid_wheeler_graph(msg, print_invalid, false);
                break;
            } 
        }
    }
    return WG_valid;
}


bool digraph::WG_checker(bool print_invalid) {
    string msg;
    
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** `WG_checker` " << endl;
    cout << "***************************" << endl;
#endif
    string first_edge_label = this -> get_first_edge_label();
    string label = first_edge_label;
    while(label != "" ) {
        this -> sort_edge_label_2_edge(label);
        label = this -> get_next_edge_label(label);
    }

    int last_edgegp_num = 0;
    string last_label = "";
    map<string, vector<edge> >::iterator it;
    bool WG_valid = true;
    for (it = _edge_label_2_edge.begin(); it != _edge_label_2_edge.end(); it++) {
#ifdef DEBUGPRINT
        if (it != _edge_label_2_edge.begin()) {
            cout << "prev(it).first: " << prev(it)->first << endl;
        }
        cout << "it.first: " << it->first << endl;
#endif
        if (next(it) != _edge_label_2_edge.end()) {
#ifdef DEBUGPRINT
            cout << "next(it).first: " << next(it)->first << endl;
            cout << "it.second: " << (it->second.end()-1)->get_tail_label() << endl;
            cout << "next(it).second: " << next(it)->second.begin()->get_tail_label() << endl;
#endif
            // Check adjacent edge group
            if ((it->second.end()-1)->get_tail_label() >= next(it)->second.begin()->get_tail_label()) {
                WG_valid = false; 
                msg = "The tail of the last edge in edge group " + it->first + " (" + to_string((it->second.end()-1)->get_tail_label()) + ") has to be bigger than the tail of the last edge in edge group " + next(it)->first + " (" + to_string(next(it)->second.begin()->get_tail_label()) + ").";
                this -> invalid_wheeler_graph(msg, print_invalid, false);
                break;
            }
        }
        // Check in edge group
        WG_valid = this -> WG_checker_in_edge_group(it->first, it->second, print_invalid);
        if (!WG_valid) break;
    }
    return WG_valid;
}


void digraph::WG_final_check() {
    if (_valid_WG_num > 0) {
        _is_wg = true;
        cout << "(v) It is a wheeler graph!!" << endl;
    } else {
        _is_wg = false;
        cout << "(x) It is not a wheeler graph!!" << endl;
    }
    this -> exit_program();
}


void digraph::find_root_node() {
    int counter = 0;
    for (auto& [node, ptr_idx] : _node_2_ptr_address) {
            // cout << "Trying node name: " << this->ascii2string(node) << endl;
        if (_node_2_innodes.find(node) == _node_2_innodes.end()) {
            // cout << "node name: " << this->ascii2string(node) << " is indegree 0." << endl;
#ifdef DEBUGPRINT
            cout << "node name: " << this->ascii2string(node) << " is indegree 0." << endl;
            this->print_node(node);
#endif
            // Not found => The in-degree of the node is zero. => possible root.
            counter += 1;
            _is_wg = true;
            _root.push_back(node);
        }
    }   
}


vector<int> digraph::get_root() {
    return _root;
}


bool digraph::get_is_wg() {
    return _is_wg;
}


void digraph::bfs() {
    // queue<int> bfsq;
    // // enqueue
    // unordered_map<int, bool> visited;
    // bfsq.push(_root);
    // while (!bfsq.empty()) {
    //     int node = bfsq.front();
    //     bfsq.pop();

    //     if (visited[node] != true) {
    //         visited[node] = true;
    //         cout << this -> get_node_label(node) << " ";
    //         for (auto& child : _node_2_outnodes[node]) {
    //             if (child != node) {
    //                 bfsq.push(child);
    //                 // this -> bfs(child);
    //             }
    //         }
    //     }
    //     // if (visited.find(node) == visited.end()) {
    //     //     // not found
    //     //     visited[node] = true;
    //     //     cout << this -> get_node_label(node)+1 << " ";
    //     //     for (auto& child : _node_2_outnodes[node]) {
    //     //         if (child != node) {
    //     //             bfsq.push(child);
    //     //             // this -> bfs(child);
    //     //         }
    //     //     }
    //     // }
    // }
    // // cout << this -> get_node_label(node)+1 << " ";
}


int digraph::string2ascii(string line) {
    string s_join;
    for (int i = 0; i < line.length(); i++) {
        int x = int(line.at(i));
        if (x >= 32 && x <= 122) {
            // Concatenate strings
            s_join = s_join + to_string(x);
        } 
    }
    int c = stoi(s_join);
    return c;
}


string digraph::ascii2string(int node_name) {
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


void digraph::valid_wheeler_graph(bool early_stop) {
    cout << endl << endl << endl;
    cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
    cout << "%%%%% Valid WG !!!!!!!!!!!!!!!!!! %%%%%" << endl;
    cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
    this -> print_graph("%%");
    cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
    cout << "%%%%% Valid WG !!!!!!!!!!!!!!!!!! %%%%%" << endl;
    cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
    _valid_WG_num += 1;
    // this -> output_wg_gagie();
    // if (early_stop) {
    //     this -> WG_final_check();
    //     this -> exit_program();
    // }
}


void digraph::invalid_wheeler_graph(string msg, bool print_invalid, bool stop) {
    _invalid_stop_num += 1;
    if (print_invalid) {
        cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
        cout << "XXXXX Invalid WG !!!!!!!!!!!!!!!! XXXXX" << endl;
        cout << "XXXXX   " << msg << endl;
        cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
        this -> print_graph("XX");
        cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
        cout << "XXXXX Invalid WG !!!!!!!!!!!!!!!! XXXXX" << endl;
        cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
        cout << "=================================================================" << endl;   
    }
    if (stop) {
        this -> exit_program();
    }
}


void digraph::exit_program() {
    this -> print_wg_result_number();
    exit(0);
}


void digraph::output_wg_gagie(string dir_name) {
    filesystem::create_directory(dir_name);
    string outfile_O = dir_name + "/O.txt";
    string outfile_I = dir_name + "/I.txt";
    string outfile_L = dir_name + "/L.txt";
    string outfile_DOT = dir_name + "/graph.dot";
    string outfile_NC = dir_name + "/nodes.txt";

    ofstream ofile_O;
    ofstream ofile_I;
    ofstream ofile_L;
    ofstream ofile_DOT;
    ofstream ofile_NC;

    ofile_I.open (outfile_I);
    ofile_O.open (outfile_O);
    ofile_L.open (outfile_L);
    ofile_DOT.open(outfile_DOT); 
    ofile_NC.open(outfile_NC);
    ofile_DOT << "strict digraph  {" << endl;
    /****************************************
    **** Processing _root
    *****************************************/
    for (auto& root_node : _root) {
        int outnodes_size = 0;
        for (auto& [edgelabel, outnodes] : _node_2_edgelabel_2_outnodes[root_node]) {
            outnodes_size += outnodes.size();
        }
        ostringstream repeated_I;
        ostringstream repeated_O;
        string repeated_L;
        // Output Travis data structure
        fill_n(ostream_iterator<string>(repeated_I), _node_2_innodes[root_node].size(), string("0"));
        fill_n(ostream_iterator<string>(repeated_O), outnodes_size, string("0"));
        // Bit array I
        ofile_I << repeated_I.str()+"1";
#ifdef DEBUGPRINT
        cout << "repeated_I: " << repeated_I.str()+"1" << endl;
#endif
        // Bit array O
        ofile_O << repeated_O.str()+"1";
#ifdef DEBUGPRINT
        cout << "repeated_O: " << repeated_O.str()+"1" << endl;
#endif
        // Bit array L
        for (auto& [edgelabel, outnodes] : _node_2_edgelabel_2_outnodes[root_node]) {
            for (int i = 0; i < outnodes.size(); i++) {
                repeated_L = repeated_L + edgelabel;
            }
        }
        ofile_L << repeated_L;
#ifdef DEBUGPRINT
        cout << "repeated_L: " << repeated_L << endl;
        cout << endl;
#endif

        // Output nodes conversion
        ofile_NC << this -> ascii2string(root_node) << "\t" << to_string(this -> get_node_label(root_node)) << endl;
    }

    /****************************************
    **** Processing _edge_label_2_edge
    *****************************************/
    for (auto& [label, edges] : _edge_label_2_edge) {
#ifdef DEBUGPRINT
        cout << "** labels: " << label << endl;
#endif
        edge pre_edge = edge();
        for (auto& edge : edges) {
            // Output new DOT
            ofile_DOT << "\t" << to_string(edge.get_head_label()) << " -> " << to_string(edge.get_tail_label()) << " [label=" << edge.get_label() << "];" << endl;
            if ((edge.get_tail() != pre_edge.get_tail())) {
            int outnodes_size = 0;
            for (auto& [edgelabel, outnodes] : _node_2_edgelabel_2_outnodes[edge.get_tail_name()]) {
                outnodes_size += outnodes.size();
            }

#ifdef DEBUGPRINT
                cout << "node name (tail): " << this -> ascii2string(edge.get_tail_name()) << "    node label: " << this -> get_node_label(edge.get_tail_name()) << endl;
                cout << to_string(_node_2_innodes[edge.get_tail_name()].size()) << endl;
                cout << to_string(outnodes_size) << endl;
#endif
                // Output Travis data structure    
                ostringstream repeated_I;
                ostringstream repeated_O;
                // ostringstream repeated_L;
                string repeated_L;

                fill_n(ostream_iterator<string>(repeated_I), _node_2_innodes[edge.get_tail_name()].size(), string("0"));
                fill_n(ostream_iterator<string>(repeated_O), outnodes_size, string("0"));
                // Bit array I
                ofile_I << repeated_I.str()+"1";
#ifdef DEBUGPRINT
                cout << "repeated_I: " << repeated_I.str()+"1" << endl;
#endif
                // Bit array O
                ofile_O << repeated_O.str()+"1";
#ifdef DEBUGPRINT
                cout << "repeated_O: " << repeated_O.str()+"1" << endl;
#endif
                // Bit array L
                for (auto& [edgelabel, outnodes] : _node_2_edgelabel_2_outnodes[edge.get_tail_name()]) {
                    for (int i = 0; i < outnodes.size(); i++) {
                        repeated_L = repeated_L + edgelabel;
                    }
                }
                ofile_L << repeated_L;
#ifdef DEBUGPRINT
                cout << "repeated_L: " << repeated_L << endl;
                cout << endl;
#endif

                // Output nodes conversion
                ofile_NC << this -> ascii2string(edge.get_tail_name()) << "\t" << to_string(this -> get_node_label(edge.get_tail_name())) << endl;
            }
            pre_edge = edge;
        }
    }
    ofile_DOT << "}" << endl;
    ofile_I.close();
    ofile_O.close();
    ofile_L.close();
    ofile_DOT.close();
    ofile_NC.close();
}

void digraph::output_wg_dot() {
    filesystem::create_directory(to_string(_valid_WG_num)+"__"+_path_name);
    string outfile_dot = to_string(_valid_WG_num)+"__"+_path_name + "/graph.dot";
    for (auto& [label, edges] : _edge_label_2_edge) {

    }
}

void digraph::output_nodes_conversion() {
}