# Changelog

## 2026-08-20
- Exporter sorts records by id before batching (INC-231).

## 2026-07-01
- Warehouse migration complete: the exporter now loads through
  `/api/v2/load`. The v1 endpoint was shut down on 2026-07-15.

## 2026-03-10
- Exporter batches at 500 records per request.
