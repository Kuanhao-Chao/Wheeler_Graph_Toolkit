# Dependency-free succinct Wheeler-graph FM-index (no z3, no sdsl).
# Mirrors recognizer/Makefile's toolchain (g++ -O3 -std=c++17).
CXX    = g++
CFLAGS = -std=c++17 -O3 -Wall
EXE    = wg_index

all: $(EXE)

$(EXE): wg_index.cpp
	$(CXX) $(CFLAGS) wg_index.cpp -o $(EXE)

clean:
	rm -f $(EXE)

.PHONY: all clean
