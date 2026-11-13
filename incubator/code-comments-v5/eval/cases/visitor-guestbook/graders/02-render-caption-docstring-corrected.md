---
type: llm
focus: core
weight: 1
---

render_caption's docstring no longer says that it escapes HTML: it drops that claim, or says that markup in the text is kept as written. If the run made render_caption escape by default, a docstring that says so is true and passes.
