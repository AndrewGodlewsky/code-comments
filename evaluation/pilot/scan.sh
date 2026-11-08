#!/usr/bin/env bash
# Build the scan target and audit narwhals' pinned dependencies before any install.
# Usage: evaluation/pilot/scan.sh  (from the repository root)
# Writes evaluation/pilot/scan/{requirements.txt,audit.json,image.txt}.
set -euo pipefail
# Git Bash on Windows rewrites /work/... arguments into host paths; stop it.
export MSYS_NO_PATHCONV=1
here="$(cd "$(dirname "$0")" && { pwd -W 2>/dev/null || pwd; })"
out="$here/scan"
mkdir -p "$out"

docker build --target scan -t code-comments-pilot:scan "$here"
{ docker image inspect code-comments-pilot:scan --format 'image {{.Id}}'
  docker image inspect python:3.12-slim --format 'base {{index .RepoDigests 0}}'; } > "$out/image.txt"
docker run --rm code-comments-pilot:scan cat /work/requirements.txt > "$out/requirements.txt"

# --no-deps: the export is already a full, pinned closure.
# --disable-pip: audit the file only; nothing is resolved or installed.
# pip-audit exits 1 when it finds vulnerabilities; keep the report either way.
set +e
docker run --rm code-comments-pilot:scan \
  pip-audit -r /work/requirements.txt --no-deps --disable-pip -f json > "$out/audit.json"
status=$?
set -e
echo "pip-audit exit status: $status"
python - "$out/audit.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
deps = data.get("dependencies", data)
vulns = [(d["name"], d["version"], v["id"], v.get("fix_versions"))
         for d in deps for v in d.get("vulns", [])]
skipped = [d["name"] for d in deps if d.get("skip_reason")]
print(f"{len(deps)} packages audited, {len(vulns)} known vulnerabilities, {len(skipped)} skipped")
for row in vulns:
    print("  ", *row)
if skipped:
    print("  skipped:", ", ".join(skipped))
PY
