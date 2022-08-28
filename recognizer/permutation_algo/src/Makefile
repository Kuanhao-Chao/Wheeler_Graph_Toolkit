output: wg.o graph.o edge.o GBase.o GArgs.o print_func.o get_func.o
	g++ -std=c++17 wg.o graph.o edge.o GBase.o GArgs.o print_func.o get_func.o -o recognizer_p -lstdc++fs
	rm *.o
	rm ../../../bin/recognizer_p
	cp recognizer_p ../../../bin

wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp -lstdc++fs

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp -lstdc++fs

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp -lstdc++fs

GBase.o: GBase.cpp
	g++ -std=c++17 -c GBase.cpp -lstdc++fs

GArgs.o: GArgs.cpp
	g++ -std=c++17 -c GArgs.cpp -lstdc++fs

get_func.o: get_func.cpp
	g++ -std=c++17 -c get_func.cpp -lstdc++fs

print_func.o: print_func.cpp
	g++ -std=c++17 -c print_func.cpp -lstdc++fs

remove:
	rm -R -- */ 

clean:
	rm -R -- */ recognizer
