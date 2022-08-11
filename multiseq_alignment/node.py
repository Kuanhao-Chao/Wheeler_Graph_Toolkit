class node:
    def __init__(self, nodeID, nodeLabel):
        self.nodeid = nodeID
        self.nodelabel = nodeLabel
        self.parents = []
        self.children = []
        print("Initializing a node: ", self.nodeid, self.nodelabel)
    
    def add_parent(self, parent):
        self.parents.append(parent)

    def add_child(self, child):
        self.children.append(child)

    # def merge_node(self, node):
    #     # check children
    #     for c in self.children:
    #         print(c)
    #     # check parents
    #     for c in self.children:
    #         print(c)
        