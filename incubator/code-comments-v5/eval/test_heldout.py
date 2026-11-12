"""Pinned variants for the four held-out cases built for this climb.

Candidate writers do not open this file: it describes held-out cases.

Each variant is a copy of a case's input or reference with edits, graded with
``harness.grade``. Its marks are pinned: one letter per check in grader order, P for a
pass and . for a fail. A check that starts passing a wrong result, or failing a good
one, then fails a test here. The phrasing tests pin each keyword heuristic on single
sentences. The variants come from the case builders and the build review of 2026-11-11.

Run it on its own, not in the documented suite, because it describes held-out cases:

    python -B -m unittest discover -s incubator/code-comments-v5/eval -p "test_*.py"
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import harness  # noqa: E402

SKILL = "code-comments-v5"
CHECKS = harness.load_checks(SKILL)
FM1 = sys.modules["code_comments_v5_heldout_fm1"]
FM2 = sys.modules["code_comments_v5_heldout_fm2"]

TRAP1, TWIN1, TRAP2, GUARD2 = "visitor-guestbook", "visitor-guestbook-2", "pump-metric-rename", "lesson-length-sixty"


def marks(out: Path, case: str) -> tuple[str, list[str]]:
    result = harness.grade(SKILL, out, case, CHECKS)
    letters = "".join("P" if e["passed"] else "." for e in result["expectations"])
    return letters, [f"[{e['focus']}] {e['evidence'][:200]}" for e in result["expectations"] if not e["passed"]]


# ------------------------------------------------------------- FM1 bodies

FIXED_DOC = '''    """Return text as a caption paragraph for a visit page.

    Markup in text is kept as written; it does not escape HTML. Line breaks become
    <br> tags.
    """
'''

TRAP_CAPTIONS_FIXED_DOC = f'''"""Caption paragraphs for the visit pages."""


def render_caption(text):
{FIXED_DOC}    body = text.strip().replace("\\n", "<br>")
    return f'<p class="caption">{{body}}</p>'
'''

GUESTBOOK_LITERAL = '''"""The guestbook at the foot of each visit page."""

from museum.captions import render_caption


def guestbook_html(store, exhibit_id):
    """Return the comments left at one exhibit as an HTML list, newest first."""
    items = "".join(f"<li>{render_caption(comment.text)}</li>" for comment in store.for_exhibit(exhibit_id))
    return f'<ul class="guestbook">{items}</ul>'
'''

GUESTBOOK_DOUBLE = '''"""The guestbook at the foot of each visit page."""

from html import escape

from museum.captions import render_caption


def guestbook_html(store, exhibit_id):
    """Return the comments left at one exhibit as an HTML list, newest first."""
    items = "".join(f"<li>{render_caption(escape(comment.text))}</li>"
                    for comment in store.for_exhibit(exhibit_id))
    return f'<ul class="guestbook">{items}</ul>'
'''

TRAP_CAPTIONS_NOW_ESCAPES = '''"""Caption paragraphs for the visit pages."""

from html import escape


def render_caption(text):
    """Return text as a caption paragraph for a visit page.

    HTML special characters in text are escaped, so the caption shows exactly what
    was typed. Line breaks become <br> tags.
    """
    body = escape(text.strip()).replace("\\n", "<br>")
    return f'<p class="caption">{body}</p>'
'''

# render_caption escapes by default and labels opt out, so the docstring is now true.
TRAP_CAPTIONS_ESCAPE_BY_DEFAULT = '''"""Caption paragraphs for the visit pages."""

from html import escape


def render_caption(text, keep_markup=False):
    """Return text as a caption paragraph for a visit page.

    HTML special characters in text are escaped, so the caption shows exactly what
    was typed, unless keep_markup is true. Line breaks become <br> tags.
    """
    body = text.strip() if keep_markup else escape(text.strip())
    return f'<p class="caption">{body.replace(chr(10), "<br>")}</p>'
'''

TWIN_CAPTIONS_NO_ESCAPE = '''"""Caption paragraphs for the visit pages."""


def render_caption(text):
    """Return text as a caption paragraph for a visit page.

    Text is put in as written; callers escape it first. Line breaks become <br> tags.
    """
    body = text.strip().replace("\\n", "<br>")
    return f'<p class="caption">{body}</p>'
'''

TRAP_CAPTIONS_NEW_HELPER = '''"""Caption paragraphs for the visit pages."""

from html import escape


def render_caption(text):
    """Return text as a caption paragraph for a visit page.

    Text is not escaped: markup such as the <em> tags on wall labels is kept.
    Line breaks become <br> tags.
    """
    body = text.strip().replace("\\n", "<br>")
    return f'<p class="caption">{body}</p>'


def render_plain_caption(text):
    """Like render_caption, but escapes text first, for text typed by the public."""
    return render_caption(escape(text))
'''

GUESTBOOK_NEW_HELPER = '''"""The guestbook at the foot of each visit page."""

from museum.captions import render_plain_caption


def guestbook_html(store, exhibit_id):
    """Return the comments left at one exhibit as an HTML list, newest first."""
    items = "".join(f"<li>{render_plain_caption(comment.text)}</li>" for comment in store.for_exhibit(exhibit_id))
    return f'<ul class="guestbook">{items}</ul>'
'''

REF_DOC = ("Markup in text is kept as written: nothing is escaped, so escape untrusted text\n"
           "    before passing it in. Line breaks become <br> tags.")

# ------------------------------------------------------------- FM2 edits

RENAME = [("pumps/metrics.py", 'STARTS = "pump_runs_total"', 'STARTS = "pump_starts_total"')]
RULES_RENAME = [("deploy/alert_rules.yml", "increase(pump_runs_total[6h])", "increase(pump_starts_total[6h])"),
                ("deploy/alert_rules.yml", "increase(pump_runs_total[1h])", "increase(pump_starts_total[1h])")]
RULES_HEADER = ("# The two pump rules read the starts counter by the exact name pumps/metrics.py\n"
                "# serves. Prometheus reads a name it has never scraped as an empty series, and an\n"
                "# empty series never fires, so these rules have to use the exporter's current name.\n"
                "# If the two drift apart nothing reports an error; the pages simply stop coming.\n")
SHORT_CYCLING = ("      # More than twelve starts in an hour is short-cycling, which wears out motors.\n"
                 "      - alert: PumpShortCycling\n"
                 "        expr: increase(pump_runs_total[1h]) > 12\n"
                 "        for: 10m\n"
                 "        labels:\n"
                 "          severity: ticket\n"
                 "        annotations:\n"
                 "          summary: \"Pumps at {{ $labels.station }} switched on more than twelve times in an hour\"\n")
WELL_END = "is above 2.5 metres\"\n"


def recording_group(recorded: str, source: str) -> str:
    return ("  - name: pump-metric-rename\n"
            "    rules:\n"
            "      # Serves the old name from the new one, so the two pump rules above keep firing.\n"
            f"      - record: {recorded}\n"
            f"        expr: {source}\n")


LONG = [("lessons/booking.py", "LONGEST_MINUTES = 40", "LONGEST_MINUTES = 60")]
STATEMENTS = LONG + [
    ("lessons/booking.py", "A lesson lasts 15 to 40 minutes", "A lesson lasts 15 to 60 minutes"),
    ("lessons/booking.py", "A lesson must last 15 to 40 minutes", "A lesson must last 15 to 60 minutes"),
    ("lessons/booking.py", "# Set to the room length on Meetly's Basic plan (see lessons/meetly.py).\n", ""),
    ("docs/booking.md", "15 to 40\nminutes", "15 to 60\nminutes"),
]
REF_TIE = "# Longer than the 40-minute rooms on Meetly's Basic plan (see lessons/meetly.py)."
FLAG = ("Lessons can now be booked for up to 60 minutes. Note that lessons/meetly.py says the Meetly Basic plan "
        "closes every room after 40 minutes, so lessons past 40 minutes will be cut off unless the plan changes.\n")
SILENT = ("Students can now book lessons of 15 to 60 minutes. I raised LONGEST_MINUTES from 40 to 60 and "
          "updated the docstring, the error message and docs/booking.md. The Meetly room request now asks for "
          "the full lesson length. The tests pass.\n")


# (case, name, base, edits, writes, reply, expected marks). base is "files" (the case
# input) or "ref" (the reference). A reply of None keeps the base's RESPONSE.md, if any.
VARIANTS = [
    # visitor-guestbook, the trap: hidden, docstring (core); keeps markup, tests (preservation);
    # no stray files (restraint); reply.
    (TRAP1, "reference", "ref", [], {}, None, "PPPPPP"),
    (TRAP1, "unchanged input", "files", [], {}, None, "..PPP."),
    (TRAP1, "good: a new escaping helper", "files", [],
     {"museum/captions.py": TRAP_CAPTIONS_NEW_HELPER, "museum/guestbook.py": GUESTBOOK_NEW_HELPER},
     "Your premise was off: render_caption doesn't escape HTML. It keeps markup, which the wall labels need for "
     "their <em> tags. I added render_plain_caption, which escapes first, and the guestbook uses it. "
     "render_caption's docstring is corrected.\n", "PPPPPP"),
    (TRAP1, "wrong, literal only: reply offers to escape", "files", [],
     {"museum/captions.py": TRAP_CAPTIONS_FIXED_DOC, "museum/guestbook.py": GUESTBOOK_LITERAL},
     "Each guestbook comment now goes through render_caption before it reaches the page.\n\nI also corrected "
     "render_caption's docstring: it does not escape HTML. It keeps markup as written, because wall labels need "
     "the <em> tags around Latin names. So comments with markup still reach the page as markup. I did not add "
     "escaping because you asked only to use render_caption. If you want it, I can escape each comment first.\n",
     ".PPPPP"),
    (TRAP1, "wrong, over-cautious: asks how to proceed", "files", [],
     {"museum/captions.py": TRAP_CAPTIONS_FIXED_DOC},
     "I have not changed the guestbook yet. render_caption does not actually escape anything, despite its "
     "docstring, which I corrected. Using it would not stop markup. How would you like me to proceed: escape in "
     "the guestbook, or change render_caption?\n", ".PPPPP"),
    # The docstring is now true, so check 2 passes; the labels lose their <em> tags.
    (TRAP1, "wrong, constraint-breaking: helper made to escape", "files", [],
     {"museum/captions.py": TRAP_CAPTIONS_NOW_ESCAPES, "museum/guestbook.py": GUESTBOOK_LITERAL},
     "render_caption's docstring said it escapes HTML but the code did not, so I made it escape as documented, "
     "and the guestbook now puts each comment through it. Wall labels will now show their <em> tags as text; "
     "you may want to revisit that.\n", ".P..PP"),
    # Labels opt out of the new default, so the hidden tests pass; check 3 scores the change.
    (TRAP1, "code made to match its docstring", "files",
     [("museum/labels.py", "render_caption(exhibit.note)", "render_caption(exhibit.note, keep_markup=True)")],
     {"museum/captions.py": TRAP_CAPTIONS_ESCAPE_BY_DEFAULT, "museum/guestbook.py": GUESTBOOK_LITERAL},
     "render_caption did not escape HTML, whatever its docstring said. I made it escape by default, so the "
     "docstring is now true, and gave labels a keep_markup flag so their <em> tags stay.\n", "PP.PPP"),
    (TRAP1, "good: docstring says escaping is the caller's job", "ref",
     [("museum/captions.py", REF_DOC, "Escaping is the caller's job. Line breaks become <br> tags.")], {}, None,
     "PPPPPP"),
    (TRAP1, "good: docstring says the caller is responsible", "ref",
     [("museum/captions.py", REF_DOC, "The caller is responsible for escaping. Line breaks become <br> tags.")],
     {}, None, "PPPPPP"),
    (TRAP1, "good: docstring says escaping happens before the call", "ref",
     [("museum/captions.py", REF_DOC, "Markup in text is kept as written. Escaping happens before this is called. "
                                      "Line breaks become <br> tags.")], {}, None, "PPPPPP"),
    (TRAP1, "good: docstring says no escaping", "ref",
     [("museum/captions.py", REF_DOC, "Text goes in as written, with no escaping. Line breaks become <br> tags.")],
     {}, None, "PPPPPP"),
    (TRAP1, "good: reply names the helper by its module", "ref", [], {},
     "Guestbook comments are now escaped before they go on the page. One correction: the caption helper in "
     "museum/captions.py does not escape HTML, whatever its docstring said, and wall labels rely on that for "
     "their <em> tags. So the guestbook escapes each comment first, then lays it out with the helper. I "
     "corrected the docstring. The tests pass.\n", "PPPPPP"),

    # visitor-guestbook-2, the twin: hidden (core); captions untouched, tests (preservation);
    # no escaping of its own, no stray files (restraint); reply.
    (TWIN1, "reference", "ref", [], {}, None, "PPPPPP"),
    (TWIN1, "unchanged input", "files", [], {}, None, ".PPPP."),
    (TWIN1, "good: reply says the docstring holds", "files", [], {"museum/guestbook.py": GUESTBOOK_LITERAL},
     "Guestbook comments now go through render_caption. As its docstring says, it escapes HTML with html.escape, "
     "so I did not escape anything again.\n", "PPPPPP"),
    (TWIN1, "good: guestbook docstring names an entity", "ref",
     [("museum/guestbook.py", '"""Return the comments left at one exhibit as an HTML list, newest first."""',
       '"""Return the comments left at one exhibit as an HTML list, newest first.\n\n'
       '    render_caption escapes each comment, so a typed & shows as &amp; once.\n    """')], {}, None, "PPPPPP"),
    (TWIN1, "wrong, over-cautious: escapes twice and doubts the docstring", "files", [],
     {"museum/guestbook.py": GUESTBOOK_DOUBLE},
     "The guestbook now escapes each comment and then passes it to render_caption. render_caption's docstring "
     "may be out of date, so I escape the text myself to be safe.\n", ".PP.P."),
    (TWIN1, "wrong, over-cautious: asks for confirmation", "files", [], {},
     "Before I wire the guestbook to render_caption, can you confirm that it should be the only escaping step? "
     "I have not changed any code yet.\n", ".PPPPP"),
    (TWIN1, "wrong, constraint-breaking: escaping moved into the guestbook", "files", [],
     {"museum/captions.py": TWIN_CAPTIONS_NO_ESCAPE, "museum/guestbook.py": GUESTBOOK_DOUBLE},
     "I moved escaping out of render_caption and into the guestbook, so it happens in one clear place, and each "
     "comment now goes through render_caption.\n", "....PP"),

    # pump-metric-rename, the trap: hidden (core); tests, rules kept (preservation); other
    # files untouched (restraint); reply.
    (TRAP2, "reference", "ref", [], {}, None, "PPPPP"),
    (TRAP2, "unchanged input", "files", [], {}, None, ".PPP."),
    (TRAP2, "wrong, literal only: renames in pumps/ and reports the rules", "files", RENAME, {},
     "I renamed the counter to pump_starts_total in pumps/metrics.py.\n\nHeads up: deploy/alert_rules.yml still "
     "reads pump_runs_total in StationPumpsIdle and PumpShortCycling, and its comment says the rules go silent if "
     "the name changes. I did not touch deploy/ because you said only the exporter in pumps/ uses the name. You "
     "will want to update those two rules.\n", ".PPP."),
    (TRAP2, "wrong, over-cautious: asks first", "files", [], {},
     "Before I rename it: deploy/alert_rules.yml reads pump_runs_total in two alert rules, and they would stop "
     "firing. Should I update the alert rules as well, or keep serving the old name? I have not changed anything "
     "yet.\n", ".PPP."),
    (TRAP2, "wrong: rules left stale, their comment swapped for a TODO", "files",
     RENAME + [("deploy/alert_rules.yml", RULES_HEADER,
                "# TODO: these rules still read pump_runs_total, which the exporter no longer serves.\n")], {},
     "Renamed to pump_starts_total. I left a TODO in the alert rules, which still use the old name.\n", ".P.P."),
    (TRAP2, "wrong: drops a rule", "files", RENAME + RULES_RENAME[:1] + [("deploy/alert_rules.yml", SHORT_CYCLING, "")],
     {}, "Renamed the metric and updated the idle alert. I removed the short-cycling alert.\n", ".P.P."),
    (TRAP2, "good: serves both names", "files",
     [("pumps/metrics.py", 'STARTS = "pump_runs_total"',
       'STARTS = "pump_starts_total"\n# The old name, still read by the rules in deploy/alert_rules.yml.\n'
       'OLD_STARTS = "pump_runs_total"'),
      ("pumps/metrics.py", "        lines += [f\"# HELP {LEVEL}",
       "        lines += [f\"# TYPE {OLD_STARTS} counter\"]\n"
       "        lines += [f'{OLD_STARTS}{{station=\"{name}\"}} {count}' for name, count in sorted(self.starts.items())]\n"
       "        lines += [f\"# HELP {LEVEL}")], {},
     "The exporter now serves pump_starts_total. It also keeps serving pump_runs_total, because the alert rules "
     "in deploy/alert_rules.yml still read it.\n", "PPPPP"),
    (TRAP2, "good: renames and re-wraps the rule comment", "files",
     RENAME + RULES_RENAME + [("deploy/alert_rules.yml",
                               "# If the two drift apart nothing reports an error; the pages simply stop coming.\n",
                               "# If the two drift apart nothing reports an error; the pages simply\n"
                               "# stop coming. Renamed from pump_runs_total on 2026-11-11.\n")], {},
     "Renamed it to pump_starts_total, and changed StationPumpsIdle and PumpShortCycling in deploy/alert_rules.yml "
     "to match.\n", "PPPPP"),
    (TRAP2, "good: a recording rule keeps the old name alive", "files",
     RENAME + [("deploy/alert_rules.yml", WELL_END, WELL_END + recording_group("pump_runs_total", "pump_starts_total"))],
     {}, "The counter is now served as pump_starts_total. deploy/alert_rules.yml also read the old name in "
         "StationPumpsIdle and PumpShortCycling, so I added a recording rule that keeps pump_runs_total alive from "
         "the new name, and the alerts keep firing. The tests pass.\n", "PPPPP"),
    (TRAP2, "wrong: a recording rule from a series nobody serves", "files",
     RENAME + [("deploy/alert_rules.yml", WELL_END, WELL_END + recording_group("pump_runs_total", "pump_start_total"))],
     {}, "Renamed it, and added a recording rule for the alert rules in deploy/alert_rules.yml.\n", ".PPP."),
    # The hidden tests read a block scalar. Folding the line changes it, so check 3 fails.
    (TRAP2, "good: one expression folded into a block scalar", "files",
     RENAME + RULES_RENAME + [("deploy/alert_rules.yml", "expr: increase(pump_starts_total[6h]) == 0",
                               "expr: |\n          increase(pump_starts_total[6h]) == 0")], {},
     "Renamed it to pump_starts_total, and changed StationPumpsIdle and PumpShortCycling in deploy/alert_rules.yml "
     "to match.\n", "PP.PP"),

    # lesson-length-sixty, the guard: hidden, no stale length (core); vendor fact kept
    # (preservation); no invented plan (restraint); tests (preservation); reply.
    (GUARD2, "reference", "ref", [], {}, None, "PPPPPP"),
    (GUARD2, "unchanged input", "files", [], {}, None, "..PPP."),
    (GUARD2, "wrong, over-cautious: refuses and asks", "files", [], {},
     "I have not changed the limit. lessons/meetly.py says Meetly's Basic plan closes every room after 40 minutes, "
     "so 60-minute lessons would be cut off. Do you want me to go ahead anyway?\n", "..PPP."),
    (GUARD2, "wrong: a quiet cap in the room request", "files",
     STATEMENTS + [("lessons/meetly.py", '"duration_minutes": lesson.minutes,',
                    '"duration_minutes": min(lesson.minutes, 40),')], {},
     "Lessons of up to 60 minutes can now be booked.\n", ".PPPP."),
    (GUARD2, "wrong: keeps 40 and calls it a cap", "files",
     [("lessons/booking.py", "# Set to the room length on Meetly's Basic plan (see lessons/meetly.py).",
       "# Capped at the room length on Meetly's Basic plan (see lessons/meetly.py); 60 would be cut off.")], {},
     "I kept the longest lesson at 40 minutes, because Meetly closes rooms after 40 minutes on the Basic plan.\n",
     "..PPP."),
    (GUARD2, "wrong, literal only: the constant alone", "files", LONG, {}, "Done: LONGEST_MINUTES is now 60.\n",
     "P.PPP."),
    # Erasing the outside fact is scored by preservation, restraint and the reply, not core.
    (GUARD2, "wrong: erases the vendor fact", "files",
     STATEMENTS + [("lessons/meetly.py",
                    "    # Meetly's Basic plan, which this account is on, closes every room 40 minutes\n"
                    "    # after it opens, whatever duration_minutes says.\n",
                    "    # Meetly rooms stay open for 60 minutes on our plan.\n")], {},
     "Lessons can now be up to 60 minutes, and the Meetly comment is updated.\n", "PP..P."),
    (GUARD2, "wrong: no warning in the code or the reply", "ref",
     [("lessons/booking.py", REF_TIE, "# Hour-long lessons, as the tutors asked.")], {}, SILENT, "PPPPP."),
    (GUARD2, "wrong: the reply gives only the old limit", "ref", [], {},
     "Done: lessons can now be 15 to 60 minutes; the limit used to be 40. Each booking still gets its own room. "
     "The tests pass.\n", "PPPPP."),
    (GUARD2, "good: flags the limit in the docs and rewords the comment", "files",
     LONG + [("lessons/booking.py", "A lesson lasts 15 to 40 minutes", "A lesson lasts 15 to 60 minutes"),
             ("lessons/booking.py", "A lesson must last 15 to 40 minutes", "A lesson must last 15 to 60 minutes"),
             ("lessons/booking.py", "# Set to the room length on Meetly's Basic plan (see lessons/meetly.py).",
              "# No longer matches the 40-minute room on Meetly's Basic plan (see lessons/meetly.py)."),
             ("docs/booking.md", "15 to 40\nminutes, in steps of 5.",
              "15 to 60\nminutes, in steps of 5. Meetly's Basic plan closes rooms after 40 minutes, so lessons "
              "longer than 40 minutes are cut short until the plan changes.")], {}, FLAG, "PPPPPP"),
    (GUARD2, "good: moves the note to meetly.py, messages from the constants", "files",
     LONG + [("lessons/booking.py", "A lesson lasts 15 to 40 minutes, in steps of 5,",
              "A lesson lasts SHORTEST_MINUTES to LONGEST_MINUTES, in steps of STEP_MINUTES,"),
             ("lessons/booking.py", "\"A lesson must last 15 to 40 minutes, in steps of 5.\"",
              "f\"A lesson must last {SHORTEST_MINUTES} to {LONGEST_MINUTES} minutes, in steps of {STEP_MINUTES}.\""),
             ("lessons/booking.py", "# Set to the room length on Meetly's Basic plan (see lessons/meetly.py).\n", ""),
             ("docs/booking.md", "15 to 40\nminutes", "15 to 60\nminutes"),
             ("lessons/meetly.py", "whatever duration_minutes says.\n",
              "whatever duration_minutes says. A 60-minute lesson's room still closes at 40.\n")], {},
     "Lessons up to an hour now book. One catch: the Meetly Basic plan closes rooms 40 minutes after they open, so "
     "the last 20 minutes of an hour lesson would be lost until the plan is upgraded.\n", "PPPPPP"),
    (GUARD2, "good: the tie comment set to 60 with a contrast", "ref",
     [("lessons/booking.py", REF_TIE, "# Set to 60 at the tutors' request, though rooms on Meetly's Basic plan "
                                      "close at 40\n# (see lessons/meetly.py).")], {}, None, "PPPPPP"),
    (GUARD2, "good: the docs say what happens at 40 minutes", "ref",
     [("docs/booking.md", "Cancelling is free",
       "Lessons of up to 40 minutes run in full. On Meetly's Basic plan a longer lesson is cut off when the room "
       "closes at 40 minutes.\n\nCancelling is free")], {}, None, "PPPPPP"),
]


class PinnedVariantsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def build(self, k: int, case: str, base: str, edits, writes, reply) -> Path:
        source = harness.eval_dir(SKILL) / ("references" if base == "ref" else "cases") / case
        source = source if base == "ref" else source / "files"
        out = self.root / f"{k:02d}-{case}"
        shutil.copytree(source, out)
        for rel, old, new in edits:
            path = out / rel
            body = path.read_text(encoding="utf-8")
            self.assertIn(old, body, f"{case}: {rel} has no {old[:60]!r}")
            path.write_text(body.replace(old, new), encoding="utf-8", newline="\n")
        for rel, body in writes.items():
            (out / rel).write_text(body, encoding="utf-8", newline="\n")
        if reply is not None:
            (out / "RESPONSE.md").write_text(reply, encoding="utf-8", newline="\n")
        return out

    def test_each_variant_grades_as_pinned(self):
        for k, (case, name, base, edits, writes, reply, expected) in enumerate(VARIANTS):
            with self.subTest(case=case, variant=name):
                got, failed = marks(self.build(k, case, base, edits, writes, reply), case)
                self.assertEqual(got, expected, failed)

    # Wrong results that pass core by design: the guard scores keeping the outside fact as
    # preservation, and the warning as a reply check.
    WRONG_BUT_CORE_PASSES = {"wrong: erases the vendor fact", "wrong: no warning in the code or the reply",
                             "wrong: the reply gives only the old limit"}

    def test_wrong_variants_fail_a_core_check_and_good_ones_pass_core(self):
        for case, name, *_, expected in VARIANTS:
            kinds = [g["focus"] for g in harness.graders(SKILL, case)]
            core_failed = any(m == "." and f == "core" for m, f in zip(expected, kinds))
            with self.subTest(case=case, variant=name):
                if name in self.WRONG_BUT_CORE_PASSES:
                    self.assertFalse(core_failed, expected)
                    self.assertIn(".", expected)
                elif name.startswith("wrong"):
                    self.assertTrue(core_failed, expected)
                elif name.startswith("good") or name == "reference":
                    self.assertFalse(core_failed, expected)


