# Bug: first page of search results is missing

Support ticket #2291 (details in `docs/ticket-2291.md`): page 1 of the search
results starts at the 21st result, and the last page always comes back empty.
`page_count` and `has_next` look right to me. Please fix `page_slice` in
`paging.py`. Page numbers start at 1.
