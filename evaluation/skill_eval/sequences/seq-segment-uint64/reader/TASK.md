# Support 64-bit segment sequence numbers

The log writer switches to unsigned 64-bit segment sequence numbers in the next
release. Update `segments.py` so that `segment_name` accepts every sequence
number from 0 up to and including `2**64 - 1`, and raises `ValueError` for
anything larger (as it already does for negative or non-integer values).
`parse_segment` must keep returning the sequence number for any name that
`segment_name` produces.

Ops will migrate the segment files already on disk during the upgrade window if
the naming changes, so you don't need to handle existing files.
