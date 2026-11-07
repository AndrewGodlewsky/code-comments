"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""

import random


SEQS = [0, 1, 7, 9, 10, 11, 99, 100, 101, 999999, 1000000, 999999999, 1000000000, 4294967294, 4294967295]


def check():
    failures = []
    segments = load("segments", failures)
    compactor = load("compactor", failures)
    if segments is None or compactor is None:
        return failures
    names = []
    for seq in SEQS:
        try:
            names.append(segments.segment_name(seq))
        except Exception as error:
            failures.append(f"segment_name({seq}) raised {type(error).__name__}: {error}")
            return failures
    for seq, name in zip(SEQS, names):
        middle = name[len(segments.PREFIX):-len(segments.SUFFIX)] if len(name) > len(segments.PREFIX) + len(segments.SUFFIX) else ""
        if not (name.startswith(segments.PREFIX) and name.endswith(segments.SUFFIX) and middle.isdigit() and middle.isascii()):
            failures.append(f"segment_name({seq}) = {name!r} is not PREFIX + digits + SUFFIX")
        expect(failures, f"parse_segment round trip {seq}", lambda n=name: segments.parse_segment(n), seq)
    expect(failures, "string order equals numeric order", lambda: sorted(names), names)
    shuffled = list(names)
    random.Random(2231).shuffle(shuffled)
    expect(failures, "latest_segment picks the highest sequence", lambda: compactor.latest_segment(shuffled), names[-1])
    window = [segments.segment_name(seq) for seq in (8, 9, 10, 11, 12)]
    random.Random(9).shuffle(window)
    expect(failures, "redundant_segments below snapshot", lambda: compactor.redundant_segments(window + ["notes.txt"], 11),
           [segments.segment_name(seq) for seq in (8, 9, 10)])
    expect(failures, "active segment never redundant", lambda: compactor.redundant_segments(window, 99),
           [segments.segment_name(seq) for seq in (8, 9, 10, 11)])
    for bad in (-1, True, "3", 1.5):
        expect_raises(failures, f"segment_name({bad!r})", lambda b=bad: segments.segment_name(b), ValueError)
    return failures
