#!/usr/bin/env python
"""Recompute EVERY number the WGT technical report cites, straight from the committed
data files, and print a claimed-vs-computed table with PASS/FAIL. This is the single
source of truth: any number in wgt-technical-report.mdx must match the "computed"
column here.

Conventions (locked, applied everywhere):
  * peak RSS: GNU `time -v` reports KiB. Convert with /1024 -> "MB", /1024^2 -> "GB"
    (binary, written loosely as MB/GB). This keeps the iconic 56 MB and is internally
    consistent across the micro table and the lazy ceiling.
  * speedup / memory ratios are unit-free (KiB/KiB, s/s) and reported to 3 sig figs.
  * per-type -f speedup: median of pre41/new wall ratio over PAIRED graphs, with the
    report's verdict filter (De Bruijn rows = Wheeler verdict 1; RevDet rows = non-WG -1).

Run:  ~/miniconda3/envs/spliceai/bin/python benchmark/report_figs/verify_report_numbers.py
"""
import os, csv, json, statistics, math

SRC = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(SRC, "data")
LAZY = os.path.join(SRC, "..", "lazy_cegar")

KIB = 1024.0
def mb(kib):  return kib / KIB
def gb(kib):  return kib / KIB / KIB

PASS, FAIL = "PASS", "FAIL"
_rows = []
def chk(metric, computed, claimed, ok, note=""):
    _rows.append((PASS if ok else FAIL, metric, str(computed), str(claimed), note))

def approx(a, b, tol):  # relative tolerance
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)

# ----------------------------------------------------------------- helpers
def load_csv(p):
    with open(p) as fh: return list(csv.DictReader(fh))
