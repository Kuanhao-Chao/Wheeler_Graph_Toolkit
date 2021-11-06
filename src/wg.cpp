#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <graphviz>


using namespace std;

// class node {
//     public:
//         node(int)
//     private:

// }

class edge {
    private:
        char label;
        int* head;
        int* tail;

    public:
        edge(string label, int* head, int* tail) {
            label = label;
            head = head;
            tail = tail;
        }

        void print_edge() {
            // cout << "label: " << label << endl;
            cout << " head: " << head << " tail: " << tail << endl;
        }

        void set_node(int a, int b) {
            *head = a;
            *tail = b;
        }
};

int main(int argc, char* argv[]) {
    (void)argc;
    ifstream ifile_fasta(argv[1]);

    int* node1;
    int* node2;
    *node1 = 10;

    cout << "node1: " << node1 << endl;
    cout << "*node1: " << *node1 << endl;

    edge e1 = edge("a", node1, node2);

    // edge e1 = edge("a", node1, node2);

    e1.print_edge();
    e1.set_node(10, 20);
    e1.print_edge();

    return 0;
}