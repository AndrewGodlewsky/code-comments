"""Paging for search results."""

from app.config import PAGE_SIZE


def page(results, number):
    """Return page number (counting from 1) of results."""
    start = (number - 1) * PAGE_SIZE
    return results[start:start + PAGE_SIZE]
