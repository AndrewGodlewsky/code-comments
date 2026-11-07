# Contrasting examples

Each pair shows a bad comment and a better one, with a line on why, adapted from
the sources behind this skill. Use them to calibrate judgement, not as templates.
Every "good" version assumes the task evidence (the request, a ticket, a test, a
commit) establishes what it states. Without that evidence, see section 3.

## Contents

- [1. Keep it true](#1-keep-it-true): falsified elsewhere (1.1), one wrong clause
  (1.2), misattached (1.3), labelled not fixed (1.4), narrated history (1.5)
- [2. Capture](#2-capture-what-the-code-cannot-say): invariant (2.1), assumption
  and its expiry (2.2), decisive choice (2.3), deliberate oddity (2.4), wasteful
  on purpose (2.5), origin of a constant (2.6)
- [3. Never invent](#3-never-invent): fabricated reason versus the gap (3.1),
  contract copied from buggy code (3.2)
- [4. Restraint](#4-restraint): restating (4.1), labels and placeholders (4.2),
  commented-out code (4.3), a routine fix (4.4)

## 1. Keep it true

### 1.1 A change falsifies a comment outside the edited lines

```python
# ---- bad: the edit changed the sort key; the module header was not touched ----
"""Search page helpers. Results are listed alphabetically by title."""
def rank(results):
    return sorted(results, key=lambda r: r.score, reverse=True)

# ---- good: the header is corrected in the same edit ----
"""Search page helpers. Results are listed best match first."""
```

Why: the next agent reads the header first and believes it, so look beyond the
lines you touched. *(After Parnas; the comment-misleads studies.)*

### 1.2 One wrong clause in a good comment

```java
// ---- bad: load() now throws on a parse error, but one clause still says otherwise ----
/** Reads the theme file, validates it, and logs any parse error, falling back to defaults. */
Theme load(Path file) throws ThemeException { ... }

// ---- good: every clause checked against the final code ----
/** Reads the theme file and validates it; throws ThemeException if it does not parse. */
Theme load(Path file) throws ThemeException { ... }
```

Why: the true clauses make the false one persuasive; one wrong "how" clause was
enough to steer a model to a wrong fix. *(From the comments-and-bug-fixing study.)*

### 1.3 A comment that travelled to the wrong code

```go
// ---- bad: flush was extracted from Write, and Write's lock note came along ----
// Caller must hold w.mu.
func (w *Writer) flush() error { w.mu.Lock(); defer w.mu.Unlock(); ... }

// ---- good: the comment describes the code it now sits on ----
// flush takes w.mu itself, so callers must not hold it.
func (w *Writer) flush() error { w.mu.Lock(); defer w.mu.Unlock(); ... }
```

Why: a coherent comment about different code hurt models more than random noise;
after moving code, recheck what travelled with it. *(The comment-misleads studies.)*

### 1.4 Labelled, not fixed

```typescript
// ---- bad: a stale claim "disarmed" with a label ----
// NOTE: may be outdated. Renders at most 50 rows; the rest load on scroll.
const PAGE_SIZE = 200;

// ---- good: the claim is corrected ----
// Renders PAGE_SIZE rows; the rest load on scroll.
const PAGE_SIZE = 200;
```

Why: tagging misleading text left nearly all its effect on code models; the reader
still absorbs "50". *(From the comment-traps study.)*

### 1.5 The story of the change instead of the design

```python
# ---- bad: narrates history ----
# Switched from a regex to a trie in March after search got slow.
index = PrefixTrie(words)

# ---- good: states why the design is what it is now ----
# A trie keeps prefix lookup proportional to the query length, not the vocabulary size.
index = PrefixTrie(words)
```

Why: version control keeps the history, and a narrative contradicts the code the
next time it changes. *(After Parnas, "faking" a rational design.)*

## 2. Capture what the code cannot say

### 2.1 An invariant at the point of reliance

```go
// ---- bad: the search relies on an ordering nobody states ----
i := sort.Search(len(r.spans), func(i int) bool { return r.spans[i].end > pos })

// ---- good: the invariant sits where a careless edit would break it ----
// spans stays sorted by start and non-overlapping (insert merges neighbours),
// so the first span ending after pos is the only one that can contain it.
i := sort.Search(len(r.spans), func(i int) bool { return r.spans[i].end > pos })
```

Why: an edit to `insert` that skips the merge breaks this line silently; the note
names the coupling where it matters. *(After Knuth's literate programs.)*

### 2.2 An assumption and the condition that breaks it

```java
// ---- bad ----
int pivot = ids[lo]; // pick pivot

// ---- good ----
// First-element pivot is fine because ids are hash-assigned, so they arrive in
// random order. Sorted input would make this quadratic; revisit if that changes.
int pivot = ids[lo];
```

Why: saying when the assumption stops holding tells the next editor when the
decision has expired. *(After the 1956 FORTRAN manual; Google on noting factors.)*

### 2.3 The decisive choice

```typescript
// ---- bad: narrates steps and misses the one thing that matters ----
for (const [i, n] of nums.entries()) {
  const j = seen.get(target - n); // look up complement
  if (j !== undefined) return [j, i];
  seen.set(n, i); // store index
}

// ---- good: names the choice and what it rules out ----
  // Look up before storing, so an element is never paired with itself.
  const j = seen.get(target - n);
  if (j !== undefined) return [j, i];
  seen.set(n, i);
```

Why: swapping the steps looks harmless and is wrong; one decision like this ("a
sum, not a product") most helped weaker models. *(The talking-while-coding study.)*

### 2.4 A deliberate oddity

```java
// ---- bad: looks like an oversight ----
try { channel.close(); } catch (IOException e) { }

// ---- good ----
try {
    channel.close();
} catch (IOException ignored) {
    // Deliberate: this runs at shutdown after the final flush succeeded, so a
    // close failure loses no data and has nowhere useful to be reported.
}
```

Why: an empty catch invites a "fix"; saying it is intentional, and why, stops the
next agent from adding unwanted handling. *(After Google's rules on empty catches.)*

### 2.5 Code that looks wasteful on purpose

```typescript
// ---- bad: no reason given, so the clone looks like waste ----
plugin.init(structuredClone(baseConfig));

// ---- good ----
// Clone per plugin rather than share one object: plugins mutate the config they
// receive, and a shared object would carry one plugin's settings into the next.
plugin.init(structuredClone(baseConfig));
```

Why: code slower than it needs to be gets "optimised" unless the reason sits beside
it. *(After von Neumann's deliberately less efficient routine; Chesterton's fence.)*

### 2.6 Where a constant comes from

```go
// ---- bad: copies the value, gives no source ----
const maxUDPPayload = 1232 // max payload is 1232 bytes

// ---- good: names the origin and what it is tied to ----
// EDNS buffer size recommended by DNS Flag Day 2020 to avoid IP fragmentation.
// Keep in step with the buffer size the resolver advertises.
const maxUDPPayload = 1232
```

Why: the source tells an editor what must change with the value; the number in
prose is a copy that drifts. *(After historical constant notes; Pragmatic DRY.)*

## 3. Never invent

### 3.1 A fabricated reason versus reporting the gap

```typescript
// ---- bad: a plausible reason no evidence supports ----
// 340 ms matches the median pause between keystrokes.
const SEARCH_DEBOUNCE_MS = 340;

// ---- good: the code stays silent on the reason ----
const SEARCH_DEBOUNCE_MS = 340;
```

Why: an invented reason is wrong and looks authoritative, so the next agent will
defend it. Report the gap instead: "I couldn't find why the search debounce is
340 ms; worth recording if someone knows." *(After "do not turn inference into
history"; Parnas notes missing information rather than filling it.)*

### 3.2 A contract copied from the buggy code

```python
# Request: "chunk() drops the tail; the last chunk may be shorter, nothing lost."
# ---- bad: the docstring paraphrases the code being fixed ----
def chunk(items, size):
    """Split items into consecutive lists of exactly `size` items."""
    return [items[i:i + size] for i in range(0, len(items) - size + 1, size)]

# ---- good: the contract comes from the request, and the code matches it ----
def chunk(items, size):
    """Split items into consecutive lists of `size`; the last may be shorter."""
    return [items[i:i + size] for i in range(0, len(items), size)]
```

Why: a faithful description of buggy logic hides the bug; comments generated from
buggy code did not help repair models. *(The comments-and-bug-fixing study.)*

## 4. Restraint

### 4.1 Restating the code

```python
# ---- bad ----
# Sort the scores
scores.sort()
# Iterate over (index, value) pairs
for rank, score in enumerate(scores, start=1): ...

# ---- good: the code already says it ----
scores.sort()
for rank, score in enumerate(scores, start=1): ...
```

Why: each restatement is a second copy to maintain and buries the comments that
matter. *(The Pragmatic Programmer; the talking-while-coding study.)*

### 4.2 Labels and placeholder docs

```java
// ---- bad ----
/** Sample class. */
public final class Swatch {
    // Constructor
    public Swatch(Color base) { ... }
    /** Gets the base. @return the base */
    public Color getBase() { ... }

// ---- good: one fact the names cannot carry ----
/** Immutable, so palettes can share swatches without copying them. */
public final class Swatch {
    public Swatch(Color base) { ... }
    public Color getBase() { ... }
```

Why: labels add lines without facts; the one sentence worth writing says why the
type exists or what it promises. *(After Software Engineering at Google.)*

### 4.3 Commented-out code

```python
# ---- bad: the replaced call left above the new one ----
# conn = ssl.wrap_socket(sock)
conn = ssl.create_default_context().wrap_socket(sock, server_hostname=host)

# ---- good: deleted; version control keeps it ----
conn = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
```

Why: a commented-out insecure call near the cursor led code models to reproduce
it. Delete what you replace. If you *find* old commented-out code near your edit,
leave it and mention it to the user. *(From the comment-traps study.)*

### 4.4 A routine fix that needs nothing

```go
// ---- bad: the comment tells the story of the fix ----
last := rows[len(rows)-1] // fixed off-by-one: was rows[len(rows)]

// ---- good: a plain fix; the story goes in the commit message ----
last := rows[len(rows)-1]
```

Why: nothing here could mislead a capable reader, so a comment is only noise that
goes stale. *(Google review practice; the talking-while-coding study on volume.)*
