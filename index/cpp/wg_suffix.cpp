// wg_suffix.cpp -- a dependency-free C++ port of index/suffix_index.py (the tagged suffix Wheeler
// pangenome index). Native species+position resolution, exact multi-hit locate.
//
// Builds the multi-string BWT of a MAF block's first-a / ungapped / cap-l rows with DISTINCT
// per-document separators (sep_i = i < DNA: A=a..T=a+3) and a cyclic-rotation suffix array, exactly as
// the Python SuffixIndex. backward_search is forward; locate -> (record_idx, ungapped_pos), or genomic
// (species, src, gstart, gend, strand) when a coords.json is given. No sdsl/z3 (sdsl wavelet tree is a
// drop-in for a large alphabet; the query logic is unchanged).
//
// Verified C++ == Python SuffixIndex == brute oracle by index/tests/test_cpp_suffix.py.
//
//   wg_suffix <block.fa> --a A --l L --s S [--coords c.json]
//             --locate P | --queries FILE | --bench [REPS] | --info

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <chrono>
#include <set>

namespace {

// ---------------------------------------------------------------- FASTA + ungap/cap (== faithful._ungap_cap)
std::vector<std::pair<std::string,std::string>> read_fasta(const std::string& path) {
    std::ifstream f(path);
    if (!f) { fprintf(stderr, "error: cannot open %s\n", path.c_str()); exit(2); }
    std::vector<std::pair<std::string,std::string>> recs;
    std::string line, id, seq;
    bool have = false;
    while (std::getline(f, line)) {
        while (!line.empty() && (line.back()=='\n'||line.back()=='\r')) line.pop_back();
        if (!line.empty() && line[0]=='>') {
            if (have) recs.push_back({id, seq});
            id = line.substr(1); seq.clear(); have = true;
        } else if (!line.empty()) seq += line;
    }
    if (have) recs.push_back({id, seq});
    return recs;
}

std::string ungap_cap(const std::string& s, long l) {
    std::string u;
    for (char c : s) if (c != '-') u.push_back((char)std::toupper((unsigned char)c));
    if (l >= 0 && (size_t)l < u.size()) u.resize(l);
    return u;
}

// ---------------------------------------------------------------- the index
struct SuffixIndex {
    int a = 0, sigma = 0;
    std::vector<int> T, doc, doc_start, SA, BWT, DOC, C;
    long n = 0, r = 0, s = 8;
    std::vector<char> sampled;
    std::vector<long> sa_at;                 // sa_at[i] = SA[i] if sampled else -1
    std::vector<std::vector<long>> rankpre;  // block-rank: rankpre[c][i/B]; + scan (BLOCK=64)
    static const int BLOCK = 64;
    int dna_code[256];                       // 'A'->a ... 'T'->a+3, else -1

    void build(const std::vector<std::string>& seqs, long l, long s_) {
        s = s_ < 1 ? 1 : s_;
        a = (int)seqs.size();
        sigma = a + 4;
        for (int i = 0; i < 256; ++i) dna_code[i] = -1;
        dna_code[(int)'A'] = a; dna_code[(int)'C'] = a+1; dna_code[(int)'G'] = a+2; dna_code[(int)'T'] = a+3;
        // build T (distinct separators), doc, doc_start
        for (int i = 0; i < a; ++i) {
            doc_start.push_back((int)T.size());
            for (char ch : seqs[i]) { T.push_back(dna_code[(unsigned char)ch]); doc.push_back(i); }
            T.push_back(i); doc.push_back(i);      // separator sep_i = i
        }
        n = (long)T.size();
        build_sa();
        BWT.resize(n);
        for (long i = 0; i < n; ++i) BWT[i] = T[(SA[i]-1+n) % n];
        // C[]
        std::vector<long> cnt(sigma, 0);
        for (int x : T) cnt[x]++;
        C.assign(sigma, 0);
        for (int c = 1; c < sigma; ++c) C[c] = C[c-1] + cnt[c-1];
        // block-rank over BWT
        long nb = n / BLOCK + 1;
        rankpre.assign(sigma, std::vector<long>(nb + 1, 0));
        std::vector<long> run(sigma, 0);
        for (long i = 0; i < n; ++i) {
            if (i % BLOCK == 0) for (int c = 0; c < sigma; ++c) rankpre[c][i/BLOCK] = run[c];
            run[BWT[i]]++;
        }
        for (int c = 0; c < sigma; ++c) rankpre[c][(n + BLOCK - 1)/BLOCK] = run[c];
        // runs, DOC, sampled SA (rate mode -- matches the Python default)
        r = n ? 1 : 0;
        for (long i = 1; i < n; ++i) if (BWT[i] != BWT[i-1]) r++;
        DOC.resize(n); sampled.assign(n, 0); sa_at.assign(n, -1);
        for (long i = 0; i < n; ++i) {
            DOC[i] = doc[SA[i]];
            if (SA[i] % s == 0) { sampled[i] = 1; sa_at[i] = SA[i]; }
        }
    }

