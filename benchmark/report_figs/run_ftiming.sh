#!/usr/bin/env bash
# S3  3-point `-f` timing: pre41 (dense A2+A3) -> pre42 (sparse A2) -> new (sparse A2+A3).
# DNA corpus first (tractable, sure to finish), then AA (large; pre41 may time out -- that is a
# legitimate "OLD cannot do this" result). Resumable via the .raw.jsonl caches.
set -u
cd "$(dirname "$0")/../.." || exit 1
D=benchmark/report_figs/data
BINS=new=recognizer/bin/recognizer_linux,pre42=recognizer/bin/recognizer_linux_old,pre41=recognizer/bin/recognizer_pre41

echo "######## S3-DNA  DeBruijnG_DNA + RevDetG_DNA ########"
python3 benchmark/report_figs/ftiming.py --binaries "$BINS" \
    --corpus data/graph/SMT_vs_RHSMT/DeBruijnG_DNA,data/graph/SMT_vs_RHSMT/RevDetG_DNA \
    --timeout 90 --replicates 3 --out "$D/ftiming_dna" 2>&1
echo "S3-DNA done (rc=$?)"

echo "######## S3-AA  DeBruijnG_AA + RevDetG_AA (large; pre41 timeouts expected) ########"
python3 benchmark/report_figs/ftiming.py --binaries "$BINS" \
    --corpus data/graph/SMT_vs_RHSMT/DeBruijnG_AA,data/graph/SMT_vs_RHSMT/RevDetG_AA \
    --timeout 120 --replicates 3 --out "$D/ftiming_aa" 2>&1
echo "S3-AA done (rc=$?)"
echo "ALL FTIMING DONE"
