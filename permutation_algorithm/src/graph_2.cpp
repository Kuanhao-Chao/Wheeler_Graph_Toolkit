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

void digraph::in_out_nodelist_repeat_node_sort(vector<int> &nodes_same_label_vec, vector<vector<int> > &nodes_2_innodes, vector<map<string, vector<int> > > &nodes_2_outnodes, vector<int> &index) {
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
                        this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", true);
                    }
                    b_bigger_entry = true;
                    final_cmp = true;
                } else if (nodes_2_innodes[a] > nodes_2_innodes[b]) {
#ifdef DEBUGPRINT
                    cout << "\t\t\t\tnodes_2_innodes[a] is bigger" << endl;
#endif
                    if (nodes_2_innodes[a].front() < nodes_2_innodes[b].back()) {
                        this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", true);
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
                            this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", true);
                        }
                        b_bigger_entry = true;
                        final_cmp = true;
                    } else if (nodes_2_outnodes[a][edgelabel] > nodes_2_outnodes[b][edgelabel]) {
#ifdef DEBUGPRINT
                        cout << "\t\t\t\tnodes_2_outnodes[a][edgelabel] is bigger" << endl;
#endif
                        if (nodes_2_outnodes[a][edgelabel].front() < nodes_2_outnodes[b][edgelabel].back()) {
                            this -> invalid_wheeler_graph("'in_out_nodelist_repeat_node_sort'!!!", true);
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
                    this -> invalid_wheeler_graph("Wrong!! The vector comparisons in different edge labels have to be in consistant order.", true);
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

void digraph::in_out_nodelist_sort_relabel() {
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
        int prev_num = edges.begin()->get_head_label();

        vector<edge>::iterator edge_itv = edges.begin();
        do{
            if (edge_itv != edges.end()) {
#ifdef DEBUGPRINT
                edge_itv->print_edge();
                cout << "Current edge.get_head_label(): " << edge_itv->get_head_label() << endl;
                cout << "Previous prev_num: " << prev_num << endl;
#endif
                if (prev_num == edge_itv->get_head_label()) {
                    nodes_same_label_set.insert(edge_itv->get_head_name());
                } else if (prev_num != edge_itv->get_head_label()) {
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
                        this -> in_out_nodelist_repeat_node_sort(nodes_same_label_vec, nodes_2_innodes, nodes_2_outnodes, index);
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
                    nodes_same_label_set.insert(edge_itv->get_head_name());
                }
                prev_num = edge_itv->get_head_label();
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
            this -> in_out_nodelist_repeat_node_sort(nodes_same_label_vec, nodes_2_innodes, nodes_2_outnodes, index);
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

