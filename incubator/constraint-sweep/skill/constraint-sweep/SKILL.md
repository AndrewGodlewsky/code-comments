---
name: constraint-sweep
description: Before you change what existing code returns, raises, orders, deduplicates or accepts, or whether it exists, sweep the repository for what other files' comments, docstrings and test names say about the symbols you are changing, and keep or openly report every constraint stated there. Use it even when the request looks local to one file, for requests to simplify, speed up, raise instead of returning a value, remove dead or unused code, or add a field or argument to existing code. It gives a word-bounded search recipe that covers SQL, config, YAML, JSON, shell, CI and Markdown files, not only importers, and says how to treat a constraint the code no longer relies on (report it as stale; it does not block the change). Not for new code that changes nothing existing, questions, formatting or comment wording (the code-comments skill covers comments).
---

# Constraint sweep

Code in other files can rely on what yours returns, orders or accepts, and the only
record may be a comment, docstring or test name over there. Nothing makes you open those
files, and the visible tests may not pin the property, so a change can pass them and
still break that code. Before the first edit, **sweep**: find every mention of the
symbols you will change, read what each says, and keep or openly report every constraint
it states.

This complements the `code-comments` skill. That skill governs the comment text a change
leaves behind; this one governs what you read before changing behaviour, and whether the
code still honours constraints stated elsewhere. This skill asks for no new comments.
When your change needs one, or makes an existing one false in any file, follow
`code-comments` for the wording. Fixing text your change made false is part of this
change, not a follow-up for the user.

## 1. Name the symbols
Before the first edit, list each function, method, class, constant and module whose
behaviour will change, with its module path (`pkg.module`) and file path (`pkg/module`).
Sweep only these. Done when every behaviour you will change has a name to search for.

## 2. Follow the symbol's own pointers
Read each symbol's docstring and comments, and its module's header. Open every file or
symbol they name ("see", "mirrors", "must match", a path). Done when each one is open.

## 3. Search every text file
For each name, from the repository root:

    rg -n -w --hidden -g '!.git' NAME
    rg -n -F --hidden -g '!.git' pkg.module
    rg -n -F --hidden -g '!.git' pkg/module

- Search every file type. Constraints sit in SQL, INI, YAML, JSON, shell, CI and
  Markdown files that nothing imports, which a type or glob filter such as `-t py` skips.
- `--hidden` reaches directories such as `.github/`; `-g '!.git'` keeps git's own files out.
- Without ripgrep: `grep -rnw --exclude-dir=.git NAME .`, and `grep -rnF` for the paths.
- With a built-in search tool, pass no type or glob filter, and make sure it covers hidden
  directories.
- When code reaches the symbol by a name built at run time (`getattr`, `importlib`, a
  registry, a fixed string joined to a variable), also search the code doing the lookup
  and the fixed part of the string.
- When an import renames the symbol (`as alias`), search the alias in that file.

Done when every name has been searched this way and every hit outside the symbol's own
definition has been read. For a name with more hits than you can read, done when its
qualified forms have been searched and their hits read, and the reply names the hits
left unread (judgement).

## 4. Sort each mention
At each hit, read the code there, the comment on or just above it, the enclosing
function's docstring, and the test name if it is a test. In a config, SQL or shell file,
read the comment block above the entry. Then sort it:
- **States nothing**: it only says that the site uses the symbol.
- **Constraint**: it says what the symbol must do, keep or provide for that site. Cue
  words: must, never, only, relies on, assumes, expects, in order, keep in sync, mirrors,
  same as. A test name that states a property counts.

Treat each constraint as a claim and check it against the code it protects:
- **Live**: that code still depends on your symbol for the property. It does not establish
  the property itself, and nothing between them does.
- **Stale**: that code no longer depends on it, for example because it now establishes
  the property itself.

## 5. Change the code
- **A live constraint binds.** Keep it with the first of these that fits:
  1. Keep the property where it is produced, by a means that still does what was asked.
     Moving the work that provides it out of your symbol and into a dependent is not
     this option: it edits a file the request did not name, and when the request is
     about cost, that dependent still pays it. Look first for another way, such as a
     cheaper one, for your symbol itself to provide the property. Move the work only
     when there is none, and say why in the reply.
  2. If the request itself changes the property (it is what the user asked to change, or
     the form they named changes it), update each dependent site in the same change.
  3. If neither can keep it, make the change as asked, and report the break with the
     constraint's file:line. Never break a live constraint silently.
- **Keep the form the user named.** When the request names a form (a position, a name, an
  error type), make the change in that form, and keep live constraints with whichever
  option above still allows it. Choose a different form only when the user stated a goal
  rather than a form, and then say why in the reply.
- **A stale constraint does not block the change.** Make it, and report the stale text
  with its file:line. If your change makes that text false, for example because it
  describes behaviour your change removes, correct or delete it in the same change;
  reporting it does not replace the fix. Otherwise leave the stale text as it is.
- Before removing a symbol as unused, sort its hits. An import or call (a test's included),
  or a name that a config file, string, registry, script or CI step supplies for code to
  look up, is a use. Prose that only describes it is not. Remove what has no use, as asked.
- **Reliance the code shows binds; reliance you only suspect does not.** If the code at a
  mention demonstrably depends on the old behaviour (it would compute a wrong result after
  your change), treat that as a live constraint even though nothing states it. If you
  suspect reliance that reading the code cannot confirm, make the change and name that
  site in the reply (judgement).
- **Restraint**: when a mention states nothing and its code does not depend on what you
  change, make the change as asked and leave that file as it was. Such a mention is no
  reason to add defensive code, ask or refuse. Edit another file only to keep a live
  constraint true or to fix text your change made false.

## Report
In the reply, list each constraint that shaped the change (file:line, what it says, what
you did), each stale one and whether you corrected it, and each site of suspected
reliance. Mention the sweep only when it changed the plan or found something stale.

Rules marked *judgement* rest on reasoning, not on a measured result.
