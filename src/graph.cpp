// #define DEBUGPRINT

#include <iostream>
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

digraph::digraph(vector<string> node_names, int nodes_num, int edges_num) {
    _nodes_num = nodes_num;
    _edges_num = edges_num;
    _node_ptrs = new int[_nodes_num];

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
    // This is a temporary variable storing node group set.
    map<string, set<int> > label_2_node_group_set;
    // map<string, vector<int*> > label_2_node_group;
    for (int i=0; i<_edges_num; i++) {
        int node_1_name = this->string2ascii(node1_vec[i]);
        int node_2_name = this->string2ascii(node2_vec[i]);
#ifdef DEBUGPRINT
        cout << "node1_vec[i]: " << node_1_name << "  node2_vec[i]: " << node_2_name << endl;
        cout << "node1_vec[i] addr: " << _node_2_ptr_address[node_1_name] << "  node2_vec[i] addr: " << _node_2_ptr_address[node_2_name] << endl;
        cout << "node1_vec[i] label: " << *_node_2_ptr_address[node_1_name] << "  node2_vec[i] label: " << *_node_2_ptr_address[node_2_name] << endl;
        cout << "_node_ptrs[i]: " << _node_ptrs[i] << endl;
#endif
        // Find the outnode vector
        if (_node_2_outnodes.find(node_1_name) == _node_2_outnodes.end()) {
            // Not found
            set<int> new_outnodes_vc{node_2_name};
            _node_2_outnodes[node_1_name] = new_outnodes_vc;
        } else {
            _node_2_outnodes[node_1_name].insert(node_2_name);
        }

        // Find the innode vector
        if (_node_2_innodes.find(node_2_name) == _node_2_innodes.end()) {
            // Not found
            set<int> new_innodes_vc{node_1_name};
            _node_2_innodes[node_2_name] = new_innodes_vc;
        } else {
            _node_2_innodes[node_2_name].insert(node_1_name);
        }
        
        this -> find_root_node();

        edge e = edge(edge_labels[i], node_1_name, _node_2_ptr_address[node_1_name], node_2_name, _node_2_ptr_address[node_2_name]);
        
        // Find the label to edge vector & calculate node group set.
        if (_label_2_edge.find(e.get_label()) == _label_2_edge.end()) {
            // Not found
            vector<edge> new_sub_edge_vc{e};
            _label_2_edge[e.get_label()] = new_sub_edge_vc;

            set<int> new_sub_tail_set;
            new_sub_tail_set.insert(e.get_tail_name());
            label_2_node_group_set[e.get_label()] = new_sub_tail_set;
        } else {
            _label_2_edge[e.get_label()].push_back(e);
            label_2_node_group_set[e.get_label()].insert(e.get_tail_name());
        }
        _edges.push_back(e);
    }
    // calculate number of nodes in each node group set.
    string prev_label = "";
    for (auto& [label, node_group_set] : label_2_node_group_set ) {
        vector<int> node_group;
        // for(unsigned i=0; i<node_group.size(); ++i) node_group_set.insert(node_group[i]);
        node_group.assign(node_group_set.begin(), node_group_set.end());
        _label_2_edgegpnodes[label] = node_group;
        if (prev_label != "") {
            _edge_label_2_next_edge_label[prev_label] = label;
        }
        prev_label = label;
    }
}

