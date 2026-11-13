"""The guestbook at the foot of each visit page."""

from museum.captions import render_caption


def guestbook_html(store, exhibit_id):
    """Return the comments left at one exhibit as an HTML list, newest first."""
    items = "".join(f"<li>{render_caption(comment.text)}</li>" for comment in store.for_exhibit(exhibit_id))
    return f'<ul class="guestbook">{items}</ul>'
