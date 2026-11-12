#!/bin/sh
# Export tonight's ledger and send it to the bank's matching service.
#
# The bank matches our file against its own statement in a single pass and
# rejects the upload unless the entry ids ascend. The file goes up exactly as
# ledger.nightly writes it, in the order fetch_rows returns the rows, so this
# relies on fetch_rows returning them sorted by id.
set -eu

spool=/var/spool/ledger
out="$spool/ledger-$(date +%Y%m%d).csv"

python -m ledger.nightly "$spool/ledger.db" "$out"
curl --fail --silent --show-error --upload-file "$out" "$BANK_MATCH_URL"