void digraph::print_graph() {
    cout << "\t************************** " << endl; 
    cout << "\t** Print _edge_labels: " << endl; 
    cout << "\t************************** " << endl; 
    for (edge x : _edges) 
        cout << "\t   " << x.get_label() << " ";
    cout << endl;
    cout << "\t************************** " << endl; 
    cout << "\t** Print _label_2_edge: " << endl; 
    cout << "\t************************** " << endl; 
    for (auto& it : _label_2_edge) {
        cout << "\t   >> " << it.first << endl;
        for (auto& it_e : it.second) 
            it_e.print_edge();
    }
    cout << endl;
    cout << "\t************************** " << endl; 
    cout << "\t** Print node_names_2_node_labels: " << endl;
    cout << "\t************************** " << endl; 
    cout << "\t\t** Root: " << endl;
    cout << "\t\t   node name: " << this -> ascii2string(_root) << "    node label: " << this -> get_node_label(_root) << endl;
    for (auto& [label, edgegpnodes] : _label_2_edgegpnodes) {
        cout << "\t\t** labels: " << label << endl;
        for (auto& edgegpnode : edgegpnodes) {
            cout << "\t\t   node name: " << this -> ascii2string(edgegpnode) << "    node label: " << this -> get_node_label(edgegpnode) << endl;
        }
    }
    cout << endl << endl << endl;
}

void digraph::print_label_2_edge_graph() {
    cout << "************************** " << endl; 
    cout << "** Print 'label_2_edge': " << endl;
    cout << "************************** " << endl; 
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
    cout << "************************** " << endl; 
    cout << "** Print '_node_2_innodes': " << endl;
    cout << "************************** " << endl; 
    for (auto& [node, innodes] : _node_2_innodes) {
        // cout << "edge: " << edge << endl;
        cout << "** " << this->get_node_label(node) << ": " << endl;
        for (auto& innode: innodes) {
            cout << "   " << this->get_node_label(innode) << " ";
        }
        cout << endl;
    }
}

void digraph::print_node_2_outnodes_graph(int node_name) {
    cout << "************************** " << endl; 
    cout << "** Print '_node_2_outnodes': " << endl;
    cout << "************************** " << endl; 
    // for (auto& [node, outnodes] : _node_2_outnodes) {
        // cout << "edge: " << edge << endl;
    cout << "** " << this->get_node_label(node_name) << ": " << endl;
    for (auto& outnode: _node_2_outnodes[node_name]) {
        cout << "   " << this->get_node_label(outnode) << " ";
    }
    cout << endl;
    // }
}

void digraph::print_label_2_edgegpnodes() {
    cout << "************************** " << endl; 
    cout << "** Print '_label_2_edgegpnodes': " << endl;
    cout << "************************** " << endl; 
    for (auto& [edge_label, grps] : _label_2_edgegpnodes) {
        // cout << "edge: " << edge << endl;
        cout << edge_label << ": " << endl;
        for (auto& grp : grps) {
            cout << grp << " " << endl;
        }
    }
}

