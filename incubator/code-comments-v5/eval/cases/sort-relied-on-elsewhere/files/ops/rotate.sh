#!/bin/sh
# Keep eight weeks of nightly export files.
set -eu
find /var/spool/ledger -name 'ledger-*.csv' -mtime +56 -delete
