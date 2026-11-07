DEFAULT_PAGE_SIZE = 20


def page_slice(items, page, page_size=DEFAULT_PAGE_SIZE):
    if page < 1:
        raise ValueError("page numbers start at 1")
    start = (page - 1) * page_size
    return items[start:start + page_size]


def page_count(total, page_size=DEFAULT_PAGE_SIZE):
    return -(-total // page_size)


def has_next(page, total, page_size=DEFAULT_PAGE_SIZE):
    return page < page_count(total, page_size)
