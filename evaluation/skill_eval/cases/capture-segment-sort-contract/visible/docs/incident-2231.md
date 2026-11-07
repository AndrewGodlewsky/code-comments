# Incident 2231: compaction treated an old segment as active

**Timeline:** At 03:12 the log writer on db-3 closed `segment-9.log` and opened
`segment-10.log`. The next compaction run reported `segment-9.log` as the
active segment and listed `segment-10.log` among the redundant ones. Nothing was
deleted only because the snapshot was behind. Replay on the standby started
from the wrong segment the same night.

**Standup hypothesis:** db-3 moved to XFS last week, and XFS returns directory
entries in a different order, so the compactor sees the files in the wrong
order. Checked and ruled out: the compactor never relies on directory listing
order, and the same misbehaviour reproduces on ext4 with the names in any
order.

**Root cause:** the segment file name format. See how `compactor.py` decides
which segment is active.

**Constraints:** the log writer assigns segment sequence numbers as unsigned
32-bit integers starting from 0. Ops will rename existing files during the
maintenance window.
