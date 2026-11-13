The deliveries CLI (`deliveries/cli.py`) now checks what `parse_date` returns. If it gets `None`, it prints "invalid date" to stderr and exits with status 2.

I checked the docstring claim before relying on it. `parse_date` calls `read_date`, which returns `None` for text that matches no format and for dates that don't exist, such as 31/02/2026.

I ran it by hand. `python -m deliveries.cli 31/02/2026` prints "invalid date" and exits 2. `python -m deliveries.cli 2026-03-14` still prints the delivery date and exits 0. I did not add a test for the new behaviour.

A missing date argument still raises an `IndexError`. I left that alone because you only asked about invalid dates.
