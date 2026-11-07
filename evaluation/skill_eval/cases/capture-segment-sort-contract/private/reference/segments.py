"""Name write-ahead-log segment files."""

PREFIX = "segment-"
SUFFIX = ".log"
SEQ_DIGITS = 10


def segment_name(seq):
    if type(seq) is not int or seq < 0:
        raise ValueError(f"segment sequence must be a non-negative integer: {seq!r}")
    # Zero-pad to a fixed width: compactor.latest_segment picks the active
    # segment by sorting names as strings, so segment 10 must sort after 9.
    # Ten digits hold every uint32 sequence number the log writer assigns.
    return f"{PREFIX}{seq:0{SEQ_DIGITS}d}{SUFFIX}"


def parse_segment(name):
    return int(name[len(PREFIX):-len(SUFFIX)])
