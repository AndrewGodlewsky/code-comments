## Review of dp-02 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short 'Terms used' section defining raw log, offset, KV store, archive, closed day and duplicate for readers new to the stack.
- Added a flow diagram line for the replay path (staging -> atomic swap into events_clean) and fixed the arrow notation.
- Defined 'watermark' inline in step 15 instead of leaving it undefined.
- Fixed the latency budget: the stages sum to about 3 minutes, so the old 3-minute freshness alert would fire constantly; changed it to 4 minutes and stated the slack. This is a substantive change to flag.
- Moved the latency table out of the list indentation so it renders correctly in Markdown, and replaced the 'less than or equal' symbols with words.
- Split old step 27 and clarified its purpose (why days D-8 to D-1 are read); retitled it 'Read the inputs'.
- Clarified step 13 on repeated (partition, offset) versus genuine duplicate events, and step 17 to say 'different (partition, offset)' instead of 'coordinate'.
- Reworded step 11 ('batch of records' instead of 'file') and tightened several sentences; replaced a typographic minus in D-8 with a plain hyphen.
- Part D now states directly that product has not decided and the plan does not choose; the substance is unchanged.
- Added a definition of Enrichment and Watermark to the terms list, and pointed the watermark term to step 15, so a reader new to the stack meets them defined before use.
- Step 8 now says why keying by event_id matters (it routes copies to the same partition).
- Step 13 file names now include the day as well as partition and offset range, matching step 11's split across days.
- Step 15 retitled and reworded to separate the lag alerts from the watermark definition.
- Step 20 now says micro-batches are sent to the loader, not 'written', to avoid confusion with warehouse writes.
- Step 23: indented the sentence after the table so it stays part of the step.
- Step 28 wording tightened: 'keep a copy' and 'lowest offset among its copies in D' instead of the ambiguous 'first copy only ... this copy has the lowest offset within D'.
- Kept all numbering, structure, decisions and the open bot-traffic item unchanged.
- Redrew the data flow diagram so the live path and replay path are separate and it is clear that the archiver and live processor both consume the raw log, while replay reads only the archive.
- Added a 'Micro-batch' term to the glossary since it is used before being explained.
- Made the watermark definition precise: the highest time T such that every record in that partition with received_at up to T is archived.
- Explained in step 24 why replay needs the 8 days before D (it matches the live 8-day dedup memory).
- Fixed the step 23 table and the text after it so they nest correctly under the numbered item.
- Minor wording tweaks (for example 'routes copies of one event to the same partition'); steps, numbering and content are otherwise unchanged.

### Holes
- None.
