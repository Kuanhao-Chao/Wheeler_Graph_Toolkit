CXX = g++
CFLAGS = -std=c++17 -lstdc++fs
STATIC_LIB = libz3.a
EXE = recognizer_p

$(EXE): wg.o graph.o edge.o GBase.o GArgs.o print_func.o get_func.o smt.o
	@echo "> Compiling $(EXE)"
	@$(CXX) $^ -o $(EXE) $(CFLAGS) $(STATIC_LIB)
	@cp $(EXE) ../../../bin
	@echo $(EXE) copied to ../../../bin

%.o: %.cpp
	@echo "> Compiling $^"
	@$(CXX) $(CFLAGS) -c $<

remove:
	@rm -R -- */ 

clean:
	@rm -R -- */ $(EXE) *.o
