# Invalid climb run: placeholder artifact

`mig-02/junior-v1/sonnet/natural/run-1` from climb iteration 1. The loop ended on a correct
teach-back, but the author answered the verdict step with the placeholder "Unchanged: the
document as given above" instead of the document. The harness took the placeholder as the
final plan, so the readers saw 42 words and scored 0.00. The harness now keeps the current
document on a correct verdict, and rejects any returned artifact under 30% of the current
length (`test_placeholder_artifacts_never_replace_the_document`). The run was rerun in
`iterations/climb-01/`. A scan of every other run found no other case like it.
