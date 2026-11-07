"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""

import ast
from pathlib import Path

LIMIT = 10 * 1024 * 1024


def _uses_settings_constant(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "settings":
            if any(alias.name in ("MAX_UPLOAD_BYTES", "*") for alias in node.names):
                return True
        if isinstance(node, ast.Attribute) and node.attr == "MAX_UPLOAD_BYTES":
            if isinstance(node.value, ast.Name) and node.value.id == "settings":
                return True
    return False


def _defines_constant(tree):
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else []
        if any(isinstance(target, ast.Name) and target.id == "MAX_UPLOAD_BYTES" for target in targets):
            return True
    return False


def check():
    failures = []
    settings = load("settings", failures)
    uploads = load("uploads", failures)
    api = load("api", failures)
    if None in (settings, uploads, api):
        return failures
    expect(failures, "settings.MAX_UPLOAD_BYTES", lambda: getattr(settings, "MAX_UPLOAD_BYTES", None), LIMIT)
    expect(failures, "settings.DEFAULT_REGION", lambda: settings.DEFAULT_REGION, "eu-west-1")
    for module in (uploads, api):
        name = Path(module.__file__).name
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        if _defines_constant(tree):
            failures.append(f"{name} still defines its own MAX_UPLOAD_BYTES")
        if not _uses_settings_constant(tree):
            failures.append(f"{name} does not take MAX_UPLOAD_BYTES from settings")
    expect(failures, "check_size ok", lambda: uploads.check_size(b"x" * 10), 10)
    expect(failures, "check_size at limit", lambda: uploads.check_size(b"x" * LIMIT), LIMIT)
    expect_raises(failures, "check_size over", lambda: uploads.check_size(b"x" * (LIMIT + 1)), ValueError)
    expect(failures, "chunks", lambda: [len(c) for c in uploads.chunks(b"x" * (2 * 1024 * 1024 + 5))], [1048576, 1048576, 5])
    expect(failures, "handle_upload ok", lambda: api.handle_upload({"body": b"abc"}), {"status": 201, "size": 3})
    expect(failures, "handle_upload over", lambda: api.handle_upload({"body": b"x" * (LIMIT + 1)}),
           {"status": 413, "error": "payload too large"})
    expect(failures, "describe_limits", lambda: api.describe_limits(), {"max_upload_bytes": LIMIT})
    return failures
