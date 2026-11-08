#!/usr/bin/env bash
# Validate the oracle chain for issue #40 inside the runtime container.
# Usage: evaluation/pilot/validate_chain.sh OUT_DIR   (from the repository root)
# For each chain diff, in order: apply it, run the step's own tests, then the full
# suite. Writes OUT_DIR/{baseline,step-N}.xml and OUT_DIR/summary.txt.
set -euo pipefail
export MSYS_NO_PATHCONV=1
here="$(cd "$(dirname "$0")" && { pwd -W 2>/dev/null || pwd; })"
mkdir -p "$1"
out="$(cd "$1" && { pwd -W 2>/dev/null || pwd; })"

docker run --rm -v "$here/chain:/chain:ro" -v "$out:/out" code-comments-pilot:runtime bash -c '
set -uo pipefail
. /chain/constructors.env
run() { python -m pytest -q -p no:randomly -n 8 --constructors="$CONSTRUCTORS" "$@" 2>&1 | tail -1; }
git config user.email pilot@localhost; git config user.name pilot
# Image layers change file stat data; refresh the index so git apply --index trusts it.
git update-index -q --refresh; git status --short | head -5
echo "baseline: $(run --junitxml=/out/baseline.xml -o junit_family=xunit1)" | tee /out/summary.txt
for d in $(ls /chain/*.diff | sort -V); do
  n=$(basename "$d" .diff)
  if ! git apply --index "$d" 2>/out/$n.apply.err; then
    echo "$n: DOES NOT APPLY ($(head -1 /out/$n.apply.err))" | tee -a /out/summary.txt; continue
  fi
  git commit -qm "$n"
  tests=$(git diff --name-only HEAD~1 HEAD -- "tests/*_test.py" | tr "\n" " ")
  echo "$n: applied; own tests [$tests]: $(run $tests)" | tee -a /out/summary.txt
  echo "$n: full suite: $(run --junitxml=/out/$n.xml -o junit_family=xunit1)" | tee -a /out/summary.txt
done
'
