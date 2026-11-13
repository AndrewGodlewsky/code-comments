---
type: llm
focus: preservation
weight: 1
---

render_caption, called with only the text, still keeps markup as written: `<em>Atta cephalotes</em> & co` comes back as `<p class="caption"><em>Atta cephalotes</em> & co</p>`, even after a visit page with comments has been built.
