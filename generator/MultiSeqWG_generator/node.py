class node:
    def __init__(self, nodeID, nodeorder, out_edgelabel, nodeColid):
        self.nodeid = nodeID # S+ID
        self.nodeorder = nodeorder # WG ordering
        self.out_edgelabel = out_edgelabel # Outgoing edge labels 
        self.nodecolid = nodeColid # The column ID where the node is at.
        self.parents = []
        self.children = []
        print("Initializing a node: ", self.nodeid, self.nodeorder)
    
    def add_parent(self, parent):
        if parent not in self.parents:
            self.parents.append(parent)
        else:
            print("The parent was added before!")

    def add_child(self, child):
        if child not in self.children:
            self.children.append(child)
        else:
            print("The child was added before!")


    def set_nodeorder(self, nodeOrder):
        self.nodeorder = nodeOrder