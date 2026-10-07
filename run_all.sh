#!/bin/sh
# Rebuild every derived dataset, report and figure from data/raw + data/foods + config (PLAN D.12).
# Usage (VS Code Flatpak terminal):  host-spawn sh run_all.sh      normal terminal:  sh run_all.sh
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
echo "1/10 composition";        $PY -W ignore src/data/resolve.py > /dev/null
echo "2/10 prices";             $PY -W ignore src/prices/summary.py > /dev/null
echo "3/10 master dataset";     $PY -W ignore src/build_master.py > /dev/null
echo "4/10 food exploration";   $PY -W ignore src/analysis/explore.py > /dev/null
echo "5/10 food figures";       $PY -W ignore src/analysis/figures.py > /dev/null
echo "6/10 profile scenarios";  $PY -W ignore src/analysis/scenarios.py > /dev/null
echo "7/10 optimizer report";   $PY -W ignore src/analysis/optimize_report.py > /dev/null
echo "8/10 robustness";         $PY -W ignore src/analysis/robustness.py > /dev/null
echo "9/10 comparison";        $PY -W ignore src/analysis/comparison.py > /dev/null
echo "10/10 v2.0 nutrients";    $PY -W ignore src/analysis/v2_report.py > /dev/null
$PY -m pytest -q tests
echo "done: data/processed, reports/, figures/"
