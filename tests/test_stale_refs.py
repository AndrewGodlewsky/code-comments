"""Tests for the stale-reference lint (scripts/stale_refs.py, #44)."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "stale_refs.py"
_SPEC = importlib.util.spec_from_file_location("stale_refs", _PATH)
stale_refs = importlib.util.module_from_spec(_SPEC)
sys.modules["stale_refs"] = stale_refs  # dataclasses look the module up while it loads
_SPEC.loader.exec_module(stale_refs)


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")


def refs(files: dict[str, str], **kwargs) -> list[str]:
    """The refs the lint reports for a fixture tree."""
    with tempfile.TemporaryDirectory() as temporary:
        write(Path(temporary), files)
        return [f.ref for f in stale_refs.lint(Path(temporary), **kwargs)]


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = stale_refs.main(argv)
    return code, out.getvalue(), err.getvalue()


BASE = {
    "pkg/core.py": '''
        def parse_rows(text):
            return text.split()


        class Loader:
            def load(self):
                return parse_rows("")
        ''',
    "README.md": "readme\n",
}


class PositiveTests(unittest.TestCase):
    """Each kind of reference to missing code is reported."""

    def test_backticked_identifier_dotted_and_call(self):
        found = refs({**BASE, "pkg/use.py": '''
            # `read_rows` was renamed; see `Loader.fetch` and `split_rows(text)`.
            x = 1
            '''})
        self.assertEqual(sorted(found), ["Loader.fetch", "read_rows", "split_rows"])

    def test_missing_builtin_attribute_and_unrelated_plural(self):
        found = refs({**BASE, "pkg/use.py": '''
            # `str.is_alnum` and `fetchers` are not real.
            x = 1
            '''})
        self.assertEqual(sorted(found), ["fetchers", "str.is_alnum"])

    def test_prose_snake_and_bare_call(self):
        found = refs({**BASE, "pkg/use.py": '''
            # Call fetch_rows() first, then old_helper_name runs.
            x = 1
            '''})
        self.assertEqual(sorted(found), ["fetch_rows", "old_helper_name"])

    def test_docstring_reference(self):
        found = refs({**BASE, "pkg/use.py": '''
            def go():
                """Wraps `gone_helper`."""
            '''})
        self.assertEqual(found, ["gone_helper"])

    def test_missing_file_and_flag(self):
        found = refs({**BASE, "pkg/use.py": '''
            # Settings live in pkg/settings.toml; pass --dry-run to skip.
            x = 1
            '''})
        self.assertEqual(sorted(found), ["--dry-run", "pkg/settings.toml"])

    def test_heuristic_language(self):
        found = refs({**BASE, "web/app.js": '''
            // `renderPage` draws the page; don't call `paintPage` either.
            const url = "http://example.com/a"; // see `drawFrame`
            function draw() { return `tpl // not_a_comment`; }
            '''})
        self.assertEqual(sorted(found), ["drawFrame", "paintPage", "renderPage"])


class NegativeTests(unittest.TestCase):
    """Existing code, and text that only looks like a reference, are not reported."""

    def assertClean(self, files):
        self.assertEqual(refs({**BASE, **files}), [])

    def test_existing_names_resolve(self):
        self.assertClean({"pkg/use.py": '''
            # `parse_rows`, `Loader.load`, parse_rows() and `os.path.join` all exist.
            x = 1
            '''})

    def test_math_is_skipped(self):
        self.assertClean({"pkg/use.py": '''
            # Solve $x_0 + w_i$ for each step; x_0 and w_i are not names.
            x = 1
            '''})

    def test_placeholders_are_skipped(self):
        self.assertClean({"pkg/use.py": '''
            # Use `Implementation.<BACKEND>` with `BACKEND` being one of the names.
            # ### `Native<Thing>` and `<Other>Convertible` are naming patterns.
            # Results go to OUT_DIR/summary.txt or to src/.../config.py.
            x = 1
            '''})

    def test_doctest_and_fenced_names_are_known(self):
        self.assertClean({"pkg/use.py": '''
            def go():
                """Example.

                >>> sample_frame = make_frame()
                >>> missing_call()

                Then `sample_frame` holds the result.

                ```python
                fenced_value = 1
                ```
                `fenced_value` is set above.
                """
            '''})

    def test_prefix_name_resolves(self):
        self.assertClean({"pkg/use.py": '''
            # Every `parse_` helper returns a list.
            x = 1
            '''})

    def test_relative_link_falls_back_to_suffix(self):
        self.assertClean({"docs/guide/page.md": "x\n", "pkg/use.py": '''
            # See ../guide/page.md and ./README.md.
            x = 1
            '''})

    def test_flag_in_shell_code_is_known(self):
        self.assertClean({"run.sh": '''
            # Pass --index so the index is updated too.
            git apply --index patch.diff
            '''})

    def test_opt_out_and_directives(self):
        self.assertClean({"pkg/use.py": '''
            # `vanished_name` is quoted from upstream.  stale-refs: ignore
            x = 1  # type: ignore[attr-defined]
            '''})

    def test_urls_are_skipped(self):
        self.assertClean({"pkg/use.py": '''
            # From https://example.com/docs/old_page_name.py#some_anchor
            x = 1
            '''})

    def test_builtin_attributes_resolve(self):
        self.assertClean({"pkg/use.py": '''
            # `str.isalnum` accepts Unicode letters; `dict.setdefault` keeps the first.
            x = 1
            '''})

    def test_plural_of_known_name_resolves(self):
        self.assertClean({"pkg/use.py": '''
            # Both `Loader`s share one cache.
            x = 1
            '''})

    def test_name_backticked_in_docs_is_known(self):
        self.assertClean({"docs/api.md": "The issuer sends `issued_at` and `expires_in`.\n",
                          "pkg/use.py": '''
            # Don't derive the expiry from `issued_at`.
            x = 1
            '''})

    def test_allow_list(self):
        self.assertEqual(refs({**BASE, "pkg/use.py": "# `upstream_name` comes from elsewhere.\n"},
                              allow={"upstream_name"}), [])


class DiffModeTests(unittest.TestCase):
    def test_only_new_findings_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            base, head = Path(temporary, "base"), Path(temporary, "head")
            write(base, {**BASE, "pkg/use.py": "# `old_missing` predates the change.\nx = 1\n"})
            write(head, {**BASE, "pkg/use.py":
                         "# `old_missing` predates the change.\n"
                         "# `new_missing` came with it.\nx = 1\n"})
            found = stale_refs.new_findings(base, head)
            self.assertEqual([f.ref for f in found], ["new_missing"])
            code, out, _ = run([str(head), "--base-dir", str(base)])
            self.assertEqual(code, 1)
            self.assertIn("new_missing", out)
            self.assertNotIn("old_missing", out)

    def test_removing_the_code_makes_its_comment_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            base, head = Path(temporary, "base"), Path(temporary, "head")
            use = "# `parse_rows` splits the text.\nx = 1\n"
            write(base, {**BASE, "pkg/use.py": use})
            write(head, {"pkg/core.py": "def split_text(text):\n    return text.split()\n",
                         "pkg/use.py": use})
            self.assertEqual([f.ref for f in stale_refs.new_findings(base, head)], ["parse_rows"])


class CliTests(unittest.TestCase):
    def test_stats_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as temporary:
            write(Path(temporary), BASE)
            code, out, err = run([temporary, "--stats"])
            self.assertEqual((code, out), (0, ""))
            # README.md has no comments to check, so only the source file counts.
            self.assertRegex(err, r"^1 files, \d+ references checked, 0 findings")
            write(Path(temporary), {"pkg/use.py": "# `gone_name` is missing.\nx = 1\n"})
            code, out, err = run([temporary, "--stats", "--only", "pkg"])
            self.assertEqual(code, 1)
            self.assertIn("pkg/use.py:1: identifier `gone_name` not found", out)
            self.assertIn("1 findings", err)

    def test_json_output(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            write(Path(temporary), {**BASE, "pkg/use.py": "# `gone_name` is missing.\nx = 1\n"})
            code, out, _ = run([temporary, "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)[0]["ref"], "gone_name")


if __name__ == "__main__":
    unittest.main()
