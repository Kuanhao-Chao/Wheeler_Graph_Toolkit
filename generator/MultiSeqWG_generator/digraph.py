import node as n
class digraph:
    def __init__(self, col_num):
        self.node_num = 0
        self.col_num = col_num
        self.all_nodes = [None]*col_num
        self.column_nodes = {}
        self.edgelabel_num = {}
        self.edgelabel_num["$"] = 0
        self.edgelabel_num["A"] = 0
        self.edgelabel_num["C"] = 0
        self.edgelabel_num["G"] = 0
        self.edgelabel_num["T"] = 0
        self.edgelabel_prev_dict = {"A": "$", "C":"A", "G":"C", "T":"G"} 
    
    def col_initialize(self, col_idx):
        self.column_nodes[col_idx] = {}
        self.column_nodes[col_idx]["A"] = []
        self.column_nodes[col_idx]["C"] = []
        self.column_nodes[col_idx]["G"] = []
        self.column_nodes[col_idx]["T"] = []

    def add_node_firstSeq(self, prev_node, curr_node):
        self.column_nodes[curr_node.nodecolid][curr_node.out_edgelabel].append(curr_node)
        self.all_nodes[curr_node.nodeorder-1] = curr_node
        self.node_num += 1

        # if (curr_node.nodecolid == 0):
        #     self.edgelabel_num["$"] += 1
        #     self.edgelabel_num["A"] += 1
        #     self.edgelabel_num["C"] += 1
        #     self.edgelabel_num["G"] += 1
        #     self.edgelabel_num["T"] += 1
        in_edge_key = ""
        if prev_node is None:
            in_edge_key = "$"
        else:
            in_edge_key = prev_node.out_edgelabel
        
        for key, _ in self.edgelabel_num.items():
            if key >= in_edge_key:
                self.edgelabel_num[key] += 1


    def update_all_nodes(self):
        del self.all_nodes[self.node_num:]

    def add_root_node(self, added_root_node):
        # update all the node with ordering bigger or equal to the 'new_node_order'
        for node in self.all_nodes:
            print("added_root_node.nodeorder: ", added_root_node.nodeorder)
            if node.nodeorder >= added_root_node.nodeorder:
                node.nodeorder += 1        
        self.all_nodes.insert(added_root_node.nodeorder-1, added_root_node)
        self.column_nodes[added_root_node.nodecolid][added_root_node.out_edgelabel].insert(0, added_root_node)
        self.node_num += 1

        for key, _ in self.edgelabel_num.items():
            if key >= "$":
                self.edgelabel_num[key] += 1

    def add_head_node(self, added_tail_node, added_head_node):
        for node in self.all_nodes:
            print("added_head_node.nodeorder: ", added_head_node.nodeorder)
            if node.nodeorder >= added_head_node.nodeorder:
                node.nodeorder += 1        
        self.all_nodes.insert(added_head_node.nodeorder-1, added_head_node)
        self.column_nodes[added_head_node.nodecolid][added_head_node.out_edgelabel].insert(0, added_head_node)
        self.node_num += 1
        print("Later ~~ added_head_node.nodeorder: ", added_head_node.nodeorder)

        # if (added_head_node.nodecolid == 0):
        #     self.edgelabel_num["$"] += 1
        #     self.edgelabel_num["A"] += 1
        #     self.edgelabel_num["C"] += 1
        #     self.edgelabel_num["G"] += 1
        #     self.edgelabel_num["T"] += 1

        in_edge_key = ""
        if added_tail_node is None:
            in_edge_key = "$"
        else:
            in_edge_key = added_tail_node.out_edgelabel
        
        for key, _ in self.edgelabel_num.items():
            if key >= in_edge_key:
                self.edgelabel_num[key] += 1


    def connect_head_tail(self, added_tail_node, added_head_node):
        added_head_node.add_parent(added_tail_node)
        added_tail_node.add_child(added_head_node)
        print("XXXXXXXXXXXXXXXXXXXXXXXX")
        print("self.edgelabel_num: ", self.edgelabel_num)

    def finding_head(self, row_idx, tail_seq, tail_seq_idx, tail_node, head_seq, head_seq_idx, head_node):
        print("\n\n >> Tail now!!!")
        tail_node.print_node()
        print(" >> Head now!!!")
        if head_node != None:
            head_node.print_node()
        ##########################
        # Finding the head!!
        ##########################
        print("#############################")
        print("### Condition 4 : Finding head now. There are seqs here => deciding whether to create new node!!")
        print("#############################")

        print(">> Incoming edge label: ", tail_seq)

        if self.edgelabel_prev_dict[tail_seq] is None:
            idx_s = 0
        else:
            idx_s =  self.edgelabel_num[self.edgelabel_prev_dict[tail_seq]]
        idx_e = self.edgelabel_num[tail_seq]
        print("\tself.edgelabel_num: ", self.edgelabel_num)
        print("\tStart range: ",idx_s)
        print("\tEnd range  : ", idx_e)

        # Check the edge with the same edge label. Find the "compactable node" with the "smallest" node_ordering.
        # for node in self.all_nodes[ idx_s:idx_e ]:

        # The condition that only 1 edge in that group!!
        if (idx_e-idx_s == 1):
            cmp_tail=0
            cmp_head=0
            cmp_node = self.all_nodes[idx_s]
            if len(cmp_node.parents) == 0:
                cmp_tail = 0
            else:
                # cmp_tail = cmp_node.parents[0].nodeorder
                cmp_tails = [parent.nodeorder for parent in cmp_node.parents]
                # left_cmp_tail = max(left_cmp_tails)


            min_cmp_tail = min(cmp_tails)
            max_cmp_tail = max(cmp_tails)

            print("min_cmp_tail: ", min_cmp_tail, ";  max_cmp_tail: ", max_cmp_tail)
            # I find a node! I can reuse the created node!!!
            if cmp_node.nodecolid == head_seq_idx:
                head_node = self.all_nodes[idx_s]

            # I need to create a new node!!
            else:
                # cmp_tails
                if tail_node.nodeorder <= min_cmp_tail:
                    head_node = n.node("S_"+str(row_idx)+"_"+str(head_seq_idx), cmp_node.nodeorder, tail_seq, head_seq_idx)
                    self.add_head_node(tail_node, head_node)
                elif tail_node.nodeorder > min_cmp_tail and tail_node.nodeorder < max_cmp_tail:
                    print("NNNNNNNNNNNNNAAAAAAAAAAAA")
                elif tail_node.nodeorder >= max_cmp_tail:
                    head_node = n.node("S_"+str(row_idx)+"_"+str(head_seq_idx), cmp_node.nodeorder+1, tail_seq, head_seq_idx)
                    self.add_head_node(tail_node, head_node)

        # The condition of more than 1 edges in that group!!
        else:
            for nidx in range(idx_s, idx_e-1):
                print(">> Round ", nidx-idx_s+1)
                # Check WG property & the node needs to be in the same column
                # self.print_all_nodes()
                # print("nidx: ", nidx)
                # print("self.all_nodes: ", self.all_nodes)
                left_cmp_tail = 0
                right_cmp_tail = 0

                left_head_idx = nidx
                right_head_idx = nidx+1

                print(">> left_head_idx: ", left_head_idx)
                print(">> right_head_idx: ", right_head_idx)

                left_head_node = self.all_nodes[left_head_idx]
                right_head_node = self.all_nodes[right_head_idx]

                left_head_node.print_node()
                right_head_node.print_node()

                if len(left_head_node.parents) == 0:
                    left_cmp_tail = 0
                else:
                    # left_cmp_tail = left_head_node.parents[0].nodeorder
                    left_cmp_tails = [parent.nodeorder for parent in left_head_node.parents]
                    print("\t>> left_cmp_tails: ", left_cmp_tails)
                    left_cmp_tail = max(left_cmp_tails)

                if len(right_head_node.parents) == 0:
                    right_cmp_tail = 0
                else:
                    # right_cmp_tail = right_head_node.parents[0].nodeorder
                    right_cmp_tails = [parent.nodeorder for parent in right_head_node.parents]
                    print("\t>> right_cmp_tails: ", right_cmp_tails)
                    right_cmp_tail = min(right_cmp_tails)
                print("\t>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
                print("\t>> Left node to compare!!!")
                left_head_node.print_node()

                print("\t>> Right node to compare!!!")
                right_head_node.print_node()


                print("left_cmp_tail :", left_cmp_tail, ";  \ttail_node.nodeorder: ", tail_node.nodeorder, ";  \tright_cmp_tail: ", right_cmp_tail)
                print("left_head_node colidx :", left_head_node.nodecolid, ";  \thead_node column: ", head_seq_idx, ";  \tright_head_node colidx : ", right_head_node.nodecolid)
                print("\t>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")

                if tail_node.nodeorder < left_cmp_tail:
                    if left_head_node.nodecolid == head_seq_idx:
                        head_node = self.all_nodes[left_head_idx]
                        print("\t@@@ left node!! head ordering: ", head_node.nodeorder)
                    else:
                        # Create a new node.
                        head_node = n.node("S_"+str(row_idx)+"_"+str(head_seq_idx), left_head_node.nodeorder, head_seq, head_seq_idx)
                        # self.add_head_node(tail_node, head_node)
                        print("\t@@@ new node!! head ordering: ", head_node.nodeorder)
                        self.add_head_node(tail_node, head_node)
                    break
                elif tail_node.nodeorder >= left_cmp_tail and tail_node.nodeorder <= right_cmp_tail:
                    # I find a node! I can reuse the created node!!!
                    if left_head_node.nodecolid == head_seq_idx:
                        head_node = self.all_nodes[left_head_idx]
                        print("\t@@@ left node!! head ordering: ", head_node.nodeorder)
                        break
                    # I find a node! I can reuse the created node!!!
                    elif right_head_node.nodecolid == head_seq_idx:
                        head_node = self.all_nodes[right_head_idx]
                        print("\t@@@ right node!! head ordering: ", head_node.nodeorder)
                        break

                    # I need to create a new node!!
                    else:
                        head_node = n.node("S_"+str(row_idx)+"_"+str(head_seq_idx), right_head_node.nodeorder, head_seq, head_seq_idx)
                        print("\t@@@ >> new node!! head ordering: ", right_head_node.nodeorder)
                        self.add_head_node(tail_node, head_node)
                        print("\t@@@ >> new node!! head ordering: ", head_node.nodeorder)
                        break
                elif tail_node.nodeorder > right_cmp_tail and left_head_idx == idx_e-2: 
                    if right_head_node.nodecolid == head_seq_idx:
                        head_node = self.all_nodes[right_head_idx]
                        print("\t@@@ right node!! head ordering: ", head_node.nodeorder)
                    else:
                        head_node = n.node("S_"+str(row_idx)+"_"+str(head_seq_idx), right_head_node.nodeorder+1, head_seq, head_seq_idx)
                        self.add_head_node(tail_node, head_node)
                        print("\t@@@ new node!! head ordering: ", head_node.nodeorder+1)
                    break
                else:
                    print("\t@@@ NANI!!!")
                print("\n\n")
            print("\n\n")
        self.print_all_nodes()

        self.connect_head_tail(tail_node, head_node)
        print("VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")
        print("VVVVVVVVVVVVVVVVVV  Done!!! VVVVVVVVVVVVVVVVVV")
        print("VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")
        self.print_all_nodes()
        print("VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")
        print("Found head_node: ")
        head_node.print_node()
        print("\n\n\n")
        return tail_seq, tail_seq_idx, tail_node, head_seq, head_seq_idx, head_node


    def print_all_nodes(self):
        for node in self.all_nodes:
            node.print_node()

    # def add_edge(n1, n2):

