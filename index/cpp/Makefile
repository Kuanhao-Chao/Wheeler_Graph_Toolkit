# Dependency-free succinct Wheeler-graph FM-index (no z3, no sdsl).
# Mirrors recognizer/Makefile's toolchain (g++ -O3 -std=c++17).
CXX    = g++
CFLAGS = -std=c++17 -O3 -Wall

all: wg_index wg_suffix

wg_index: wg_index.cpp
	$(CXX) $(CFLAGS) wg_index.cpp -o wg_index

wg_suffix: wg_suffix.cpp
	$(CXX) $(CFLAGS) wg_suffix.cpp -o wg_suffix

clean:
	rm -f wg_index wg_suffix

.PHONY: all clean
