"""Parse the comma-separated tag lists that users type into the search box."""


def parse_tags(text):
    """Split text on commas into lower-case tags, dropping blanks and repeats.

    Raises ValueError if text is None or holds no tags.
    """
    if text is None:
        raise ValueError("no tag text")
    tags = []
    for part in text.split(","):
        tag = part.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    if not tags:
        raise ValueError("no tags in text")
    return tags
