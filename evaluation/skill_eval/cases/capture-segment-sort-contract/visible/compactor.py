"""Find write-ahead-log segments that a snapshot has made redundant.

Shared by the compaction job and the offline replay tool.
"""

from segments import PREFIX, SUFFIX, parse_segment


def segment_files(names):
    return [name for name in names if name.startswith(PREFIX) and name.endswith(SUFFIX)]


def latest_segment(names):
    """The active segment: the one the log writer is appending to."""
    candidates = sorted(segment_files(names))
    return candidates[-1] if candidates else None


def redundant_segments(names, snapshot_seq):
    """Segments wholly covered by the snapshot, never including the active one."""
    active = latest_segment(names)
    return [
        name for name in sorted(segment_files(names))
        if name != active and parse_segment(name) < snapshot_seq
    ]
