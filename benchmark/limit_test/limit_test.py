#!/usr/bin/env python3
"""
limit_test.py -- scalability LIMIT test for the WGT Wheeler-graph algorithms.

For each algorithm and graph family, find the LARGEST graph that can be decided ("recognize") or
repaired ("fix") within a wall-clock timeout T. Method: climb a geometric size ladder (n=8,16,32,...),
run R replicate graphs per rung, and call a rung a PASS iff the MEDIAN replicate finishes within T,
returns a decisive verdict, and (for Wheeler-by-construction families) is CORRECT. On the first
failing rung, BISECT (last_pass, first_fail) for a tight threshold.

The reported limit is TYPED:
  THRESHOLD(n*)    -- largest n decided within T; n*+ε fails by TIMEOUT.
  CAPPED(reason)   -- the tool gave up before any timeout: exp over-cap (col0=-1 / time 60000000),
                      -f UNDECIDED (z3 unknown, col0=0), or repair trie-too-large (exit 3).
  UNREACHED(>=cap) -- still passing at the per-algo cap (a lower bound).
  GEN_INFEASIBLE   -- couldn't even generate at that size.

Outcome classes are never conflated: DECISIVE(verdict in {1,-1}) / TIMEOUT / CAPPED / UNDECIDED /
ERR (abort/unparseable -- e.g. `-i` on string labels core-dumps; must NOT be read as not-WG).

This run DOUBLES as a large-scale differential correctness test: for Wheeler-by-construction families
every decisive verdict must be WG (a not-WG is a false-reject bug); the brute oracle (n<=9) anchors
the small rungs. Any violation is saved to results/repro/ and flagged (process exits 1 at the end).

Reproducible (seeded), resumable (per-run cache), tmux-durable (flush after every run).

Recognize families:  complete, dnfa  (Wheeler by construction => truth known)
Fix family:          random-dag       (for wheelerize; truth via the tool's own verification)

Usage:
  python3 benchmark/limit_test/limit_test.py --quick                       # fast smoke
  python3 benchmark/limit_test/limit_test.py --timeout 600 --replicates 3 \
      --families complete,dnfa,random-dag --algorithms smt,perm,full,full-old,exp,wheelerize --old-f
"""

import argparse
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "verify"))
import brute_oracle as bo  # noqa: E402

PY = sys.executable
REC = os.path.join(ROOT, "recognizer", "bin", "recognizer_linux")           # NEW (current devel)
# OLD = last stable release on GitHub (main @ 4c601cc7c, v1.0.0). Built as recognizer_main; override
# with WGT_REC_OLD. (The legacy recognizer_linux_old = an intermediate pre-4.2 binary, not used here.)
REC_OLD = os.environ.get("WGT_REC_OLD") or os.path.join(ROOT, "recognizer", "bin", "recognizer_main")
EXP = os.path.join(ROOT, "benchmark", "exponential_recognizer", "bin", "recognizer_e")
GEN_COMPLETE = os.path.join(ROOT, "generator", "Random_generator", "gen_complete_WG.py")
GEN_DNFA = os.path.join(ROOT, "generator", "Random_generator", "gen_d-nfa_WG.py")
WHEELERIZE = os.path.join(ROOT, "repair", "wheelerize.py")

# Recognize backends: build the argv for a given DOT path. Integer labels => -i (the WG generators
# emit integer labels). exp (recognizer_e) has no -b/-i and always prints the benchmark columns.
RECOGNIZE_CMD = {
    "smt":      lambda p: [REC, p, "-b", "-i"],
    "perm":     lambda p: [REC, p, "-b", "-s", "p", "-i"],
    "full":     lambda p: [REC, p, "-b", "-f", "-i"],
    "full-old": lambda p: [REC_OLD, p, "-b", "-f", "-i"],
    "exp":      lambda p: [EXP, p],
    # --- clean two-way OLD(v1.0.0) vs NEW(current) algos for the report ---
    # OLD's default path is vanilla z3 + heuristic (pairwise A3, same encoding as NEW -s smt). NEW's
    # default is now lazy/CEGAR. NEW -s smt is the vanilla control. -f is OLD-dense vs NEW-sparse.
    "old-default": lambda p: [REC_OLD, p, "-b", "-i"],            # v1.0.0 vanilla z3
    "new-lazy":    lambda p: [REC, p, "-b", "-i"],               # current default (lazy)
    "new-smt":     lambda p: [REC, p, "-b", "-i", "-s", "smt"],  # current vanilla control
    "old-f":       lambda p: [REC_OLD, p, "-b", "-f", "-i"],     # v1.0.0 full-range (dense)
    "new-f":       lambda p: [REC, p, "-b", "-f", "-i"],         # current full-range (sparse)
}
RECOGNIZE_ALGOS = set(RECOGNIZE_CMD)
ALL_ALGOS = list(RECOGNIZE_CMD) + ["wheelerize"]

