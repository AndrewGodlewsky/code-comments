Guestbook comments now go on the visit page escaped, so a comment that holds markup or a
script shows as plain text and cannot run.

One correction to the premise: render_caption does not escape HTML, whatever its docstring
said. It puts the text in as written and only turns line breaks into `<br>`. Wall labels
rely on that: the catalogue export wraps Latin names in `<em>`, and museum/labels.py says
the label must keep those tags. Passing comments straight to render_caption would have left
kiosk text on the page as live markup.

So `guestbook_html` now escapes each comment with `html.escape` first, then passes it to
render_caption for the caption paragraph and line breaks. I left render_caption's behaviour
alone, so the labels keep their italics, and corrected its docstring to say that it keeps
markup and escapes nothing. The tests pass.
