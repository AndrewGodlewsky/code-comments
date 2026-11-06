# Code As Documentation: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_essay`. Text SHA-256: `fc16eb158d4a3428519aaf9fd362db48776d8a257d4da75a658e051db46629b0`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Archived HTML retains original-site assets/navigation not fully mirrored.
- Missing external site assets do not supply additional essay text in the local HTML.

<a id="code-as-documentation-001"></a>
## code-as-documentation-001 — Code as primary documentation and the supplementary-documentation qualification

Source: [fowler-code-as-documentation-2005.html](../../../../papers/fowler-code-as-documentation-2005.html); reading unit `fowler-code-as-documentation-2005`, lines 85–103.

Attribution: Martin Fowler; Jack Reeves explicitly credited in the primary-source rationale

Context: Complete essay argument retained in order; code as documentation is not asserted here to mean code comments.

Related: [code-as-documentation-002](#code-as-documentation-002)

```text
One of the common elements of agile methods is that they raise
	 programming to a central role in software
	development - one much greater than the software engineering
	community usually does. Part of this is classifying the code as a
	major, if not the primary documentation of a software system.

Almost immediately I feel the need to rebut a common
	misunderstanding. Such a principle is not saying that code is the
	only documentation. Although I've often heard this said of Extreme
	Programming - I've never heard the leaders of the Extreme
	Programming movement say this. Usually there is a need for
	further documentation to act as a supplement to the code.

The rationale for the code being the primary source of
	documentation is that it is the only one that is sufficiently
	detailed and precise to act in that role - a point made so
	eloquently by Jack Reeves's famous essay
“What
  is Software Design?”
```

<a id="code-as-documentation-002"></a>
## code-as-documentation-002 — Clarity is not inherent and requires effort

Source: [fowler-code-as-documentation-2005.html](../../../../papers/fowler-code-as-documentation-2005.html); reading unit `fowler-code-as-documentation-2005`, lines 105–132.

Attribution: Martin Fowler; Jack Reeves explicitly credited in the primary-source rationale

Context: Complete essay argument retained in order; code as documentation is not asserted here to mean code comments.

Related: [code-as-documentation-001](#code-as-documentation-001), [code-as-documentation-003](#code-as-documentation-003)

```text
This principle comes with a important consequence - that it's
	important that programmers put in the effort to make sure that this
	code is clear and readable. Saying that code is documentation isn't
	saying that a particular code base is good documentation. Like any
	documentation, code can be clear or it can be gibberish. Code is no
	more inherently clear than any other form of documentation. (And
	other forms of documentation can be hopelessly unclear too - I've
	seen plenty of gibberish UML diagrams, to flog a popular horse.)

Certainly it seems that most code bases aren't very good
	documentation. But just as it's a fallacy to conclude that declaring
	code to be documentation excludes other forms, it's a fallacy to say
	that because code is often poor documentation means that it's

necessarily
 poor. It is possible to write clear code, indeed I'm
	convinced that most code bases can be made much more clear.

I think part of the reason that code is often so hard to read is
	because people aren't taking it seriously as documentation. If
	there's no will to make code clear, then there's little chance it
	will spring into clarity all by itself. So the first step to clear
	code is to accept that code is documentation, and then put the
	effort in to make it be clear. I think this comes down to what was
	taught to most programmers when they began to program. My teachers didn't put much emphasis on
	making code clear, they didn't seem to value it and certainly didn't
	talk about how to do it. We as a whole industry need to put much
	more emphasis on valuing the clarity of code.
```

<a id="code-as-documentation-003"></a>
## code-as-documentation-003 — Readers, review and style-book references

Source: [fowler-code-as-documentation-2005.html](../../../../papers/fowler-code-as-documentation-2005.html); reading unit `fowler-code-as-documentation-2005`, lines 134–154.

Attribution: Martin Fowler; Jack Reeves explicitly credited in the primary-source rationale

Context: Complete essay argument retained in order; code as documentation is not asserted here to mean code comments.

Related: [code-as-documentation-002](#code-as-documentation-002), [code-as-documentation-004](#code-as-documentation-004)

```text
The next step is to learn how, and here let me offer you the
	advice of a best selling technical author - there's nothing like
	review. I would never think of publishing a book without having many
	people read it and give me feedback. Similarly there's nothing more
	important to clear code than getting feedback from others about
	what is or isn't easy to understand. So take every opportunity to
	find ways to get other people to read your code. Find out what they
	find easy to understand, and what things confuse them. (Yes, pair
	programming is a great way to do this.)

For more concrete advice - well I suggest reading good books on
	programming style.
Code Complete
 is the first place to look. I'll
	naturally suggest
Refactoring
 - after all much of refactoring is
	about making code clearer. After Refactoring,
Refactoring to
	Patterns
 is an obvious suggestion.
```

<a id="code-as-documentation-004"></a>
## code-as-documentation-004 — Team readers and personal style

Source: [fowler-code-as-documentation-2005.html](../../../../papers/fowler-code-as-documentation-2005.html); reading unit `fowler-code-as-documentation-2005`, lines 156–164.

Attribution: Martin Fowler; Jack Reeves explicitly credited in the primary-source rationale

Context: Complete essay argument retained in order; code as documentation is not asserted here to mean code comments.

Related: [code-as-documentation-003](#code-as-documentation-003)

```text
You'll always find people will disagree on various
	points. Remember that a code base is owned primarily by a team (even
	if you practice individual code ownership over bits of it). A
	professional programmer is prepared to bend her personal style to
	reflect the needs of the team. So even if you like ternary operators
	don't use them if your team doesn't find them easy to
	understand. You can program in your own style on your personal
	projects, but anything you do in a team should follow the needs of
	that team.
```
