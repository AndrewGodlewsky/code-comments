MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def check_size(data):
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"upload exceeds {MAX_UPLOAD_BYTES} bytes")
    return len(data)


def chunks(data, size=1024 * 1024):
    for start in range(0, len(data), size):
        yield data[start:start + size]
