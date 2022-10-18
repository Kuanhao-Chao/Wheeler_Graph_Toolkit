CXX = g++
CFLAGS = -std=c++17 -lstdc++fs -pthread -O3
STATIC_LIB = libz3.a
EXE = recognizer
INCLUDE=-I /home/kh.chao/miniconda3/include/

$(EXE): wg.o graph.o edge.o GBase.o GArgs.o print_func.o get_func.o smt.o
	@echo "> Compiling $(EXE)"
	@$(CXX) $^ -o $(EXE) $(CFLAGS) $(STATIC_LIB) $(INCLUDE) -w
	@cp $(EXE) ../../../bin
	@echo $(EXE) copied to ../bin

%.o: %.cpp
	@echo "> Compiling $^"
	@$(CXX) $(CFLAGS) -c $(INCLUDE)  $<

remove:
	@rm -R -- */ 

clean:
	@rm -R -- */ $(EXE) *.o
