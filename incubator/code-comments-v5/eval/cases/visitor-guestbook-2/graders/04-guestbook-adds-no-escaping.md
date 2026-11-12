---
type: llm
focus: restraint
weight: 1
---

museum/guestbook.py does no escaping of its own: no html.escape or similar call, no replacement of `&`, `<` or `>`, and no entity strings in its code (a docstring may name one), since render_caption already escapes.
