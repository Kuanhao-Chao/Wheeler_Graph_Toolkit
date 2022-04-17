output: wg.o graph.o edge.o GBase.o GArgs.o
	g++ -std=c++17 wg.o graph.o edge.o GBase.o GArgs.o -o recognizer
	rm *.o
	
wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp

GBase.o: GBase.cpp
	g++ -std=c++17 -c GBase.cpp

GArgs.o: GArgs.cpp
	g++ -std=c++17 -c GArgs.cpp

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp

remove:
	rm -R -- */ 

clean:
	rm -R -- */ recognizer
