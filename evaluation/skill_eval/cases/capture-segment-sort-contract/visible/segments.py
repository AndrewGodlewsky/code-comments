"""Name write-ahead-log segment files."""

PREFIX = "segment-"
SUFFIX = ".log"


def segment_name(seq):
    if type(seq) is not int or seq < 0:
        raise ValueError(f"segment sequence must be a non-negative integer: {seq!r}")
    return f"{PREFIX}{seq}{SUFFIX}"


def parse_segment(name):
    return int(name[len(PREFIX):-len(SUFFIX)])
