"""The page a visitor's phone opens from the code printed beside an exhibit."""

from museum.guestbook import guestbook_html
from museum.labels import label_html


def visit_page(exhibit, store):
    """Return the body of one exhibit's visit page: its label, then its guestbook."""
    return "<main>" + label_html(exhibit) + guestbook_html(store, exhibit.exhibit_id) + "</main>"
