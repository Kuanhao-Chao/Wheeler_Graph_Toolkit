# GDIR := ./gclib
# INCDIRS := -I. -I${GDIR}

# OBJS := ${GDIR}/GBase.o ${GDIR}/GArgs.o ${GDIR}/GStr.o ${GDIR}/GSam.o \
 ${GDIR}/gdna.o ${GDIR}/codons.o ${GDIR}/GFastaIndex.o ${GDIR}/GFaSeqGet.o ${GDIR}/gff.o 

output: dot_2_bitv.o graph.o edge.o wg.o
	g++ -std=c++17 dot_2_bitv.o graph.o edge.o -o dot_2_bitv
	g++ -std=c++17 wg.o  -o wg
	rm *.o

wg.o: wg.cpp
	g++ -std=c++17 -c wg.cpp

# link.o: link.cpp
# 	g++ -std=c++17 -c link.cpp

dot_2_bitv.o: dot_2_bitv.cpp
	g++ -std=c++17 -c dot_2_bitv.cpp

graph.o: graph.cpp
	g++ -std=c++17 -c graph.cpp

edge.o: edge.cpp
	g++ -std=c++17 -c edge.cpp

remove:
	rm -R -- */ 

clean:
	rm -R dot_2_bitv *.o
