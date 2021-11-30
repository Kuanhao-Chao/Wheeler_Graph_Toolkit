output: wg.o graph.o edge.o
	g++ -std=c++17 wg.o graph.o edge.o -o wg

wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp

clean:
	rm *.o wg