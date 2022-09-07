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
        
        added_tail_node.print_node()
        added_head_node.print_node()
        for node in self.all_nodes:
            print("added_head_node.nodeorder: ", added_head_node.nodeorder)
            if node.nodeorder >= added_head_node.nodeorder:
                node.nodeorder += 1        
        self.all_nodes.insert(added_head_node.nodeorder-1, added_head_node)
        self.column_nodes[added_head_node.nodecolid][added_head_node.out_edgelabel].insert(0, added_head_node)
        self.node_num += 1

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


        added_head_node.add_parent(added_tail_node)
        added_tail_node.add_child(added_head_node)
        print("XXXXXXXXXXXXXXXXXXXXXXXX")
        print("self.edgelabel_num: ", self.edgelabel_num)
        added_head_node.print_node()
        self.print_all_nodes()


    def finding_head(self, row_idx, tail_node, tail_seq_idx, tail_seq, head_node, head_seq_idx, head_seq):
        ##########################
        # Finding the head!!
        ##########################
        if len(self.column_nodes[head_seq_idx][head_seq]) == 0:
            print("#############################")
            print("### Finding head now. No this seq in this column => creating new node!!")
            print("#############################")
            # Find possible smallest range.
            # Become the first node of that group
            # print("tail_node.out_edgelabel: ", tail_node.out_edgelabel)
            # print("self.edgelabel_num[tail_node.out_edgelabel]: ", self.edgelabel_num[tail_node.out_edgelabel])
            
            head_node = n.node("S"+str(row_idx)+str(head_seq_idx), tail_node.nodeorder, head_seq, head_seq_idx)
            self.add_head_node(tail_node, head_node)
            self.print_all_nodes()
        
        # 'column_nodes' is in the sorted order.
        elif len(self.column_nodes[head_seq_idx][head_seq]) != 0:
            print("#############################")
            print("### Condition 4 : Finding head now. There are seqs here => deciding whether to create new node!!")
            print("#############################")

            print(">> Incoming edge label: ", tail_seq)

            if self.edgelabel_prev_dict[tail_seq] is None:
                idx_s = 0
            else:
                idx_s =  self.edgelabel_num[self.edgelabel_prev_dict[tail_seq]]
            idx_e = self.edgelabel_num[tail_seq]
            print("self.edgelabel_num: ", self.edgelabel_num)
            print("self.edgelabel_num[self.edgelabel_prev_dict[tail_seq]]: ",idx_s)
            print("self.edgelabel_num[tail_seq]: ", idx_e)

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
                    cmp_tail = cmp_node.parents[0].nodeorder
                cmp_head = cmp_node.nodeorder

                # I find a node! I can reuse the created node!!!
                if cmp_node.nodecolid == head_seq_idx:
                    head_node = self.all_nodes[idx_s]

                # I need to create a new node!!
                else:
                    if tail_node.nodeorder <= cmp_tail:
                        head_node = n.node("S"+str(row_idx)+str(head_seq_idx), cmp_head, tail_seq, head_seq_idx)
                        self.add_head_node(tail_node, head_node)
                    else:
                        head_node = n.node("S"+str(row_idx)+str(head_seq_idx), cmp_head+1, tail_seq, head_seq_idx)
                        self.add_head_node(tail_node, head_node)


            # The condition of more than 1 edges in that group!!
            else:
                for nidx in range(idx_s, idx_e-1):
                    # Check WG property & the node needs to be in the same column
                    self.print_all_nodes()
                    # print("nidx: ", nidx)
                    # print("self.all_nodes: ", self.all_nodes)
                    left_cmp_tail = 0
                    right_cmp_tail = 0

                    left_cmp_head = 0
                    right_cmp_head = 0
                    left_node = self.all_nodes[nidx]
                    right_node = self.all_nodes[nidx+1]

                    if len(left_node.parents) == 0:
                        left_cmp_tail = 0
                    else:
                        left_cmp_tail = left_node.parents[0].nodeorder
                    left_cmp_head = left_node.nodeorder

                    if len(right_node.parents) == 0:
                        right_cmp_tail = 0
                    else:
                        right_cmp_tail = right_node.parents[0].nodeorder
                    right_cmp_head = right_node.nodeorder
                    left_node.print_node()
                    right_node.print_node()


                    print("left_cmp_tail :", left_cmp_tail, ";  tail_node.nodeorder: ", tail_node.nodeorder, ";  right_cmp_tail: ", right_cmp_tail)
                    print("left_node colidx :", left_node.nodecolid, ";  head_node.nodeorder: ", head_seq_idx, ";  right_node colidx : ", right_node.nodecolid)
                    if tail_node.nodeorder >= left_cmp_tail and tail_node.nodeorder <= right_cmp_tail:
                        # I find a node! I can reuse the created node!!!
                        if left_node.nodecolid == head_seq_idx:
                            head_node = self.all_nodes[nidx]
                            print("left node!!")
                            break
                        # I find a node! I can reuse the created node!!!
                        elif right_node.nodecolid == head_seq_idx:
                            head_node = self.all_nodes[nidx+1]
                            print("right node!!")
                            break

                        # I need to create a new node!!
                        else:
                            head_node = n.node("S"+str(row_idx)+str(head_seq_idx), nidx+1, head_seq, head_seq_idx)
                            self.add_head_node(tail_node, head_node)
                            print("new node!!")
                            break
                    else:
                        print("NANI!!!")




    def print_all_nodes(self):
        for node in self.all_nodes:
            node.print_node()

    # def add_edge(n1, n2):

