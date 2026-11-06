"""Traceability failures must fail closed before passages are presented to readers."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("comment_context", Path(__file__).resolve().parents[1] / "scripts/comment_context.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "original.txt").write_bytes(b"original")
        self.text = {"schema_version": 1, "source_id": "example", "units": [
            {"id": "p001", "source_path": "original.txt", "location": "page 1",
             "lines": ["first", "```", "qualification"]}]}
        self.write("text.json", self.text)
        self.source = {"id": "example", "title": "Example", "extent": "extract", "limitations": [],
                       "inputs": [{"path": "original.txt", "bytes": 8, "sha256": cc.sha256(self.root / "original.txt")}],
                       "text_path": "text.json", "text_sha256": cc.sha256(self.root / "text.json"), "unit_count": 1}
        self.records = {"schema_version": 1, "source_id": "example", "text_sha256": self.source["text_sha256"],
                        "records": [{"id": "example-001", "unit": "p001", "start_line": 1, "end_line": 3,
                                     "heading": "Example", "attribution": "Author", "context": "Section", "notes": "",
                                     "related_record_ids": []}]}
        self.coverage = {"schema_version": 1, "source_id": "example", "text_sha256": self.source["text_sha256"],
                         "units": [{"unit": "p001", "reading_status": "read", "checks": ["search"], "notes": ""}],
                         "search_terms": [], "exclusions": [], "unresolved_gaps": [], "audit": []}
        self.persist()

    def write(self, path, value):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def persist(self):
        self.write(cc.COLLECTION / "sources/example/records.json", self.records)
        self.write(cc.COLLECTION / "sources/example/coverage.json", self.coverage)

    def test_verbatim_render_escapes_source_fences(self):
        data = cc.validate_source(self.root, self.source)
        _, output = cc.render_source(self.root, self.source, data)
        self.assertIn("````text\nfirst\n```\nqualification\n````", output)

    def test_original_mutation_rejected(self):
        (self.root / "original.txt").write_bytes(b"changed!")
        with self.assertRaisesRegex(ValueError, "original bytes changed"):
            cc.validate_source(self.root, self.source)

    def test_derived_mutation_rejected_even_with_unchanged_original(self):
        self.text["units"][0]["lines"].insert(0, "new line")
        self.write("text.json", self.text)
        with self.assertRaisesRegex(ValueError, "text hash mismatch"):
            cc.validate_source(self.root, self.source)

    def test_repin_catalog_alone_does_not_retarget_existing_spans(self):
        self.text["units"][0]["lines"].insert(0, "new line")
        self.write("text.json", self.text)
        self.source["text_sha256"] = cc.sha256(self.root / "text.json")
        with self.assertRaisesRegex(ValueError, "stale selection"):
            cc.validate_source(self.root, self.source)

    def test_invalid_spans_and_related_records_rejected(self):
        baseline = copy.deepcopy(self.records)
        for key, value in [("start_line", 0), ("end_line", 4), ("unit", "missing"),
                           ("related_record_ids", ["missing"])]:
            with self.subTest(key=key):
                self.records = copy.deepcopy(baseline)
                self.records["records"][0][key] = value
                self.persist()
                with self.assertRaises(ValueError):
                    cc.validate_source(self.root, self.source)

    def test_duplicate_coverage_cannot_mask_missing_unit(self):
        self.coverage["units"] *= 2
        self.persist()
        with self.assertRaisesRegex(ValueError, "every unit exactly once"):
            cc.validate_source(self.root, self.source)

    def test_pending_reading_requires_explicit_flag(self):
        self.coverage["units"][0]["reading_status"] = "pending"
        self.persist()
        with self.assertRaisesRegex(ValueError, "pending reading"):
            cc.validate_source(self.root, self.source)
        cc.validate_source(self.root, self.source, allow_pending=True)


if __name__ == "__main__":
    unittest.main()
