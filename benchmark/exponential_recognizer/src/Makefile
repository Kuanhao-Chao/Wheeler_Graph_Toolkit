# GDIR := ./gclib
# INCDIRS := -I. -I${GDIR}

# OBJS := ${GDIR}/GBase.o ${GDIR}/GArgs.o ${GDIR}/GStr.o ${GDIR}/GSam.o \
 ${GDIR}/gdna.o ${GDIR}/codons.o ${GDIR}/GFastaIndex.o ${GDIR}/GFaSeqGet.o ${GDIR}/gff.o 

output: wg.o graph.o edge.o GBase.o GArgs.o
	g++ -std=c++17 wg.o graph.o edge.o GBase.o GArgs.o -o recognizer_e -lstdc++fs
	rm *.o
	cp recognizer_e ../bin/recognizer_e

wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp -lstdc++fs

# link.o: link.cpp
# 	g++ -std=c++17 -c link.cpp

GBase.o: GBase.cpp
	g++ -std=c++17 -c GBase.cpp -lstdc++fs

GArgs.o: GArgs.cpp
	g++ -std=c++17 -c GArgs.cpp -lstdc++fs

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp -lstdc++fs

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp -lstdc++fs

remove:
	rm -R -- */ || true

clean:
	rm -R -- */ recognizer_e *.o || true
