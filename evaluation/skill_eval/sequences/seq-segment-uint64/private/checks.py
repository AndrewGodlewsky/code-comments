"""Hidden checks for the reader step. `load`, `expect`, `expect_raises` are injected by check_runner."""

import random


STEP1_SEQS = [0, 1, 7, 9, 10, 11, 99, 100, 101, 999999, 1000000, 999999999, 1000000000, 4294967294, 4294967295]
WIDE_SEQS = [0, 9, 10, 4294967295, 4294967296, 9999999999, 10000000000, 2**63, 2**64 - 2, 2**64 - 1]


def names_for(segments, seqs, failures):
    names = []
    for seq in seqs:
        try:
            names.append(segments.segment_name(seq))
        except Exception as error:
            failures.append(f"segment_name({seq}) raised {type(error).__name__}: {error}")
            return None
    return names


def check_names(segments, compactor, seqs, label, failures):
    names = names_for(segments, seqs, failures)
    if names is None:
        return
    for seq, name in zip(seqs, names):
        middle = name[len(segments.PREFIX):-len(segments.SUFFIX)] if len(name) > len(segments.PREFIX) + len(segments.SUFFIX) else ""
        if not (name.startswith(segments.PREFIX) and name.endswith(segments.SUFFIX) and middle.isdigit() and middle.isascii()):
            failures.append(f"segment_name({seq}) = {name!r} is not PREFIX + digits + SUFFIX")
        expect(failures, f"parse_segment round trip {seq}", lambda n=name: segments.parse_segment(n), seq)
    expect(failures, f"{label}: string order equals numeric order", lambda: sorted(names), names)
    shuffled = list(names)
    random.Random(2231).shuffle(shuffled)
    expect(failures, f"{label}: latest_segment picks the highest sequence", lambda: compactor.latest_segment(shuffled), names[-1])


def check():
    failures = []
    segments = load("segments", failures)
    compactor = load("compactor", failures)
    if segments is None or compactor is None:
        return failures
    # Step-1 behaviour (no regressions).
    check_names(segments, compactor, STEP1_SEQS, "uint32 range", failures)
    window = names_for(segments, (8, 9, 10, 11, 12), failures)
    if window is not None:
        random.Random(9).shuffle(window)
        expect(failures, "redundant_segments below snapshot", lambda: compactor.redundant_segments(window + ["notes.txt"], 11),
               [segments.segment_name(seq) for seq in (8, 9, 10)])
        expect(failures, "active segment never redundant", lambda: compactor.redundant_segments(window, 99),
               [segments.segment_name(seq) for seq in (8, 9, 10, 11)])
    for bad in (-1, True, "3", 1.5):
        expect_raises(failures, f"segment_name({bad!r})", lambda b=bad: segments.segment_name(b), ValueError)
    # New: the full uint64 range, mixed with small sequence numbers.
    check_names(segments, compactor, WIDE_SEQS, "uint64 range", failures)
    span = names_for(segments, (9999999998, 9999999999, 10000000000, 10000000001), failures)
    if span is not None:
        random.Random(64).shuffle(span)
        expect(failures, "redundant_segments across the 10-digit boundary", lambda: compactor.redundant_segments(span, 10000000001),
               [segments.segment_name(seq) for seq in (9999999998, 9999999999, 10000000000)])
    for bad in (2**64, 2**70):
        expect_raises(failures, f"segment_name({bad}) beyond uint64", lambda b=bad: segments.segment_name(b), ValueError)
    return failures
