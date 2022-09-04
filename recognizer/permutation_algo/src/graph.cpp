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

// extern bool debugMode;
extern string outDir;
extern bool verbose;
extern bool writeIOL;
extern bool writeRange;
extern bool print_invalid;
extern bool all_valid_WG;
extern bool benchmark_mode;
extern clock_t c_start;
extern clock_t c_end;
extern double cpu_time_used;

digraph::digraph(vector<string> node_names, int nodes_num, int edges_num, string path_name) {
    // Storing the current node label and previous node label.
    _nodes_num = nodes_num;
    _edges_num = edges_num;
    _node_ptrs = new int[_nodes_num];
    _prev_node_ptrs = new int[_nodes_num];

    _path_name = path_name;

    /********************************
    *** Initialize the node indices. 
    ********************************/
    // This number decides the offset.
    int itr_count = 0;
    for(auto node : node_names) {
        _node_2_ptr_address[this->string2ascii(node)] = &_node_ptrs[itr_count];
        _prev_node_2_ptr_address[this->string2ascii(node)] = &_prev_node_ptrs[itr_count];

        _node_ptrs[itr_count] = itr_count + 1; 
        _prev_node_ptrs[itr_count] = itr_count + 1; 

        itr_count = itr_count+1;
#ifdef DEBUGPRINT
        cout << "** itr_count: " << itr_count-1 << endl;
        cout << "** _node_2_ptr_address[node]: " << _node_2_ptr_address[this->string2ascii(node)] << endl;
        cout << "** _prev_node_2_ptr_address[node]: " << _prev_node_2_ptr_address[this->string2ascii(node)] << endl;
        cout << "** _node_ptrs[itr_count]: " << _node_ptrs[itr_count-1] << endl;
        cout << "** _prev_node_ptrs[itr_count]: " << _prev_node_ptrs[itr_count-1] << endl;
#endif
    }
}


digraph::~digraph() {
    delete [] _node_ptrs;
}


void digraph::add_edges(vector<string> node1_vec, vector<string> node2_vec, vector<string> edgeLabels) {
    /***********************************************
    *** Iterate through all edges and add one by one
    ************************************************/
#ifdef DEBUGPRINT
    cout << "* Initialize the graph: " << endl;
#endif
    /***********************************************
    *** Iterating all edges and constructing all data structures.
    ************************************************/
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

        /***********************************************
        ***  Constructing the outnode dictionary.
        ************************************************/
        if (_node_2_edgeLabel_2_outnodes.find(node_1_name) == _node_2_edgeLabel_2_outnodes.end()) {
            //  The node key is not found.
            map<string, set<int> > edgelabel_2_outnodes;
            _node_2_edgeLabel_2_outnodes[node_1_name] = edgelabel_2_outnodes; 
            for (auto& edgeLabel : edgeLabels) {
                set<int> outnodes{};
                _node_2_edgeLabel_2_outnodes[node_1_name][edgeLabel] = outnodes;
            }
        } 
        _node_2_edgeLabel_2_outnodes[node_1_name][edgeLabels[i]].insert(node_2_name);

        /***********************************************
        ***  Constructing the innode dictionary.
        ************************************************/
        if (_node_2_innodes.find(node_2_name) == _node_2_innodes.end()) {
            // Not found => the first appearance.
            set<int> new_innodes_vc{node_1_name};
            _node_2_innodes[node_2_name] = new_innodes_vc;
        } else {
            _node_2_innodes[node_2_name].insert(node_1_name);
        }
        edge e = edge(edgeLabels[i], node_1_name, this->get_node_address(node_1_name), node_2_name, this->get_node_address(node_2_name));

        /***********************************************
        ***  Constructing the edge dictionary.
        ************************************************/
        if (_edgeLabel_2_edge.find(e.get_label()) == _edgeLabel_2_edge.end()) {
            // Not found => the first appearance.
            vector<edge> new_sub_edge_vc{e};
            _edgeLabel_2_edge[e.get_label()] = new_sub_edge_vc;
        } else {
            _edgeLabel_2_edge[e.get_label()].push_back(e);
        }
    }
    this -> find_root_node();

    /***********************************************
    *** Chaining the edge labels.
    ************************************************/
    string prev_label = "";
    for (auto& [label, edges] : _edgeLabel_2_edge ) {
        if (prev_label != "") {
            _edgeLabel_2_next_edgeLabel[prev_label] = label;
        }
        prev_label = label;
    }
}