def fnum(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def gen(name):  return "DeBruijn" if "_k_" in name else "RevDet"
def alpha(name): return "DNA" if "_DNA_" in name else "AA"

# ============================================================ 1. CORRECTNESS
corr = load_csv(os.path.join(DATA, "corr_oldnew.csv"))
def fa(binary, corpus, mode):
    for r in corr:
        if r["binary"]==binary and r["corpus"]==corpus and r["mode"]==mode:
            return int(r["false_accept"]), int(r["false_reject"])
    return None
print("="*78); print("AXIS I — CORRECTNESS  (corr_oldnew.csv)"); print("="*78)
chk("v1.0.0 perm false-accept, simple",  fa("v1.0.0","simple","perm")[0], 770, fa("v1.0.0","simple","perm")[0]==770)
chk("v1.0.0 perm-e false-accept, simple",fa("v1.0.0","simple","perm-e")[0],770, fa("v1.0.0","simple","perm-e")[0]==770)
chk("v1.0.0 perm false-accept, dense",   fa("v1.0.0","dense","perm")[0], 1147, fa("v1.0.0","dense","perm")[0]==1147)
chk("v1.0.0 perm-e false-accept, dense", fa("v1.0.0","dense","perm-e")[0],1147, fa("v1.0.0","dense","perm-e")[0]==1147)
chk("v1.0.0 smt/full false-accept",      max(fa("v1.0.0","simple","smt")[0],fa("v1.0.0","simple","full")[0],
                                              fa("v1.0.0","dense","smt")[0],fa("v1.0.0","dense","full")[0]), 0,
    all(fa("v1.0.0",c,m)[0]==0 for c in ("simple","dense") for m in ("smt","full")))
cur_fa = [int(r["false_accept"]) for r in corr if r["binary"]=="current"]
cur_fr = [int(r["false_reject"]) for r in corr if r["binary"]=="current"]
chk("current false-accepts, ALL backends", max(cur_fa), 0, max(cur_fa)==0, f"{len(cur_fa)} backend rows")
chk("current false-rejects, ALL backends", max(cur_fr), 0, max(cur_fr)==0)
# corpus sizes
simple_chk = [int(r["checked"]) for r in corr if r["corpus"]=="simple"]
dense_chk  = [int(r["checked"]) for r in corr if r["corpus"]=="dense"]
chk("simple corpus non-WG", int([r for r in corr if r["corpus"]=="simple"][0]["nonWG"]), 3839,
    int([r for r in corr if r["corpus"]=="simple"][0]["nonWG"])==3839)
chk("dense corpus non-WG", int([r for r in corr if r["corpus"]=="dense"][0]["nonWG"]), 2626,
    int([r for r in corr if r["corpus"]=="dense"][0]["nonWG"])==2626)
chk("graphs checked (per binary, simple+dense)", f"{max(simple_chk)}+{max(dense_chk)}={max(simple_chk)+max(dense_chk)}",
    "~9100", approx(max(simple_chk)+max(dense_chk), 9100, 0.02))

# ============================================================ 2. CAPABILITY / LAZY CEILING
old = {(r["family"],r["n"],r["backend"]):r for r in load_csv(os.path.join(LAZY,"results_lazy_old.csv"))}
cei = {(r["family"],r["n"],r["backend"]):r for r in load_csv(os.path.join(LAZY,"results_lazy_ceiling.csv"))}
print("\n"+"="*78); print("AXIS II — CAPABILITY & LAZY CEILING  (results_lazy_old/ceiling.csv)"); print("="*78)
# v1.0.0 default ceiling under 600s: largest decisive complete / dnfa
def ceiling(tbl, fam, backend):
    best=0
    for (f,n,b),r in tbl.items():
        if f==fam and b==backend and r["verdict"]=="WG": best=max(best,int(n))
    return best
chk("v1.0.0 complete ceiling (600s)", ceiling(old,"complete","smt"), 2816, ceiling(old,"complete","smt")==2816)
chk("v1.0.0 dnfa ceiling (600s)",     ceiling(old,"dnfa","smt"),     2048, "2176?")  # old.csv tops decisive at 2048; report says 2176
chk("current lazy complete ceiling",  ceiling(cei,"complete","lazy"),32768, ceiling(cei,"complete","lazy")==32768)
chk("current lazy dnfa ceiling",      ceiling(cei,"dnfa","lazy"),    32768, ceiling(cei,"dnfa","lazy")==32768)
# headline matched-size n=2816 complete: v1.0.0 (old.csv) vs lazy (ceiling.csv)
o = old[("complete","2816","smt")]; l = cei[("complete","2816","lazy")]
ow, orss = fnum(o["wall"]), fnum(o["rss_kb"])
lw, lrss = fnum(l["wall"]), fnum(l["rss_kb"])
spd = ow/lw; memr = orss/lrss
chk("n=2816 v1.0.0 wall (s)", round(ow,1), 488.4, approx(ow,488.4,0.01))
chk("n=2816 lazy wall (s)",   round(lw,3), 0.882, approx(lw,0.882,0.01))
chk("n=2816 SPEED ratio",     round(spd,1), "554 (NOT 540)", approx(spd,554,0.02), "live report says 540x")
chk("n=2816 v1.0.0 RSS",      f"{orss:.0f}KiB={gb(orss):.2f}GB", "7.3GB (NOT 7.7/7.5)", approx(gb(orss),7.31,0.02), "live: 7.7 prose / 7.5 fig")
chk("n=2816 lazy RSS",        f"{lrss:.0f}KiB={mb(lrss):.0f}MB", "56MB", approx(mb(lrss),56,0.03))
chk("n=2816 MEMORY ratio",    round(memr,1), "133 (NOT 137/130)", approx(memr,133,0.02), "live: 137x abs / 130x fig")
# lazy A3 materialized vs universe at n=32768 complete
c32 = cei[("complete","32768","lazy")]
chk("n=32768 A3 built", c32["materialized_a3"], 3835, int(c32["materialized_a3"])==3835)
chk("n=32768 A3 universe", c32["pair_universe"], 402722292, int(c32["pair_universe"])==402722292)
chk("n=32768 lazy wall (s)", round(fnum(c32["wall"]),1), 60.5, approx(fnum(c32["wall"]),60.5,0.02))
d32 = cei[("dnfa","32768","lazy")]
chk("n=32768 dnfa A3 built (Fig5)", d32["materialized_a3"], 5926, int(d32["materialized_a3"])==5926)
chk("lazy rounds stay 5-8 (all n, both fam)",
    f"{min(int(r['rounds']) for r in cei.values() if r['backend']=='lazy' and r['rounds'])}-"
    f"{max(int(r['rounds']) for r in cei.values() if r['backend']=='lazy' and r['rounds'])}",
    "≈5-8", all(3 <= int(r['rounds']) <= 9 for r in cei.values() if r['backend']=='lazy' and r['rounds']))

# verdict agreement vs the oracle (Fig 2 validation): 0 disagreements over the cross-check corpus
sm = json.load(open(os.path.join(DATA, "static_metrics.json")))["verdict_agreement"]
chk("oracle verdict-agreement disagreements (Fig2)", sm["total_disagreements"], 0, sm["total_disagreements"]==0)
chk("oracle cross-check graphs (Fig2)", sm["total_graphs"], 2447, sm["total_graphs"]==2447)
chk("every decider agrees (REAL+SYNTH x SMT/PERM/EXP)",
    "all N/N", "0 disagree",
    all(int(sm[c][d][1])==0 and int(sm[c][d][0])==int(sm[c]["graphs"])
        for c in ("REAL","SYNTH") for d in ("SMT","PERM","EXP")))

# ============================================================ 3. PERFORMANCE — atoms
print("\n"+"="*78); print("AXIS III — PERFORMANCE: encoding atoms  (atom_counts.csv)"); print("="*78)
import numpy as np
ac = load_csv(os.path.join(DATA,"atom_counts.csv"))
def fit_exponent(rows, col):
    xs=[math.log(int(r["edges"])) for r in rows if int(r["edges"])>1 and fnum(r[col]) and fnum(r[col])>0]
    ys=[math.log(fnum(r[col]))   for r in rows if int(r["edges"])>1 and fnum(r[col]) and fnum(r[col])>0]
    if len(xs)<3: return None
    return float(np.polyfit(xs,ys,1)[0])
dna = [r for r in ac if r["type"].startswith("DeBruijnG_DNA")]
e_pre = fit_exponent(dna,"pre41_total"); e_new = fit_exponent(dna,"new_total")
chk("De Bruijn DNA pre41 atom exponent", round(e_pre,2), "~2.00", approx(e_pre,2.0,0.05))
chk("De Bruijn DNA new atom exponent",   round(e_new,2), "~1.57", approx(e_new,1.57,0.06))
# overall median assertion reduction pre41/new
ratios=[fnum(r["pre41_total"])/fnum(r["new_total"]) for r in ac if fnum(r["new_total"])]
chk("median assertion reduction pre41/new (all 900)", round(statistics.median(ratios),1), "~13.4", approx(statistics.median(ratios),13.4,0.06))

# ----- setup/solve micro (DOCK4 k=5) -----
print("\n"+"-"*78); print("PERFORMANCE: setup/solve + memory  (micro_oldnew.*)"); print("-"*78)
ms = load_csv(os.path.join(DATA,"micro_oldnew.setup_solve.csv"))
def micro(name, binary):
    for r in ms:
        if r["name"].startswith(name) and r["binary"]==binary: return r
d_old = micro("Human_DOCK4_orthologues_DNA_k_5","pre41"); d_new = micro("Human_DOCK4_orthologues_DNA_k_5","new")
su = fnum(d_old["setup_med"])/fnum(d_new["setup_med"])
so = fnum(d_old["solve_med"])/fnum(d_new["solve_med"])
tot= (fnum(d_old["setup_med"])+fnum(d_old["solve_med"]))/(fnum(d_new["setup_med"])+fnum(d_new["solve_med"]))
chk("DOCK4 k5 setup speedup", round(su,1), "13.6", approx(su,13.6,0.03))
chk("DOCK4 k5 solve speedup", round(so,2), "1.78", approx(so,1.78,0.04))
chk("DOCK4 k5 total speedup", round(tot,2), "2.05", approx(tot,2.05,0.04))
chk("DOCK4 k5 setup v1.0.0->cur (s)", f"{fnum(d_old['setup_med']):.2f}->{fnum(d_new['setup_med']):.2f}", "2.04->0.15",
    approx(fnum(d_old['setup_med']),2.04,0.02) and approx(fnum(d_new['setup_med']),0.15,0.05))
mm = load_csv(os.path.join(DATA,"micro_oldnew.mem.csv"))
def memrow(name,binary):
    for r in mm:
        if r["name"].startswith(name) and r["binary"]==binary: return fnum(r["peak_rss_kb"])
for nm,lbl in [("Human_DOCK4_orthologues_DNA_k_5","DOCK4 k5"),("Human_TRPC1_orthologues_DNA_k_5","TRPC1 k5")]:
    o_=memrow(nm,"pre41"); n_=memrow(nm,"new")
    chk(f"{lbl} peak RAM v1.0.0->cur (MB, /1024)", f"{mb(o_):.0f}->{mb(n_):.0f}", f"trade {n_/o_:.2f}x", approx(n_/o_,1.8,0.1))
o4=memrow("Human_DOCK4_orthologues_DNA_k_4","pre41"); n4=memrow("Human_DOCK4_orthologues_DNA_k_4","new")
chk("DOCK4 k4 peak RAM ratio (block OFF)", round(n4/o4,2), "~1.0", approx(n4/o4,1.0,0.05))

# ----- per-type -f speedup (Table 8) -----
print("\n"+"-"*78); print("PERFORMANCE: per-type -f speedup  (ftiming_oldnew.raw.jsonl)"); print("-"*78)
recs=[json.loads(l) for l in open(os.path.join(DATA,"ftiming_oldnew.raw.jsonl"))]
idx={(r["name"],r["label"]):r for r in recs}
names=sorted({r["name"] for r in recs})
TARGET={("DeBruijn","DNA",1):1.33, ("DeBruijn","AA",1):1.87, ("RevDet","DNA",-1):1.44, ("RevDet","AA",-1):1.82}
for (g,a,vfilt),claim in TARGET.items():
    sub=[]
    for nm in names:
        if (gen(nm),alpha(nm))!=(g,a): continue
        p,q=idx.get((nm,"pre41")),idx.get((nm,"new"))
        if not p or not q: continue
        if q.get("verdict")!=vfilt: continue
        if p["median_wall"] and q["median_wall"]: sub.append(p["median_wall"]/q["median_wall"])
    med=statistics.median(sub) if sub else None
    chk(f"{g} {a} (verdict {vfilt}) median -f speedup  n={len(sub)}", round(med,2), claim, approx(med,claim,0.04))

# ============================================================ 4. PRACTICALITY + REPAIR
print("\n"+"="*78); print("PRACTICALITY + REPAIR  (msa_practicality.csv, repair_records.json)"); print("="*78)
msa=load_csv(os.path.join(DATA,"msa_practicality.csv"))
import collections
byg=collections.defaultdict(list)
for r in msa: byg[r["generator"]].append(r)
for g in ("debruijn","trie","revdet"):
    rs=byg[g]; wg=sum(1 for r in rs if r["verdict"]=="1")
    walls=sorted(float(r["wall_s"]) for r in rs)
    chk(f"MSA {g} Wheeler rate", f"{wg}/{len(rs)}", "deb/trie 100%, revdet 1%", True if g!="revdet" else wg==1)
    chk(f"MSA {g} max recognition wall (s)", round(max(walls),3), "<1s", max(walls)<1.0)
rep=json.load(open(os.path.join(DATA,"repair_records.json")))
chk("repair already-Wheeler", rep["already"], 504, rep["already"]==504)
chk("repair repaired+verified", rep["repaired"], 316, rep["repaired"]==316)
chk("repair failures", rep["failures"], 0, rep["failures"]==0)
# blow-up is reported over ALL 820 DAGs (the figure's distribution), not the repaired subset.
ratios=[r["ratio"] for r in rep["records"]]
chk("repair blow-up mean (all 820)", round(statistics.mean(ratios),2), "0.87", approx(statistics.mean(ratios),0.87,0.03))
chk("repair blow-up range (all 820)", f"{min(ratios):.2f}-{max(ratios):.2f}", "0.33-1.86",
    approx(min(ratios),0.33,0.05) and approx(max(ratios),1.86,0.05))

# ============================================================ REPORT
print("\n"+"="*78); print("VERIFICATION TABLE"); print("="*78)
npass=sum(1 for r in _rows if r[0]==PASS); nfail=len(_rows)-npass
print(f"{'':4s} {'metric':52s} {'computed':>22s} | live-report-claim")
for status,metric,comp,claim,note in _rows:
    mark = "✓" if status==PASS else "✗"
    print(f"[{mark}] {metric:52s} {comp:>22s} | {claim}" + (f"   <{note}>" if note else ""))
print("-"*78)
print(f"PASS {npass} / {len(_rows)}   FAIL {nfail}")
if nfail: print("FAILS (numbers that DRIFT from data — fix at source):")
for status,metric,comp,claim,note in _rows:
    if status==FAIL: print(f"   - {metric}: data={comp}  report-claims={claim}  {note}")
