"""Caption paragraphs for the visit pages."""


def render_caption(text):
    """Return text as a caption paragraph for a visit page.

    HTML special characters in text are escaped, so the caption shows exactly what
    was typed. Line breaks become <br> tags.
    """
    body = text.strip().replace("\n", "<br>")
    return f'<p class="caption">{body}</p>'
