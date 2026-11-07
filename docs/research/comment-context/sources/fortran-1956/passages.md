# FORTRAN Programmer's Reference Manual, IBM 704: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_manual`. Text SHA-256: `d9eeedd435fd243dc1236dd726cf5354113f3ff70567b9f31630dcb244f27496`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Historical scan/text layer; layouts, card columns and specimen comments need visual verification.
- Physical pages 9 and 48 code sheets are now transcribed in supplemental spans; alignment, faint characters and handwritten/source anomalies retain explicit notes. No certified transcription of other manual formulas is claimed.
- Reading text has OCR defects in mathematical notation, code and table alignment. Relevant comment rules/specimens were visually inspected; this is full sequential traversal of the available 54-page manual, not a certified transcription of every formula.

<a id="fortran-1956-001"></a>
## fortran-1956-001 — General properties: program description and introductory commented specimen

Source: [physical PDF page 9](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=9); reading unit `p009`, lines 1–16.

Attribution: IBM, FORTRAN Programmer's Reference Manual (October 15, 1956)

Context: Physical page 9, printed page 7. The manual introduces the source-program representation and explains the largest-value example, explicitly identifying its opening comment.

Transcription/context notes: The figure appears before the explanatory paragraph in the original. Its garbled reading-text lines 17-27 are not selected as a faithful specimen; a separate visual transcription preserves its two C-marked lines and program.

