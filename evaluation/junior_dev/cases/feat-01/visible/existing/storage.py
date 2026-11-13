"""Object storage helpers (existing). The `exports` bucket already exists.

Lifecycle rules on the `exports` bucket:
  - every object is deleted 7 days after it was created
  - a multipart upload that is not completed within 24 hours is discarded
"""

MIN_PART_BYTES = 5 * 1024 * 1024  # each part except the last must be >= 5 MB
MAX_PARTS = 10_000


def start_multipart(bucket, key):
    """Begin a multipart upload and return its upload_id.
    Nothing is visible at `key` until complete_multipart succeeds."""


def upload_part(upload_id, part_number, data):
    """Upload one part (part_number counts from 1). Returns an etag."""


def complete_multipart(upload_id, etags):
    """Join the parts and make the object visible at its key,
    replacing any object already there."""


def abort_multipart(upload_id):
    """Discard every part uploaded so far."""


def signed_url(bucket, key, ttl_seconds):
    """Return a download URL that works for ttl_seconds.
    ttl_seconds may be at most 86_400 (24 hours)."""
