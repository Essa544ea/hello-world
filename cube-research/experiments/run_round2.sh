#!/bin/bash
# Runs the rest of round 2 sequentially after E03 finishes. Logs in results/.
cd "$(dirname "$0")"
while ps -eo args | grep -q "^python3 e03_ll"; do sleep 20; done
python3 e06_chains.py 30 dev > ../results/e06.log 2>&1
python3 e09_influence.py 30 dev > ../results/e09.log 2>&1
python3 e08_ergo_validity.py > ../results/e08.log 2>&1
python3 e02_analyze.py > /dev/null 2>&1
echo ROUND2-DONE >> ../results/round2.status
