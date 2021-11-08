#include <iostream>
#include <queue>

using namespace std;

int main (){
    queue<int> myQ;
    for (int i=0; i<10; i++) {
        cout << "enqueuing " << i << endl;
        myQ.push(i);
    }
  return 0;
}