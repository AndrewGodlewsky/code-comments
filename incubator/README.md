# Incubator: candidate skills next to the hygiene skill

The incubator holds candidate skills that sit next to the shipped
[`code-comments` hygiene skill](../plugins/code-comments/README.md). Each one was
researched, built and evaluated on its own (issue
[#50](https://github.com/AndrewGodlewsky/code-comments/issues/50)). None of them ships.
None makes a performance claim beyond what its own eval shows. A skill moves from here
into a plugin only after the user decides it should.

Each skill keeps to the same limits as the shipped skill:
- No index, generated docs view, memory store or lookup service
  ([ADR 0001](../docs/adr/0001-context-lives-inline-no-central-index.md)).
- Context lives in the source files.
- Any script uses only the Python standard library.

## Layout

```text
incubator/
  harness.py            shared eval harness: prepare, grade, self-test, lint, verify-reads
  gradelib.py           shared readers for comments, docstrings and code shape
  <skill>/
    README.md           what it is for, results, limits and next steps
    research.md         sources, findings and how they shaped the skill
    skill/<skill>/      the installable skill: SKILL.md, plus scripts/ if it has any
    eval/
      arms.json         the one-line reminder used as the comparison arm
      cases/<case>/     prompt.md, case.yaml, graders/, files/, place-files.sh
      references/<case>/  a good result for the case, which passes every check
      grade.py          one mechanical check per grader file
      iterations/<name>/  run records, grades and benchmark.md
```

Cases use the layout that `claude plugin eval` reads, the same as
[`evaluation/hygiene/`](../evaluation/hygiene/README.md).

## Running an eval

```sh
python incubator/harness.py self-test                 # every skill: references pass, inputs fail
python incubator/harness.py lint                      # every skill: format, portability, no copied case text
python incubator/harness.py prepare SKILL --iteration iteration-1-haiku --runs 3
#   ...give each prompt in eval/iterations/<name>/runs.json to a fresh agent of the chosen model...
python incubator/harness.py grade SKILL --iteration iteration-1-haiku
python incubator/harness.py verify-reads SKILL --iteration iteration-1-haiku TRANSCRIPT_DIR
python incubator/harness.py summary SKILL iteration-1-haiku iteration-1-sonnet
```

`prepare` snapshots the skill into the iteration, so the files a run read are kept with
its grades. It copies each case's `files/` into a fresh `outputs/` folder per run. It
writes the exact prompt for each run to `runs.json` and `prompt.txt`. The prompt
follows the hygiene eval's wording:
- **with_skill** runs must read the snapshot of the new skill's `SKILL.md` first.
- **shipped_skill** runs must read a snapshot of the shipped `code-comments` skill first.
  This arm asks whether the new skill adds anything the existing one does not.
- **reminder** runs get one sentence from `arms.json` added to the request. The pilot
  found one general sentence as good as the full skill downstream, so a new skill has to
  beat this arm, not just the bare model.
- **without_skill** runs get the request alone.

Each grader's frontmatter sets a `focus`:
- `core`: the target behaviour, graded by hidden tests where it can be. Hidden tests live
  in `eval/hidden/<case>/hidden_tests/`. The agent never sees them, and
  `gradelib.run_hidden_tests` runs them on a copy of the run.
- `preservation`, `restraint`: what must not be damaged or added.
- `reply`: what the message to the user says. These are mostly keyword checks.

The benchmark reports each focus separately, so a keyword check on the reply cannot
carry the headline on its own.

`verify-reads` reads the agent transcripts and lists any with-skill run that did not
read the skill before its first edit. Exclude and re-run those.

`tests/test_incubator.py` runs every skill's self-test and lint with the rest of the
suite, and tests the harness on a synthetic skill.

## Rules for every skill here

- **Score preservation and restraint alongside the target behaviour.** Round 1 of the
  tournament showed that a skill can win on a proxy while doing harm.
- **Keep held-out cases.** Cases marked `held_out: true` in `case.yaml` are never used
  to decide a skill edit. They are run at the end, as a check on overfitting.
- **Record rulings, never hide them.** A heuristic check that misgrades a run gets an
  `overrides.json` entry that says who made the ruling and why. The check's own result
  stays in the evidence.
- **Publish null and negative results.** A skill that does not beat the one-line
  reminder says so in its README.
