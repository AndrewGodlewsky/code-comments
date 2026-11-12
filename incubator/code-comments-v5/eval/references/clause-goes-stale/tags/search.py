"""Build search filters from request parameters."""

from tags.parse import parse_tags


def tag_filter(params):
    """Return the tags to filter on, or None when the request has no tag filter."""
    text = params.get("tags")
    # No parameter means no filter, which is not the same as an empty tag list.
    if text is None:
        return None
    return parse_tags(text)