# Per-algorithm ladder cap (max n to even attempt). exp self-over-caps near n=12.
ALGO_CAP = {"exp": 12, "smt": 8192, "perm": 8192, "full": 8192, "full-old": 8192, "wheelerize": 8192,
            "old-default": 8192, "new-lazy": 65536, "new-smt": 8192, "old-f": 8192, "new-f": 8192}

# Which families each algorithm runs on.
RECOGNIZE_FAMILIES = ["complete", "dnfa"]
FIX_FAMILIES = ["random-dag"]


# ----------------------------------------------------------------------------- output parsing
def parse_last4(stdout):
    """Return (col0:int|None, col2:str|None) from the LAST 4+-field TAB row (skips the ASCII banner)."""
    last = None
    for line in stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            last = parts
    if last is None:
        return None, None
    try:
        return int(last[0]), last[2]
    except (ValueError, IndexError):
        return None, None


class Outcome:
    __slots__ = ("klass", "verdict", "wall", "cpu")

    def __init__(self, klass, verdict, wall, cpu):
        self.klass = klass      # DECISIVE | TIMEOUT | CAPPED | UNDECIDED | ERR | VERIFY_FAIL
        self.verdict = verdict  # 1 (WG) | -1 (not-WG) | None
        self.wall = wall        # seconds (float)
        self.cpu = cpu          # raw col2 string (CPU ticks; scientific notation at scale) or None


def run_recognize(algo, path, timeout):
    cmd = RECOGNIZE_CMD[algo](path)
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Outcome("TIMEOUT", None, float(timeout), None)
    wall = time.perf_counter() - t0
    col0, col2 = parse_last4(r.stdout)
    if algo == "exp":
        # exp columns: 1=WG, 0=not-WG, -1=over-cap (time sentinel 60000000).
        if col0 == 1:
            return Outcome("DECISIVE", 1, wall, col2)
        if col0 == 0:
            return Outcome("DECISIVE", -1, wall, col2)
        if col0 == -1:
            return Outcome("CAPPED", None, wall, col2)
        return Outcome("ERR", None, wall, col2)
    # main recognizer (-b): 1=WG, -1=not-WG, 0=undecided (z3 unknown under -f).
    if col0 == 1:
        return Outcome("DECISIVE", 1, wall, col2)
    if col0 == -1:
        return Outcome("DECISIVE", -1, wall, col2)
    if col0 == 0:
        return Outcome("UNDECIDED", None, wall, col2)
    return Outcome("ERR", None, wall, col2)  # crash / no parseable row (e.g. -i on string labels)