    void build_sa() {
        SA.resize(n);
        std::vector<long> rank(n), tmp(n);
        for (long i = 0; i < n; ++i) { SA[i] = (int)i; rank[i] = T[i]; }
        for (long k = 1; ; k <<= 1) {
            auto key2 = [&](long i){ return rank[(i + k) % n]; };
            auto cmp = [&](int x, int y){
                if (rank[x] != rank[y]) return rank[x] < rank[y];
                return key2(x) < key2(y);
            };
            std::sort(SA.begin(), SA.end(), cmp);
            tmp[SA[0]] = 0;
            for (long i = 1; i < n; ++i) tmp[SA[i]] = tmp[SA[i-1]] + (cmp(SA[i-1], SA[i]) ? 1 : 0);
            rank = tmp;
            if (rank[SA[n-1]] == n - 1) break;
        }
    }

    long rnk(int c, long i) const {                 // occurrences of symbol c in BWT[0:i]
        long b = i / BLOCK, res = rankpre[c][b];
        for (long j = b * BLOCK; j < i; ++j) res += (BWT[j] == c);
        return res;
    }
    long lf(long i) const { int c = BWT[i]; return C[c] + rnk(c, i); }
    long recover_pos(long i) const {
        long steps = 0, j = i;
        while (!sampled[j]) { j = lf(j); steps++; }
        return sa_at[j] + steps;
    }

    bool encode(const std::string& P, std::vector<int>& cs) const {
        cs.clear();
        for (char ch : P) {
            int c = dna_code[(unsigned char)std::toupper((unsigned char)ch)];
            if (c < 0) return false;
            cs.push_back(c);
        }
        return true;
    }
    bool backward_search(const std::string& P, long& lo, long& hi) const {
        std::vector<int> cs;
        if (!encode(P, cs) || cs.empty()) { lo = hi = 0; return false; }
        lo = 0; hi = n;
        for (auto it = cs.rbegin(); it != cs.rend(); ++it) {
            int c = *it;
            lo = C[c] + rnk(c, lo);
            hi = C[c] + rnk(c, hi);
            if (lo >= hi) { lo = hi; return false; }
        }
        return true;
    }
    // locate -> sorted unique (record_idx, ungapped_pos)
    std::vector<std::pair<int,long>> locate(const std::string& P) const {
        long lo, hi; std::set<std::pair<int,long>> out;
        if (P.empty() || !backward_search(P, lo, hi)) return {};
        for (long i = lo; i < hi; ++i) {
            long p = recover_pos(i); int d = doc[p];
            out.insert({d, p - doc_start[d]});
        }
        return {out.begin(), out.end()};
    }
};

// ---------------------------------------------------------------- coords.json (flat fixed schema) + transform
struct Coord { std::string fasta_id, src, strand; long start=0, size=0, srcSize=0; };

static std::string jstr(const std::string& o, const std::string& key) {
    auto p = o.find("\"" + key + "\""); if (p == std::string::npos) return "";
    p = o.find(':', p); p = o.find('"', p) + 1; auto q = o.find('"', p);
    return o.substr(p, q - p);
}
static long jint(const std::string& o, const std::string& key) {
    auto p = o.find("\"" + key + "\""); if (p == std::string::npos) return 0;
    p = o.find(':', p) + 1; while (p < o.size() && (o[p]==' ')) p++;
    return strtol(o.c_str() + p, nullptr, 10);
}
std::vector<Coord> read_coords(const std::string& path) {
    std::ifstream f(path); std::stringstream ss; ss << f.rdbuf(); std::string s = ss.str();
    std::vector<Coord> out;
    size_t p = 0;
    while ((p = s.find('{', p)) != std::string::npos) {
        size_t q = s.find('}', p); std::string o = s.substr(p, q - p + 1);
        Coord c; c.fasta_id = jstr(o,"fasta_id"); c.src = jstr(o,"src"); c.strand = jstr(o,"strand");
        c.start = jint(o,"start"); c.size = jint(o,"size"); c.srcSize = jint(o,"srcSize");
        out.push_back(c); p = q + 1;
    }
    return out;
}
// genomic tuple string (matches the Python _dedup_sort key + transform)
std::string genomic(const Coord& c, long pos, long m) {
    long gs, ge;
    if (c.strand == "-") { gs = c.srcSize - (c.start + pos + m); ge = c.srcSize - (c.start + pos); }
    else { gs = c.start + pos; ge = c.start + pos + m; }
    char buf[512];
    snprintf(buf, sizeof(buf), "%s\t%s\t%ld\t%ld\t%s", c.fasta_id.c_str(), c.src.c_str(), gs, ge,
             c.strand.c_str());
    return buf;
}

int usage() {
    fprintf(stderr, "usage: wg_suffix <block.fa> --a A --l L --s S [--coords c.json] "
                    "--locate P | --queries FILE | --bench [REPS] | --info\n");
    return 2;
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 3) return usage();
    std::string fa = argv[1], mode, P, qfile, coordsf; long A = -1, L = -1, S = 8; int reps = 100000;
    for (int i = 2; i < argc; ++i) {
        std::string f = argv[i];
        if (f == "--a") A = atol(argv[++i]);
        else if (f == "--l") L = atol(argv[++i]);
        else if (f == "--s") S = atol(argv[++i]);
        else if (f == "--coords") coordsf = argv[++i];
        else if (f == "--locate") { mode = f; P = argv[++i]; }
        else if (f == "--queries") { mode = f; qfile = argv[++i]; }
        else if (f == "--bench") { mode = f; if (i+1 < argc && argv[i+1][0] != '-') reps = atoi(argv[++i]); }
        else if (f == "--info") mode = f;
    }
    auto recs = read_fasta(fa);
    if (A >= 0 && (size_t)A < recs.size()) recs.resize(A);
    std::vector<std::string> seqs; for (auto& r : recs) seqs.push_back(ungap_cap(r.second, L));

