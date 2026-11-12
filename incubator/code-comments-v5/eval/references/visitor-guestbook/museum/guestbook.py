"""The guestbook at the foot of each visit page."""

from html import escape

from museum.captions import render_caption


def guestbook_html(store, exhibit_id):
    """Return the comments left at one exhibit as an HTML list, newest first."""
    # Comments come from the public kiosk and render_caption keeps markup as written,
    # so each one is escaped first.
    items = "".join(f"<li>{render_caption(escape(comment.text))}</li>"
                    for comment in store.for_exhibit(exhibit_id))
    return f'<ul class="guestbook">{items}</ul>'