void digraph::relabel_initialization() {
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
    for (auto& [edgeLabel, edges] : _edgeLabel_2_edge) {
        set<int> edgenodes_set;
        for (auto& edge : edges) {
            edgenodes_set.insert(edge.get_head_name());
        }
        // Relabel the node with the largest possible value in the edge group.
        accum_label = accum_label + edgenodes_set.size();
        for (auto& edge: edges) {
            this -> relabel_node(edge.get_head(), accum_label);
        }
    }

    bool WG_valid = true;
    WG_valid = this -> WG_checker();
    if (!WG_valid) {
        // Invalid graph!!! Terminate the program.
        if (!benchmark_mode) {
            cout << "XX After initialization, it is not a wheeler graph." << endl;
        }
        this -> exit_program(-1);
    }
}


void digraph::innodelist_sort_relabel() {
#ifdef DEBUGPRINT
    cout << "************************** " << endl; 
    cout << "** Sort & Pre-relabel nodes in same edge group: " << endl;
    cout << "************************** " << endl; 
#endif
    int accum_edgegp_size = 0;

    // To-do: maybe I can repeat the sorting & relabling until the node labels do not change.
    bool prelabels_fixed = false;
    while (!prelabels_fixed) {
        accum_edgegp_size = 0;
        for (auto& [label, edges] : _edgeLabel_2_edge) {
#ifdef DEBUGPRINT
            cout << "****** LABEL: " << label << endl;
#endif
            vector<int> edgegp_nodes;
            vector<vector<int> > edgegp_node_2_innodes_vec;

            for (auto& edge : edges) {
#ifdef DEBUGPRINT
                edge.print_edge();
#endif
                if (find(edgegp_nodes.begin(), edgegp_nodes.end(), edge.get_head_name()) == edgegp_nodes.end()) {
                    // The node has not been added into the map yet! 
                    edgegp_nodes.push_back(edge.get_head_name());
                    edgegp_node_2_innodes_vec.push_back(this->get_innodes_labels(label, edge.get_head_name()));
                }
            }

            /********************************
            *** Sorting nodes by in-node list (sort `edgegp_node_2_innodes` map by values).
            ********************************/
            vector<int> index(edgegp_nodes.size(), 0);
            this->in_edge_group_sort(edgegp_nodes, edgegp_node_2_innodes_vec, index);

            /********************************
            *** Get the new pre-label list
            ***      When there is a tie, label nodes with the **smallest**.
            ********************************/
            this->in_edge_group_pre_label(label, edgegp_nodes, edgegp_node_2_innodes_vec, index, accum_edgegp_size);
            accum_edgegp_size += edgegp_nodes.size();
        }
        // Check if all the prelabels are fixed.
        for (int i=0; i<_nodes_num; i++ ) {
#ifdef DEBUGPRINT
            // cout << "*_node_ptrs[i]: " << _node_ptrs[i] << endl;
            // cout << "*_prev_node_ptrs[i]: " << _prev_node_ptrs[i] << endl;
#endif
            prelabels_fixed = true;
            if (_node_ptrs[i] != _prev_node_ptrs[i]) {
                prelabels_fixed = false;
            }
        }
    }



    bool WG_valid = true;
    WG_valid = this -> WG_checker();


    if (!WG_valid) {
        // Invalid graph !! Terminate the program.
        if (!benchmark_mode) {
            cout << "XX After sorting by innode-list and relabelling, it is not a wheeler graph" << endl;
        }
        this -> WG_final_check();
        this -> exit_program(-1);
    } else {
        // Writing out the new possible range.
        if (writeRange) {
            int cur_min = 0;
            int cur_max = 0;

            int curr_val = 0;
            int prev_val = 0;
            set<string> node_set;
            
            ofstream ofile_range;
            filesystem::create_directories(outDir);
            ofile_range.open (outDir+"range.txt");

            int roots_size = _root.size();
            for (auto root : _root) {
                ofile_range << ascii2string(root) << " " << 1 << " " << roots_size << endl;   
            }
            for (auto& [label, edges] : _edgeLabel_2_edge) {
                for (auto& edge : edges) {
        #ifdef DEBUGPRINT
                    edge.print_edge();
        #endif
                    curr_val = edge.get_head_label();
                    if (curr_val == prev_val) {
                        // 'cur_min' remain the same
                    } else if (curr_val != prev_val) {
                        cur_min = cur_max + 1;
                        cur_max = curr_val - 1;
    #ifdef DEBUGPRINT
                        cout << "~~ edge: " << "curr_val: " << curr_val << "; prev_val: " << prev_val << "; cur_min: " << cur_min << "; cur_max: " << cur_max << endl;
    #endif
                        for (auto node_string : node_set) {
    #ifdef DEBUGPRINT
                            cout << "&&&& " << node_string << ": " << cur_min << " - " << cur_max << endl;
    #endif
                            ofile_range << node_string << " " << cur_min << " " << cur_max << endl;
                        }
                        node_set.clear();
                    }
                    node_set.insert(edge.get_head_name_string());
                    prev_val = curr_val;
                }
            }
            cur_min = cur_max + 1;
            cur_max = _nodes_num;
    #ifdef DEBUGPRINT
            cout << "~~ edge: " << "curr_val: " << curr_val << "; prev_val: " << prev_val << "; cur_min: " << cur_min << "; cur_max: " << cur_max << endl;
    #endif
            for (auto node_string : node_set) {
    #ifdef DEBUGPRINT
                cout << "&&&& " << node_string << ": " << cur_min << " - " << cur_max << endl;
    #endif
                ofile_range << node_string << " " << cur_min << " " << cur_max << endl;
            }
            node_set.clear();
        }
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
        this -> relabel_node(nodes_2_relabelled_nodes_vec[prev_num_vec[index]][i], repeat_vec[i]);
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
        this -> relabel_node(nodes_2_relabelled_nodes_vec[prev_num_vec[index]][i], original_labels[i]);
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
    cout << "_prev_node_2_ptr_address[node_name]: " << _prev_node_2_ptr_address[node_name] << endl;
    cout << "*_prev_node_2_ptr_address[node_name]: " << *_prev_node_2_ptr_address[node_name] << endl;
    cout << "prev_val: " << *_node_2_ptr_address[node_name] << endl;

    cout << "_node_2_ptr_address[node_name]: " << _node_2_ptr_address[node_name] << endl;
    cout << "*_node_2_ptr_address[node_name]: " << *_node_2_ptr_address[node_name] << endl;
    cout << "new_val: " << new_val << endl;
#endif
    *_prev_node_2_ptr_address[node_name] = *_node_2_ptr_address[node_name];
    *_node_2_ptr_address[node_name] = new_val;
}


void digraph::relabel_node(int* node_add, int new_val) {
    *node_add = new_val;
}


map<string, vector<int> > digraph::get_outnodes_labels(int node_name) {
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "*** get_outnodes_labels =>  node_name: " << this->ascii2string(node_name) << "  "<< this -> get_node_label(node_name) << endl;
    cout << "*********************************" << endl;
#endif
    map<string, vector<int> > outnodes_label_ls;
    for (auto& pair : _node_2_edgeLabel_2_outnodes[node_name]) {
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


vector<int> digraph::get_innodes_labels(string edgeLabel, int node_name) {
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "*** get_innodes_labels =>  node_name: "  << this->ascii2string(node_name) << "  "<< this -> get_node_label(node_name) << endl;
    cout << "*********************************" << endl;
#endif
    // vector<int> innodes_label_ls;
    vector<int> innodes_label_uniq_ls;
    set<int*> innodes_address_set;
    for (auto& edge : _edgeLabel_2_edge[edgeLabel]) {
        if (edge.get_head_name() == node_name) {
            if (innodes_address_set.find(edge.get_tail()) == innodes_address_set.end()) {
#ifdef DEBUGPRINT
                cout << "edge.get_tail(): " << edge.get_tail() << endl; 
#endif
                innodes_address_set.insert(edge.get_tail());
                // innodes_label_ls.push_back(edge.get_tail_label());
                if (innodes_label_uniq_ls.size() == 0) {
                    innodes_label_uniq_ls.push_back(edge.get_tail_label());
                } else {
                    if (edge.get_tail_label() != innodes_label_uniq_ls.back()) {
                        innodes_label_uniq_ls.push_back(edge.get_tail_label());
                    }
                }
            }
        }
    }
#ifdef DEBUGPRINT
    cout << "*********************************" << endl;
    cout << "Starting of in_node_list: " ;
    // for (auto& node_label : innodes_label_ls) {
    for (auto& node_label : innodes_label_uniq_ls) {
        cout << node_label << " ";
    }
    cout << "End of in_node_list " << endl;
    cout << "*********************************" << endl;
#endif
    // return innodes_label_ls;
    return innodes_label_uniq_ls;
}


int digraph::get_valid_WG_num_2() {
    _valid_WG_num = 1;
    for (auto& [label, edges] : _edgeLabel_2_edge) {
        set<int*> node_with_same_label;
        int prev_node_label = edges.front().get_head_label();
        for (auto& edge : edges) {
#ifdef DEBUGPRINT
            edge.print_edge();
#endif
            if (edge.get_head_label() == prev_node_label) {
                node_with_same_label.insert(edge.get_head());
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
                node_with_same_label.insert(edge.get_head());
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

    vector<edge>::iterator itv_1 = _edgeLabel_2_edge[label].begin();

    start_node_label = itv_1 -> get_head_label();
    end_node_label = prev(_edgeLabel_2_edge[label].end()) -> get_head_label();
#ifdef DEBUGPRINT
    cout << "start_node_label: " << start_node_label << endl;
    cout << "end_node_label: " << end_node_label << endl;
#endif  

    vector<edge>::iterator itv = _edgeLabel_2_edge[label].begin();
    vector<edge> smaller_gp;
    vector<edge> same_gp;
    vector<edge> bigger_gp;

    do{
        if (itv != _edgeLabel_2_edge[label].end()) {
#ifdef DEBUGPRINT
            itv -> print_edge();
#endif  
            if (itv -> get_tail_label() < start_node_label) {
                smaller_gp.push_back(*itv);
#ifdef DEBUGPRINT
                cout << "Smaller group" << endl;
#endif  
            } else if (itv -> get_tail_label() >= start_node_label && itv -> get_tail_label() <= end_node_label) {
                same_gp.push_back(*itv);
#ifdef DEBUGPRINT
                cout << "Same group" << endl;
#endif  
            } else if (itv -> get_tail_label() > end_node_label) {
                bigger_gp.push_back(*itv);
#ifdef DEBUGPRINT
                cout << "Bigger group" << endl;
#endif  
            }
        }
    } while (itv++ != _edgeLabel_2_edge[label].end());
#ifdef DEBUGPRINT
    cout << "** >> smaller_gp: " << endl;
    cout << "** >> same_gp: " << endl;;
    cout << "** >> bigger_gp: " << endl;
#endif  
}

void digraph::permutation_start(bool early_stop) {
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
#ifdef DEBUGPRINT
        cout << "*******************************" << endl;
        cout << "***     Root permutation   ****" << endl;
        cout << "*******************************" << endl;
        for (int& root : repeat_vec) {
            cout << root << " ";
        }
        cout << endl;
#endif
        this -> permutation_4_edge_group(this -> get_first_edgeLabel(), early_stop);
        // Relabel back before trying another permutation.
        this -> relabel_reverse_root(repeat_vec, original_labels);
    } while(std::next_permutation(repeat_vec.begin(), repeat_vec.end()));
}

void digraph::permutation_4_edge_group(string label, bool early_stop) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `permutation_4_edge_group` " << endl;
    cout << "****   Label: " << label << endl;
    cout << "***************************" << endl;
#endif
    int prev_num = 0;
    int prev_address_set_size = 0;
    set<int*> address_set;
    int accum_same = 1;
    vector<int> prev_num_vec;
    vector<int> accum_same_vec;
    map<int, vector<int*> > nodes_2_relabelled_nodes_vec;

    vector<edge>::iterator itv = _edgeLabel_2_edge[label].begin();
    vector<int*> relabelled_nodes_vec;

    this -> sort_edgeLabel_2_edge_by_tail(label);

    do{
        if (itv != _edgeLabel_2_edge[label].end()) {
#ifdef DEBUGPRINT
            cout << "&&&&& Iterating edges!!!" << endl;
            itv->print_edge();
#endif
            address_set.insert(itv->get_head());
            if (prev_num == itv->get_head_label() && address_set.size() == prev_address_set_size) {
#ifdef DEBUGPRINT
                cout << "They are the same node. No accumulation." << endl;
#endif
            } else if (prev_num == itv->get_head_label() && address_set.size() == (prev_address_set_size+1) ) {
                if (relabelled_nodes_vec.size() == 0) {
                    relabelled_nodes_vec.push_back(prev(itv)->get_head());
                }
#ifdef DEBUGPRINT
                cout << "Same" << endl;
#endif
                accum_same += 1;
                relabelled_nodes_vec.push_back(itv->get_head());
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
            cout << "itv->get_head_label(): " << itv->get_head_label() << endl;
#endif
            prev_num = itv->get_head_label();
            prev_address_set_size = address_set.size();
        }
    } while (itv++ != _edgeLabel_2_edge[label].end());

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
    this -> permutation_4_sub_edge_group(label, prev_num_vec, accum_same_vec, nodes_2_relabelled_nodes_vec, 0, early_stop);
}


void digraph::permutation_4_sub_edge_group(string &label, vector<int> &prev_num_vec, vector<int> &accum_same_vec, map<int, vector<int*> > &nodes_2_relabelled_nodes_vec, int index, bool early_stop) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****   Entry to  'permutation_4_sub_edge_group' !!!!!! " << endl;
    cout << "****   label: " << label << "  index: " << index << endl;
    cout << "****  `permutation_4_sub_edge_group` " << endl;
    cout << "***************************" << endl;
    cout << "index: " << index << endl;
    cout << "prev_num_vec.size(): " << prev_num_vec.size() << endl;
    for (int& i : prev_num_vec) {
        cout << i << endl;
    }

    cout << "accum_same_vec.size(): " << accum_same_vec.size() << endl;
    for (int& i : accum_same_vec) {
        cout << i << endl;
    }
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
            WG_valid = this -> WG_checker_in_edge_group(label, _edgeLabel_2_edge[label]);
#ifdef DEBUGPRINT
            cout << "???????????????????????????" << endl;
            cout << "????   permutation_4_sub_edge_group" << endl;
            cout << "???????????????????????????" << endl;
            for (int& ele : repeat_vec) {
                cout << ele << " ";
            }
            cout << endl;
            cout << "$$$$$ WG_valid : " << WG_valid << endl;
#endif
            if (WG_valid) {
                this -> permutation_4_sub_edge_group(label, prev_num_vec, accum_same_vec, nodes_2_relabelled_nodes_vec, index+1, early_stop);
            }
            // Relabel back before trying another permutation.
            this -> relabel_reverse(repeat_vec, original_labels, nodes_2_relabelled_nodes_vec, prev_num_vec, index);
        } while(std::next_permutation(repeat_vec.begin(), repeat_vec.end()));
    } else {
#ifdef DEBUGPRINT
        cout << "There is no more permutation in 'permutation_4_edge_group' label " << label << endl;
#endif
        if (this -> get_next_edgeLabel(label)  != "" ) {
#ifdef DEBUGPRINT
            cout << "Move on to the next edge group label: " << this -> get_next_edgeLabel(label) << endl;
#endif   
            bool WG_valid = true;
            WG_valid = this -> WG_checker_in_edge_group(label, _edgeLabel_2_edge[label]);
            if (WG_valid) {
                this -> permutation_4_edge_group(this -> get_next_edgeLabel(label), early_stop);            
            }
        } else if (this -> get_next_edgeLabel(label)  == ""  ) {
#ifdef DEBUGPRINT
            cout << "This is the end of all edge groups!!!! " << this -> get_next_edgeLabel(label) << endl;
#endif
            bool WG_valid = true;
            WG_valid = this -> WG_checker();
            if (WG_valid) {
                this -> valid_wheeler_graph(early_stop);
            } else {
                // Print the invalid graph!!!
                this -> invalid_wheeler_graph("After final check, it is an invalid wheeler graph", false);
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


void digraph::in_edge_group_sort(vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index) {
#ifdef DEBUGPRINT
    cout << "*************************" << endl;
    cout << "******* Inside 'in_edge_group_sort'" << endl;
    cout << "*************************" << endl;
    cout << "Before sorting." << endl;
#endif
    for (int i = 0 ; i != index.size() ; i++) {
        index[i] = i;
    }
    sort(index.begin(), index.end(),
        [&](const int& a, const int& b) {
            if (edgegp_node_2_innodes_vec[a] < edgegp_node_2_innodes_vec[b]) {
                if (edgegp_node_2_innodes_vec[b].front() < edgegp_node_2_innodes_vec[a].back()) {
                    this -> invalid_wheeler_graph("'in_edge_group_sort'!!!", true);
                }
            } else if (edgegp_node_2_innodes_vec[a] > edgegp_node_2_innodes_vec[b]) {
                if (edgegp_node_2_innodes_vec[a].front() < edgegp_node_2_innodes_vec[b].back()) {
            
#ifdef DEBUGPRINT
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n";
                    cout << "XX\tedgegp_nodes[a]: " << this -> ascii2string(edgegp_nodes[a]) << endl;
                    cout << "XX\tedgegp_label: " << this -> get_node_label(edgegp_nodes[a]) << endl;
                    cout << "XX\tedgegp_node_2_innodes_vec[a]: " << endl << "\t\t";
                    for (auto& aa : edgegp_node_2_innodes_vec[a]) {
                        cout << aa << " ";
                    }
                    cout << endl;
                    cout << "XX\tedgegp_nodes[b]: " << this -> ascii2string(edgegp_nodes[b]) << endl;
                    cout << "XX\tedgegp_label: " << this -> get_node_label(edgegp_nodes[b]) << endl;
                    cout << "XX\tedgegp_node_2_innodes_vec[b]: " << endl << "\t\t";
                    for (auto& bb : edgegp_node_2_innodes_vec[b]) {
                        cout << bb << " ";
                    }
                    cout << endl;
#endif
                    this -> invalid_wheeler_graph("'in_edge_group_sort'!!!", true);
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
                cout << bb << " ";
            }
            cout << endl;
#endif
            return (edgegp_node_2_innodes_vec[a] < edgegp_node_2_innodes_vec[b]);
        }
    );
#ifdef DEBUGPRINT
    cout << "After sorting." << endl;
    for (int i = 0 ; i != index.size() ; i++) {
        cout << index[i] << " ";
    }
    cout << endl;
#endif
}


void digraph::in_edge_group_pre_label(string label, vector<int> &edgegp_nodes, vector<vector<int> > &edgegp_node_2_innodes_vec, vector<int> &index, int &accum_edgegp_size) {
#ifdef DEBUGPRINT
    cout << "*************************" << endl;
    cout << "******* Inside 'in_edge_group_pre_label'" << endl;
    cout << "*************************" << endl;
#endif
    vector<int> prev {};
    int prev_relabel_num = 0;    
    for (int i = 0; i < edgegp_nodes.size(); i++) {
        int relabel_num = 0;

        int prev_len = prev.size();
        int curr_len = edgegp_node_2_innodes_vec[index[i]].size();
        int itr_len = 0;
        if (prev_len >= curr_len) {
            itr_len = curr_len;
        } else {
            itr_len = prev_len;
        }

#ifdef DEBUGPRINT
        cout << "prev_len: " << prev_len << endl;
        cout << "curr_len: " << curr_len << endl;
        cout << "itr_len: " << itr_len << endl;
#endif

        bool vector_contained = true;
        if (itr_len == 0) {
            vector_contained = false;
        } else {
            for (int idx=0; idx < itr_len; idx++) {
#ifdef DEBUGPRINT
                cout << "prev[idx]                               : " << prev[idx] << endl;
                cout << "edgegp_node_2_innodes_vec[index[i]][idx]: " << edgegp_node_2_innodes_vec[index[i]][idx] << endl;
#endif
                if (prev[idx] != edgegp_node_2_innodes_vec[index[i]][idx]) {
                    vector_contained = false;
                    break;
                }
            }
        }
        if (vector_contained) {
            relabel_num = prev_relabel_num;
#ifdef DEBUGPRINT
            cout << "Contained !!!!" << endl;
            cout << "** Repeat label!!!  " << endl;
            for (auto& x : prev) {
                cout << x << ", ";
            }
            cout << endl;
#endif
        } else {
#ifdef DEBUGPRINT
            cout << "Not contained!!!!" << endl;
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


void digraph::sort_edgeLabel_2_edge(string &label) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** sort_edgeLabel_2_edge " << endl;
    cout << "***************************" << endl;

    cout << "&&& label: " << label << endl;
    cout << "Before sorting ... "  << endl;
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << edge.get_tail() << ", " << edge.get_head() << endl;
    }
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << *edge.get_tail() << ", " << *edge.get_head()<< endl;
    }
#endif

    sort(_edgeLabel_2_edge[label].begin(), _edgeLabel_2_edge[label].end(),
        [&](edge& e1, edge& e2) {
            return (e1 < e2);
        }
    );

#ifdef DEBUGPRINT
    cout << "After sorting ... "  << endl;
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << edge.get_tail() << ", " << edge.get_head() << endl;
    }
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << *edge.get_tail() << ", " << *edge.get_head()<< endl;
    }
#endif
}

void digraph::sort_edgeLabel_2_edge_by_tail(string &label) {
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** sort_edgeLabel_2_edge_by_tail" << endl;
    cout << "***************************" << endl;

    cout << "&&& label: " << label << endl;
    cout << "Before sorting ... "  << endl;
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << edge.get_tail() << ", " << edge.get_head() << endl;
    }
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << *edge.get_tail() << ", " << *edge.get_head()<< endl;
    }
#endif

    sort(_edgeLabel_2_edge[label].begin(), _edgeLabel_2_edge[label].end(),
        [&](edge& e1, edge& e2) {
            return (e1 << e2);
        }
    );

#ifdef DEBUGPRINT
    cout << "After sorting ... "  << endl;
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << edge.get_tail() << ", " << edge.get_head() << endl;
    }
    for (auto& edge: _edgeLabel_2_edge[label]) {
        cout << *edge.get_tail() << ", " << *edge.get_head()<< endl;
    }
#endif
}


string digraph::get_first_edgeLabel() {
    return _edgeLabel_2_edge.begin()->first;
}


string digraph::get_last_edgeLabel() {
    return (--_edgeLabel_2_edge.end())->first;
}


string digraph::get_next_edgeLabel(string label) {
    if (_edgeLabel_2_next_edgeLabel.find(label) != _edgeLabel_2_next_edgeLabel.end()) {
        return _edgeLabel_2_next_edgeLabel[label];
    } else {
#ifdef DEBUGPRINT
        cout << "The label " << label << " is the last edge label in the graph." << endl;
#endif
        return "";
    }
}


bool digraph::WG_checker_in_edge_group(string label, vector<edge> &edges) {
    string msg;
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "****  `WG_checker_in_edge_group` " << endl;
    cout << "***************************" << endl;
#endif
    this -> sort_edgeLabel_2_edge(label);
    bool WG_valid = true;
    vector<edge>::iterator edge;
    for (edge = edges.begin(); edge != edges.end(); edge++) {
        if (edge != edges.begin()) {
            if (edge->get_tail_label() < prev(edge)->get_tail_label()) {
                WG_valid = false; 
                msg = "In the same edge group, the tail of the current edge (" + to_string(edge->get_tail_label()) + ") has to be bigger or equal to the tail of the previous edge (" + to_string(prev(edge)->get_tail_label()) + ").";
                if (print_invalid && !benchmark_mode) {
                    cout << endl << endl << endl;
                    cout << "=================================================================" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    cout << "XXXXX After sorting, the invalid edges: XXXXX" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    prev(edge) -> print_edge();
                    edge -> print_edge();
                    this->get_innodes_labels(label, prev(edge)->get_head_name());
                    this->get_innodes_labels(label, edge->get_head_name());
                }
                this -> invalid_wheeler_graph(msg, false);
                break;
            } 
            if (edge->get_head_label() < prev(edge)->get_head_label()) {
                WG_valid = false; 
                msg = "In the same edge group, the head of the current edge (" + to_string(edge->get_head_label()) + ") has to be bigger or equal to the head of the previous edge (" + to_string(prev(edge)->get_head_label()) + ")." ;
                if (print_invalid && !benchmark_mode) {
                    cout << endl << endl << endl;
                    cout << "=================================================================" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    cout << "XXXXX After sorting, the invalid edges: XXXXX" << endl;
                    cout << "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" << endl;
                    prev(edge) -> print_edge();
                    edge -> print_edge();


                    this->get_innodes_labels(label, prev(edge)->get_head_name());
                    this->get_innodes_labels(label, edge->get_head_name());
                }
                this -> invalid_wheeler_graph(msg, false);
                break;
            } 
        }
    }
    return WG_valid;
}


bool digraph::WG_checker() {
    string msg;
    
#ifdef DEBUGPRINT
    cout << "***************************" << endl;
    cout << "**** `WG_checker` " << endl;
    cout << "***************************" << endl;
#endif
    string first_edgeLabel = this -> get_first_edgeLabel();
    string label = first_edgeLabel;
    while(label != "" ) {
        this -> sort_edgeLabel_2_edge(label);
        label = this -> get_next_edgeLabel(label);
    }

    int last_edgegp_num = 0;
    string last_label = "";
    map<string, vector<edge> >::iterator it;
    bool WG_valid = true;
    for (it = _edgeLabel_2_edge.begin(); it != _edgeLabel_2_edge.end(); it++) {
#ifdef DEBUGPRINT
        if (it != _edgeLabel_2_edge.begin()) {
            cout << "prev(it).first: " << prev(it)->first << endl;
        }
        cout << "it.first: " << it->first << endl;
#endif
        if (next(it) != _edgeLabel_2_edge.end()) {
#ifdef DEBUGPRINT
            cout << "next(it).first: " << next(it)->first << endl;
            cout << "it.second: " << (it->second.end()-1)->get_head_label() << endl;
            cout << "next(it).second: " << next(it)->second.begin()->get_head_label() << endl;
#endif
            // Check adjacent edge group
            if ((it->second.end()-1)->get_head_label() >= next(it)->second.begin()->get_head_label()) {
                WG_valid = false; 
                msg = "The head of the last edge in edge group " + it->first + " (" + to_string((it->second.end()-1)->get_head_label()) + ") has to be bigger than the head of the last edge in edge group " + next(it)->first + " (" + to_string(next(it)->second.begin()->get_head_label()) + ").";
                this -> invalid_wheeler_graph(msg, false);
                break;
            }
        }
        // Check in edge group
        WG_valid = this -> WG_checker_in_edge_group(it->first, it->second);
        if (!WG_valid) break;
    }
    return WG_valid;
}


void digraph::WG_final_check() {
    print_node_2_innodes_graph();
    if (_valid_WG_num > 0) {
        _is_wg = true;
        if (!benchmark_mode) {
            cout << "(v) It is a wheeler graph!!" << endl;
        }
        this -> exit_program(1);
    } else {
        _is_wg = false;
        if (!benchmark_mode) {
            cout << "(x) It is not a wheeler graph!!" << endl;
        }
        this -> exit_program(-1);
    }
}


void digraph::find_root_node() {
    int counter = 0;
    if (verbose && !benchmark_mode) {
        cout << "Step 1: finding the root nodes." << endl;
    }
    for (auto& [node, ptr_idx] : _node_2_ptr_address) {
        if (verbose) {
            cout << "\tTrying node name: " << this->ascii2string(node) << endl;
        }

        /***********************************************
        ***  Cannot find this node in the innodes dictionary.
        ************************************************/
        if (_node_2_innodes.find(node) == _node_2_innodes.end()) {
            if (verbose && !benchmark_mode) {
#ifdef DEBUGPRINT
                cout << "node name: " << this->ascii2string(node) << " is indegree 0." << endl;
                this->print_node(node);
#endif
            }
            // Not found => The in-degree of the node is zero. => root.
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
    if (verbose && !benchmark_mode) {
        cout << endl << endl << endl;
        cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
        cout << "%%%%% Valid WG !!!!!!!!!!!!!!!!!! %%%%%" << endl;
        cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
        this -> print_graph("%%");
        cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
        cout << "%%%%% Valid WG !!!!!!!!!!!!!!!!!! %%%%%" << endl;
        cout << "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" << endl;
    }
    _valid_WG_num += 1;
    if (writeIOL) {
        this -> output_wg_gagie();
    }
    if (early_stop) {
        this -> WG_final_check();
    }
}


void digraph::invalid_wheeler_graph(string msg, bool stop) {
    _invalid_stop_num += 1;
    if (verbose) {
        if (print_invalid && !benchmark_mode) {
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
    }
    if (stop) {
        // cout << "(x) It is not a wheeler graph!!" << endl;
        this -> exit_program(-1);
    }
}


void digraph::exit_program(int return_val) {
    if (verbose) {
        this -> print_wg_result_number();
    }
    // c_end = chrono::high_resolution_clock::now();
    // auto duration = chrono::duration_cast<chrono::microseconds>(c_end - c_start);
    c_end = clock();
    cpu_time_used = ((double) (c_end - c_start));

    if (benchmark_mode) {
        cout << return_val << "\t" << to_string(_nodes_num) << "\t" << cpu_time_used << "\t" << _path_name << endl;
    } else {
        cout << "Runtime : " << cpu_time_used << " microseconds" << endl;
    }
    exit(return_val);
}


void digraph::output_wg_gagie() {
    filesystem::create_directories(outDir+to_string(_valid_WG_num)+"__"+_path_name);
    string outfile_O = outDir+to_string(_valid_WG_num)+"__"+_path_name + "/O.txt";
    string outfile_I = outDir+to_string(_valid_WG_num)+"__"+_path_name + "/I.txt";
    string outfile_L = outDir+to_string(_valid_WG_num)+"__"+_path_name + "/L.txt";
    string outfile_DOT = outDir+to_string(_valid_WG_num)+"__"+_path_name + "/graph.dot";
    string outfile_NC = outDir+to_string(_valid_WG_num)+"__"+_path_name + "/nodes.txt";

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
        for (auto& [edgelabel, outnodes] : _node_2_edgeLabel_2_outnodes[root_node]) {
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
        for (auto& [edgelabel, outnodes] : _node_2_edgeLabel_2_outnodes[root_node]) {
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
    **** Processing _edgeLabel_2_edge
    *****************************************/
    for (auto& [label, edges] : _edgeLabel_2_edge) {
#ifdef DEBUGPRINT
        cout << "** labels: " << label << endl;
#endif
        edge pre_edge = edge();
        for (auto& edge : edges) {
            // Output new DOT
            ofile_DOT << "\t" << to_string(edge.get_tail_label()) << " -> " << to_string(edge.get_head_label()) << " [label=" << edge.get_label() << "];" << endl;
            if ((edge.get_head() != pre_edge.get_head())) {
            int outnodes_size = 0;
            for (auto& [edgelabel, outnodes] : _node_2_edgeLabel_2_outnodes[edge.get_head_name()]) {
                outnodes_size += outnodes.size();
            }

#ifdef DEBUGPRINT
                cout << "node name (head): " << this -> ascii2string(edge.get_head_name()) << "    node label: " << this -> get_node_label(edge.get_head_name()) << endl;
                cout << to_string(_node_2_innodes[edge.get_head_name()].size()) << endl;
                cout << to_string(outnodes_size) << endl;
#endif
                // Output Travis data structure    
                ostringstream repeated_I;
                ostringstream repeated_O;
                // ostringstream repeated_L;
                string repeated_L;

                fill_n(ostream_iterator<string>(repeated_I), _node_2_innodes[edge.get_head_name()].size(), string("0"));
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
                for (auto& [edgelabel, outnodes] : _node_2_edgeLabel_2_outnodes[edge.get_head_name()]) {
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
                ofile_NC << this -> ascii2string(edge.get_head_name()) << "\t" << to_string(this -> get_node_label(edge.get_head_name())) << endl;
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