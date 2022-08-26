output: wg.o graph.o edge.o GBase.o GArgs.o print_func.o get_func.o
	g++ -std=c++17 wg.o graph.o edge.o GBase.o GArgs.o print_func.o get_func.o -o recognizer_p
	rm *.o
	rm ../../../bin/recognizer_p
	cp recognizer_p ../../../bin
	
wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp

GBase.o: GBase.cpp
	g++ -std=c++17 -c GBase.cpp

GArgs.o: GArgs.cpp
	g++ -std=c++17 -c GArgs.cpp

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp

get_func.o: get_func.cpp
	g++ -std=c++17 -c get_func.cpp

print_func.o: print_func.cpp
	g++ -std=c++17 -c print_func.cpp

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp

remove:
	rm -R -- */ || true

clean:
	rm -R -- */ recognizer_p || true