    auto t0 = std::chrono::high_resolution_clock::now();
    SuffixIndex idx; idx.build(seqs, L, S);
    auto t1 = std::chrono::high_resolution_clock::now();
    double build_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::vector<Coord> coords; if (!coordsf.empty()) coords = read_coords(coordsf);

    auto emit = [&](const std::string& pat) {
        auto hits = idx.locate(pat);
        if (coords.empty()) {
            for (auto& h : hits) printf("%d %ld\n", h.first, h.second);   // record_idx ungapped_pos
        } else {
            std::set<std::string> g;                                       // dedup genomic tuples
            for (auto& h : hits) g.insert(genomic(coords[h.first], h.second, (long)pat.size()));
            for (auto& t : g) printf("%s\n", t.c_str());
        }
    };

    if (mode == "--info") {
        printf("n=%ld r=%ld n_samples=%ld sigma=%d a=%d build_ms=%.3f\n",
               idx.n, idx.r, (long)std::count(idx.sampled.begin(), idx.sampled.end(), (char)1),
               idx.sigma, idx.a, build_ms);
        return 0;
    }
    if (mode == "--locate") { printf("# %s\n", P.c_str()); emit(P); return 0; }
    if (mode == "--queries") {
        std::ifstream f(qfile); if (!f) { fprintf(stderr, "cannot open %s\n", qfile.c_str()); return 2; }
        std::string line;
        while (std::getline(f, line)) {
            while (!line.empty() && std::isspace((unsigned char)line.back())) line.pop_back();
            if (line.empty()) continue;
            printf("# %s\n", line.c_str()); emit(line);
        }
        return 0;
    }
    if (mode == "--bench") {
        std::string alpha = "ACGT"; unsigned long seed = 0x9e3779b97f4a7c15UL;
        auto nxt = [&]() { seed ^= seed<<13; seed ^= seed>>7; seed ^= seed<<17; return seed; };
        std::vector<std::string> pats;
        for (int i = 0; i < 1000; ++i) {
            std::string p; int len = 4 + (int)(nxt()%5);
            for (int j = 0; j < len; ++j) p.push_back(alpha[nxt()%4]);
            pats.push_back(p);
        }
        long sink = 0; auto b0 = std::chrono::high_resolution_clock::now();
        for (int i = 0; i < reps; ++i) sink += idx.locate(pats[i % pats.size()]).size();
        auto b1 = std::chrono::high_resolution_clock::now();
        double us = std::chrono::duration<double, std::micro>(b1 - b0).count();
        printf("n=%ld reps=%d us_per_locate=%.4f sink=%ld\n", idx.n, reps, us/reps, sink);
        return 0;
    }
    return usage();
}
