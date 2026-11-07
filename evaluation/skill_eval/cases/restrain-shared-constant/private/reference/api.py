from settings import MAX_UPLOAD_BYTES
from uploads import check_size


def handle_upload(request):
    body = request.get("body", b"")
    if len(body) > MAX_UPLOAD_BYTES:
        return {"status": 413, "error": "payload too large"}
    check_size(body)
    return {"status": 201, "size": len(body)}


def describe_limits():
    return {"max_upload_bytes": MAX_UPLOAD_BYTES}