void digraph::print_node_names_2_node_labels() {
    cout << "************************** " << endl; 
    cout << "** Print node_names_2_node_labels: " << endl;
    cout << "************************** " << endl; 
    cout << "\t** Root: " << endl;
    cout << "\t   node name: " << this -> ascii2string(_root) << "    node label: " << this -> get_node_label(_root) << endl;
    for (auto& [label, edgegpnodes] : _label_2_edgegpnodes) {
        cout << "\t** labels: " << label << endl;
        for (auto& edgegpnode : edgegpnodes) {
            cout << "\t   node name: " << this -> ascii2string(edgegpnode) << "    node label: " << this -> get_node_label(edgegpnode) << endl;
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

void digraph::relabel_initialization() {
    // root has already added.
    cout << "************************** " << endl; 
    cout << "** Relabelling initialization: " << endl;
    cout << "************************** " << endl; 
    int accum_label = 1; 
    for (auto& [edge_label, edges] : _label_2_edge) {
        // cout << "_label_2_edgegpnodes[edge_label].size(): " << _label_2_edgegpnodes[edge_label].size() << endl;
        accum_label = accum_label + _label_2_edgegpnodes[edge_label].size();
        for (auto& edge: edges) {
            this -> relabel_by_node_address(edge.get_tail(), accum_label);
        }
    }
}

void digraph::innodelist_sort_relabel() {
    cout << "************************** " << endl; 
    cout << "** Sort & Pre-relabel nodes in same edge group: " << endl;
    cout << "************************** " << endl; 
    int accum_edgegp_size = 0;

    for (auto& [label, edges] : _label_2_edge) {
        cout << "****** LABEL: " << label << endl;
        unordered_map<int, vector<int> > edgegp_node_2_innodes;

        vector<int> edgegp_nodes;
        vector<vector<int> > edgegp_node_2_innodes_vec;

        for (auto& edge : edges) {
            edge.print_edge();
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
        this->in_edge_group_sort(edgegp_nodes, edgegp_node_2_innodes_vec, index);

        /********************************
        *** Get the new pre-label list
        ***      When there is a tie, label nodes with the smallest.
        ********************************/
        // this->in_edge_group_pre_label(label, edgegp_node_2_innodes, accum_edgegp_size);
        accum_edgegp_size += edgegp_node_2_innodes.size();
        cout << endl << endl;
    }


    // for (auto& [label, edgegp_nodes] : _label_2_edgegpnodes) {
    //     vector<vector<int> > edgegp_nodes_innodes;
        
    //     for (auto& edgegp_node: edgegp_nodes)  {
    //         vector<int> innodes_labels;
    //         innodes_labels = this->get_innodes_labels(edgegp_node);
    //         edgegp_nodes_innodes.push_back(innodes_labels);
    //     }

    //     // /********************************
    //     // *** Sorting
    //     // ********************************/
    //     // vector<int> index(edgegp_nodes_innodes.size(), 0);
    //     // this->in_edge_group_sort(edgegp_nodes_innodes, index);

    //     // /********************************
    //     // *** Get the new pre-label list
    //     // ***      When there is a tie, label nodes with the smallest.
    //     // ********************************/
    //     // this->in_edge_group_pre_label(label, edgegp_nodes_innodes, index, accum_edgegp_size);
    //     // accum_edgegp_size += edgegp_nodes.size();
    // }
}


void digraph::outnodelist_sort_relabel(vector<edge> &edges) {
    // Nodes we are going to sort have the same label but are different nodes.
    // Node label : nodes.
    cout << "************************** " << endl; 
    cout << "** Sort & relabel nodes by out-node-list in the same edge group: " << endl;
    cout << "************************** " << endl; 

    map<int, vector<int> > label_2_non_repeat_nodes;
    for (auto& edge: edges)  {
        if (label_2_non_repeat_nodes.find(edge.get_head_label()) == label_2_non_repeat_nodes.end()) {
            vector<int> nodes{edge.get_head_name()};
            label_2_non_repeat_nodes[edge.get_head_label()] = nodes;
        } else {
            if(find(label_2_non_repeat_nodes[edge.get_head_label()].begin(), label_2_non_repeat_nodes[edge.get_head_label()].end(), edge.get_head_name()) == label_2_non_repeat_nodes[edge.get_head_label()].end()) {
                // Only add into the `label_2_non_repeat_nodes` when the target node is not found in the vector.
                label_2_non_repeat_nodes[edge.get_head_label()].push_back(edge.get_head_name());
            }
        }
        edge.print_edge();
        // vector<int> innodes_labels;
        // innodes_labels = this->get_innodes_labels(edgegp_node);
        // edgegp_nodes_innodes.push_back(innodes_labels);
    }

    // Now, sort node by its outnode list
    for (auto& [label, nodes]: label_2_non_repeat_nodes) {
        cout << "Node label: " << label << endl;
        for (auto& node : nodes) {
            cout << "\tNode name: " << this -> ascii2string(node) << "\tAddress: " << this -> get_node_address(node) << "\tValue: " << this -> get_node_label(node) << endl;
            cout << "\tNode_2_outnodes: " << endl;
            this -> print_node_2_outnodes_graph(node);
        }
        cout << endl;
    }

        // vector<vector<int> > edgegp_nodes_innodes;
        
        

        /********************************
        *** Sorting
        ********************************/
        // vector<int> index(edgegp_nodes_innodes.size(), 0);
        // this->in_edge_group_sort(edgegp_nodes_innodes, index);

        /********************************
        *** Get the new pre-label list
        ***      When there is a tie, label nodes with the smallest.
        ********************************/
        // this->in_edge_group_pre_label(label, edgegp_nodes_innodes, index, accum_edgegp_size);
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

vector<edge> digraph::get_edges() {
    return _edges;
}

map<string, vector<edge> > digraph::get_label_2_edge() {
    return _label_2_edge;
}

map<string, vector<int> > digraph::get_label_2_edgegpnodes() {
    return _label_2_edgegpnodes;
}

unordered_map<int,set<int> > digraph::get_node_2_innodes() {
    return _node_2_innodes;
}

unordered_map<int,set<int> > digraph::get_node_2_outnodes() {
    return _node_2_outnodes;
}

vector<int> digraph::get_outnodes_labels(int node_name) {
    vector<int> outnodes_label_ls;
    for (auto& x : _node_2_outnodes[node_name]) {
        outnodes_label_ls.push_back(this -> get_node_label(x));
    }
    // sort(outnodes_label_ls.begin(), outnodes_label_ls.end());
    return outnodes_label_ls;
}

vector<int> digraph::get_innodes_labels(string edge_label, int node_name) {
    cout << "*** get_innodes_labels =>  node_name: " << this->ascii2string(node_name) << "  "<< this -> get_node_label(node_name) << endl;
    vector<int> innodes_label_ls;
    set<int*> innodes_address_set;


    for (auto& edge : _label_2_edge[edge_label]) {
        if (edge.get_tail_name() == node_name) {
            if (innodes_address_set.find(edge.get_head()) == innodes_address_set.end()) {
                cout << "edge.get_head(): " << edge.get_head() << endl; 
                innodes_address_set.insert(edge.get_head());
                innodes_label_ls.push_back(edge.get_head_label());
            }
        }
    }
    cout << "Starting of in_node_list: " ;
    for (auto& node_label : innodes_label_ls) {
        cout << node_label << " ";
    }
    cout << "End of in_node_list " << endl;
    return innodes_label_ls;
}

int digraph::get_valid_WG_num() {
    return _valid_WG_num;
}
























void digraph::one_scan_through_wg_rg(string label) {
// #ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `one_scan_through_wg_rg` " << endl;
    cout << "****   Label: " << label << endl;
    cout << "***************************" << endl;
// #endif  
    int start_node_label = 0;

    int end_node_label = 0;

    int prev_num = 0;
    int* prev_address = &prev_num; // This is just initialization to a random address.
    int accum_same = 1;




    vector<edge>::iterator itv_1 = _label_2_edge[label].begin();

    start_node_label = itv_1 -> get_tail_label();
    end_node_label = prev(_label_2_edge[label].end()) -> get_tail_label();
    cout << "start_node_label: " << start_node_label << endl;
    cout << "end_node_label: " << end_node_label << endl;

    vector<edge>::iterator itv = _label_2_edge[label].begin();
    // vector<int*> relabelled_nodes_vec;
    vector<edge> smaller_gp;
    vector<edge> same_gp;
    vector<edge> bigger_gp;

    do{
        if (itv != _label_2_edge[label].end()) {
            itv -> print_edge();
            if (itv -> get_head_label() < start_node_label) {
                smaller_gp.push_back(*itv);
                cout << "Smaller group" << endl;
            } else if (itv -> get_head_label() >= start_node_label && itv -> get_head_label() <= end_node_label) {
                same_gp.push_back(*itv);
                cout << "Same group" << endl;
            } else if (itv -> get_head_label() > end_node_label) {
                bigger_gp.push_back(*itv);
                cout << "Bigger group" << endl;
            }
        }
    } while (itv++ != _label_2_edge[label].end());

    cout << "** >> smaller_gp: " << endl;
    this -> outnodelist_sort_relabel(smaller_gp);

    cout << "** >> same_gp: " << endl;
    this -> outnodelist_sort_relabel(same_gp);

    cout << "** >> bigger_gp: " << endl;
    this -> outnodelist_sort_relabel(bigger_gp);
}



























void digraph::permutation_4_edge_group(string label) {
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

    vector<edge>::iterator itv = _label_2_edge[label].begin();
    vector<int*> relabelled_nodes_vec;
    do{
        if (itv != _label_2_edge[label].end()) {
            // cout << "itv->get_tail_label(): " << itv->get_tail_label() << endl;            
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
    } while (itv++ != _label_2_edge[label].end());
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
    this -> permutation_4_sub_edge_group(label, prev_num_vec, accum_same_vec, nodes_2_relabelled_nodes_vec, 0);
}

void digraph::permutation_4_sub_edge_group(string &label, vector<int> &prev_num_vec, vector<int> &accum_same_vec, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, int index) {
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
            WG_valid = this -> WG_checker_in_edge_group(label);
#ifdef DEBUGPRINT
            cout << "$$$$$ WG_valid : " << WG_valid << endl;
#endif
            if (WG_valid) {
                this -> permutation_4_sub_edge_group(label, prev_num_vec, accum_same_vec, nodes_2_relabelled_nodes_vec, index+1);
            } else {
#ifdef DEBUGPRINT
                cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                cout << "XXXXX Invalid WG !!!!!!!!!!!!!!!! XXXXX" << endl;
                cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                this -> print_graph();
#endif
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
            this -> permutation_4_edge_group(this -> get_next_edge_label(label));            
        } else if (this -> get_next_edge_label(label)  == ""  ) {
#ifdef DEBUGPRINT
            cout << "This is the end of all edge groups!!!! " << this -> get_next_edge_label(label) << endl;
#endif
            bool WG_valid = true;
            WG_valid = WG_checker();
            if (WG_valid) {
// #ifdef DEBUGPRINT
                cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
                cout << "%%%%% Valid WG !!!!!!!!!!!!!!!!!! %%%%%" << endl;
                cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
                this -> print_graph();
// #endif
                _valid_WG_num += 1;
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




void digraph::in_edge_group_sort(vector<int> edgegp_nodes, vector<vector<int> > edgegp_node_2_innodes_vec, vector<int> index) {
    for (int i = 0 ; i != index.size() ; i++) {
        index[i] = i;
        // cout << "** Index: " << index[i] << endl;
    }
    sort(index.begin(), index.end(),
        [&](const int& a, const int& b) {
            cout << "edgegp_node_2_innodes_vec[a]: " << endl;
            for (auto& aa : edgegp_node_2_innodes_vec[a]) {
                cout << aa << " ";
            }
            cout << endl;
            cout << "edgegp_node_2_innodes_vec[b]: " << endl;
            for (auto& bb : edgegp_node_2_innodes_vec[b]) {
                cout << b << " ";
            }
            cout << endl;
            return (edgegp_node_2_innodes_vec[a] < edgegp_node_2_innodes_vec[b]);
        }
    );
}

void digraph::in_edge_group_pre_label(string label, unordered_map<int, vector<int> > &edgegp_node_2_innodes, int &accum_edgegp_size) {
//     vector<int> prev{};
//     int prev_relabel_num = 0;
//     for (auto& [node, innodes] : edgegp_node_2_innodes) {
//         int relabel_num = 0;
//         if (prev == edgegp_nodes_innodes[index[i]]) {
//             relabel_num = prev_relabel_num;
// #ifdef DEBUGPRINT
//             cout << "** Repeat label!!!  " << endl;
//             for (auto& x : prev) {
//                 cout << x << ", ";
//             }
//             cout << endl;
// #endif
//         } else {
//             relabel_num = i + accum_edgegp_size + 2;
//             prev_relabel_num = relabel_num;
//         }
// #ifdef DEBUGPRINT
//         cout << "index: " << index[i] << "\tnew_label: " << relabel_num << "\t edgegp_nodes: " << this -> ascii2string(_label_2_edgegpnodes[label][i]);

//         cout << "\toriginal: ";
//         for (auto& edgegp_node_innode : edgegp_nodes_innodes[i]) {
//             cout << edgegp_node_innode << "  ";
//         }
//         cout << "\t edgegp_nodes: " << this -> ascii2string(_label_2_edgegpnodes[label][index[i]]) << "\tordered: ";
//         for (auto& edgegp_node_innode : edgegp_nodes_innodes[index[i]]) {
//             cout << edgegp_node_innode << "  ";
//         }
//         cout << endl;
// #endif
//         // g.relabel_by_node_name(edgegp_nodes[index[i]], relabel_num);
//         this -> relabel_by_node_name(_label_2_edgegpnodes[label][index[i]], relabel_num);
//         prev = edgegp_nodes_innodes[index[i]];
//     }


//     for (int i = 0 ; i != index.size() ; i++) {
//         int relabel_num = 0;
//         if (prev == edgegp_nodes_innodes[index[i]]) {
//             relabel_num = prev_relabel_num;
// #ifdef DEBUGPRINT
//             cout << "** Repeat label!!!  " << endl;
//             for (auto& x : prev) {
//                 cout << x << ", ";
//             }
//             cout << endl;
// #endif
//         } else {
//             relabel_num = i + accum_edgegp_size + 2;
//             prev_relabel_num = relabel_num;
//         }
// #ifdef DEBUGPRINT
//         cout << "index: " << index[i] << "\tnew_label: " << relabel_num << "\t edgegp_nodes: " << this -> ascii2string(_label_2_edgegpnodes[label][i]);

//         cout << "\toriginal: ";
//         for (auto& edgegp_node_innode : edgegp_nodes_innodes[i]) {
//             cout << edgegp_node_innode << "  ";
//         }
//         cout << "\t edgegp_nodes: " << this -> ascii2string(_label_2_edgegpnodes[label][index[i]]) << "\tordered: ";
//         for (auto& edgegp_node_innode : edgegp_nodes_innodes[index[i]]) {
//             cout << edgegp_node_innode << "  ";
//         }
//         cout << endl;
// #endif
//         // g.relabel_by_node_name(edgegp_nodes[index[i]], relabel_num);
//         this -> relabel_by_node_name(_label_2_edgegpnodes[label][index[i]], relabel_num);
//         prev = edgegp_nodes_innodes[index[i]];
//     }   
}

void digraph::sort_label_2_edge(string &label) {
    // for (auto& [label, edges] : _label_2_edge) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** sort_label_2_edge " << endl;
    cout << "***************************" << endl;

    cout << "&&& label: " << label << endl;
    cout << "Before sorting ... "  << endl;
    // vector<edge> edges;
    // edges = _label_2_edge[label];
    for (auto& edge: _label_2_edge[label]) {
        cout << edge.get_head() << ", " << edge.get_tail() << endl;
    }
    for (auto& edge: _label_2_edge[label]) {
        cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
    }
#endif

    sort(_label_2_edge[label].begin(), _label_2_edge[label].end(),
        [&](edge& e1, edge& e2) {
            return (e1 < e2);
        }
    );

#ifdef DEBUGPRINT
    cout << "After sorting ... "  << endl;
    for (auto& edge: _label_2_edge[label]) {
        cout << edge.get_head() << ", " << edge.get_tail() << endl;
    }
    for (auto& edge: _label_2_edge[label]) {
        cout << *edge.get_head() << ", " << *edge.get_tail()<< endl;
    }
#endif
    // }
}

string digraph::get_first_edge_label() {
    return _label_2_edgegpnodes.begin()->first;
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

bool digraph::WG_checker_in_edge_group(string &label) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `WG_checker_in_edge_group` " << endl;
    cout << "***************************" << endl;
#endif
    this -> sort_label_2_edge(label);
    bool WG_valid = true;
    vector<edge>::iterator edge;
    for (edge = _label_2_edge[label].begin(); edge != _label_2_edge[label].end(); edge++) {
        if (edge != _label_2_edge[label].begin()) {
            // cout << "edge: " << prev(edge)->get_head_label() << endl;
            if (edge->get_head_label() < prev(edge)->get_head_label()) {
                WG_valid = false; 
                break;
            } 
            if (edge->get_tail_label() < prev(edge)->get_tail_label()) {
                WG_valid = false; 
                break;
            } 
        }
        // cout << "edge: " << edge->get_head_label() << endl;
    }
    return WG_valid;
}

/*********************************
* This is a light version of WG checker!!
*   I do not consider the case that different nodes have to have different labels.
*********************************/
bool digraph::WG_checker() {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** `WG_checker` " << endl;
    cout << "***************************" << endl;
#endif
    string first_edge_label = this -> get_first_edge_label();
    string label = first_edge_label;
    while(label != "" ) {
        this -> sort_label_2_edge(label);
        label = this -> get_next_edge_label(label);
    } 

    int last_edgegp_num = 0;
    string last_label = "";
    map<string, vector<edge> >::iterator it;
    bool WG_valid = true;
    for (it = _label_2_edge.begin(); it != _label_2_edge.end(); it++) {
#ifdef DEBUGPRINT
        if (it != _label_2_edge.begin()) {
            cout << "prev(it).first: " << prev(it)->first << endl;
        }
        cout << "it.first: " << it->first << endl;
#endif
        if (next(it) != _label_2_edge.end()) {
#ifdef DEBUGPRINT
            cout << "next(it).first: " << next(it)->first << endl;

            cout << "it.second: " << (it->second.end()-1)->get_tail_label() << endl;
            cout << "next(it).second: " << next(it)->second.begin()->get_tail_label() << endl;
#endif
            WG_valid = (it->second.end()-1)->get_tail_label() < next(it)->second.begin()->get_tail_label();
            if (! WG_valid) {
                break;
            }
        }
        vector<edge>::iterator edge;
        for (edge = it->second.begin(); edge != it->second.end(); edge++) {
            if (edge != it->second.begin()) {
                // cout << "edge: " << prev(edge)->get_head_label() << endl;
                // if (edge->get_head_name() != prev(edge)->get_head_name()) {
                //     if (edge->get_head_label() == prev(edge)->get_head_label()) {
                //         WG_valid = false; 
                //         break;
                //     }
                // }
                // if (edge->get_tail_name() != prev(edge)->get_tail_name()) {
                //     if (edge->get_tail_name() == prev(edge)->get_tail_name()) {
                //         WG_valid = false; 
                //         break;
                //     }
                // }
                if (edge->get_head_label() < prev(edge)->get_head_label()) {
                    WG_valid = false; 
                    break;
                } 
                if (edge->get_tail_label() < prev(edge)->get_tail_label()) {
                    WG_valid = false; 
                    break;
                } 
            }
            // cout << "edge: " << edge->get_head_label() << endl;
        }
        if (! WG_valid) {
            break;
        }
    }
    return WG_valid;
}

void digraph::find_root_node() {
    int counter = 0;
    for (auto& [node, ptr_idx] : _node_2_ptr_address) {
        if (_node_2_innodes.find(node) == _node_2_innodes.end()) {
            // Not found => The in-degree of the node is zero. => possible root.
            counter += 1;
            // cout << "node: " << node << endl;
            _root = node;
        }
        if (counter == 0) {
            // OK! There is no root in this WG
        } else if (counter == 1) {
            _is_wg = true;
        } else {
            _is_wg = false;
            _root = int(NULL);
        }
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
    // cout << c << endl;
    // cout << &c << endl;
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