# Pilot container (#37, #39)

The narwhals pilot runs only inside this container. Nothing from narwhals is installed
or run on the host.

| File | Purpose |
| --- | --- |
| `Dockerfile` | `scan` target: clones narwhals at the start commit and exports hash-pinned requirements from its `uv.lock`, without installing anything. `runtime` target: installs exactly those hashes, then narwhals itself (editable, no dependencies). |
| `scan.sh` | Builds `scan`, runs `pip-audit` on the export, and writes the results to `scan/`. |
| `scan/` | The audited `requirements.txt`, the `pip-audit` JSON, and the image and base digests. |

Order: run `scan.sh`, read the result, and build `runtime`
(`docker build --target runtime -t code-comments-pilot:runtime evaluation/pilot`)
only when the audit is clean or the user has decided on each finding.

## Scan result, 2026-11-07

- **Start commit:** narwhals `7d3a326100decf6258cc5386fbb5ad70990b36bd`, the parent of
  PR #3996's merge commit.
- **Tools:** uv 0.13.5 and pip-audit 2.10.1 (the PyPI advisory service, via
  pip-audit's default), on the digest-pinned `python:3.12-slim` base.
- **Scope:** narwhals' `core` and `tests` dependency groups plus the `dask` extra.
  The backends are pandas, polars, pyarrow, duckdb, sqlframe and dask. pyspark,
  modin, cudf and ibis are excluded, so tests for those backends are skipped.
- **Result:** 45 pins exported, 38 audited, **0 known vulnerabilities**. The other 7
  (colorama, exceptiongroup, importlib-metadata, pytz, tomli, tzdata, zipp) carry
  environment markers for Windows or Python below 3.12, so they are not installed
  in this image.
- **Main versions:** pandas 3.0.6, polars 1.44.2, pyarrow 25.0.1, duckdb 1.5.5,
  dask 2026.8.0, sqlframe 4.4.0, numpy 2.5.3, pytest 9.1.1, hypothesis 6.168.3.

## Limits

- `pip-audit` covers Python packages only. The Debian packages in the base image
  are not scanned. They come from the official image, pinned by digest.
- The audit reflects advisories known on 2026-11-07. Rerun `scan.sh` if the full run
  starts much later.
- The model sessions (#41) need API credentials inside the container. How they are
  passed is decided in #41, before the smoke run.
