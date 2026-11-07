# Stop compaction from picking the wrong active segment

Compaction misbehaved on db-3 once the log writer rolled past segment 9; the
incident is in `docs/incident-2231.md`. Fix it in `segments.py`.

Don't change `compactor.py`: the replay tool ships its own copy of that module
on a separate release train, so the fix has to work with it as it is. Ops will
rename the segment files already on disk, so you don't need to handle the old
names.
