"""Build search filters from request parameters."""

from tags.parse import parse_tags


def tag_filter(params):
    """Return the tags to filter on, or None when the request has no tag filter."""
    text = params.get("tags")
    # parse_tags rejects a missing value, so return early when the parameter is absent.
    if text is None:
        return None
    return parse_tags(text)
