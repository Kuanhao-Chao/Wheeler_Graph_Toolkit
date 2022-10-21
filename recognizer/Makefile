CXX = g++
CFLAGS = -std=c++17 -pthread -O3
SRCDIR = ./src
Z3DIR = ./z3
SRC = $(shell find $(SRCDIR) -name '*.cpp')
OBJ = $(SRC:%.cpp=%.o)
STATIC_LIB = $(Z3DIR)/lib/libz3.a
INCLUDE=-I $(Z3DIR)/include/
EXE = recognizer

.PHONY: z3 clean

$(EXE): $(OBJ)
	@echo "> Compiling $(EXE)"
	@$(CXX) $^ -o $(EXE) $(CFLAGS) $(STATIC_LIB) $(INCLUDE) -w
	@mkdir -p ./bin; cp $(EXE) ./bin
	@rm $(EXE)
	@echo $(EXE) copied to ./bin

%.o: %.cpp
	@echo "> Compiling $^"
	@$(CXX) $(CFLAGS) -c $(INCLUDE) $< -o $@

z3:
	@cd $(Z3DIR); python3 scripts/mk_make.py -p ../ --staticlib
	@cd $(Z3DIR)/build; make -j4; sudo make install

clean:
	@rm ./bin/$(EXE) $(OBJ)

