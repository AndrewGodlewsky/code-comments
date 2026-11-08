# Pilot container for issue #37 (narwhals long-horizon pilot).
#
# Three targets, built in order:
#   scan    - clones narwhals at the start commit and exports pinned requirements
#             from its uv.lock. Nothing from narwhals is installed or run.
#   runtime - installs those requirements. Build it only after scan.sh reports
#             a clean audit, or after the user decides on any finding (#39).
#   agent   - runtime plus a pinned Claude Code, run as uid 1000, for the model
#             sessions of the pilot runner (#41). Credentials are never baked in;
#             the runner passes them by name (`-e VAR`) from the host shell.
# Base pinned by digest (python:3.12-slim as pulled on 2026-11-07).
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54 AS scan

ARG NARWHALS_SHA=7d3a326100decf6258cc5386fbb5ad70990b36bd
# uv 0.13.5 (2026-10-22) and pip-audit 2.10.1 (2026-06-10): pinned, both
# published at least two weeks before the image was first built.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir uv==0.13.5 pip-audit==2.10.1

WORKDIR /work
RUN git init -q narwhals \
 && git -C narwhals remote add origin https://github.com/narwhals-dev/narwhals.git \
 && git -C narwhals fetch -q --depth 1 origin "$NARWHALS_SHA" \
 && git -C narwhals checkout -q FETCH_HEAD

# Backends: pandas, polars, pyarrow, duckdb, sqlframe (core group) and dask.
# Excluded and disclosed: pyspark, modin, cudf, ibis.
RUN cd narwhals && uv export --frozen --no-default-groups --no-emit-project \
      --group core --group tests --extra dask \
      --format requirements-txt -o /work/requirements.txt

FROM scan AS runtime
# --require-hashes: install exactly the audited, hash-pinned artifacts.
RUN pip install --no-cache-dir --require-hashes -r /work/requirements.txt \
 && pip install --no-cache-dir --no-deps -e /work/narwhals
WORKDIR /work/narwhals

FROM runtime AS agent
# Claude Code 2.1.319, the version the skill eval's isolation was verified on.
RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code@2.1.319 \
 && useradd -m -u 1000 pilot
USER pilot
WORKDIR /work/narwhals
