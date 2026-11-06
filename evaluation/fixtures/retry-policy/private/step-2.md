# Accept the upgraded backend limit

The upgraded backend now accepts at most eight retries. The legacy maximum of
five no longer applies. Update validation to accept integers through eight and
reject larger values. Preserve override precedence, None/default semantics,
explicit zero and the rejection of non-integer values (including bool).