def run_wheelerize(path, timeout, out_path):
    # exit: 0 success+verified, 1 verify FAIL (bug), 2 cyclic, 3 trie too large (capability cap).
    t0 = time.perf_counter()
    try:
        r = subprocess.run([PY, WHEELERIZE, path, "-o", out_path, "--int"],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return Outcome("TIMEOUT", None, float(timeout), None)
    wall = time.perf_counter() - t0
    rc = r.returncode
    if rc == 0:
        return Outcome("DECISIVE", 1, wall, None)        # repaired AND self-verified
    if rc == 3:
        return Outcome("CAPPED", None, wall, None)       # trie > --max-nodes
    if rc == 1:
        return Outcome("VERIFY_FAIL", None, wall, None)  # repair produced a non-WG / lost strings: BUG
    return Outcome("ERR", None, wall, None)              # rc==2 cyclic (shouldn't happen for DAGs)


# ----------------------------------------------------------------------------- graph generation
def feasible_edges(n, labels, density, root=1):
    """e ~ density*n, clamped to the WG feasibility window [n-root, n*labels+n-labels-root]."""
    lo = n - root
    hi = n * labels + n - labels - root
    return max(lo, min(int(round(density * n)), hi))


def gen_wg(family, n, labels, density, seed, path):
    """Generate a Wheeler-by-construction graph (complete | dnfa). Returns True on success.

    The dnfa generator has internal asserts that fail for some (n,e,d) combos, so retry with nearby
    edge counts (still inside the feasibility window, still ~density*n) until one succeeds. The
    candidate order is deterministic, so the same (family,n,seed) yields the same graph (reproducible).
    """
    e0 = feasible_edges(n, labels, density)
    lo, hi = n - 1, n * labels + n - labels - 1
    gen = GEN_COMPLETE if family == "complete" else GEN_DNFA
    for delta in (0, 1, -1, 2, -2, 3, -3, 4, 5, 6):
        e = e0 + delta
        if e < lo or e > hi:
            continue
        cmd = [PY, gen, "-n", str(n), "-e", str(e), "-l", str(labels),
               "-s", "--seed", str(seed), "-o", path]
        if family == "dnfa":
            cmd += ["-d", "2"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(path):
            return True
    return False


def gen_random_dag(n, n_labels, c, seed, path):
    """Random labeled DAG (forward edges in a random topo order). avg out-degree ~ c (density min(.35,c/n))."""
    rng = random.Random(seed)
    order = list(range(n))
    rng.shuffle(order)
    pos = {node: i for i, node in enumerate(order)}
    p = min(0.35, c / max(1, n))
    names = [f"S{i}" for i in range(n)]
    edges = []
    for u in range(n):
        for v in range(n):
            if pos[u] < pos[v] and rng.random() < p:
                edges.append((names[u], names[v], rng.randrange(n_labels)))
    if not edges:                                   # guarantee >=1 edge so the file is non-trivial
        a, b = sorted(rng.sample(range(n), 2), key=lambda x: pos[x])
        edges.append((names[a], names[b], 0))
    with open(path, "w") as f:
        f.write("strict digraph {\n")
        for (u, v, lab) in edges:
            f.write(f"\t{u} -> {v} [ label = {lab} ];\n")
        f.write("}\n")
    return True


def make_graph(family, n, seed, args, tmpdir):
    """Return (path, measured_n, n_edges, truth) or None if generation failed/infeasible."""
    path = os.path.join(tmpdir, f"{family}_n{n}_s{seed}.dot")
    if family in ("complete", "dnfa"):
        ok = gen_wg(family, n, args.labels, args.density, seed, path)
        truth = 1  # Wheeler by construction
    elif family == "random-dag":
        ok = gen_random_dag(n, max(2, args.labels), args.dag_density, seed, path)
        truth = None  # unknown; oracle decides at n<=9
    else:
        raise ValueError(f"unknown family {family}")
    if not ok or not os.path.exists(path):
        return None
    try:
        nodes, edges = bo.parse_dot(path)
    except Exception:
        return None
    return path, len(nodes), len(edges), truth


# ----------------------------------------------------------------------------- correctness layer
def oracle_truth(path):
    nodes, edges = bo.parse_dot(path)
    if len(nodes) > 9:
        return None
    rank = bo.rank_labels(edges, int_mode=True)
    return 1 if bo.is_wheeler(nodes, edges, rank) else 0


# ----------------------------------------------------------------------------- the harness
class LimitHarness:
    def __init__(self, args):
        self.args = args
        self.out = args.out
        self.raw_dir = os.path.join(self.out, "raw")
        self.repro_dir = os.path.join(self.out, "repro")
        self.summary_dir = os.path.join(self.out, "summary")
        for d in (self.raw_dir, self.repro_dir, self.summary_dir):
            os.makedirs(d, exist_ok=True)
        self.tmpdir = os.path.join(self.out, "_graphs")
        os.makedirs(self.tmpdir, exist_ok=True)
        self.cache = {}            # key -> outcome dict   (resumability)
        self.cache_path = os.path.join(self.raw_dir, "runs.jsonl")
        self._load_cache()
        self.cache_fh = open(self.cache_path, "a")
        self.correctness_failures = 0

    def _load_cache(self):
        if not os.path.exists(self.cache_path):
            return
        with open(self.cache_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self.cache[d["key"]] = d
                except (ValueError, KeyError):
                    pass

    def _run_cached(self, algo, family, n, seed):
        """Run one (algo, family, n, seed) replicate, with caching. Returns the row dict."""
        key = f"{family}|{algo}|{n}|{seed}"
        if key in self.cache:
            return self.cache[key]
        g = make_graph(family, n, seed, self.args, self.tmpdir)
        if g is None:
            row = {"key": key, "family": family, "algo": algo, "n": n, "seed": seed,
                   "measured_n": None, "edges": None, "klass": "GEN_INFEASIBLE",
                   "verdict": None, "wall": None, "cpu": None, "truth": None, "correct": None}
            self._emit(row)
            return row
        path, mn, e, truth = g
        if algo == "wheelerize":
            # NOTE: the recognizer rejects any input not ending in ".dot" ("not a DOT file" -> usage
            # exit), and wheelerize verifies its output by running the recognizer on it -- so the
            # output path MUST end in ".dot" or every repair spuriously fails verification.
            oc = run_wheelerize(path, self.args.timeout, os.path.splitext(path)[0] + ".repaired.dot")
        else:
            oc = run_recognize(algo, path, self.args.timeout)
        correct = self._check_correctness(algo, family, path, mn, e, seed, truth, oc)
        row = {"key": key, "family": family, "algo": algo, "n": n, "seed": seed,
               "measured_n": mn, "edges": e, "klass": oc.klass, "verdict": oc.verdict,
               "wall": round(oc.wall, 4) if oc.wall is not None else None, "cpu": oc.cpu,
               "truth": truth, "correct": correct}
        self._emit(row)
        return row

    def _emit(self, row):
        self.cache[row["key"]] = row
        self.cache_fh.write(json.dumps(row) + "\n")
        self.cache_fh.flush()

    def _check_correctness(self, algo, family, path, mn, e, seed, truth, oc):
        """Return True/False/None. A detected failure is RE-RUN in isolation and only flagged if it
        gives a confirmed-wrong result every time -- this guards a long unattended run against
        transient contention failures (e.g. a starved/killed subprocess giving a spurious 'not WG')."""
        if algo == "wheelerize":
            if oc.klass == "VERIFY_FAIL":
                if not self._persists(lambda: run_wheelerize(
                        path, self.args.timeout,
                        os.path.splitext(path)[0] + ".rechk.dot").klass == "VERIFY_FAIL"):
                    print(f"  (transient VERIFY_FAIL ignored: {family}/{algo} n={mn} seed={seed})",
                          flush=True)
                    return None
                self._save_repro("verify_fail", algo, family, path, mn, e, seed, {"klass": oc.klass}, None)
                return False
            return True if oc.klass == "DECISIVE" else None
        if oc.klass != "DECISIVE":
            return None  # TIMEOUT/CAPPED/UNDECIDED/ERR are non-decisions, not correctness verdicts
        # Known-truth families: a decisive verdict must equal the construction truth.
        ref = truth if truth is not None else oracle_truth(path)  # random-dag: anchor at n<=9
        if ref is None:
            return None  # truth unknown at this size; cross-backend agreement covers it elsewhere
        if oc.verdict != ref:
            if not self._persists(lambda: self._recognize_wrong(algo, path, ref)):
                print(f"  (transient wrong verdict ignored: {family}/{algo} n={mn} seed={seed})",
                      flush=True)
                return None
            self._save_repro("false_verdict", algo, family, path, mn, e, seed,
                             {"verdict": oc.verdict, "truth": ref}, ref)
            return False
        return True

    @staticmethod
    def _persists(confirmed_fail, tries=2):
        """Re-run a failing check; return True only if it CONFIRMS the failure every time (real bug)."""
        for _ in range(tries):
            if not confirmed_fail():
                return False
        return True

    def _recognize_wrong(self, algo, path, ref):
        """True iff a fresh run gives a DECISIVE verdict that disagrees with ref (a confirmed wrong)."""
        oc = run_recognize(algo, path, self.args.timeout)
        return oc.klass == "DECISIVE" and oc.verdict != ref

    def _save_repro(self, kind, algo, family, path, mn, e, seed, extra, oracle):
        self.correctness_failures += 1
        base = f"{kind}_{family}_{algo}_n{mn}_s{seed}_{self.correctness_failures:03d}"
        try:
            with open(path) as src, open(os.path.join(self.repro_dir, base + ".dot"), "w") as dst:
                dst.write(src.read())
        except OSError:
            pass
        meta = {"kind": kind, "family": family, "algo": algo, "measured_n": mn, "edges": e,
                "seed": seed, "labels": self.args.labels, "density": self.args.density,
                "oracle": oracle, **extra}
        with open(os.path.join(self.repro_dir, base + ".json"), "w") as fh:
            json.dump(meta, fh, indent=2)
        print(f"  ** CORRECTNESS FAILURE [{kind}] {family}/{algo} n={mn} seed={seed} {extra} "
              f"-> repro/{base}.dot", flush=True)
        if self.args.abort_on_mismatch:
            raise SystemExit(f"aborting on correctness failure: {base}")

    # -------- rung evaluation: median pass-rule over R replicates --------
    def eval_rung(self, algo, family, n):
        rows = [self._run_cached(algo, family, n, self.args.seed + r)
                for r in range(self.args.replicates)]
        passes, walls, fail_klasses = 0, [], []
        for row in rows:
            ok = (row["klass"] == "DECISIVE" and row["wall"] is not None
                  and row["wall"] <= self.args.timeout and row["correct"] is not False)
            if ok:
                passes += 1
                walls.append(row["wall"])
            else:
                fail_klasses.append(row["klass"])
        need = math.ceil(self.args.replicates / 2)  # median pass
        passed = passes >= need
        median_wall = statistics.median(walls) if walls else None
        # dominant reason a non-passing rung failed (TIMEOUT vs CAPPED vs UNDECIDED vs ERR)
        reason = None
        if not passed and fail_klasses:
            reason = max(set(fail_klasses), key=fail_klasses.count)
        return passed, reason, median_wall

    # -------- ladder -> bisect for one (algo, family) --------
    def find_limit(self, algo, family):
        cap = min(self.args.max_n, ALGO_CAP.get(algo, self.args.max_n))
        n = self.args.start_n
        last_pass, first_fail, fail_reason = None, None, None
        while True:
            probe = min(n, cap)                       # always test the cap exactly as the top rung
            passed, reason, mwall = self.eval_rung(algo, family, probe)
            tag = "PASS" if passed else f"FAIL({reason})"
            print(f"  [{algo:9} {family:11}] n={probe:<6} -> {tag}"
                  f"{'' if mwall is None else f'  med={mwall:.2f}s'}", flush=True)
            if passed:
                last_pass = probe
                if probe >= cap:                      # passed at the cap => only a lower bound
                    break
                n = max(probe + 1, int(n * self.args.ladder_factor))
            else:
                first_fail, fail_reason = probe, reason
                break
        if first_fail is None:
            # never failed up to the cap
            kind = "UNREACHED" if last_pass is not None else "GEN_INFEASIBLE"
            return self._limit(algo, family, kind, last_pass, fail_reason)
        if last_pass is None:
            # failed at the very first rung
            kind = self._fail_kind(fail_reason)
            return self._limit(algo, family, kind, None, fail_reason, boundary=first_fail)
        # bisect (last_pass, first_fail) unless disabled
        if not self.args.no_bisect:
            lo, hi = last_pass, first_fail
            while hi - lo > max(2, int(0.07 * lo)):
                mid = (lo + hi) // 2
                passed, reason, mwall = self.eval_rung(algo, family, mid)
                print(f"  [{algo:9} {family:11}] bisect n={mid:<6} -> "
                      f"{'PASS' if passed else f'FAIL({reason})'}", flush=True)
                if passed:
                    lo = mid
                else:
                    hi, fail_reason = mid, reason
            last_pass = lo
        kind = self._fail_kind(fail_reason)
        _, _, mwall = self.eval_rung(algo, family, last_pass)
        return self._limit(algo, family, kind, last_pass, fail_reason, median_wall=mwall)

    @staticmethod
    def _fail_kind(reason):
        # what TYPE of limit does the failure imply
        if reason in ("CAPPED", "UNDECIDED"):
            return "CAPPED"
        if reason == "ERR":
            return "ERROR"
        if reason == "GEN_INFEASIBLE":
            return "GEN_LIMITED"
        return "THRESHOLD"  # TIMEOUT (or unknown) => a genuine wall-clock threshold

    def _limit(self, algo, family, kind, n, reason, boundary=None, median_wall=None):
        return {"algo": algo, "family": family, "kind": kind, "limit_n": n,
                "timeout_s": self.args.timeout, "fail_reason": reason,
                "boundary": boundary, "median_wall_at_limit": median_wall}

    # -------- drive everything --------
    def run(self):
        algos = self.args.algorithms
        results = []
        for algo in algos:
            fams = FIX_FAMILIES if algo == "wheelerize" else RECOGNIZE_FAMILIES
            fams = [f for f in fams if f in self.args.families]
            for family in fams:
                print(f"\n=== limit: {algo} on {family} (T={self.args.timeout}s, "
                      f"R={self.args.replicates}) ===", flush=True)
                results.append(self.find_limit(algo, family))
        self._write_summary(results)
        self.cache_fh.close()
        return results

    def _write_summary(self, results):
        csvp = os.path.join(self.summary_dir, "limit_summary.csv")
        with open(csvp, "w") as fh:
            fh.write("algo,family,kind,limit_n,timeout_s,fail_reason,median_wall_at_limit\n")
            for r in results:
                fh.write(f"{r['algo']},{r['family']},{r['kind']},{r['limit_n']},"
                         f"{r['timeout_s']},{r['fail_reason']},{r['median_wall_at_limit']}\n")
        print("\n==================== LIMIT SUMMARY ====================")
        print(f"timeout T = {self.args.timeout}s, replicates R = {self.args.replicates}")
        for r in results:
            n = r["limit_n"]
            detail = ""
            if r["kind"] == "THRESHOLD":
                detail = f"largest decided n = {n}"
            elif r["kind"] == "CAPPED":
                detail = f"capability cap at n = {n} (reason {r['fail_reason']})"
            elif r["kind"] == "UNREACHED":
                detail = f"still passing at n = {n} (lower bound)"
            else:
                detail = f"{r['kind']} n={n} reason={r['fail_reason']}"
            print(f"  {r['algo']:10} {r['family']:11} -> {r['kind']:10} {detail}")
        print(f"\nwrote {csvp}")
        print(f"correctness failures: {self.correctness_failures} "
              f"({'CLEAN' if self.correctness_failures == 0 else 'SEE repro/'})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=float, default=600.0, help="wall-clock budget per run (s)")
    ap.add_argument("--families", default="complete,dnfa,random-dag",
                    help="comma list: complete,dnfa,random-dag")
    ap.add_argument("--algorithms", default="smt,perm,full,exp,wheelerize",
                    help="comma list: smt,perm,full,full-old,exp,wheelerize")
    ap.add_argument("--max-n", type=int, default=8192, help="global ladder cap")
    ap.add_argument("--start-n", type=int, default=8, help="first ladder rung")
    ap.add_argument("--ladder-factor", type=float, default=2.0, help="geometric step")
    ap.add_argument("--replicates", type=int, default=3, help="replicate graphs per rung (median rule)")
    ap.add_argument("--density", type=float, default=1.5, help="avg out-degree for WG families (e=density*n)")
    ap.add_argument("--labels", type=int, default=3, help="edge labels")
    ap.add_argument("--dag-density", type=float, default=2.5, help="target avg out-degree for random-dag")
    ap.add_argument("--seed", type=int, default=1, help="base seed; replicate r uses seed+r")
    ap.add_argument("--old-f", action="store_true", help="also run full-old (OLD -f, Phase-4.2 overlay)")
    ap.add_argument("--no-bisect", action="store_true", help="ladder only (skip threshold refinement)")
    ap.add_argument("--abort-on-mismatch", action="store_true", help="stop on first correctness failure")
    ap.add_argument("--quick", action="store_true", help="smoke: T=5, R=2, start-n=8, max-n=64")
    ap.add_argument("--out", default=os.path.join(HERE, "results"), help="results root")
    args = ap.parse_args()

    if args.quick:
        args.timeout, args.replicates, args.start_n, args.max_n = 5.0, 2, 8, 64

    args.families = [f.strip() for f in args.families.split(",") if f.strip()]
    args.algorithms = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    if args.old_f and "full-old" not in args.algorithms:
        args.algorithms.append("full-old")
    for a in args.algorithms:
        if a not in ALL_ALGOS:
            ap.error(f"unknown algorithm {a}; choose from {ALL_ALGOS}")
    if "full-old" in args.algorithms and not os.path.exists(REC_OLD):
        print(f"WARN: {REC_OLD} missing; dropping full-old", file=sys.stderr)
        args.algorithms = [a for a in args.algorithms if a != "full-old"]

    harness = LimitHarness(args)
    harness.run()
    sys.exit(1 if harness.correctness_failures else 0)


if __name__ == "__main__":
    main()
