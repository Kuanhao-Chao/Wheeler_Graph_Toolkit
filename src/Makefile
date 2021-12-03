output: wg.o graph.o edge.o
	g++ -std=c++17 wg.o graph.o edge.o -o recognizer
	rm *.o

wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp

remove:
	rm -R -- */ 

clean:
	rm -R -- */ recognizer