Related: [fortran-1956-002](#fortran-1956-002), [fortran-1956-003](#fortran-1956-003), [fortran-1956-004](#fortran-1956-004)

```text
a CHAPTER I. GENERAL PROPERTIES
OFAFORTRANSOURCEPROGRAM
A FORTRAN source program consists of a sequence of FORTRAN statements.
There are 32 different types of statement, which are described in detail in the
chapters which follow.
Example of a The following brief program will serve to illustrate the general appearance and
'Ortran Program some of the properties of a FORTRAN program. It is shown as coded on a
standard FORTRAN coding sheet.
This program examines the set of n numbers a i (i= 1,. . . . , n) and sets the
quantity BIGA to the largest value attained in the set. It begins (after a com-
ment describing the program) by setting BIGA equal to al. Next the DO
statement causes the succeeding statements to and including statement 20 to
be carried out repeatedly, first with i=2, then with i=3, etc., and finally with
i=n. During each repetition of this loop the IF statement compares BIGA with
ai; if BlGA is less than ai, statement 10, which replaces BIGA by ai, is executed
before continuing.
```

<a id="fortran-1956-002"></a>
## fortran-1956-002 — Keypunching and continuation conventions

Source: [physical PDF page 9](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=9); reading unit `p009`, lines 28–35.

Attribution: IBM, FORTRAN Programmer's Reference Manual (October 15, 1956)

Context: Physical page 9, printed page 7. Card and coding-form conventions surrounding the commented example; the marked continuation column explains the X visible on the second comment line.

Transcription/context notes: This passage describes statement continuation generally; it is not an inferred rule that comments execute or continue as statements.

Related: [fortran-1956-001](#fortran-1956-001), [fortran-1956-003](#fortran-1956-003), [fortran-1956-007](#fortran-1956-007)

```text
Keypunching Each statement is punched on a separate card. If a statement is too long to
the Program fit on a single card it can be continued over as many as 9 additional continuation
cards. For each statement the initial card must contain either a zero or a blank
in column 6; on continuation cards column 6 must not contain a zero or a blank,
and it should be used to number the continuation cards consecutively from 1 to 9.
If a statement is too long to fit on a single line of the coding form, the
programmer can signal to the keypuncher that he has continued on to the next
line by placing a mark in the column labeled CONTINUATION.
```

<a id="fortran-1956-007"></a>
## fortran-1956-007 — Introductory largest-value program on FORTRAN coding sheet (visual transcription)

Source: [physical PDF page 9](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=9); reading unit `p009`, lines 40–46.

Attribution: International Business Machines Corporation

Context: Manual visual transcription from original PDF physical page 9 (printed page 7), pypdfium2 rendered image. Appended reading aid for the original code sheet; base OCR retained separately.

Transcription/context notes: Code-sheet layout normalized to plain text: C occupies column 1; X is visible in the CONTINUATION column on the second comment line. Statement-number positions and internal spaces are approximated. Both first lines bear C in the original. Blank identification fields and ruled grid omitted. The header identifies C FOR COMMENT, STATEMENT NUMBER (columns 1-5), CONTINUATION (6), FORTRAN STATEMENT (7-72), and IDENTIFICATION (73-80).

Related: [fortran-1956-002](#fortran-1956-002)

```text
C     PROGRAM FOR FINDING THE LARGEST VALUE
C    X    ATTAINED BY A SET OF NUMBERS
      BIGA = A(1)
      DO 20 I = 2,N
      IF (BIGA - A(I)) 10,20,20
   10 BIGA = A(I)
   20 CONTINUE
```

<a id="fortran-1956-003"></a>
## fortran-1956-003 — Comment cards, identifying fields, and readable listings

Source: [physical PDF page 10](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=10); reading unit `p010`, lines 1–23.

Attribution: IBM, FORTRAN Programmer's Reference Manual (October 15, 1956)

Context: Physical page 10, printed page 8. The manual distinguishes statement numbers, C-marked ignored cards, arbitrary identification columns, statement columns, and blank spacing, then identifies the actual input medium.

Transcription/context notes: The reading text misextracts the exponent in line 2 as 2'5; the original shows 2 to the power 15 (=32768). Minor OCR in line 13 reads iliitial for initial. Core comment-card rule at lines 8-10 was visually verified.

Related: [fortran-1956-001](#fortran-1956-001), [fortran-1956-002](#fortran-1956-002), [fortran-1956-006](#fortran-1956-006)

```text
The order of the statements is governed solely by the order of the cards.
However, any number less than 2'5 (=32768) may be associated with any
statement by punching it in columns 1-5 of the initial card bearing that state-
ment. Thereupon this number becomes the statement number of that statement.
Statement numbers, besides permitting cross-references within the source pro-
gram, also help the programmer to correlate the object program with his
source program.
Punching the character C in column 1 will cause the card to be ignored by
FORTRAN. Such cards may therefore be used to carry comments which will
appear when the deck is listed.
Columns 73-80 are not read by FORTRAN and may be punched with any
desired identifying information.
The statements themselves are punched in columns 7-72, both on iliitial
and continuation cards. Thus a statement consists of not more than 10 x 66=660
characters. A table of the admissible characters in FORTRAN is given in
Appendix A.
Blank characters, except in column 6, are simply ignored by FORTRAN,
and the programmer may use blanks freely to improve the readability of his
FORTRAN listing.
The actual input to FORTRAN is either this deck of cards or a BCD tape
written from it on the 704 peripheral card-to-tape equipment with the standard
SHARE 80 x 84 board. On the tape an End of File mark after the last card
is required.
```

<a id="fortran-1956-004"></a>
## fortran-1956-004 — Complete largest-value program: purpose and input explanation

Source: [physical PDF page 48](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=48); reading unit `p048`, lines 1–20.

Attribution: IBM, FORTRAN Programmer's Reference Manual (October 15, 1956)

Context: Physical page 48, printed page 46. The manual revisits the chapter 1 program, now complete with the same two opening comment cards. The passage gives its purpose, input size/format and first executed statement.

Transcription/context notes: The original code sheet lies between lines 10 and 11. Reading-text lines 21-72 mix form rules with damaged code and are not selected as faithful code; the original specimen is separately transcribed. Explanation continues on physical page 49.

Related: [fortran-1956-001](#fortran-1956-001), [fortran-1956-005](#fortran-1956-005), [fortran-1956-008](#fortran-1956-008)

```text
CHAPTER 8. EXAMPLES OF FORTRAN PROGRAMMING
A Complete
but Simple
Program
The example below is the same as that given in Chapter 1, but expanded into a
complete program. The purpose of the program is to discover the largest value
attained by a set of numbers A(1) and to print that number on the attached
printer. The numbers A(1) exist on punched cards, 12 to a card, each number
occupying a field of 6 columns. There are not more than 999 numbers; the
actual number N is punched on a lead card.
The first executable statement is the READ; therefore the program begins there.
The READ causes first N and then A(1), A(2), . . . . . , A(N) to be brought
in from the card reader, in accordance with the FORMAT statement 1. Notice
that the indexing of the loop bringing in A will work correctly, since the
indexing parameter N occurs earlier in the list.
The FORMAT statement says that there is first a single card with format
13, followed by any number of cards with format 12F6.2. On the single card
N is punched as a decimal integer in columns 1-3 and is also to be converted
into a fixed point number. In the remainder of the deck the numbers A(1) are
punched 12 to a card in columns 1-6, 7-12, etc. Each number is presumably
```

<a id="fortran-1956-008"></a>
## fortran-1956-008 — Complete largest-value program on FORTRAN coding sheet (visual transcription)

Source: [physical PDF page 48](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=48); reading unit `p048`, lines 74–87.

Attribution: International Business Machines Corporation

Context: Manual visual transcription from original PDF physical page 48 (printed page 46), pypdfium2 rendered image. Appended reading aid for the original code sheet; base OCR retained separately.

Transcription/context notes: Code-sheet layout normalized to plain text: C occupies column 1 and X is visible in the CONTINUATION column on the second comment line. Statement-number positions and internal spaces approximated; two C-marked opening lines preserved. Blank identification fields and ruled grid omitted. FORMAT Hollerith text is executable-output specification, not a source comment; spaces within the printed fields are visually approximated, so this is not a byte-exact executable card deck.

Related: [fortran-1956-004](#fortran-1956-004)

```text
C     PROGRAM FOR FINDING THE LARGEST VALUE
C    X    ATTAINED BY A SET OF NUMBERS
      DIMENSION A(999)
      FREQUENCY 30(2,1,10), 5(100)
      READ 1, N, (A(I), I = 1,N)
    1 FORMAT (I3/(12F6.2))
      BIGA = A(1)
    5 DO 20 I = 2,N
   30 IF (BIGA-A(I)) 10,20,20
   10 BIGA = A(I)
   20 CONTINUE
      PRINT 2, N, BIGA
    2 FORMAT (22H1THE LARGEST OF THESE I3, 12H NUMBERS IS F7.2)
      STOP 77777
```

<a id="fortran-1956-005"></a>
## fortran-1956-005 — Complete largest-value program: control flow, output and frequency assumptions

Source: [physical PDF page 49](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=49); reading unit `p049`, lines 1–38.

Attribution: IBM, FORTRAN Programmer's Reference Manual (October 15, 1956)

Context: Physical page 49, printed page 47. Continuation of the explanation of the commented specimen: data interpretation, loop execution, printed output, termination, dimensions and conditional frequency assumptions.

Transcription/context notes: Runtime Hollerith output text is retained as context for this specimen, not relabeled as a source comment. OCR confuses I/1 in places and line 9 damages the comparison sign; visual source controls interpretation. Line 30 flattens the octal subscript on 77777.

Related: [fortran-1956-004](#fortran-1956-004)

```text
punched as xxxxx or -xxxxx with the decimal point understood to precede the
last two digits. If, however, a column is used for a decimal point, its position
overrides this understanding.
After the READ is executed control moves to the next executable state-
ment, the arithmetic formula BIGA = A(1). The cell BIGA now contains A(1).
Next the DO statement sets I to 2 and creates a loop starting with the IF
and ending with the CONTINUE. The first time the IF is executed it transfers
control either to statement 10 or statement 20, according as A(2) > BIGA or
A(2),< BIGA. In the first case, therefore, BIGA becomes A(2); otherwise it
remains A ( 1 ) .
Control is now in the CONTINUE, which is the last statement in the range
of a DO which is still unsatisfied (provided that N > 2), and which is not a
transfer. Therefore DO-sequencing occurs: I is increased to 3 and control goes
back to the IF. The comparison now is between BIGA and A(3); if A(3) is
the larger it becomes the new BIGA.
This process continues until control is in the CONTINUE with I = N.
The DO is satisfied; therefore normal sequencing occurs and control moves to
the PRINT. BIGA now contains the largest value in the set of A's; N and the
A-array have not been altered.
The PRINT statement causes N and BIGA to be printed on the attached
printer in accordance with the FORMAT statement 2. This statement causes
a line to be printed as follows. The carriage control character is a Hollerith "1"
which causes a skip to channel 1, bringing the paper to the top of a new sheet.
Type wheels 1-21 receive the text 'THE LARGEST OF THESE '; wheels 22-24
receive N converted back to decimal integer form; wheels 25-36 receive ' NUM-
BERS IS '; and wheels 37-43 receive BIGA converted into fixed decimal form,
with a decimal point preceding the last two digits. Notice that an extra column
is allotted to BIGA to allow for the decimal point, which was presumably
omitted in the data input.
The program ends with a HALT and 777778 in the address field of the
storage register on the console. Pressing the START button will have no effect.
The only subscripted variable used in the program is A. Hence DIMEN-
SION A(999) is the only dimension information required.
The only statements about which a FREQUENCY statement can be made
are the IF and the DO. The programmer anticipates that BIGA will usually be
greater than A(I), a plausible guess if the A(1) are randomly arranged but
not if they tend to increase with increasing I. He also predicts for the DO that
100 is a reasonable average for N.
```

<a id="fortran-1956-006"></a>
## fortran-1956-006 — Index: comment cards

Source: [physical PDF page 53](../../../../papers/ibm-fortran-704-programmers-reference-manual-1956.pdf#page=53); reading unit `p053`, lines 19–19.

Attribution: IBM, FORTRAN Programmer's Reference Manual (October 15, 1956)

Context: Physical page 53, printed page 51. Index entry points to printed page 8, the syntax and listing explanation.

Transcription/context notes: Navigation entry; no additional author claim.

Related: [fortran-1956-003](#fortran-1956-003)

```text
Comment cards 8
```
