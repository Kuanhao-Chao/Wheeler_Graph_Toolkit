class TrieNode(object):
    def __init__(self, char):
        self.char = char
        self.children = []
        self.word_end = False

def print_trie(prefix, trie, depth):
    depth += 1
    if depth <= 1:
        print('\n>> Printing Trie...')
    else:
        prefix += trie.char
        print(depth, depth*' ', prefix)

    if len(trie.children) == 0:
        return

    for node in trie.children:
        print_trie(prefix, node, depth)

    return None

def insert(root, word):
    print('\n>> Inserting Word "{}"'.format(word))
    node = root

    for w in word:
        print('checking node = {}'.format(node.char))
        for child in node.children:
            if w == child.char:
                print('"{}" is found!'.format(w))
                node = child
                break
        else:
            # add new node
            print('letter "{}" not in trie, add!'.format(w))
            new_node = TrieNode(w)
            node.children.append(new_node)
            node = new_node

    # mark the node as ended
    node.word_end = True

    print('word "{}" is added!'.format(word))
    return


def delete(root, word):
    print('\n>> Deleting Word "{}"'.format(word))
    if not word:
        return

    # 1. check if existed
    print('>>> Check if the word exists')
    existed, nodes = look_up(root, word)
    if not existed:
        print('word "{}" not found'.format(word))
        return

    # 2. if existed, start deleted
    print('>>> Start deleting')
    nodes[-2].children.remove(nodes[-1])

    for i in range(len(nodes)-2, 0, -1):
        # print('pos = {}, word_end? {}'.format(i, nodes[i].word_end))
        if nodes[i].word_end:
            break
        nodes[i-1].children.remove(nodes[i])

    return

# if word exist: return True and its nodes, else: return False and prefix_nodes
def look_up(root, word: str) -> (bool, list):
    print('\n>> Looking up Word "{}"'.format(word))
    node = root
    prefix = ''
    prefix_nodes = [root]


    for w in word:
        # print('checking node = {}'.format(w))
        for child in node.children:
            if w == child.char:
                prefix += w
                prefix_nodes.append(child)
                node = child
                break
        else:
            # word not found
            print('word "{}" is not found, the nearest prefix is "{}".'.format(word, prefix))

            return False, prefix_nodes

    print('word "{}" is found!'.format(word))
    return True, prefix_nodes


def main():
    # dog, dot, document, do, cat, cap, cape

    # create Trie
    root = TrieNode('*')

    # add dictionary into Trie
    # dictionary = ['dog', 'dot', 'docs', 'do', 'cat', 'cap', 'cape']
    dictionary = ['dog', 'dot', 'docs', 'do', 'doc', 'acvb', 'dddd', 'ofkl']
    for word in dictionary:
        insert(root, word)
    # print Trie
    print_trie('', root, 0)


    # look up word
    look_up(root, 'dog')
    look_up(root, 'dop')
    look_up(root, 'dogs')


    # delete
    delete(root, 'docs')


    # print Trie
    print_trie('', root, 0)



if __name__ == '__main__':
    main()