// wg_index.cpp -- a succinct FM-index over a Wheeler graph (C++ port of index/wg_index.py).
//
// Consumes the recognizer's Gagie-Manzini-Siren succinct output (I.txt/O.txt/L.txt: per-node
// in/out-degree bitvectors in Wheeler order + the out-edge BWT label column) and answers pattern
// queries by the SAME GMS backward search the Python WGIndex implements -- bit-for-bit the same
// formulation, but with compact arrays and a block-rank on L so it scales past the Python ceiling.
//
// count(P) -> (lo, hi, n): the half-open range [lo, hi) of Wheeler-order nodes reachable by a walk
// spelling P (from any start), n = hi - lo matches.  Identical to WGIndex.count.
//
// Dependency-free (no z3, no sdsl).  DNA alphabet is <=5 single-char labels; L is one byte per edge.
// For a large alphabet, swap the block-rank for an sdsl wavelet tree on L -- the query logic is
// unchanged.  Build:  make   (g++ -O3 -std=c++17).
//
// CLI:
//   wg_index <out__dir> --query P            print "lo hi n" for one pattern
//   wg_index <out__dir> --queries FILE       one pattern per line -> "pattern lo hi n"
//   wg_index <out__dir> --bench [REPS]       time count() over the queries file (or random walks)
//
// Correctness is gated by index/tests/test_cpp_index.py: this binary's count/range must equal the
// Python WGIndex and the brute oracle on the example, real yeast blocks, and random WGs.

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <chrono>
#include <algorithm>

namespace {

std::string read_file_stripped(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) { fprintf(stderr, "error: cannot open %s\n", path.c_str()); exit(2); }
    std::stringstream ss; ss << f.rdbuf();
    std::string s = ss.str();
    // strip leading/trailing whitespace (the files carry no internal spaces)
    size_t a = 0, b = s.size();
    while (a < b && std::isspace((unsigned char)s[a])) ++a;
    while (b > a && std::isspace((unsigned char)s[b - 1])) --b;
    return s.substr(a, b - a);
}

// Block-rank over the byte string L, mapped to small label ids 0..A-1.
// rank(lab, i) = number of occurrences of label `lab` in L[0:i], for i in 0..E.
struct LabelRank {
    static const int BLOCK = 64;
    int A = 0;                       // alphabet size
    int lab_of[256];                 // byte -> label id (or -1)
    std::vector<unsigned char> id;   // per-edge label id, length E
    std::vector<uint32_t> block;     // (E/BLOCK + 1) * A cumulative counts at block boundaries
    size_t E = 0;

    void build(const std::string& L, const std::vector<unsigned char>& labels) {
        E = L.size();
        for (int i = 0; i < 256; ++i) lab_of[i] = -1;
        A = (int)labels.size();
        for (int i = 0; i < A; ++i) lab_of[labels[i]] = i;
        id.resize(E);
        size_t nblocks = E / BLOCK + 1;
        block.assign((nblocks + 1) * (size_t)A, 0);
        std::vector<uint32_t> run(A, 0);
        for (size_t i = 0; i < E; ++i) {
            if (i % BLOCK == 0) {
                size_t bi = i / BLOCK;
                for (int c = 0; c < A; ++c) block[bi * A + c] = run[c];
            }
            int lid = lab_of[(unsigned char)L[i]];
            id[i] = (unsigned char)lid;        // labels guaranteed present in L
            run[lid]++;
        }
        size_t bi = (E + BLOCK - 1) / BLOCK;   // final boundary (only used when E%BLOCK==0 path skips)
        for (int c = 0; c < A; ++c) block[bi * A + c] = run[c];
    }

    // count of label id `c` in L[0:i]
    uint32_t rank(int c, size_t i) const {
        if (c < 0) return 0;
        size_t bi = i / BLOCK;
        uint32_t r = block[bi * (size_t)A + c];
        size_t start = bi * BLOCK;
        for (size_t j = start; j < i; ++j) r += (id[j] == c);
        return r;
    }
};

struct WGIndex {
    long n = 0;                       // node count
    size_t E = 0;                     // edge count
    std::vector<long> inedge_node;    // length E: head node (1-indexed) of the j-th in-edge
    std::vector<long> out_prefix;     // length n+2: out_prefix[v] = #out-edges of nodes 1..v-1
    std::vector<long> C;              // per label id: # edges with strictly-smaller label
    std::vector<unsigned char> labels;// sorted distinct label bytes
    LabelRank lr;

    void load_dir(const std::string& dir) {
        std::string I = read_file_stripped(dir + "/I.txt");
        std::string O = read_file_stripped(dir + "/O.txt");
        std::string L = read_file_stripped(dir + "/L.txt");
        build(I, O, L);
    }

