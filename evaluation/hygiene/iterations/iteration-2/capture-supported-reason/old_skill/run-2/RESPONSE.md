DATA-412: staging batches are now written sorted by customer_id

I changed `write_batch` in `pipeline/stage.py` so each batch is sorted by customer_id before it is written. The loader merge-joins each batch in one pass, so out-of-order rows were being skipped; the sort now happens on our side and the loader is untouched.

What changed:
- The batch is cleaned first and then sorted on the cleaned `customer_id`. The order matters: `clean()` trims whitespace from the id, so sorting the raw values could leave the written order wrong.
- A short comment above the sort records why it exists (the single-pass merge-join and the silent skip), so the next editor does not remove it as unnecessary.

Verification:
- I ran a smoke test with a fake sink and an unsorted batch including a padded id (`" 10 "`). The rows came out in order and the emails were lower-cased. I did not run the loader or check against real data, and the repository has no test suite.

Open points for you to check:
- The sort is plain Python string order, so ids compare as text: `"1" < "10" < "2"`. If the loader expects a different order (numeric, or a specific collation), the fix will not match it. I could not see the loader's comparison rule from here, so please confirm it.
- Duplicate customer_ids within or across batches are not handled. A single-pass merge-join may have its own problem with duplicates, and this change does not address that.
- The whole batch is held in memory to sort it. That is fine for batch sizes I could see, but it is a change if batches are large.
- The 3% loss is attributed to out-of-order rows in the ticket. I did not reproduce it, so confirming the cause against last night's data would be worthwhile.
