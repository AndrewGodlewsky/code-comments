---
tags: [skill-creator]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

Visitor comments from the guestbook kiosk go onto the exhibit visit pages exactly as they were typed. render_caption already escapes HTML (its docstring says so), so please run each guestbook comment through render_caption before it goes on the page. That way nobody can slip markup or a script onto our pages from the kiosk.