    void build(const std::string& I, const std::string& O, const std::string& L) {
        n = 0; for (char ch : I) n += (ch == '1');
        E = L.size();
        if (I.size() != (size_t)n + E || O.size() != (size_t)n + E) {
            fprintf(stderr, "error: bad I/O length (n=%ld E=%zu |I|=%zu |O|=%zu)\n",
                    n, E, I.size(), O.size());
            exit(2);
        }
        long onesO = 0; for (char ch : O) onesO += (ch == '1');
        if (onesO != n) { fprintf(stderr, "error: I and O mark different node counts\n"); exit(2); }

        // inedge_node[z] = (#1s seen so far)+1  at the z-th '0' of I
        inedge_node.assign(E, 0);
        { long ones = 0; size_t z = 0;
          for (char ch : I) {
              if (ch == '1') ones += 1;
              else { inedge_node[z++] = ones + 1; }
          } }
        // out_prefix[ones+1] = z  at each '1' of O ; out_prefix[1] = 0
        out_prefix.assign(n + 2, 0);
        { long ones = 0; long z = 0;
          for (char ch : O) {
              if (ch == '1') { ones += 1; out_prefix[ones + 1] = z; }
              else z += 1;
          } }
        out_prefix[1] = 0;

        // labels = sorted distinct bytes of L ; C[c] = cumulative count of strictly-smaller labels
        std::vector<long> cnt(256, 0);
        for (char ch : L) cnt[(unsigned char)ch]++;
        labels.clear();
        for (int b = 0; b < 256; ++b) if (cnt[b]) labels.push_back((unsigned char)b);
        C.assign(labels.size(), 0);
        long running = 0;
        for (size_t i = 0; i < labels.size(); ++i) { C[i] = running; running += cnt[labels[i]]; }
        lr.build(L, labels);
    }

    int label_id(char c) const { return lr.lab_of[(unsigned char)c]; }

    // [lo,hi) node range, label c -> head range reachable by a c-edge from a tail in [lo,hi)
    std::pair<long,long> step(long lo, long hi, char c) const {
        int cid = label_id(c);
        if (cid < 0 || lo >= hi) return {lo, lo};
        long out_lo = out_prefix[lo];
        long out_hi = out_prefix[hi];
        uint32_t r_lo = lr.rank(cid, (size_t)out_lo);
        uint32_t r_hi = lr.rank(cid, (size_t)out_hi);
        if (r_lo == r_hi) return {lo, lo};
        long in_lo = C[cid] + (long)r_lo;
        long in_hi = C[cid] + (long)r_hi;
        long head_lo = inedge_node[in_lo];
        long head_hi = inedge_node[in_hi - 1];
        return {head_lo, head_hi + 1};
    }

    // backward search -> (lo, hi, n_matches)
    void count(const std::string& P, long& lo_out, long& hi_out, long& n_out) const {
        long lo = 1, hi = n + 1;
        for (char c : P) {
            auto pr = step(lo, hi, c);
            lo = pr.first; hi = pr.second;
            if (lo >= hi) { lo_out = lo; hi_out = lo; n_out = 0; return; }
        }
        lo_out = lo; hi_out = hi; n_out = hi - lo;
    }
};

int usage() {
    fprintf(stderr,
        "usage: wg_index <out__dir> --query P\n"
        "       wg_index <out__dir> --queries FILE\n"
        "       wg_index <out__dir> --bench [REPS]\n");
    return 2;
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 3) return usage();
    std::string dir = argv[1];
    std::string mode = argv[2];

    WGIndex idx;
    idx.load_dir(dir);

    if (mode == "--query") {
        if (argc < 4) return usage();
        std::string P = argv[3];
        long lo, hi, n; idx.count(P, lo, hi, n);
        printf("%ld %ld %ld\n", lo, hi, n);
        return 0;
    }
    if (mode == "--queries") {
        if (argc < 4) return usage();
        std::ifstream f(argv[3]);
        if (!f) { fprintf(stderr, "error: cannot open %s\n", argv[3]); return 2; }
        std::string line;
        while (std::getline(f, line)) {
            while (!line.empty() && std::isspace((unsigned char)line.back())) line.pop_back();
            if (line.empty()) continue;
            long lo, hi, n; idx.count(line, lo, hi, n);
            printf("%s %ld %ld %ld\n", line.c_str(), lo, hi, n);
        }
        return 0;
    }
    if (mode == "--bench") {
        int reps = (argc >= 4) ? atoi(argv[3]) : 100000;
        // generate random length-6 patterns over the alphabet; time count()
        std::vector<std::string> pats;
        std::string alpha((char*)idx.labels.data(), idx.labels.size());
        if (alpha.empty()) alpha = "A";
        unsigned long seed = 0x9e3779b97f4a7c15UL;
        auto nxt = [&]() { seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17; return seed; };
        for (int i = 0; i < 1000; ++i) {
            std::string p; int len = 1 + (int)(nxt() % 6);
            for (int j = 0; j < len; ++j) p.push_back(alpha[nxt() % alpha.size()]);
            pats.push_back(p);
        }
        long sink = 0;
        auto t0 = std::chrono::high_resolution_clock::now();
        for (int r = 0; r < reps; ++r) {
            const std::string& p = pats[r % pats.size()];
            long lo, hi, n; idx.count(p, lo, hi, n); sink += n;
        }
        auto t1 = std::chrono::high_resolution_clock::now();
        double us = std::chrono::duration<double, std::micro>(t1 - t0).count();
        printf("nodes=%ld edges=%zu reps=%d total_us=%.1f us_per_query=%.4f sink=%ld\n",
               idx.n, idx.E, reps, us, us / reps, sink);
        return 0;
    }
    return usage();
}
