I retired docs/ingest.md and moved its one fact that belongs beside the code into ingest/rows.py.

- Added to the module docstring in ingest/rows.py: "Uses only the standard library's csv module."
- The other statements on the page already live in the code: read_rows, parse_price and clean have docstrings that match the page, and is_blank is clear from its body. I did not add restating docstrings.
- Deleted docs/ingest.md. Nothing else in the repo links to it (README.md and docs/deploy.md do not mention it). tests/test_rows.py is unchanged.

Gap to check: the page does not say what parse_price does with more than two decimal places. The code truncates, so "12.509" becomes 1250 cents. I did not record this in a comment because no ticket or test states the intent. Tell me if it should be documented, and why.
