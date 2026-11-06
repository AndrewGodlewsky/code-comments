# A Philosophy of Software Design, second-edition extract: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `available_extract`. Text SHA-256: `bd3f6ae5d5b597d4c6c86d4fbff5b9e3b78179b13cad21b0977b4865dda7857f`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Only the 20-page local extract is available, not the full book. PDF has no extractable text layer; reading text uses local OCR and requires visual verification.
- This is a discontinuous 20-page extract: printed pages 39?49, 76, 99?100 and 171?174 plus title/copyright. Most of the book, including earlier pages of Why Write Comments, is not local.
- All available OCR units read; only physical pages 15?16 visually checked during extraction. OCR contains code-identifier and punctuation defects; selected blocks preserve them with caveats.

<a id="philosophy-of-software-design-001"></a>
## philosophy-of-software-design-001 — Editor API example and cognitive load

Source: [physical PDF page 5](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=5); reading unit `p005`, lines 2–36.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-002](#philosophy-of-software-design-002)

```text
6.2 Example: storing text for an editor
Let's consider an example from a software design class in which students were asked
to build simple a GUI text editor. The editor had to display a file and allow users to
point, click, and type to edit the file. It also had to support multiple simultaneous views
of the same file in different windows, and it had to support multi-level undo and redo
for modifications to the file.
Each of the student projects included a class that managed the underlying text of
the file. The text classes typically provided methods for loading a file into memory,
reading and modifying the text of the file, and writing the modified text back to a file.
Many of the student teams implemented special-purpose APIs for the text class.
They knew that the class was going to be used in an interactive editor, so they thought
about the features that the editor had to provide and tailored the API of the text class
to those specific features. For example, if a user of the editor typed the backspace key,
the editor deleted the character immediately to the left of the cursor; if the user typed
the delete key, the editor deleted the character immediately to the right of the cursor.
Knowing this, some of the teams created one method in the text class to support each
of these specific features:
void backspace (Cursor cursor) ;
void delete(Cursor cursor) ;
Each of these methods takes the cursor position as its argument; a special type Cursor
represents this position. The editor also had to support a selection that could be copied
or deleted. The students handled this by defining a Sel ection class and passing an
object of this class to the text class during deletions:
void deleteSeIection(SeIection selection) ;
The students probably thought that it would be easier to implement the user inter-
face if the methods of the text class corresponded to the features visible to users. In
reality, however, this specialization provided little benefit for the user interface code,
and it created a high cognitive load for developers working on either the user interface
or the text class. The text class ended up with a large number of shallow methods, each
of which was only suitable for one user interface operation. Many of the methods, such
as del ete, were only invoked in a single place. As a result, a developer working on
the user interface had to learn about a large number of methods for the text class.
This approach created information leakage between the user interface and the text
class. Abstractions related to the user interface, such as the selection or the backspace
key, were reflected in the text class; this increased the cognitive load for developers
```

<a id="philosophy-of-software-design-002"></a>
## philosophy-of-software-design-002 — General-purpose API example and visible behavior

Source: [physical PDF page 6](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=6); reading unit `p006`, lines 2–35.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-001](#philosophy-of-software-design-001), [philosophy-of-software-design-003](#philosophy-of-software-design-003)

```text
working on the text class. Each new user interface operation required a new method to
be defined in the text class, so a developer working on the user interface was likely to
end up working on the text class as well. One of the goals in class design is to allow
each class to be developed independently, but the specialized approach tied the user
interface and text classes together.
6.3 A more general-purpose API
A better approach is to make the text class more generic. Its API should be defined
only in terms of basic text features, without reflecting the higher-level operations that
will be implemented with it. For example, only two methods are needed for modifying
text:
void insert(Position position, String newText) ;
void delete(Position start, Position end) ;
The first method inserts an arbitrary string at an arbitrary position within the text, and
the second method deletes all of the characters at positions greater than or equal to
start but less than end. This API also uses a more generic type Position instead
of Cursor, which reflects a specific user interface. The text class should also pro-
vide general-purpose facilities for manipulating positions within the text, such as the
following:
Position changePosition(Position position, int numChars) ;
This method returns a new position that is a given number of characters away from a
given position. If the numChars argument is positive, the new position is later in the
file than position; if numChars is negative, the new position is before posi t ion.
The method automatically skips to the next or previous line when necessary. With
these methods, the delete key can be implemented with the following code (assuming
the cu rsor variable holds the current cursor position):
text. delete(cursor, text. changePosition(cursor, 1)) ;
Similarly, the backspace key can be implemented as follows:
text . del ete (text . changePosi ti on (cursor ,
-1), cursor) ;
With the general-purpose text API, the code to implement user interface functions
such as delete and backspace is a bit longer than with the original approach using a
specialized text API. However, the new code is more obvious than the old code. A
developer working in the user interface module probably cares about which characters
are deleted by the backspace key. With the new code, this is obvious. With the old
```

<a id="philosophy-of-software-design-003"></a>
## philosophy-of-software-design-003 — Reading documentation, information hiding and explicit details

Source: [physical PDF page 7](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=7); reading unit `p007`, lines 2–34.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-002](#philosophy-of-software-design-002), [philosophy-of-software-design-004](#philosophy-of-software-design-004)

```text
code, the developer had to go to the text class and read the documentation and/or code
of the backspace method to verify the behavior. Furthermore, the general-purpose
approach has less code overall than the specialized approach, since it replaces a large
number of special-purpose methods in the text class with a smaller number of general-
purpose ones.
A text class implemented with the general-purpose interface could potentially be
used for other purposes besides an interactive editor. As one example, suppose you
were building an application that modified a specified file by replacing all occurrences
of a particular string with another string. Methods from the specialized text class, such
as backspace and del ete, would have little value for this application. However, the
general-purpose text class would already have most of the functionality needed for the
new application. All that is missing is a method to search for the next occurrence of a
given string, such as this:
Position fi ndNext(Position start, String stri ng) ;
Of course, an interactive text editor is likely to have a mechanism for searching and
replacing, in which case the text class would already include this method.
6.4 Generality leads to better information hiding
The general-purpose approach provides a cleaner separation between the text and user
interface classes, which results in better information hiding. The text class need not
be aware of specifics of the user interface, such as how the backspace key is han-
dled; these details are now encapsulated in the user interface class. New user interface
features can be added without creating new supporting functions in the text class. The
general-purpose interface also reduces cognitive load: a developer working on the user
interface only needs to learn a few simple methods, which can be reused for a variety
of purposes.
The backspace method in the original version of the text class was a false abstrac-
tion. It purported to hide information about which characters are deleted, but the user
interface module really needs to know this; user interface developers are likely to read
the code of the backspace method in order to confirm its precise behavior. Putting
the method in the text class just makes it harder for user interface developers to get
the information they need. One of the most important elements of software design is
determining who needs to know what, and when. When the details are important, it
is better to make them explicit and as obvious as possible, such as the revised imple-
```

<a id="philosophy-of-software-design-004"></a>
## philosophy-of-software-design-004 — Continuation and interface-design qualifications

Source: [physical PDF page 8](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=8); reading unit `p008`, lines 2–31.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-003](#philosophy-of-software-design-003), [philosophy-of-software-design-005](#philosophy-of-software-design-005)

```text
mentation of the backspace operation. Hiding this information behind an interface just
creates obscurity.
6.5 Questions to ask yourself
It is easier to recognize a clean general-purpose class design than it is to create one.
Here are some questions you can ask yourself, which will help you to find the right
balance between general-purpose and special-purpose for an interface.
What is the simplest interface that will cover all my current needs? If you reduce
the number of methods in an API without reducing its overall capabilities, then you are
probably creating more general-purpose methods. The special-purpose text API had
at least three methods for deleting text: backspace, del ete, and del eteSe1 ecti on.
The more general-purpose API had only one method for deleting text, which served
all three purposes. Reducing the number of methods makes sense only as long as the
API for each individual method stays simple; if you have to introduce lots of addi-
tional arguments in order to reduce the number of methods, then you may not really
be simplifying things.
In how many situations will this method be used? If a method is designed for one
particular use, such as the backspace method, that is a red flag that it may be too
special-purpose. See if you can replace several special-purpose methods with a single
general-purpose method.
Is this API easy to use for my current needs? This question can help you to deter-
mine when you have gone too far in making an API simple and general-purpose. If
you have to write a lot of additional code to use a class for your current purpose, that's
a red flag that the interface doesn't provide the right functionality. For example, one
approach for the text class would be to design it around single-character operations:
i nsert inserts a single character and del ete deletes a single character. This API is
both simple and general-purpose. However, it would not be particularly easy to use for
a text editor: higher-level code would contain lots of loops to insert or delete ranges
of characters. The single-character approach would also be inefficient for large opera-
tions. Thus it's better for the text class to have built-in support for operations on ranges
of characters.
```

<a id="philosophy-of-software-design-005"></a>
## philosophy-of-software-design-005 — Different opinion on function length and documentation burden

Source: [physical PDF page 14](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=14); reading unit `p014`, lines 2–28.

Attribution: John Ousterhout; Robert C. Martin quoted or reported explicitly, followed by Ousterhout response

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-004](#philosophy-of-software-design-004), [philosophy-of-software-design-006](#philosophy-of-software-design-006)

```text
9.8 A different opinion: Clean Code
In the book Clean Codel, Robert Martin argues that functions should be broken up
based on length alone. He says that functions should be extremely short, and that even
10 lines is too long:
The first rule of functions is that they should be small. The second rule of
functions is that they should be smaller than that.... Blocks within if statements,
else statements, while statements, and so on should be one line long. Probably
that line should be a function call.... This also implies that functions should not be
large enough to hold nested structures. Therefore, the indent level of a function
should not be greater than one or two. This, of course, makes the functions easier
to read and understand.
I agree that shorter functions are generally easier to understand than longer ones. How-
ever, once a function gets down to a few dozen lines, further reductions in size are
unlikely to have much impact on readability. A more important issue is: does breaking
up a function reduce the overall complexity of the system? In other words, is it easier
to read several short functions and understand how they work together than it is to read
one larger function? More functions means more interfaces to document and learn.
If functions are made too small, they lose their independence, resulting in conjoined
functions that must be read and understood together. When this happens, then it's bet-
ter to keep the larger function, so all of the related code is one place. Depth is more
important than length: first make functions deep, then try to make them short enough
to be easily read. Don't sacrifice depth for length.
9.9 Conclusion
The decision to split or join modules should be based on complexity. Pick the structure
that results in the best information hiding, the fewest dependencies, and the deepest
interfaces.
I Clean Code, Robert C. Marun, Pearson Education, Inc., Boston, MA 2009
```

<a id="philosophy-of-software-design-006"></a>
## philosophy-of-software-design-006 — Documentation, forgotten intent and Martin quotation

Source: [physical PDF page 15](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=15); reading unit `p015`, lines 1–35.

Attribution: John Ousterhout; Robert C. Martin quoted or reported explicitly, followed by Ousterhout response

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. Physical page 15 is printed page 99 and begins mid-sentence; preceding chapter pages are absent. OCR line 29 omits the leading ellipsis before the Martin quotation.

Related: [philosophy-of-software-design-005](#philosophy-of-software-design-005), [philosophy-of-software-design-007](#philosophy-of-software-design-007)

```text
Why Write Comments? The Four Excuses
and there is a risk of bugs if the new developer misunderstands the original designer's
intentions. Comments are valuable even when the original designer is the one making
the changes: if it has been more than a few weeks since you last worked in a piece of
code, you will have forgotten many of the details of the original design.
Chapter 2 described three ways in which complexity manifests itself in software
systems:
Change amplification: a seemingly simple change requires code modifications in
many places.
Cognitive load: in order to make a change, the developer must accumulate a large
amount of information.
Unknown unknowns: it is unclear what code needs to be modified, or what infor-
mation must be considered in order to make those modifications.
Good documentation helps with the last two of these issues. Documentation can re-
duce cognitive load by providing developers with the information they need to make
changes and by making it easy for developers to ignore information that is irrelevant.
Without adequate documentation, developers may have to read large amounts of code
to reconstruct what was in the designer's mind. Documentation can also reduce the
unknown unknowns by clarifying the structure of the system, so that it is clear what
information and code is relevant for any given change.
Chapter 2 pointed out that the primary causes of complexity are dependencies and
obscurity. Good documentation can clarify dependencies, and it fills in gaps to elimi-
nate obscurity.
The next few chapters will show you how to write good documentation. They will
also discuss how to integrate documentation-writing into the design process so that it
improves the design of your software.
12.6 A different opinion: comments are failures
In his book Clean Code, Robert Martin takes a more negative view of comments:
comments are, at best, a necessary evil. If our programming languages
were expressive enough, or if we had the talent to subtly wield those languages to
express our intent, we would not need comments very much — perhaps not at all.
The proper use of comments is to compensate for our failure to express our-
selves in code.... Comments are always failures. We must have them because we
can't always figure out how to express ourselves without them, but their use is not
a cause for celebration.
```

<a id="philosophy-of-software-design-007"></a>
## philosophy-of-software-design-007 — Response to Martin: code and comments, interface comments and method names

Source: [physical PDF page 16](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=16); reading unit `p016`, lines 2–25.

Attribution: John Ousterhout; Robert C. Martin quoted or reported explicitly, followed by Ousterhout response

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. Physical page 16 is printed page 100. Visual source has isLeastRelevantMultipleOfNextLargerPrimeFactor; OCR splits/substitutes letters. The quoted question ends comments? in the original; OCR loses its final punctuation.

Related: [philosophy-of-software-design-006](#philosophy-of-software-design-006), [philosophy-of-software-design-008](#philosophy-of-software-design-008)

```text
I agree that good software design can reduce the need for comments (particularly
those in method bodies). But comments do not represent failures. The information
they provide is quite different from that provided by code, and this information can't
be represented in code today. Code and comments are each well-suited to the things
they represent and they each provide important benefits; even if the information in
comments could somehow be captured in code, it's unclear that this would be an im-
provement.
One of the purposes of comments is to make it it unnecessary to read the code: for
example, instead of reading the entire body of a method, a developer can read a short
interface comment to get all the information they need in order to invoke the method.
Martin takes the opposite tack: he advocates replacing comments with code. Instead
of writing a comment to explain what is happening in a block of code in a method,
Martin suggests pulling that block out into a separate method (with no comments) and
using the name of the method as a replacement for the comment. This results in long
names such as i sLeastRe1 evantMu1 ti pl eOfNextLargerPri meFactor. Even with
all these words, names like this are cryptic and provide less information than a well-
written comment. And, with this approach, developers end up effectively retyping the
documentation for a method every time they invoke it!
I worry that Martin's philosophy encourages a bad attitude in programmers, where
they avoid comments so as not to seem like failures. This could even result in good
designers coming under false criticism: "What's wrong with your code that it requires
comments
Well-written comments are not failures. They increase the value of code and serve
a fundamental role in defining abstractions and managing system complexity.
```

<a id="philosophy-of-software-design-008"></a>
## philosophy-of-software-design-008 — Naming and abstraction in the opening of Decide What Matters

Source: [physical PDF page 17](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=17); reading unit `p017`, lines 2–23.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-007](#philosophy-of-software-design-007), [philosophy-of-software-design-009](#philosophy-of-software-design-009)

```text
Decide What Matters
One of the most important elements of good software design is separating what matters
from what doesn't matter. Structure software systems around the things that matter.
For the things that don't matter as much, try to minimize their impact on the rest of the
system. Things that matter should be emphasized and made more obvious; things that
don't matter should be hidden as much as possible.
Many of the ideas in the preceding chapters have at their heart the notion of separat-
ing what matters from what doesn't. For example, this is what we do when designing
abstractions. The interface of a module reflects what matters to users of that module;
things that don't matter to the module's users should be hidden in the implementation,
where they are less obvious. When choosing a variable name, the goal is to pick a
few words that convey the most possible information about the variable and use those
in the name; these are the aspects of the variable that matter most. If performance
really matters for a module, then the design of the module should be structured around
achieving the performance goals; in the example of Section 20.4, this meant finding a
design where the performance-critical path had as few method calls and special-case
checks as possible, while still being clean, simple, and obvious.
21.1 How to decide what matters?
Sometimes things that are important are imposed as external constraints on a system,
such as performance in Section 20.4. More often it is up to the designer to determine
what matters. Even when there are external constraints, the designer must figure out
what matters most in achieving those constraints.
```

<a id="philosophy-of-software-design-009"></a>
## philosophy-of-software-design-009 — Invariants, names and decisions in Decide What Matters

Source: [physical PDF page 18](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=18); reading unit `p018`, lines 2–35.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-008](#philosophy-of-software-design-008), [philosophy-of-software-design-010](#philosophy-of-software-design-010)

```text
To decide what matters, look for leverage, where the solution to one problem also
allows many other problems to be solved, or where knowing one piece of information
makes it easy to understand many other things. For example, in the discussion of how
to store text in Section 6.2, a general-purpose interface for inserting and deleting ranges
of characters could be used to solve many problems, whereas specialized methods such
as backspace only solved a single problem. The general-purpose interface provided
more leverage. At the level of the text class interface, it didn't matter whether the
interface was being invoked in response to the backspace key; all that really mattered
was that text needed to be deleted. An invariant is another example of a leverage
point: once you know an invariant for a variable or structure, you can predict how that
variable or structure will behave in many different situations.
It's easier to determine what is most important if you have multiple options to
choose among. For example, when choosing a variable name, make a mental list of
words that relate to that variable, then pick a few of the words that convey the most
information. Use those words to form the variable name. This is an example of the
"design it twice" principle.
Sometimes it may not be obvious which things matter the most; this can be particu-
larly hard for younger developers who don't have much experience. In these situations
I recommend making a hypothesis: "I think this is what matters most." Then commit
to that hypothesis, build the system under that assumption, and see how it works out.
If your hypothesis was right, think about why it ended up being right, and what clues
there might have been that you can use in the future. If your hypothesis was wrong,
that's still 0K: think about why it ended up being wrong, and whether there were clues
that you could have used to avoid this choice. Either way, you will learn from the
experience and you will gradually make better and better choices.
21.2 Minimize what matters
Try to make as little matter as possible: this will result in simpler systems. For exam-
ple, try to minimize the number of parameters that must be specified to construct an
object, or provide default values that reflect most common usage. For things that do
matter, try to minimize the number of places where they matter. Information that is
hidden within a module doesn't matter to code outside that module. If an exception
can be handled entirely at a low level in a system, then it doesn't matter to the rest
of the system. If a configuration parameter can be computed automatically based on
system behavior (rather than exposing it for an administrator to choose manually) then
```

<a id="philosophy-of-software-design-010"></a>
## philosophy-of-software-design-010 — Interface documentation prominence and design mistakes

Source: [physical PDF page 19](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=19); reading unit `p019`, lines 2–32.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-009](#philosophy-of-software-design-009), [philosophy-of-software-design-011](#philosophy-of-software-design-011)

```text
it no longer matters to administrators.
21.3 How to emphasize things that matter
Once you have identified the things that matter, you should emphasize them in the
design. One way to emphasize is with prominence: important things should appear in
places where they are more likely to be seen, such as interface documentation, names,
or parameters to heavily used methods. Another way to emphasize is with repetition:
key ideas appear over and over again. A third way to emphasize is with centrality. The
things that matter the most should be at the heart of the system, where they determine
the structure of things around them. One example is the interface for device drivers in
operating systems; this is a central idea because hundreds or thousands of drivers will
depend on it.
Of course, the converse is also true: if an idea is more likely to be seen, or if it
appears over and over again, or if it impacts a system's structure in significant ways,
then that idea matters.
Similarly, things that don't matter should be de-emphasized. They should be hid-
den as much as possible, they should not be encountered frequently, and they should
not impact the structure of the system.
21.4 Mistakes
In deciding what matters, there are two kinds of mistakes you can make. The first mis-
take is to treat too many things as important. When this happens, unimportant things
clutter up the design, adding complexity and increasing cognitive load. One example
is methods with arguments that are irrelevant to most callers. Another example is the
Java 1/0 interface discussed on page 26: it forced developers to be aware of the distinc-
tion between buffered and unbuffered 1/0, even though this distinction is almost never
important (developers almost always want buffering and don't want to waste time ask-
ing for it explicitly). Shallow classes are often the result of treating too many things as
important.
The second kind of mistake is to fail to recognize that something is important.
This mistake leads to situations where important information is hidden, or important
functionality is not available so developers must continually recreate it. This kind of
mistake impedes developer productivity and leads to unknown unknowns.
```

<a id="philosophy-of-software-design-011"></a>
## philosophy-of-software-design-011 — Technical writing and the chapter conclusion

Source: [physical PDF page 20](../../../../books/ousterhout-philosophy-of-software-design-2nd-ed-extract.pdf#page=20); reading unit `p020`, lines 2–14.

Attribution: John Ousterhout

Context: Available extract only. Adjacent records retain examples, opposing views and continuations; intervening unrelated chapter pages are not reconstructed.

Transcription/context notes: Windows OCR from the available extract; spacing, punctuation and code identifiers may be wrong. 

Related: [philosophy-of-software-design-010](#philosophy-of-software-design-010)

```text
21.5 Thinking more broadly
The idea of focusing on what's most important applies in other domains beside soft-
ware design. It's also important in technical writing: the best way to make a document
easy to read is to identify a few key concepts at the beginning and structure the remain-
der of the document around them. When discussing the details of a system, it helps to
tie them back to the overall concepts.
Focusing on what is important is also a great life philosophy: identify a few things
that matter most to you, and try to spend as much of your energy as possible on those
things. Don't fritter away all of your time on things that you don't consider important
or rewarding.
The phrase "good taste" describes the ability to distinguish what is important from
what isn't important. Having good taste is an important part of being a good software
designer.
```
