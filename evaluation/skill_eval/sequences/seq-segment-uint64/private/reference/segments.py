"""Name write-ahead-log segment files."""

PREFIX = "segment-"
SUFFIX = ".log"
MAX_SEQ = 2**64 - 1  # the log writer assigns unsigned 64-bit sequence numbers
SEQ_DIGITS = len(str(MAX_SEQ))  # 20


def segment_name(seq):
    if type(seq) is not int or not 0 <= seq <= MAX_SEQ:
        raise ValueError(f"segment sequence must be an integer from 0 to {MAX_SEQ}: {seq!r}")
    # Zero-pad to a fixed width: compactor.latest_segment picks the active
    # segment by sorting names as strings, so every name needs the same number
    # of digits for segment 10 to sort after 9. Changing the width means
    # renaming the files on disk, because a mix of widths sorts wrongly.
    return f"{PREFIX}{seq:0{SEQ_DIGITS}d}{SUFFIX}"


def parse_segment(name):
    return int(name[len(PREFIX):-len(SUFFIX)])
