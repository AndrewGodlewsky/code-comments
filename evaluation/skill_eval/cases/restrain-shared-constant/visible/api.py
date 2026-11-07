from uploads import check_size

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def handle_upload(request):
    body = request.get("body", b"")
    if len(body) > MAX_UPLOAD_BYTES:
        return {"status": 413, "error": "payload too large"}
    check_size(body)
    return {"status": 201, "size": len(body)}


def describe_limits():
    return {"max_upload_bytes": MAX_UPLOAD_BYTES}
