"""Wall labels for the exhibits, built from the catalogue export."""

from collections import namedtuple

from museum.captions import render_caption

Exhibit = namedtuple("Exhibit", "exhibit_id title note")


def label_html(exhibit):
    """Return the label shown beside an exhibit: its title, then the curator's note."""
    return f"<h2>{exhibit.title}</h2>" + render_caption(exhibit.note)