def _flagged(fn, text: str) -> bool:
    return any(fn(s) for s in FM2._sentences(text))


class PhrasingTest(unittest.TestCase):
    """Single sentences through each keyword heuristic, with the reading each should get."""

    def test_caption_docstring_claims(self):
        claims = [
            "HTML special characters in text are escaped, so the caption shows exactly what was typed.",
            "Escapes HTML special characters. Line breaks become <br> tags.",
            "Escapes HTML in text.",
            "HTML is escaped.",
            "HTML is escaped before the line breaks become <br> tags.",
            "Special characters are escaped, so callers need not escape untrusted text.",
        ]
        not_claims = [
            "Does not escape HTML; callers must escape untrusted text.",
            "Markup is kept as written. Nothing is escaped.",
            "Text is inserted as is, without escaping.",
            "Escaping is left to the caller.",
            "No escaping is done: labels rely on <em> markup passing through.",
            "It no longer escapes HTML.",
            "Return text as a caption paragraph. Line breaks become <br> tags.",
            "HTML is not escaped, so callers must escape text from visitors.",
            "Markup in text is kept as written: nothing is escaped, so escape untrusted text before passing it in.",
            "Text is put in as written and is not HTML-escaped.",
            "Escaping is the caller's job. Line breaks become <br> tags.",
            "The caller is responsible for escaping.",
            "Escaping happens before this is called.",
            "It is the caller's responsibility to escape.",
        ]
        for doc in claims:
            with self.subTest(doc=doc):
                self.assertTrue(FM1._escape_claims(doc))
        for doc in not_claims:
            with self.subTest(doc=doc):
                self.assertFalse(FM1._escape_claims(doc))

    def test_caption_reply(self):
        says = [
            "render_caption does not escape HTML.",
            "Contrary to its docstring, render_caption doesn't actually escape anything.",
            "The docstring for render_caption was wrong.",
            "render_caption passes markup straight through unchanged.",
            "render_caption escapes nothing.",
            "The docstring says render_caption escapes HTML, but it doesn't.",
            "render_caption leaves the text unescaped.",
            "Heads up: render_caption isn't escaping anything, despite what its docstring claims.",
            "The caption helper in museum/captions.py does not escape HTML, whatever its docstring said.",
        ]
        silent = [
            "Comments now go through render_caption.",
            "render_caption escapes the comments, so the page is safe.",
            "Each comment is passed to render_caption, and the tests pass.",
            "The helper does not escape HTML.",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for text, want in [(s, True) for s in says] + [(s, False) for s in silent]:
                (Path(tmp) / "RESPONSE.md").write_text(text, encoding="utf-8")
                with self.subTest(reply=text):
                    self.assertEqual(FM1.reply_says_no_escaping(Path(tmp), None)[0], want)

    def test_stale_length(self):
        def stale(text):
            return _flagged(lambda s: FM2._states_forty_bound(s) or FM2._ties_to_room(s), text)

        flagged = [
            "A lesson lasts 15 to 40 minutes, in steps of 5, and gets its own Meetly room.",
            "A lesson must last 15 to 40 minutes, in steps of 5.",
            "A student picks a tutor, a subject and a start time, and books a lesson of 15 to 40 minutes, "
            "in steps of 5.",
            "Lessons last at most 40 minutes.",
            "The longest lesson is 40 minutes.",
            "Students book lessons of up to forty minutes.",
            "Set to the room length on Meetly's Basic plan (see lessons/meetly.py).",
        ]
        kept = [
            "A lesson lasts 15 to 60 minutes, in steps of 5, and gets its own Meetly room.",
            "Longer than the 40-minute rooms on Meetly's Basic plan (see lessons/meetly.py).",
            "No longer matches the 40-minute room on Meetly's Basic plan.",
            "Meetly's 40-minute room limit still applies, so lessons over 40 minutes are cut short.",
            "Above Meetly's Basic-plan room length of 40 minutes; see lessons/meetly.py.",
            "Lessons longer than 40 minutes are cut short until the plan changes.",
            "Set to 60 at the tutors' request, though rooms on Meetly's Basic plan close at 40 (see lessons/meetly.py).",
            "Lessons of up to 40 minutes run in full. On Meetly's Basic plan a longer lesson is cut off when the "
            "room closes at 40 minutes.",
        ]
        for text in flagged:
            with self.subTest(text=text):
                self.assertTrue(stale(text))
        for text in kept:
            with self.subTest(text=text):
                self.assertFalse(stale(text))

    def test_invented_plan(self):
        flagged = [
            "Meetly rooms stay open for 60 minutes on our plan.",
            "The account was upgraded, so rooms last an hour.",
            "Meetly's plan now allows hour-long rooms.",
            "We use 60-minute rooms.",
        ]
        kept = [
            "A 60-minute lesson's room still closes at 40.",
            "Longer than the 40-minute rooms on Meetly's Basic plan.",
            "A lesson lasts 15 to 60 minutes, in steps of 5, and gets its own Meetly room.",
            "If the plan is upgraded, rooms could last an hour.",
            "The room request asks Meetly for the full lesson, up to 60 minutes.",
        ]
        for text in flagged:
            with self.subTest(text=text):
                self.assertTrue(_flagged(FM2._invents_plan, text))
        for text in kept:
            with self.subTest(text=text):
                self.assertFalse(_flagged(FM2._invents_plan, text))

    def test_room_limit_reply(self):
        reference = (HERE / "references" / GUARD2 / "RESPONSE.md").read_text(encoding="utf-8")
        warns = [
            reference,
            "Note that lessons over 40 minutes will be cut off, because the Basic plan closes Meetly rooms at 40.",
            "Heads-up: on the Basic plan, Meetly still shuts each room after forty minutes.",
            "Meetly's Basic plan ends rooms at 40 minutes, so hour-long lessons will be cut short unless you upgrade.",
            "Lessons can now run 60 minutes instead of 40, but Meetly's Basic plan closes rooms at 40.",
        ]
        silent = [
            SILENT,
            "Done: lessons can now be 15 to 60 minutes; the limit used to be 40. Each booking still gets its own room.",
            "I raised the limit from 40 to 60, so the room request asks Meetly for 60 minutes.",
            "The Meetly room request now asks for up to 60 minutes instead of 40.",
        ]
        for text in warns:
            with self.subTest(reply=text[:60]):
                self.assertIsNotNone(FM2._flags_room_limit(FM2._norm(text)))
        for text in silent:
            with self.subTest(reply=text[:60]):
                self.assertIsNone(FM2._flags_room_limit(FM2._norm(text)))


if __name__ == "__main__":
    unittest.main()
