---
type: llm
focus: core
weight: 2
---

Hidden tests pass: each guestbook comment shows on the page as typed, escaped exactly once (`<script>` and `<b>` show as text, `&` becomes `&amp;` and never `&amp;amp;`), inside its caption paragraph with line breaks as `<br>`, newest first; and an ampersand in a wall label's note is still escaped once.
