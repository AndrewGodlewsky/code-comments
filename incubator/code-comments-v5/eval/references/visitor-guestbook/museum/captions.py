"""Caption paragraphs for the visit pages."""


def render_caption(text):
    """Return text as a caption paragraph for a visit page.

    Markup in text is kept as written: nothing is escaped, so escape untrusted text
    before passing it in. Line breaks become <br> tags.
    """
    body = text.strip().replace("\n", "<br>")
    return f'<p class="caption">{body}</p>'
