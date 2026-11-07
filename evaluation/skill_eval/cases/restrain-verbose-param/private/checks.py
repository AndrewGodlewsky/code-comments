"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""

import inspect
from pathlib import Path
import tempfile


def check():
    failures = []
    module = load("csv_import", failures)
    if module is None:
        return failures
    for name in ("read_rows", "read_emails", "count_rows"):
        function = getattr(module, name, None)
        parameter = inspect.signature(function).parameters.get("delimiter") if function else None
        if parameter is None or parameter.default != ",":
            failures.append(f"{name}: needs a `delimiter` parameter defaulting to ','")
    with tempfile.TemporaryDirectory() as folder:
        comma = Path(folder) / "comma.csv"
        comma.write_text("name,email\nAda, Ada@Example.com \nBob,\n", encoding="utf-8")
        semi = Path(folder) / "semi.csv"
        semi.write_text("name;email\nZoë;ZOE@example.org\nNo mail;\nIvo;ivo@example.org\n", encoding="utf-8")
        expect(failures, "read_rows default", lambda: module.read_rows(str(comma)),
               [{"name": "Ada", "email": " Ada@Example.com "}, {"name": "Bob", "email": ""}])
        expect(failures, "read_emails default", lambda: module.read_emails(str(comma)), ["ada@example.com"])
        expect(failures, "count_rows default", lambda: module.count_rows(str(comma)), 2)
        expect(failures, "read_rows ;", lambda: module.read_rows(str(semi), delimiter=";"),
               [{"name": "Zoë", "email": "ZOE@example.org"}, {"name": "No mail", "email": ""},
                {"name": "Ivo", "email": "ivo@example.org"}])
        expect(failures, "read_emails ;", lambda: module.read_emails(str(semi), delimiter=";"),
               ["zoe@example.org", "ivo@example.org"])
        expect(failures, "count_rows ;", lambda: module.count_rows(str(semi), delimiter=";"), 3)
    return failures
