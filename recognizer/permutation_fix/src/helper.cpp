#ifndef __HELPER_CPP__
#define __HELPER_CPP__
#pragma once 

#include <vector>
#include <assert.h>
using namespace std;
void reorder_node_vec(vector<int>& vA, vector<int>& vOrder) {   
    assert(vA.size() == vOrder.size());

    // for all elements to put in place
    for( int i = 0; i < vA.size() - 1; ++i )
    { 
        // while the element i is not yet in place 
        while( i != vOrder[i] )
        {
            // swap it with the element at its final place
            int alt = vOrder[i];
            swap( vA[i], vA[alt] );
            swap( vOrder[i], vOrder[alt] );
        }
    }
}
#endif