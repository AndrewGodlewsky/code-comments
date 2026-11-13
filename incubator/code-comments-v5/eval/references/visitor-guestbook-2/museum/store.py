"""Visitor comments, as the guestbook kiosk saves them."""

from collections import namedtuple

Comment = namedtuple("Comment", "exhibit_id posted_at text")


class CommentStore:
    def __init__(self):
        self._comments = []

    def add(self, exhibit_id, posted_at, text):
        self._comments.append(Comment(exhibit_id, posted_at, text))

    def for_exhibit(self, exhibit_id):
        """Return the comments left at one exhibit, newest first."""
        found = [c for c in self._comments if c.exhibit_id == exhibit_id]
        return sorted(found, key=lambda c: c.posted_at, reverse=True)
