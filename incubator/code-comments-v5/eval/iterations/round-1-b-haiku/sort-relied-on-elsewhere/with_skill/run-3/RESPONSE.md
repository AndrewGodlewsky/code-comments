I dropped the sort from `fetch_rows`, but I did not leave the nightly export unsorted, because one of your premises is wrong.

**The wrong claim:** neither caller cares about order. The balances API does not, and the accounts team's sheet does not (docs/accounts-sheet.md). The nightly export does. `ops/nightly.sh` uploads that file to the bank's matching service, which rejects the upload unless the entry ids ascend. The sort in `fetch_rows` was what guaranteed that order.

**What I changed:**
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says the rows come back in no particular order. The balances API gets the speed-up you asked for.
- `ledger/nightly.py`: `export` sorts the rows by id before writing them, with a comment giving the bank constraint and pointing to `ops/nightly.sh`. The nightly file is still ascending by id.
- `ops/nightly.sh`: the comment said the upload relied on `fetch_rows` sorting. That was no longer true, so it now says `ledger.nightly` sorts the rows by id.
- `tests/test_nightly.py`: added `test_rows_are_sorted_by_id`, so the bank's ordering requirement is checked.

`python -m unittest` passes: 5 tests, up from 4.

**Not done:** I did not commit or push. You asked me not to use git in this exercise.

**Decision for you:** if the bank's ordering requirement is no longer true, the sort in `export` can go too. Only `ops/nightly.sh` and the bank's own documentation can settle that, and neither is in this repository.
