# Planning and Coding of Problems for an Electronic Computing Instrument: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_scanned_part_ii_volumes_1_to_3`. Text SHA-256: `fafc1b5e2b021cbc932fcb95ab5a3776722598333cd5f1f32a463af11c5983db`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Historical scan with an existing OCR/text layer; sparse and diagram pages require visual inspection. Local volume extent is the scope, not the entire historical publication series.
- Combined Part II, Volumes 1-3 as confirmed by local title page; dual embedded-text and supplemental Windows OCR views. OCR does not reliably reconstruct mathematical/diagram layout.
- All194 physical pages were traversed visually; this is not a certified transcription. Windows OCR loses or reorders some prose and does not preserve complete diagram topology, coding/explanatory-column alignment or mathematical notation. Consult the original physical page for these representations.
- The available scan binds Part II Volumes I-III. References to future Chapters13-14/VolumeIV and other report parts do not make those absent works available here.

<a id="planning-and-coding-001"></a>
## planning-and-coding-001 — Preface: provisional coding method and comparison criteria (physical page 9); Volume I printed iii

Source: [physical PDF page 9](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=9); reading unit `p009`, lines 10–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-002](#planning-and-coding-002)

```text
PREFACE
This report was prepared in accordance with the terms of Contract
bk). betæen the Research and [kve opment Serv ice, U. S. Army
Ordnance Depar#rent and the Institute for Advanced Study. It is essent ial ly the
Secord paper referred to in tre Preface of the earl ier report entitled,
"Prel iminary Discussion of the Log ical Design of an Electronic Cornput ing
Inst rutrent", by A. W. Burks, H. H. Goldstine and John von Neurønn, dated 28 June
1946.
(Ming the t inp which has intervened it has beconp clear that the
issuance of a greater nurrber of reports 'Ai II be desirable. In this sense the
report, "Prel imi nary Discussion Of the Logical Cksign of an Electronic Comput ing
Instrurent't shoUld be viewed as part I Of the seqænce Of Our reports on the
Electronic Corrputer. The present report is Volume I of Part l. A Vol une I Of
Part II will follON within a months.
Part II is intended to give an account of our methods of cod ing
and of the pni losophy which governs it.
It conta ins what bel ieve to be an
adequate number of typical going from the simplest case up to several
of high it y, and in reasonable didactic ccyrpleteness. On the other hand,
Part I I in its present form is prel iminary in certaih signifi Zant ways. On this
account the fol 'cuing ought to be said.
We do not discuss the orders control ing the inputs and outputs
ard the stopping of the nvtchine. (Ihe i nputs and outputs are, hovever, d iscussed
to the extent which is required for the treatrrpnt of the binary—dec imal and
decirral—binary conversions in Chapter VI The reason for this is that in this
direction soræ eng ineering alternatives seem porth keeping Open, arvi it does not
affect the nujor problen•s of coding relevantly.
The use of the input—output npdium as a subsidiary nvmry• is not
discussed. This will probably be taken up in Part I II.
The code is not final in every respect. Several mi nor changes are
clearly cat led for, and even style major ores are conce Vable, depend inq upon various
'n all cases *ere changes are indi—
eng ineerirq possibi I ities that are still open.
catad or possible, there are several ternative ones, between which it is not yet
easy to chtnse with mch assurance. bel i eve that our present code is correct in
its basic idea, arui at any rate a reasonable basis för the discussion of other
proposals. Tat is, the examples which have ccded, nay serve as standards in
this code with variants or with more basical ly di f ferent systeræ.
It should be noted that in canpaöir*ä codes, four vie•.vpoints be
Sia-VI icity and rel iability
kept in mi M, all of then of car,parable importarce:
of the engineerirq soluti ons required by the code; (2) S imol icity, compactness and
1 3' Ease ard speed of the human procedure of translating
cmpleteness of the code;
'23503
```

<a id="planning-and-coding-002"></a>
## planning-and-coding-002 — Preface: provisional coding method and comparison criteria (physical page 10); Volume I printed iv

Source: [physical PDF page 10](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=10); reading unit `p010`, lines 7–20.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-001](#planning-and-coding-001), [planning-and-coding-003](#planning-and-coding-003)

```text
rratherrat conceived into the code, and also of fit-ding correct ing
errors in cod ing or of applying to it changes that have been dec ided upon at a
late stage; (4) Efficiency of the code in operating the nechine near its full
intrinsic speed.
We propose to carry our ccynpari sons of various variants and codes
under these aspects.
The authors wish to express thei r thanks to Professor Arthur W.
Burks, of the University of Michigan, for trany valuable discussions, as wel.l as
for his help in coding certain of the problems in the text.
H.
Inst i tute for Advanced Study
I April 1947
H. Goldstine
von Neurrann
```

<a id="planning-and-coding-003"></a>
## planning-and-coding-003 — 7.1-7.3: dynamic coding and instruction notation (physical page 11); Volume I printed 1

Source: [physical PDF page 11](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=11); reading unit `p011`, lines 7–55.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-004](#planning-and-coding-004), [planning-and-coding-002](#planning-and-coding-002)

```text
PLANNING AND COOING PROBLEMS AN ELECTRONIC co,4PUTlNG INSTRUMENT
7.0 GENERAL •FRINCIPLES CODING AND FLO#-OIAGRAWINS.
In the first part of this report we discussed in broad outline
7.1
Our basic point Of view in regard to the electronic ccynput ing machine nov envision-
There is ircll_ßed in •that discussion a tabulation of the orders the n-achine will be
In this, the second part of the report, interli to sh(M hcw the orders
able to obey _
may be used in the actual Of rune rical problems.
Before proceeding to the actual programning of such proble-rs, consider
it aesirable to discuss the nature Of ccxiing per Se ard in doing this to lay dwan a
modus operandi for hard ling specific problem'. We attempt therefore in this chapter
to are tyze the ccding of a problem in a detailed fashion, to shov where the difficulties
ie, ard hcw they are best resolved.
The actual (Ade for a problem is that sequence Of ccded symbols (express—
ing a seqænce of vords, or rather of ha I f *lords ard words) that has to be placed into
the selectron remory in order to cause the machine to perform the desired arZ planned
sequence of operations, which arrount to solving the problem in quest ion. Or to be mre
prec ise: This sequence of codes wili impose the desi-Ted seqænce of actions on C by
the fol lawing rechanism: C Scans the seqænce of codes, and effects the inst rut ions,
which they ccntain, one by one. If this were just a linear scanning of the coded
sequence, the latter in Ing throughout the procedure unchanged in form, then ratters
wou ld be quite simple. (Äding a problem for the rechine would rrerely be what its nalæ
indicates: Translating a reaningful text (the i rustræt ions that govern solving the
problem under cons iderat ion) f rcrn one language (the language of ics, in which
the planner will have conceived the problem, or rather the nurrerica' procedure by *'ich
he has decided to solve the problem) into another language (that one Of aur ccde).
This, ho.sever, is not the case. are convinced, both on general grounds
and fram our actual experience with the Cal ing of spec i fic nurnerical prob that the
rain difficulty lies just at this point.
Let us trerefore describe the process that
takes place mre ly.
The control scans the instruct ions in the se lectron netrory as a
rule linearly, i .e. beginning, say, with word No. O, and præeeding fran mrd No. y
to word No. y + I lard within each word f ran its first half to its second half), but
there are except ions: The transfer orders xC, xC', xCC, xCct (Cf. Table I at the end
Of the first part Of the report, or Table I I be 1m' cause C to jump fran vard y to the
arbitrarily prescribed word x (uncord it imally or subject to the fulfil In-ent of certain
cond it ions)- Also, these transfer orders are among the mst critical constituents of
a coded sequence. Furthermre, the subst i tut ion orders xSp, xSp' (ard also xS, cf. as
above) permit C to rxdify any part of the coded sequerx:e as it goes a long. Again,
these substitution orders are usual ly of great inportaæe.
To sun up: C will,
in gerpral, not scan the sequerce of irstrtx—
t ions i nearly.
It ray junp occasionally forward or backyard, anitting Ifor the tire
being, but probably not pemanent ly) scre parts of the sequerte, and going repeatedly
through nthers. It mdify sore parts of the seqænce while obeying the instructions
in another pmt of the seq•ææe. Thus when it scans a part of the seqtknce several
```

<a id="planning-and-coding-004"></a>
## planning-and-coding-004 — 7.1-7.3: dynamic coding and instruction notation (physical page 12); Volume I printed 2

Source: [physical PDF page 12](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=12); reading unit `p012`, lines 8–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-003](#planning-and-coding-003), [planning-and-coding-005](#planning-and-coding-005)

```text
2.
t i nes, it may actual ly find a different set Of instruct ions there at each passage.
Al I these displacerrents and rod i ficat ions may be cory} it ionat upon the nature Of
interned iate results obtained by the machine itself in the course of this procedure.
Hence it will not be pcssib'e in general to foresee in advance and ccmpleteLy the
actual course of C, its character and the sequence of its cyniss ions On one haru and
of its multiple passages over the place on the other, as welt as the actual
instructions it firÉs along this course, ard their changes through various scccessive
occas ions at the sane place, if that place is mult i ply traversed by the course of C.
These ci rcuTEtances develop in their actual ly asstned fortrE on ly during the process
(the calculation) itself, i.e. while C actual 'y runs through its gradually unfolding
course.
Thus the relat ion of the coded instruct ion seqærEe to the iCal ly
conce ived procedure Of (nun-ericar ) solut ion is not a stat iCal one, that of a trans—
ion, but highly dynamical : A coded order stands not simply for its present contents
at its present locat ion, but more ful ly for any succession Of passages Of C through it,
in connect ion with any succession of modified contents to be found by C there, all of
this being determined by all other orders of the sequence in conjunction with the one
under cons ideration) This ent ire, potentially very involved, i inter—
act ions evolves SunceSs ively whi le C runs through the operat ions control led and
di rected by these cont inuasl,y chanq ing instruct icns.
These cunpl icat ions are, fur-thenmre, not hypothet icat or except ional.
It does not require a deep ana lysis of any induct ive or iterative mthénøt icat prcx:ess
to see that they are indeed the norrn. Also, the flexibil i ty ard efficiercy of our
ccrie is essent ial (y due to them, i . e. to the extensive combinatorial pcEsibi I ities
which they indicate.
Final ly, those rratherrat iCal problens, which by their cornplex it y
justify the use of the rechine that we envis ion, require an appl ication of these control
procedures at a rather high level of ccmp( icat ion' and of mult icity of the course of
C am of the sccessive changes in the orders.
All these assert ions wi be arrply just ified and elaborated in detail
by the specific ccÉed examples which const i tute the hulk of this report, and by the
nethods that are going to evolve to ccde
air problem is then to f irri Simple, step—by—step hy which
these difficulties can be overcorne. Sirce codirq is not a static process of trans-
(at ion, but rather the technique of prov id•ihg a dynamic backgrourd to control the
au-tonetic evolution Of a tæaning, it has to be viewed as a loqical problem am one
that represents a new brarEh Of format logics. propose to sha•.' in the course of
this report ho." this task is mastered.
Tte balarce of this chapter gives a rigorous and complete descript ion
of our rrethod of cod ing, and of the auxi jar-y corcepts which we found convenient to
introduce in order to expound this method. (The subsequent chapters of the report
deaf with specific examp les, and with the rrethcds Of ccynbining already exist ing
ccded seqænces.' Since this is the first report on this subject, we felt justified
to st ress rigor am completeness rather than didactic simpl icity. A later presenta—
t ion will be written from the didact ic point Of view, which, we be' ieve, will show
that our TEth0dS are fairly easy to 'earn.
```

<a id="planning-and-coding-005"></a>
## planning-and-coding-005 — 7.1-7.3: dynamic coding and instruction notation (physical page 13); Volume I printed 3

Source: [physical PDF page 13](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=13); reading unit `p013`, lines 6–60.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-004](#planning-and-coding-004), [planning-and-coding-006](#planning-and-coding-006)

```text
3.
7.2 Table on page 5 is essentially a repetition of Table I at
the end of Part I of this report, i.e. it is a table of orders with their abbreviat ions
and explanat ions. fourd it convenient to Take certain minor changes. They are as
follcms:
First :
II has been changed, so to express the round off rule dis-
cussed in 5.11 in Part I of this report. In accord with the discussion carried out
loc. cit. , we use the fi rst round off rule described there. As far as the left-hand
39 digits are concerned, this consists Of adding one to digit 40, ard effecting the
resulting carries, thereby possibly modifying the eft-haM 39 dig its. Since we keep
track of the right—hand 39 digits, too, it is desi rable to compensate for this within
the extreme left 'non sign) digit of the right—hand 39 digits. This arrounts to adding
in the The nuTber there is O (sign digit O), hence a carry results if
ard only if that number is i.e. if its extreme left (non sign) digit is l.
In
this case the carry adds
in the accumul ator and subtracts I in the register.
Herx:e instead of adding in tre reg ister we actually subtract there. Hopever,
the aggregate result (on the 78 digit numberl is in any event the addition Of in
the register (i.e. of one to digit 40), hence it Tust be cornpensated by subtracting
in the reg ister. Consequently we do nothing or subtract in the register, accord—
ing to whether its extrene left Inon sign) digit is O or l. Arri, as saw above, we
in the accumulator Note, that t he operation
correspondingly do nothing or add 2-
+2-0 , which cause carries, takes place in the accumulator, which can indeed effect
carries; whi le the operation -l, which can cause no carries, takes place in the register,
which cannot effect carries. Indeed: Subtracting I in 2he register, where the sign
digit is O (cf. above J rerely amounts to replacing the sign digit by l. The new
for-rulat ion of expresses exactly these rules.
Second :
19 have been changed sornexhat for reasons set forth in
8.2 belcw. We note that 1B, 19 assure, both in -their old form I Tab 'e J and their
nex fom {Table II ) , that in each order the nET0ry posit ion number x cccupies the 12
left digits (cf. 6.6.5 in Part of this report).
Third : 20, 21 have a! so been changed. The forTn of 20 is a right
shift, which is so arranged that it halves the number in the accurrulator, including
an arithret ically correct treatment of sign digit. The ne.•,' form Of 21 is a left
shift, which is arrarged that it douthes the number in the accumlator (provided
that that number I ies betæen and i rx: Iud ing an arithrrpt iCal ly correct treat—
At the same time, ho.vever, 21 tin its form) is so
rent of the sign digit.
arrarged that the extrerTe left digit (after the sign digit J in the accurwlator is
It is inserted there at the extreap
not lost, but transferred into the reQister.
right, ard the orig inal contents of the register are shifted left correspondingly.
The imediate uses of 20, 21 are arithmet ical, but the last rent ioned features of
21 are required for other, ratter cont inatorial uses of 20, 21. For these uses there
will be typical examples in 9.5 and 9.6.
It should be added, that various elaborations ard refinerents of i),
21 miaht oe cons idered. Shifts by a given number of places, shifts until certain
sizes have been reachai, etc. do not cons ider the t im rreture as yet as to rMke
any definite choices in this respect, variants have certain
advantages in various situations. wili,. for the t irre being, use the sirnplest
for-rib of 20, 21 as given in Table t l.
```

<a id="planning-and-coding-006"></a>
## planning-and-coding-006 — 7.1-7.3: dynamic coding and instruction notation (physical page 14); Volume I printed 4

Source: [physical PDF page 14](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=14); reading unit `p014`, lines 6–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-005](#planning-and-coding-005), [planning-and-coding-007](#planning-and-coding-007)

```text
4.
7.3 he no'* proceed to aralyze . the procedures by which one can bui ld up
the appropriate coded sequerce for a given problem — or rather for a given nurerica'
to solve that problem. As was pointed out in 7. l, this Is not a aere question
Of translat ion {of a rrathenut iCal text into a code), but rather a quest ion Of providing
a control schere for a highly dynamical process, all parts of which nay undergo repeated
and relevant changes in the course of this process.
Let us therefore apprczch the problem in this sense.
It Should be Clear fran the prel iminary analysis of 7. l, that in planning
a Ccded seqLErce the thing that should keep prinarily in mi rxi is not the orig inal
( init appear-arce of that sequence, but rather its funct ioning and cont inued changing
whi le the process that it controls goes through its course. It is therefore advisable
to begin the planning at this er6, i to plan first the course Of the præess
relationship of its successive stages to ttE•ir changirg codes, and to extract fro-n this
Furthermore, it seerrE equally
the original ccded seqt*r-xze as a secondary operation.
clear, that the basic feature of the furctioning of the code in conjurct ion with the
evolut ion of the præess that it controls, is to be seen in the course VWIich the control
C takes thrdugh the ceded sequence, paral lel ' irg the evolut ion of that process.
therefore' Öropose to begin the planning of a ccxied sequerce by laying out a scherøtic
of the course Of C through that sequence, i . e. throuæh the requi red reaion of the
select ron memory. This scheretic is the diagræn Of C. Apart fran the above a
priori reasons, the decision to make the f 1m diagram of C the first step in
planning appears to be extens ive ly justified by Our experience with the coding Of
actual probleqs. The exempl if icat ion of this k i Of experience on a mner Of selected
typical examples forns the bulk of this report.
In drawing the f 10M diagram of C fol points are relevant:
First: The reason why C may have to rmve several t irres through the
region in the selectron nemory is that the operat ions that have to be performed nay be
repetitive. by indict ion Cover arr integer variable); iterat ive processes
I ike ive approxinøt ions calculations of sun-s Or of praiucts Of rrany adderds
or factors all for-red according to the Sarre law (but on a variable ion
or multipl icatior; irøex); stepwise integrations in a simple quadrature or a mre involved
different iat equat ion or system Of differential equations, which approxirrøte the- result
and which are iterat ive in the above sense; etc. — these are typical examp tes of the
situation that have in mind. TO simplify the nonprclature, will call any simple
iterative præess of this type an induction or a Simple induction. A multipl icity Of
such iterat ive processes, -superposed upon each other or crossing each otter will be
called a induction.
When a sirrple induction takes place, C travels during each step of the
indiEt ion o.'er a certain path, at the end Of which it returns to its beginning. Herx:e
this path ray be visual ized as a loop. will call it an induction loop or a simple
induction Loo#. A TWI tiple induction gives rise to a cultipl icity•of such loops; they
form together a pattern which will be called a nultiøLe induction loop.
propcse to ind icate th-æe port Of the f læ.' diagram Of C by a
symbol ism of ines oriented by Thus a I inear seqtpnce of operat ions,
with no iritrtive elerrents in it, will be by syrbols like thcse in Figures
7.1 a—c, whi le a Simple induction loop is shc».'n in d, eod., ard multiple irdt_Etian
loops are shOMn in e—f, ecd.
```

<a id="planning-and-coding-007"></a>
## planning-and-coding-007 — 7.1-7.3: dynamic coding and instruction notation (physical page 15); Volume I printed 5

Source: [physical PDF page 15](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=15); reading unit `p015`, lines 22–92.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments. Table II rotated clockwise for readable visual inspection and supplementary OCR.

Related: [planning-and-coding-006](#planning-and-coding-006), [planning-and-coding-008](#planning-and-coding-008), [planning-and-coding-072](#planning-and-coding-072)

```text
ION
Abbre—
viat ion
ete
1.
2.
3.
a.
5.
6.
8.
9.
10.
11.
12.
13.
14.
15.
16.
17.
18.
20.
21.
SIX).
SIX).
Ac
Ac—
Act.'
Ah
Ahr
cc.S(x)
x
x hM
A
xx
x Sp
R
Clær acctnulator am add nun.er lazted at positim•y, in the selectrons into it.
Clær accurulator and subtract nuTber located at posit im x in the selectrons into it.
Clear acctnulator and add absolute vane of located at posit im x in the selectrons into it.
Clear accuulator and subtract absolute valcp. of nurrker at position x in the selectrons into it.
Add numer located at position x in the selectrons into accwuiator.
Subtract ntJTt•er lcrated at position x in the selectrors into the acctnulator.
absolute value of nonter- located at position x in the selectrons into the accurulator.
Subtract absolute val LR of nwt;er It-rated at rxSiticn x in the sela:trors into the accinulator.
Clear register* am runner lcr.ated at pæition x in the selectrons into it.
Clear accumlator ard shift numer held in reqister into it.
Clear acc.wulator ark} mltiply the rurröer Icc-ated at posit im x in tie selectrcns by the nunber in
reoister, placinq the left—hard 39 dioits of the in the accumulator ard the riqht—harvd
39 digits of the ansv.er in the register. The sinn dinit of the reaister is to racie equal to
If the latter is l, tyer is to he arEed into the accumulator.
the extrere left (non sign)dioit.
Clear register ard divide tho nunter in the accurrulator hy the nmter lcrated in position x of the
selectrors, lævim the reapinder in the accumulator ard placim the quot ient in the renister.
Shift the control to the left-hard order of the order pair located it position x in the selectrcns.
Shift the control to the rioht-hard order of tip order pair Iccated at pcsition x in the selectrcns.
If the ntnter in the accurulator is shift the cmtrol as in Cu+S(x).
If the nurrter in the accuru3ator is shift the control as in
Transfer the rurber in the accunulator to pcsitim x in the selectrons.
Replace the left-härd 12 digits of the leftoer-d order Iccatgd at position x by the 12 digits 9 to
20 (fram the left) in accumulator.
R?place the left-hard 12 digits of the order located at pcsition x by the 12 dinits 29
to 40 (frav the left) in the accumlator.
. E E of the accumulator by Eo Eo Fl
Replace the contents Eo El
38
• • of the accwulator ard the register
the contents Eo E.
• • •nag •
by Ea ...Esp no
• Req ister neans arithßEt ic register.
```

<a id="planning-and-coding-008"></a>
## planning-and-coding-008 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 16); Volume I printed 6

Source: [physical PDF page 16](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=16); reading unit `p016`, lines 7–33.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-009](#planning-and-coding-009), [planning-and-coding-007](#planning-and-coding-007)

```text
6.
FIGURE 7.1
b.
c.
d.
Second: It is clear that this notation is incomplete urEatisfactory.
Figures 7. 1 d—f fail to indiCate ho•,' C gets into these loops, hov rrany t irres it circles
each loop, and hcw it leaves it. e-f, eod. also leave it open what the hierarchy of the
IOOF is, in what order trey are taken up by C, etc.
Actual ly the description of an indLEtion is only complete if a criterium
is specified which iruiicates whether the iterat ive step should be repeated, i . e. the
loop circled mre, or whether the iterat ions are completed and a ne.•.' path is to be
entered. kcordingly a simple induct ion loop, I ike the Ore shovn in Figure 7.1 d, needs
an indication of the path on which C enters it at the beginning of the induct ion, the
path on which C leaves it at the of the induct ion, ard the area in which the criteriurn
referred to above is appl ied, i.e. Mere it is detemined whether C is to circle the loop
again, or whether it is to prcceed on the exit path. will denote this area by a box
with one i nput and two output a r rms, ard call this an alternative box. Thus
Figure 7.1 d, becorres the mre c'*Vlete Figure 7.2 b. The alternat ive box may also be
used to- bifurcate a I inear, non—looped piece of Cis course. IMeed, alternative pro—
cedures nay be required in non—inductive too. This is sho•vn in Figure 7.2 a.
Final ly m Itiple i rdwtion loops, campleted in this serse, are On c-d, eod- It
Wi II be noted that in these irÉuct ions in c the srrøll loop represents an irdu:t ion that
is subordirate to that one on the big Imp, i .e. part of its induct ive step. Simi larry
in d the two sae I I loops that are attacted to big loop are in the sarTE subordinate
relation to it, while the loop at the extre'TE right is again subordinate to the loop
to which it is attached.
```

<a id="planning-and-coding-009"></a>
## planning-and-coding-009 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 17); Volume I printed 7

Source: [physical PDF page 17](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=17); reading unit `p017`, lines 7–33.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-008](#planning-and-coding-008), [planning-and-coding-010](#planning-and-coding-010)

```text
7.2
IN
o uT
OUT
mrd: The alternat ive boxes wh ich intraitxed correspond to the
the intent ion that they express will
corditional transfer orders xCc , xCc• . .e.
be effected in the actual CCde by such an order. Of the two output brarches (cf.
e.g. Figure 7.2 a) one leads to the order fol irmediately in the select ron
rrpmry upon the last Order on the input brarch, whi le the other leads to the left
or the right hard order in S(x).
If at the mcnent at which this decision is rude
the nur±er u is in A, then u < o causes the first brarch to be taken. will place
the u which is thus val id into the alternat ive boy, arG rrerk the two brarches repre—
sent ing the two alternatives u ? o and u Coby + by respectively.
In this
way Figures 7.2 a-b beccae Figures 7.3 a-b. Figure 7.3 b be rede still mre
specific:
If the it-duct ion variable is i, arø if the irdction is to erd when i
reaches the value I (if i's suxcess ive values are O, l, 2 .
then this rreans
that I iterations are wanted), and if, as shcyn in Figure 7.3 b, the — brarch is
in the ion loop while the + branch leaves it, then the u of this Figure
•be chosen as i — I, and the ca-nplete scheme is that shovn in Figure 7.3 c.
rrøny irøuctions the natural erviing is by i + 1, having reached a certain
value Then the above
• — I is to be replaced by i —
```

<a id="planning-and-coding-010"></a>
## planning-and-coding-010 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 18); Volume I printed 8

Source: [physical PDF page 18](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=18); reading unit `p018`, lines 13–43.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-009](#planning-and-coding-009), [planning-and-coding-011](#planning-and-coding-011)

```text
8.
FIGURE 7.3
a.
c.
Two or mre Of the f ION diagram nay rærge at certain points.
This takes place of recess ity at the input of tte alternative box of an irduct ion loop
(cf. Figures 7.2 arxl 7.3 b—c), but it can also happen in I inear, nor—looped
piece of CIS course, as in Figure 7.4. This corresponds to two alternative
procedures leading up to a camon oontinuntion.
7 The f ICW diagram Of C, as described
in 7.3 is only a skeleton of the præess that is to be
represented. pass therefore to examining the add i—
t ions which have to be mede in order to carp lete ttk
schere.
First: (ÄJr f ION diagram in its present
form does not i rdicate what arithmet iCal operat ions
ard trarEfers of numbers actual ly take place along the
various parts of its course. These, hcMeveö, represent
the properly nether-rat ice I (as distinguished f rcxm
log activities Of the rrøchine, ard they should be
sti0Nn as such. For this reason '.•æ will denote each
7.4
area in which a coherent group of such operatiors takes place by a special which
we call an operation box. Since a box Of this category is an i into the •f ICN
diagram at a point where no branching or merger takes place, it rrust have one input
arro,v and one output arrcw. This distinguishes it clearly f rm the alterrztWe boxes
of Figure 7 3. Figures 7.5 the positions of operation boxes in varlas
looped unlooped f ION diagrans.
FIGURE 7.5
a.
c.
```

<a id="planning-and-coding-011"></a>
## planning-and-coding-011 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 19); Volume I printed 9

Source: [physical PDF page 19](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=19); reading unit `p019`, lines 8–45.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-010](#planning-and-coding-010), [planning-and-coding-012](#planning-and-coding-012)

```text
9.
Second: Bhile•C rrO.es along the f ICW diagram, the contents of alter—
native boxes (which have icated) arvi of operat ion boxes (which have nat
indicated yet J will, in general, keep charging — arri so will various other things ttBt
have to be asscciated with these in order to carplete the picture (arri which Be tuve
not yet irdicated either). This whole modus præedendi assures, hoæver, that the f iOS'
diagram itself (i.e. the skeleton of Figure 7.3) remains urwFanged. This, hcvever, is
not unqual ifiedly true. To be specific: The transfer orders xC, xc' (urrorøitional ) ,
and also xCc, xCc' (corditional ) , can be changed in . course of the process by substi—
tution orders xSp, xSp1. This changes the connect iors between various parts Of the
flay diagram. When this happens, will terminate the corresporviim part of the flay
diagram with a circle nerked with a Greek letter, and originate the alternat ive con-
t inuat ions f rm c i m les nerked with properly indexed spec inens of the Sane Greek letter,
as shcwn in Figure 7.6 b. call this arrangerænt a variable remote connection.
FIGURE 7.6
The circle
b.
Q.
is t entrance to t his remte connect ion, the c i rc
are the exits from it.
WTE l: The lettering with Greek letters a, p, Y, . need neither be
monotone nor uninterrupted, and deciral fract fol loving the Greek letters be
used for furthEr subdivisions or in order to interpolate omiss ions, etc. All of this
serves, of course, to facil i tate rrodificat ions arri correct ions on a diagram which is
in the process of being drawn up. The sane prirriples will be appl ied subsequently
to the enumerat ions of Other ent it ies: Constarry intervals tcf. the last gzr-t of 7 . 6,
the basic Greek letters being replaced by Arabia nugrerals ) , storage posit ions (cf. the
beg inning of 7.7, the basic Greek letters being replaced by Engl iSh capitals J, operation
boxes alternat ive boxes (Cf. the last part of 7.8, the bas ic Greek letters being
replaced by Ronen nurreralsJ.
In the case Of an uxond itional trarsfer order which is never
subst i tuted, the f I cw diagram can be kept rig id, ard no rerrote connect ion need be used.
It is neverthe less sorpt convenient to use one even in st_ch a case as shc»vn in
Figure 7.6 a. Irv-deed, this deVice may be used at any point of the f 1m' diagram, even
at a point where no transfer order is læated arid C scans I inearly ( i.e. frcM1 One
half—word to the next one). This is so when the f lcw diagram threatens to assure an
urnvieldy form (e.g. grov off the paper' ard it is desired to dissect it or . to rearrange
it. An arrangerent of this type will be cal led a fixed remote connection.
```

<a id="planning-and-coding-012"></a>
## planning-and-coding-012 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 20); Volume I printed 10

Source: [physical PDF page 20](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=20); reading unit `p020`, lines 6–60.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-011](#planning-and-coding-011), [planning-and-coding-013](#planning-and-coding-013)

```text
rhe c i rc les and
are again the entrance ard the
exit Of this connection. The Greek letter at the exit need, of course, not be indexed
nox. It is son-etirres convenient to give a rermte connection of either type more than
one entrance. These are then equivalent to a pre-entrarce confluence. They ney be
used when the gearetry Of the f 1 diagram rakes the expl icit drawing of the conf luence
i nconven ient.
7-5 pointed Out at the beg inning of the Secorri rerrerk in 7.4, that
our present form Of the flav diagram is Still incanplete in two "Bjor respects:
the contents of the operat ion boxes have not yet been indicated. Secorri, certa in
further features of the process that accompanies the course of C have not yet been
brought out. Let us begin by analyzing the latter point.
No compl icated calculat ion can be carried out without storing considerable
nurrerical ffhterial while the ion is in prcgress. This storage problem has been
cons idered in cons iderable detail in Part of this report (cf. in particular 1.3, 2,
4 there}. The storage involve data which are needed for the entire duration of the
præedure, and are therefore never changed by that præedure, as well as data which
play a role only during part of the procedure (i.e. during one circl ing of an induct ion
1009, or during a part of the course over a linear piece or an induct ion loop) ard nay
therefore be changed ( i.e. replaced by other data) at the end of their usefulness.
These changes sen,'e, Of course, the very important purpose of making it possible to use
the same storage (selectron mermryl space successively for changing and differænt eras
We will talk accordingly of fixed and of variable storage. These corcepts are to be
understocd as being meaningful only relatively to the praedure wh ich are cod ing.
it will also be found useful to use them relat ively to certain parts of
Cccas i Ona I I J
that præedure.
Before develop the rteans to irriicate the fom and contents of the
(fixed ard variable) storage that is required, it is necessary to go into another
natter.
A rretherrøtical-logical procedure of any but the Icyæst degree of
ccynplexity cannot fail to require variables for its description.
It is important
to visual tze that these variables are of kinds, narrply: Fi rst, a kind Of
variable for which the variable that occurs in an induction (or mre precisely: with
respect to which the irduction takes place J is typical. Suzh a variable exists only
within the problem. It assunps a sequerce of different values in the course of the
procedure that solves this problem, arxi these val LEs are stccess ively deterr,ined by
that procedure as it develops. It is impossible to substitute a value for it ard
senseless to attribute a value to it "fran the outside". Suth a variable is cal led
(with a ten-n borrmed f ran forrel logics) a bound variable. Second, there is another
kind of variable for which the paraneters of the problem are typical
iMee-& it is
essentially the sane thirg as a parameter. Such a variable has a fixed valLE
out the procedure that solves the problem, i.e. a fixed value for the entire problem.
If it is treated as a variable in the præess of planning the sequerxze, then a
value has to be subst ituted for it and attribited to it ("fran the outside"),
in
order to prcxiure a ccxled that can be actual ly fed •into the mchine. Sl.Eh
a variable is cat led (again, borroving a term fran fornBl l:ogics) a free variable.
[n disctßsing the Veys to ird icate the form ard contents of the
storage that is required, there is no traJbie in deal Ing with free variables:
They are as gocx:f as constants, aryl the fact that trey will acquire specific values
only after the mriing p«eess is cornpleted does not influence or compl icate that
process. Also, fixed storage offers no problerrs. The real crux of the rmtter
```

<a id="planning-and-coding-013"></a>
## planning-and-coding-013 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 21); Volume I printed 11

Source: [physical PDF page 21](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=21); reading unit `p021`, lines 7–58.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-012](#planning-and-coding-012), [planning-and-coding-014](#planning-and-coding-014)

```text
is the variable storage ard its changes. An item in the variable storage changes when
(This is effected by the operat ion boxes,
it is expl icitly replaced by a different one.
cf. 7.4 ard the detailed discuss ion in 7.7, 7.8.) When the value of a bound variable
changes 'this is effected by the subst itut ion boxes, cf. the last part of 7.6', this
should also cause irdirectly a change of those variable storage i!erTE in whose expression
this variable xcurs. Ho•ever, we prefer to treat these variable value changes merely
as changes in notat ion which do not entail any actual Ohange in the relevant variable
storage i teas. Cn the contrary, their funct ion is to establ iSh agreement between pre—
ced ing and fol ICNing express ions (occupying ident iCal storage pos it ions which differ
as expressions, but whose difference is rermved by the subst i tut ion in question. (For
details cf. the third rule relative to storage in 7.8. I
7.6 After these preparat ions we can proceed to an expl icit discussion
Of storage and Of bourgi variables.
In order tc be able to give complete indicat ions Of the state of these
ent it ies, it is necessary to keep track Of their changes. We wi II therefore nark along
the f ICN diagram the points where charges of the content of any variable storage or of
the value or dcnv•tin Of variabil i ty Of any -bound variable takes place. These points will
be cal led the transit ton Potats. The transit ion points subdi.vide the f I ON diagram into
conrected pieces, a lorg each of which all changing storages have constant contents ard
all bouM variables have constant values.
The rermte connect ions Of the second remark
in 7.4 rate in this respect as if they here unbroken paths. For a variable remote
connection all brarthes are regarded in this way.) these constancy
intervals. Clearly a constarcy interval is bounded by the transition points on its
end i ngs.
NOTE: The constant contents and va lues attached to a constarcy interval
'-ray , Of course, vary frcn one passage Of C over that interval to another.
Let us nov consider the transition points sorewhat closely.
introduced so far three kinds Of interzruptions Of the f Icy.' diagram: Alternative boxes,
operat ion boxes, rermte connect ions. Of these thc first the third effect no charges
of the type under cons iderat ion, they influence only the course Of C. The seccM, hcw—
ever performs arithrretical operat ions, therefore it rrey require storage, and her-ce
effect changes in the variable storage. In fact, ail variable storage originates in
such operat ions, and all operat ions Of this type- teminate in•cons igning their results
to storage, which storage, just by virtue of this orig in, must be variable. Accordingly
the operat ion boxes are the transition points irasrruch as the Chang ing of variable
Storage is correrred. Thus we are left to take care of •those transit ion points which
Change the values or del imit the done ins of variabil i ty cf bound variables. Changing
the value Of a bound variable involves a Fithrret iCal operat ions which rust be icated.
An i rKiuct ive variable i, which serves to entnerate SLCCessive stages cf an iterat ion,
urcergoes at each chånge an i '-crease by one. denote this subst i tut ion by i + i .
It is, hcyever, neither necessary nor advisable to pemit no ot Ypr subst i tut ions.
Irdeed, even an irduction or iterat ion begins with a different subst itution, narrely
that one assigning to i the val LEO [or I ] i . e. O i for 1 i
] . In røny cases,
of which will pregent exarples, it is necessary to subst i tute with still mre
—+ i, wrere f is a furction of i itself as Bell as
Of Other variables j, k,
'For details cf. the first part of 7.7.' For this
reason wi I denote each area in which a coherent Change or group Of sux:h changes
takes place, by a speciat box, which •.•.e call a substitution box. Next consider
```

<a id="planning-and-coding-014"></a>
## planning-and-coding-014 — 7.3-7.6: flow, storage, substitution and assertion notation (physical page 22); Volume I printed 12

Source: [physical PDF page 22](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=22); reading unit `p022`, lines 5–51.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-013](#planning-and-coding-013), [planning-and-coding-015](#planning-and-coding-015)

```text
12.
changes, actually imitat ions, of tt-e dare ins of variabi it y of one or mre bound
variables, individually or in their interrelationships. It ray be true, that whenever
C actually reaches a certain point in flow diagram, one or rrore bourri variables
will necessarily possess certain specified values, or pcssess certain propert ies , or
Furthermore, at a point, irdi—
sat isfy certain relations with each other.
cate the val id ity of these I imitations. For this reason will denote each area in
which the val idity of such I imitations is being asserted, by a Special box, which '.•.'e
call an assertion box.
The boxes of these two categories (substitut ions and assert ions) are,
I ike the operation Doxes, insertions into pieces Of trp f ION diagram where no
or rrergers take p lace. They have therefore one i nput arro•é and one output arrc»a. This
necessitates sorre special nerks to dist inguish them operation boxes. In
these boxes in detail, certain dist inguishing rterks of this type will arise auta•røt ically
(cf. as above), but in order to clarify tetters we will also nark every substitution and
In addition, we will, for the t irre be it-y, also nerk substitution
assert ion by a cross
boxes with an s, fol Io.•ed by the bound variable that is changed and assert ion boxes
with an a.
Thus the operation boxes, the subst itution bues ard the assert ion boxes
produ:e together the dissect ion Of the f ION diagram into its constarEy intervals.
wi I I number the constarcy intervals with Arabic nunerals, with the rules for
subdividing, rradifying and correct ing as given in Note I in 7.4.
TO conclude, observe that in the course Of circl ing an it-duct ion loop,
at least one variable (the induct ion variable) change, and that this variable must
be given its initial value upon entering the loop. F-énce the junction before the alter—
nat ive box of an induct ion loop rust be preceded by subst itut ion boxes atong bothrpaths
that lead to it: Along the loop aM along path that leads to the At
fran an indistion loop the irxiLEtion variable usually has a (final) value which
in advarce, or for which at any rate a mathenat ical syntol has been introduced.
amounts to a restrict ion of the domain of variabil ity of the irdct ion variab le,
the exit has been crossed — indeed, it is restricted f run then on to its final
i.e. to only one value. "-erce this is usual ly the place for an assertion box.
A schere exhibiting all the features discussed in this sect ion is
in Figure 7.7.
FIGURE 7.7
(11
3
7
the exit
is
This
once
value,
s hc»an
8
```

<a id="planning-and-coding-015"></a>
## planning-and-coding-015 — 7.7-7.8: explanatory boxes and storage representation (physical page 23); Volume I printed 13

Source: [physical PDF page 23](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=23); reading unit `p023`, lines 8–59.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-016](#planning-and-coding-016), [planning-and-coding-014](#planning-and-coding-014)

```text
13.
7.7 ncw complete the description of our rrethod to irdicate the
successive stages aM the furrt ion ing of storage.
The areas in select ron (Tenor-y that are used in the course Of the
præedure under cons iderat ion will be designated by capital Petters, with the rules
for ing, rod if ying ard correcting as given in Note in 7.4.
The changes in the contents of this storage are effected by the operat icn
boxes, as described in 7.6. An operation box should therefore contain the follo.ving
ions: F irst, the expressions which have to be calculated. Secord, the storage
posit ions to wh ich these express ions have to be sent subsequent ly. The latter are
. if the expression Viri¯ (x, y, z are variables
stated b} an affix "to .
or other expressions) is to be for-red and then stored at C. 2, then the indicat ion
will be to. C. 2". It nay also be desired to introduce a new syrrbol for this
expæssion,• i.e. to deftne ore, e w = Then the indication will be
= to C. 2".
It should be added that an expression that has been calculated in an
operation box rray also be sent to a variable remote connect ion (i.e. to its entrarce,
cf. the last part of 7.4). The expression must, of course, be the designation of ore
.of the exits of that connect ion, and the operat ion cons ists of equat ing the designat ion
of the entrance to it. The latter is the Greek letter (poss ibly with decirTBls, cf.
töte I in 7.4), the forrrer is this Greek letter with a definite index.
No affix
is needed •in this case, since the des ignation of the entrame determines
the cont-ect ion that is rreant. Berce such an ogeration 'coks I ike this: "a = .
One or mre irdicat ions of this kind rake up the contents of every operat ion box.
NOTE l: An affix "to .
rrøy also refer to several positions.
E.g.
M)TE 2: The opt ional procedure Of defining a rew symbol by an express im
forrred in an operation box beco-res nemiatory when that box is fol lcm•ed by a point of
confluerEe of several paths. Indeed, cons ider the two operat ion boxes from which the
Constar-cy interval 7. issæs in Figure 7.7. Assure that their contents are intended
to be 'tx + y to C. ard "x —y to C. respect ively. In Order that C.I have a
fixed content throughout the constarcy interval 7, as required by our definit ions,
it is necessary to give the alternat ive expressions x + y and x — y a
say z. Then the contents of the two operat ion boxes in quest ion will be "z = x + y
to C. l" ard •z -x —
Y to C. l".
NCTE 3: A variant Of the præedure of a new syrnbol is to
define an expression involvirg a rew syribol, which will afterwards only occur as a
whole, or to defiæ tte val LR of a funct ion for a value Of its variable (usual ly
in an i rdtctionl. E.g.
ft i ' ' to A.2".
The contents of a subst itut ion box are one or mre subst itut ions of the
type described in 7.6, in conrpct ion with the definit ion of the corcept of a substi—
tution box.
Suzh a Substitution is wri tten like this:
I-ere i is a bourÉ variable, the one whose value is being changed (subst i tuted), whi le
. is an expression which rrøy Or ney not contain i itself as
as any other bound variables j, k,
. (and ary free variables or constants).
```

<a id="planning-and-coding-016"></a>
## planning-and-coding-016 — 7.7-7.8: explanatory boxes and storage representation (physical page 24); Volume I printed 14

Source: [physical PDF page 24](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=24); reading unit `p024`, lines 8–53.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-015](#planning-and-coding-015), [planning-and-coding-017](#planning-and-coding-017)

```text
14.
equal it ies,
table.
In
contents Of an assert ion box are one or mre re lations. These rrøy be
or inequal ities, or any other expressions.
The successive contents of the storage positions referred to above
. with decirrzl fract ions J rust be shoNn in a separate table, the storage
conjunct ion with this table a ist Of the free variables should be given
(in one line) ard a iSt of the bound variables I i o the next
The storage table is a double entry table with its I ines corresponding
to the storage pos it ions, ard its columns to the constancy intervals. Columns arvd I ines
are to be r-arked with the syrrbols and nurr%ers of the entities to which they correspond.
Each field of this table should shov the contents of the position that corresponds to
its I ine throughout the constarcy i nterval correspond ing to its col umn. These contents
are expressions which tray contain bound variables as ver I as free variables constants.
It shouZd be noted that the bound variab les rust appear as SLEh, without any attempt to
subst i tute for them their actual values, sir-Ce only the forner are attached to a given
constancy interval as such, whi Je the latter also on the Spec if ic stage in
course Of C, in which C passes at a particular occas ion th,rotgh that constancy interval.
It is obviously canvenient to fill in a field in the storage table only
if it represents a change fran the preceding constarcy interval . Therefore ve reserve
the right (Without Baking it an obl igat ion) to leave a field empty if it represents
no such change. In this case the field must be thought. of as having the sane content
as its I ine had in the colurm (or umns) Of the constancy interval (or intervals)
irrnpdiate;y precedir8 it along the f diagram. ( In the plural case, which occurs
at a junct ion of the flov diagram, these columns [constancy intervals] rust al I have
the same content as the line in quest ion. Indeed, without observing this rule, it
would not be possible to treat all incoming bramhes Of a junct ion as one constzrcy
interval. Cf., e.g. the constarcy intervals 2 7 in Figure 7.7.)
If this ante—
cedent column is not the one imediately to the left of the column in quest ion, it tray
be advisable tc irdicate its number in brackets in the field in quest ion.
Certain storage positions ines) possess no relevarce during certain
constancy intervals (columns) i . e. their contents are changed or produced aM becaT,e
significant at other stages of the præedure in other columns). The corresponding
field rrøy then be narked With a dash. The repet it ion rules given above apply to these
fields with too.
A scheme exhibiting all these features Is shown in Figure 7.8.
FIGURE 7.8
2
2
P
[2]
gti +1)
flj+l,i)
```

<a id="planning-and-coding-017"></a>
## planning-and-coding-017 — 7.7-7.8: explanatory boxes and storage representation (physical page 25); Volume I printed 15

Source: [physical PDF page 25](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=25); reading unit `p025`, lines 6–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-016](#planning-and-coding-016), [planning-and-coding-018](#planning-and-coding-018), [planning-and-coding-020](#planning-and-coding-020)

```text
15.
In Certain problems it is advantageous to represent several storage.
posit ions, i . e. several t by one I ine which must then be by a generic
variable, or by an expression containing one or mre such variables, arc not by a
definite nurröer. This variable will replace one or mre (or all ) of tt-e decirrøl
digits (or rather numbers) fol after the capital letter that denotes the
storage area in which this æcurS, or these variables my enter into an express ion
replacing those gig its (nurters'.
a I i he which is narked in this way the fields
will also be occupied by expressions containing that gereric variable or variables.
"Expressions" incliÆe, of course, also explarat ions which state what expression
should be forrred deperd ing on various alternat ive ities.
It rrøy be desi rab*e to use such variable—aerked lines only in a part
of the storage table, i . e. only for certain col ums (constancy intervals}. Or, one
want to use different system Of variable rrørkings in different parts. This
necess itates breaking the storage table up accordingly and grouping those columns
(constancy intervals J together for which the Same system of var iable markings is
be ing used
Sirce the f Icy,' diagram is fixed arÉ expl icitly drawn, therefore, the
columns of the storage table are fixed, too, and there can be no quest ion of variable
rrørkirgs for them.
In actual Jiract ice it may be preferable to distribute alt or part of
this table over the f ICW diagram. This can be done by attaching avery field at which
a change takes place to that constarry interval to which it i .e. its column) belongs,
with an indicat ion of the storage posit ion that it represents.
(This appl ies to
fields Whose I ine has fixed as Be M as to thæe whæe I ine has variable
mrkings, cf. above.) Since the irrnpd iately preceding constarcy intervals are at
once seen in this arrangement, there is here no nee< to give any Of the indicat ions
suggested by our repet it ion rules.
For mnemtechnical reasons it Tay be occasional ly
worthwhile to ind icate at a constancy interval the contents of certain fields at which
no changes are taking place at that stage (e.g. because no change took place there over
a long run, and the brig indicat ion is at a remote point in the f I ON diagram).
These rrethcÉs, the tabular aM the distributed icat ion Of tte storage, mey also
be used together, in mixed fornE. Thus, if the distributed nethod is used in principle,
there nay be constarEy intervals at Which (Tore fields have to be described than con—
venient (e.g. for reasms of space'. Such an interval mey then be marked by an asterisk,
ard a "arhat storage table aede, which covers by its coli-rms only the constancy inter—
vals with asterisks. Figure 7.8 is the tabular form Of storage table Of a f ICW
diagram which is part of that one of Figure 7.7 (without the port ion along tre constarcy
intervals 7, 8, part of which will be given in full in Figure 7. IO. The
distributed form is shoal in Figure 7.9.
```

<a id="planning-and-coding-018"></a>
## planning-and-coding-018 — 7.7-7.8: explanatory boxes and storage representation (physical page 26); Volume I printed 16

Source: [physical PDF page 26](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=26); reading unit `p026`, lines 7–37.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-017](#planning-and-coding-017), [planning-and-coding-019](#planning-and-coding-019)

```text
16.
F I GI.JRE
7.0
2
2 9(1)
7.8 The Only const i tuants. Of the f diagram about which mre remains
to be said are the operation boxes, the subst itut ion boxes and the assert ion boxes
although even for these short descript ions were given in 7.7. will nc>v discuss
them exhaust i vel y.
An operat ion box conta ins one or rrore express ions, and it indicates
that these expressions have to be calculated. Every expression rray or rrøy not be
preceded by a syrrbpl to which it is equated aM which it is defining (cf. also
Note 3 in 7.7 J; and it trey or ray not be follcwed by an affix "to
the
being occupied by the symbol Of a def.inite posit ion, at which the express ions in
is rnissirg, this neans that the
question is to be stored. If the affix "to .
expression in quest ion rrey be stored in the accumulator or the aiithlret ical reg ister
or othersise, but that any rate it will not be needed at any remoter future stage.
A subst itution box conta ins me or mre expressions of the type
'If i" where i is a bourri variable, and f is an expression wh ich or rray not
contain i arr] any other bourd variables, as well as any free variables and constants.
A subst i tut ion box is aløhys narked With a cross g.
An assert ion box contains one or mre relations (cf.the correspo.Ging
discussion in 7.7).
It is always nerked with a cross
The three categories of boxes that have just been described, express
certain act ions which nwst occur, or situat ions which rrust exist, when C passes in
its actual course through the reg iors which they represent. will call these the
effects of these boxes, but it rust be real i zed, that trpse are effects in a symbol ic
sense only.
```

<a id="planning-and-coding-019"></a>
## planning-and-coding-019 — 7.7-7.8: explanatory boxes and storage representation (physical page 27); Volume I printed 17

Source: [physical PDF page 27](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=27); reading unit `p027`, lines 10–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-018](#planning-and-coding-018), [planning-and-coding-020](#planning-and-coding-020)

```text
17.
The effects in q'pst ion are as fol
The bound variables occurir,g in the express ions of an operat ion box must
be given the values which they pssessed in the constarEy interval itmEdiately preced ing
that box, at the stage in the course of C irmediately preceding the one at which that
box was accually reacred. The calculated expression rust then be s Lhstituted in a
storage pos it ion corresporxi ing to the irmediately fol lovirg cbnstarcy interval, as
ird icated.
A Subst i tut ion box never requires that any SPEC if ic lculat ion be rrade,
it indicates only what the value of certåin bound variables will be from then on.
Thus if it contains "f —s i", then it expresses that the value of the bound variable
i will be f in the itm•ediatel.y fo' loving constancy interval, as well as in atl subse—
quent constancy intervals, which can be reached frun there without cræsing another
substitüt ion box with a —Y i" in it. The _expression f is to be formed with all
bound variables in it having those values which they possessed in the constarcy interval
irmediately preced ing the box, at ttE stage in the course of C irmediately preceding the
one at which that was actually . (This is particularly significant for i
itself, if it æcurs in f.)
An assert. ion box never requires any calculat i Ors be nude,
it ind icates only that certain relat ions are atto-rat ical ly fulfi led whenever C gets
to the region which it occupies.
The contents of the. various fields of the storage table (tabulated' or
distributed) i .e. the storage positions at the variots Constancy intervals
rust fulfill @rtain Conditions.
It should be noted that these rerarks apply to the
contents of the field in the flou diagrams, and-not to the contents of the correspoM-
ing posit ions in the actual rachine at any actual rorent. The latter obtain from the
for-rer by subst in each case for every bound variable its va accord ing to
actual stage in the Course of C and Of course for every free riable its value
corresponding to the actual problem being solved. Nov the condit ions referred to above
are as folloas•.
First: The i nterval in quest ion is irfrrediately preceded by an operation
box with an expression in it that is referred "to this fie:d: The field contains
the express ion in q•æst ion, unless that expression is preceded by a symbol to which it
is equated arÉ which it FS defining (cf. also Note 3 in 7.7),
in 'Vhich case it contains
that syrröol.
&cond: The interval in question is irmediately preceded by a Substi—
tut ion box containing or rrore express ions "f i" where i represents any
variable that CCCuZS in expression Of the f ield: Replæe in the expression Of the
field every occurrence Of every SLCh i by its f. This rmst produce the express ion which
is val id in the field of the sane storage posit ion at the constancy interval irmediately
preced ing this subst i tutim box.
Third: The interval in question is irrrvadiate'y preceded by an assertion
box: It rust be demostrable, that the expression of the field is, by virtue of the
relations thÅt are val idated by this assert ion box, equal to the express ion whith is
valid in the field of sare storage position at the constarcy interval irmediately
```

<a id="planning-and-coding-020"></a>
## planning-and-coding-020 — 7.7-7.8: explanatory boxes and storage representation (physical page 28); Volume I printed 18

Source: [physical PDF page 28](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=28); reading unit `p028`, lines 14–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-019](#planning-and-coding-019), [planning-and-coding-021](#planning-and-coding-021), [planning-and-coding-017](#planning-and-coding-017)

```text
18.
preceding this assertion box. if this derronstration is not canpletely obvious, then
it is desirable to give indicat ions as to its nature: The min stages of the
'Tay be incl uded as asser± ions in the assertion box, or sorp reference to the place
where the proof can be found ney be made either in the assertion box or in the field
under considerat ion.
Fourth: The i nterval in quest ion is iately preceded by a box which
fal Is into ne ither of the three above categories. The field contains a repet it ion of
what the field of the San-e storage posit ion contaired at the constarzy interval irTrre -
diately preceding this box.
If the interval in quest icn contains a rrerger (Of several branches
Fifth:
of the f lm diagram}, so that it is in-mediately preceded by several boxes, belonging to
any or all of the four abwe categories, then the correspond ing condit ions (as stated
above) must hold with respect to each box.
Finally: The contents of a field need not be if it is felt that
the amiss ion (or rather the aggregate of sirrultaneously effective omissions of this
type) wi II not impose a real strain on the reader, due to the annunt of impl icitly
given rrøterial that he rust rerrerr,ber. Such unissions will be indicated in rteny cases
where nere repetitions of previous contents are involved. (Cf. the renerks rrBde in
this connect ion in 7.7, in the course of the discussion of the distributed forrn of
scorage.
The storage need not All the storage posit ions actual ly used.
The calculat that ape required by the expressions Of an operation box or Of an
alternat ive box "By necessitate the use Of add it ional storage space. This space is
then sgecifically attached to that box, i.e. its contents are no longer requi red and
its capad i ty is avai Jable for c&her use as soon as the instruct, ions of that box have
been carried out.
rigure 7. sho•vs a complete f diagram. It differs f run that one of
Figure 7.9 only inastm_Kh that the operation boxes and the storage boxes were left empty
It is easily verified that it represents the (doubly i rdct ivel prccedure
then.
defining the nuqter p, which is desqcibed unaer it.
FIGURE 7.10
1
1 t,A.1
2
12.6
2
2
- gti).
2
2
```

<a id="planning-and-coding-021"></a>
## planning-and-coding-021 — 7.9: coding stages and explanatory column (physical page 29); Volume I printed 19

Source: [physical PDF page 29](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=29); reading unit `p029`, lines 5–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-022](#planning-and-coding-022), [planning-and-coding-020](#planning-and-coding-020)

```text
Anong the boxes Shovn on this f 1m d iagram the operat ion boxes and the
alternat ive boxes ard the variable remote connect ions require further, detailed ccding.
The subst itution boxes and •the assert ion boxes { i.e. the boxes which are marked by a
are purely explaratory, and require no coding, as pointed out earl ier in 7.8.
The storage boxes have to be essent ially as they stard. (For a II this cf. the
details given in 7.9.) Thus the remaining problem of coding is attached to the opera-
t ion boxes, the alternat ive boxes and the variable renote connect ions, ar-É it Wi
prove to be in the nein only a pr±ess of static translation (cf. the erd of 7. I as
In order to prepare the ground for this final process of detai led
as 7-9).
{stat ic) ing, enurrerate the operat ion boxes and the alternat ive boxes by Rcyrøn
nun-era Is, with the rules for seqtEncing, subd ividirg, nod if ying and correcting as
Figure 7. shcvvs such an enumeration. The variable remote
given in Note I in 7.4.
connect ions are a I ready enuærated.
Final ly, irWcate the beg inning arri the erd Of the ccnpleted f 1m
diagram by two circles
and
7.9 Ve can describe the actual præess of coding. It is a
success ion Of *eps that take place in the fol Imi rg Order .
First: is, Of Course, preceded by a iCal stage of
preparat ions. The rratherrøt iCal or nztherTRt ica'—phys iCal process of understanding
the problem, of dec idirg with what assumpt ions and what ideal izations it is to be
cast into equat ions Conditions, is the first step in this stage. The equat ions
arxi corÉit ions thus obtained are rigorous, with respect to the system Of assunpt ions
andideal izations that has been selected. Next, these equations and condit ions, which
are usual ly of an analyt iCal possibly of an impl icit nature, rn_jst be replaced by
arithnetical aru expl icit procedures. (These are usually step—by—step processes or
SWCeSS ive approxiret ion prccesSeS, or processes 'Nit h, both of ttese characterist ics —
and they are a lmst a 'ways characterized by multiple i rdLEti0ns.) Thus a procedure
obtains, which is approx irate in that sense in which trp preced ing one was rigorous.
This is the second step in this Stage.
It should be noted that the first step has nothing •to do with comput ing
or with røchines: It is equally necessary in any effort in mthermt ics or aepl ied
ics. Fur-then-mre, the second step has, at least, mthing to do with
rechanlzat ion: It muld be equally necessary if the problerrs vere to be cmputed
"by hand l'.
Final ly, the precision of the approx ion prccess, introduced by t Fe
secuxd step, rust be est irreted. This inclides the .errors due to the approximations
by the sæcond stpp, as I as the errors due to the machiryrs recessari ly
rourding Off to a fixed ntner Of digits ( in our projected machine to a Sign plus 39
binary digits, cf. part l. Of this report J after every iate operat ion
tspecifical ly: after every rmltipl icat ion division). These are, of course, the
we I I—kncwn categories Of truncation errors and Of round—off errors, res*ctive'y.
In connection with these it is also necessary to eSt in-ate Sizes to which
the numbers that occur in any part and at any stage of the calculat ion, gro«.
After these imits have been establ isred, it is necessary to arrange the calculation
so that every nurrtcr is represented by a mltiple lby a fixed of 2) which I ies
in rarpe in .which the mchine porks ( in Our projected rrachire between —l ard I ,
cf. Part 1 of this report). This is the third and last step of this stage. Like
the second step, it is necessary because of the camutational character of the prob 'en,
r-atrer than because of the use of a •røchine.
```

<a id="planning-and-coding-022"></a>
## planning-and-coding-022 — 7.9: coding stages and explanatory column (physical page 30); Volume I printed 20

Source: [physical PDF page 30](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=30); reading unit `p030`, lines 10–59.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-021](#planning-and-coding-021), [planning-and-coding-023](#planning-and-coding-023)

```text
20.
In our case there ex ists an alternat ive with respect to this third step:
It rray be carried. Out by the planner, "rrathecrøt iCal I y", or it nay be set up for ccynpu—
tat ion, in which case it be advantageous to have it, too, carried out by the machine.
After these pret iminaries are the coding proper Can beg in.
Second: Coding begins with the Of the f 1 0B,' diagratæ. This is
the dynatnic or macrosco#ic stage of cod ing. The f ION diagram must be drawn on
basis of the rules and princ iples developed in 7-3
— 7.8. It has been our i nvariab'e
experieæe, that once prob 'em has been understcnd and prepared in the sense of the
preced ing first remark, the drawing of f ICN diagram presents I itt}e difficulty.
Every nhtherrøt ic ian, or every rrcÉerately aztherret iCal ly trained person should be able
to do this in a rout ine nanner, if he has famil i?rized h iffEelf with the nein examples
that follow in this report, or if he has had som equivalent training in this rrethod.
It' is advisable to draw a (usual ly partia') storage table for the mir
data of the proble&l, and from then on either purely distributed, or mixed distri—
buted and tabular storage, pari passu with the evolution of the diagram. The f
d iagram is, Of course, best started with one Of the lc»est innermcEtJ inductions,
praeed 'n9 to higher irduct ions which contain it, revert ing (after these are
•exhatßted) to another lo•.est induction if any are left), etc., etc.
No diff icutt.y
wil I be found in keeping the developing diagram corplete at every stage, except
for certain enunprat ions which are better delayed to the ervi (cf. be ION).
tt is difficult to avoid errors or omissions in any but the simplest
problers. Ho.•.ever, they should not be 'frequent, arri will in rüFt cases signal ize
theaEe Ives by soæ inner rraladjustiænt Of the diagram, which obvious before
the diagram is convleted. The flexibil ity of the system of 7.3 — 7.8 is such that
correct ions and modificat iohs of this type can almcst alnays be appl ied at any stage
Of the praess without throNirg Out Of gear the prccedure Of drawing the d iagram,
and in part icuiar without creating a recessity of "startirQ all over again".
The enumeration of the distribüted storage and of the rermte connections
and of the constarcy intervals should be done pari passu with the drawing of the diagram.
The enumeration Of the operation boxes aru Of the alternative boxes, on the other tend,
is best done at the end after the f Icy,' diagram has been canpleted.
After a nuder-ate experience has been acquired, nnny simpl i fications and
abbreviations will themelves to a Irmst any coder. These are best v as
hdividual variants. wish to mention only one here.' If distributed storage is
extensively used, only a (if any) armng the caretanéy intervals will have to be
en umerated .
Third: The next stage consists of the trdividual coding of every
operation box, at ternative box ard variable remte connection. This is the static
or microscopic stage of cod ing.
Its min virtue is, that the boxes in quest ion can
now be taken up one by ard that the work on each of them is essential ly un—
affected by the work Of others. (With one exception, cf. below.
feel certäin that a moderate armunt of with this stage
of coding suff ices to renove fron it all diff icult ies, ard to rreke it a perfectly
rout ine operation. The actual præedure Wi II arnply Clear by reading the
examples that fol in this report. state here only general principles which
govern the procedure.
```

<a id="planning-and-coding-023"></a>
## planning-and-coding-023 — 7.9: coding stages and explanatory column (physical page 31); Volume I printed 21

Source: [physical PDF page 31](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=31); reading unit `p031`, lines 5–60.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-022](#planning-and-coding-022), [planning-and-coding-024](#planning-and-coding-024)

```text
21.
The cod i nQ of a variable rerrote connect ion is best attached to the
ilmediate'v precedinq box.
If it is preceded bv several such boxes, either of these
be used; if no suitable box is avai I able, it may be given a Rorran nurreral and
treated as a separate box.
The cod inq of the I ovation or alternative) boxes rerTBins. The cod inq
Of each box is a Separate operat ion, and we cal led it, as such, stat ic. This is just i—
fied in this sense: The course of C such a pericÉ of codinQ is strict 'v linear,
i.e. there are ro jumps forward or backward 1 by the Cu or Cc type transfer orders —
the orders 13—16 in Table —
except possibly at the end Of the period — C rmveS
without omitt inq anythina and without ever qoinq twice over the sane arourri (within
one period of this tvpe). It is in this sense only that the process is static:
Substitut ions, i.e. chanaes in the memrv (her-ce either in the storage or in the
In addition, partial substitutions (bv the Sp tvoe
orders), occur at ever v step.
subst itution orders — the orders 18719 in Table Il) cause a sl inht deviation from
strict inearitv: Thev affect orders Ithe ones *ich are to be rrodified bv substitu—
In this situat ion it is best to leave in the
tion) which have been coded vet.
subst itution order the space reserved for the posit ion trørk of the order to be substi—
tuted (in the prel imi nary enurærat ion, cf. below) 3TPtv, and nerk the substitut ion
order as incarolete. After all orders have been coded. all these vacancies can be
filled in. These fill inc—in operatiohs can be effæted within a sinale linear passaae
over the enti re coded sequence.
The ccÉIng Of such a box cccurs accordingly as a simple I Inear
Sequence, ard it is therefa-e næessary to define a system for the enurrerat ion of
the orders within the seqærEe (Of thls box). We catl It the preliminary
entmeration, because the nurbers which we ass ign at this stage are not thæe that
will be the x's of the actual pcsit ion in the selectrcn rrvmry. The latter form
the final enuæration to be further be 10M. The prel imi nary Ion
is def•ned as fol icv,s: The syrrOol of the box order consideratlon is to be shoa•n,
then a cam-ä, ard then an Arabic nunerat
— the latter being wed to enurerate
the code orders of this •seqænce. We might again d I Icy,' the rules for sequertlng,
ard correcting as given in Note I in 7.4, for this enurrera—
t ion, too. It will, hosever, hardly ever be necessary to have reecurse to these —
there will alnost never be any difficulty in carrying out a s Imple Iinær
of the ent ire sequerce pari with its ccding.)
Thus the enumeration for a 11.1 miaht be 11.1
Actual lv typse t be written under each other, and the box Symbol (l J. I in
the above case) need be only the first tire. In everv order the expression
SIX) will have to be written with the full prel imi nary syrnbol Of x, e.a.; 511. l, 3).
(This exmple must, of course, be thouqht of as referrina to a select ron position x
containina order.
If x Contained a an express Ion I ike SIA. l, 2) be
tvpica!.)
Refererces to a variable rerote ion are best "Bde by its
Greek tetter Ipossiblv with decinels, cf. I in 7.4, ard with or without ir&xina
according to *ether the ent or the exit is treant), sir-ce it not be feasible
or oonvenient to determine at this staae tte ident i ficat ions of its parts With the
app 00 riate Ryrøn numeral boxes.
Anv storaae that becoaes necessary in the course of this codim in
excess of the tabulated or distributed storage of the flow diaÄrarn, i.e. storage
attached to the cf. the last part of 7.8), has to be shown separa@v, as
```

<a id="planning-and-coding-024"></a>
## planning-and-coding-024 — 7.9: coding stages and explanatory column (physical page 32); Volume I printed 22

Source: [physical PDF page 32](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=32); reading unit `p032`, lines 6–66.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments. Coordinator visual supplement is pending for the legible explanatory-column prose.

Related: [planning-and-coding-023](#planning-and-coding-023), [planning-and-coding-025](#planning-and-coding-025), [planning-and-coding-029](#planning-and-coding-029), [planning-and-coding-161](#planning-and-coding-161)

```text
22.
Local storage- The iocal storage should be enurerated in the sane wav as indicated
above, but with a syntol s after the coma, e.q. :
I s l; '1.1, s.2;
(For
an S! x: which refers to such a position one miqht write, e. Q. SI II.
l, s. 2), in the
sense of the sugqest ion in the precedinc paragraph. Hoæver, sirce the reference is
by its nature to the box under consideration at the tire, it is lea itimte to abbre—
viate bv omittina the box Symbol, writing S(s.
The cod ina itself should be done in a colum Of its own, enumerated as
indicated above. It is advisable tc paral lel it with another, explanatory, column,
which shows for each order the effect of th e substitution that it causes. This
effect apgpars, of course; in one of the fol lowinq places: The accumulator (syrtcl:
Ac', or the arithmetical reqister (symbol: R), or storage position or coded
order (symbols as described up to now). The explanaVrv column then shoas each time
the symbol of the place where the subst itut ion takes place, and its contents after
the substitution. The Cu cr Cc type transfer orders (the 0 rters 13— 16 in Table I
cause no substitut ion, thev transfer C instead land thev occur only at the end of
the sequence)
hence thev require no explanat ion.
An order in the sequence, which becmes effective in a subst ituted
form (substituted bv an earl ier order in the sequence), should be in its or i—
Qi nat form and then, in brackets, in its subst ituted form. The oriainal for-Tn mav
the sign Of irrelevance, or any other symbol (e.q. the number O, Of course,
have a
asa 12 diait binaru), in place of its x (in its SIX)).
It is this form which
'Tatters in the actual cod inq. In writing Out a code, it is best to use the sign
Of Fy-relevance in such a Case. Bhen it COTES to real coding, hovever, an actual
number ni.st be used, e.g. O.) The substituted form, on the other hand, is clearly
the one which will actually control the functioning of the machine, and it is the
one to which the expl anat ion should be attached.
repeat: feel certain that di rect, I inear coding according to
this pr incipie presents no difficulties after a mderate amunt Of experience has
been acqui red.
Fourth: The I ast stage of coding consists of assigninqkalt storage
positions and all orders their final nurrbers. forrær may be enumerated in any
order, say linearly. The latter then follow, also in a linear order, but with
the fol lowing restriction: The f lcm diagran irdicates that a certain box mst
fol law imediately after another operat ion box, or irmpdiately after the
— branch
of an alternative box. is the case where the transfer of C by a conditional
ln- this case the sequence
— type Cc — does not beccY1e effect ive).
transfer order
of the fcnrer box must begin in-rrediatety fol lowinq the end of the sequence of the
latter box: It can happen, that this principle requires that a box be the irrne—
diate successor of several boxes. In this cage all of the latter boxes (except
one) must be terminated by (uncond itional ) transfer orders to the former box.
Such a transfer order is also necessary if a.box requi res as its irmediate
successor a non—initial order of another box.
At this stage the identif 'Cation of every part (entrance aæ exits)
of every variable remote connection with appropriate (Roman nurneral) boxes i.e.
orders in them) must be establ ished. The Greek letter references to. these
connect ions will then be rewritten accordingly.
These print i ples express all the restrictions that need be observed
in the final, I inear ordering of the boxes. To conclude, ne note that it rust be
remembered, .that orders const i tute toaether a *Ord, i . e. that they have
toqether one final number, and are distinguished from each other as its "left"
or "right" order.
```

<a id="planning-and-coding-161"></a>
## planning-and-coding-161 — 7.9: explanatory column, transfer-order exception and substituted orders (visual transcription)

Source: [physical PDF page 32](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=32); reading unit `p032`, lines 68–72.

Attribution: Herman H. Goldstine and John von Neumann

Context: Supplement to the complete OCR page selection; preserves legible prose where OCR corrupts words. Neighboring source-page records retain the surrounding worked examples.

Transcription/context notes: Manual transcription from physical page 32, printed page 22. Line-wrap hyphens joined, mathematical subscripts rendered as plain Cu/Cc and punctuation dashes normalized to ASCII. These are parallel explanatory columns in the historical coding procedure, not an assertion about modern inline-comment syntax. Surrounding complete page context remains in the OCR record.

Related: [planning-and-coding-024](#planning-and-coding-024)

```text
The coding itself should be done in a column of its own, enumerated as indicated above. It is advisable to parallel it with another, explanatory, column, which shows for each order the effect of the substitution that it causes. This effect appears, of course, in one of the following places: The accumulator (symbol: Ac), or the arithmetical register (symbol: R), or some storage position or coded order (symbols as described up to now). The explanatory column then shows each time the symbol of the place where the substitution takes place, and its contents after the substitution. The Cu or Cc type transfer orders (the orders 13-16 in Table I) cause no substitution, they transfer C instead (and they occur only at the end of the sequence) -- hence they require no explanation.

An order in the sequence, which becomes effective in a substituted form (substituted by an earlier order in the sequence), should be shown in its original form and then, in brackets, in its substituted form. The original form may have a -, the sign of irrelevance, or any other symbol (e.g. the number 0, of course, as a 12 digit binary), in place of its x (in its S(x)). It is this form which matters in the actual coding. (In writing out a code, it is best to use the sign of irrelevance in such a case. When it comes to real coding, however, an actual number must be used, e.g. 0.) The substituted form, on the other hand, is clearly the one which will actually control the functioning of the machine, and it is the one to which the explanation should be attached.

We repeat: We feel certain that direct, linear coding according to this principle presents no difficulties after a moderate amount of experience has been acquired.
```

<a id="planning-and-coding-025"></a>
## planning-and-coding-025 — 7.9: coding stages and explanatory column (physical page 33); Volume I printed 23

Source: [physical PDF page 33](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=33); reading unit `p033`, lines 6–52.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-024](#planning-and-coding-024), [planning-and-coding-026](#planning-and-coding-026), [planning-and-coding-138](#planning-and-coding-138)

```text
23.
After this final enumerat ion has been ccnvleted, one mre task rerrøins:
In every order, in the express ion SIX' the prel imi nary nurber x must be replaced by
the final number x, ard for thæe orders which subst i tute posit ions that are occupied
by orders (orders without or with primes these are the orders 13—16 and 18, 19 in
Jable i i' the distinction between "left" and "riahtt' must be "ade (i, e. the order rust
In the case of posit ions which
not be primed or it must be prined, respect ively).
Correspond to the its of one variable remote connection it is clearly necessary that
they be all "left" or atl "right". This must be secured; the ways to achieve this are
Obv i Ous.
When the coding is thus co-npleted, the posit ions where the seqænce of
orders begins ard ends to i and e, cf. the erd Of 7.8', should be noted.
There will be mre to sey about these when we get to the quest ions of subrout ines and
of cornbining rout ines, tc which reference will be rrade further belov, but will not
go into this ratter now.
Al! these being understood, it is indicated to state this in
add it ion:
There are still things which have to be discussed in connect ion with
the cad ing of problerts, ard which we have neglected to consider in this chapter, am
will also disregard in the chapters which follo•./ in this Part I of the report.
refer to the orders which Stop the nechine, to the orders which control fle rugnet ic
wire or tape and the oscilloscopic output ot the nechine, to the lcgical printiples
and pract ica' rethcds applying tc the use of the magnet ic wire or tape inputs and
outputs as a subs id iary merrory Of the "EChine.
Tede brief refererces to these rutters in the paragraphs 4.5, 4.8,
6.8 (arvd the sub—paragraphs of the latter) in Part I of this report. They require,
Of course, a rush 'Tore deta i'led Cons iderat ion. That neglect to take them up here,
in I Of our report is nevertt•less del i berate. The gain reason for this neglect
is, that they deperc on parts of the machine where a number of dec is ions are still
open. These are decisions MI ich lead only to minor engineering problems either way,
but they do affect the treatrrpnt of the three subjects 'Tent iored above (Stop Orders,
output orders, use of the input—output as a subsidiary rrerrory) essent ial ly. So tre
corresponding discussion is better withheld for a later report.
Fur-them-ore, the two first items are so sirrvle, that tney do not
seriously impair the picture that we are going to present in what The
potent ial it ies Of the third item are nuch more serious, but do not knc»N as yet,
to what an extent SLEh a feature will be part of the first mdel of our rrachine.
There are further important ger,eral principles affecting the efficient
use of coding ard of routines. These are prirrarily deal ing with general rout mes arri
sutwrout•nes with t reir use in combining routines to routines. Thæe
w i 'l be taken up, as far as the underly ing prix iplæ are coxerned in Chapter 12,
and put to practical use in various examples, with further discussion in the sub—
sequent Chapters 13 aM 1 4.
In the irrrediately following Chapters 8— will
give examples of coding irdividual routines, on the basis of tre general princ iples
of this Chapter 7.
```

<a id="planning-and-coding-026"></a>
## planning-and-coding-026 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 34); Volume I printed 24

Source: [physical PDF page 34](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=34); reading unit `p034`, lines 9–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-027](#planning-and-coding-027), [planning-and-coding-025](#planning-and-coding-025)

```text
80 CODING OF TYPICAL ELEMENTARY PROBLEMS.
8.1
In this chapter, as bell as in the foll&/inq ones, we will apply
the, gereral prixiples of cæing, as outl ired in Chapter 7, to a seqterce of
cf gradually irrreasim canplexity. Tte selection of these nblers was made
with view of presenting a typical selection of exanples, on which the rein pr±lers,
difficulties, procedures and simpl ifying ard saving cr tricks of
actual coding press can be exhibited and studied. Trey will be chæen frm various
parts of ratteretics, aM sone of will be of a than rattprøtical
character. After having frm simple prchlers to cmpl icated mes within
category of thße pr&lens which have to be cæed as units, i without breaking
up into smaller problerrs, will proceed to pr±lens which can be br&en up into
Rrts, that can coda' separately and then fitted to code wholerB-cblem.
8.2 we start on this program of coding specific
hmever, there ore technical point that has to be settled first.
In all tip that we are goirp to do, references to spcif ic
rrerr«y locations will æcur. TYEse_10cat ions are in mrber, aM we always
entrerated them with ttE Yelp of a 12 binary digit nurrber or aggregate, wh ich
usually denoted by x. (Cf., e.g. through the Table II cf crders.) We will use
this 12 binary digit ntrber or aggregate, in all sittntims wtpre it may æcur, the
gerpric designation of a rnrymsition park, br iefly "itimmrk. By calling
it ambiguously ntnber, aggregate nerk, we have purposely avoided the Q.estion
wrether ard haq we wish to attr ibute a binary' point posit ion to this diq ital aggregate.
nag rrøke choice in tte mst convenient way: Let tte binary point be at tye
extre& right, i.e. let tte position gerks he integers. Thus the position narks
CTrespond to all 12 binary digit integers, i.e. to all (decimal) integers fran
o to 212-1 q,095
This choice, hoaever, is not entirely without cmseqærees
way in which the position nerks themselves must be placed inté tie and
manipulated ar itmetically by mchire, wherever strh are called for.
The point. is that the rechire will nat handle integers as stkh, but only ntrbers
between -l ard l. Furthern«e, in order that a posit ion mark x that is stred in
tie rerr«y should •tpcaæ effective, it is to "stitute it into sme
This irvolves brinqina it from its position into
(by an order Ac + [abbreviated: y] , assuming that tte storae positim in
qtestim has the rzrk y), and then "Eke a partial substitution frm the acctmulat(Y
into the desired (by an a-der S(z) Ap' S(z)
[abbreviated: zSp or
iSp'] , assming that order to be substituted has nzrk z).
If fol laqed explanatim of these cyders (Nos. 18, 19) given
in Table 'l in 6.6.5 in Fart I of this •report, then both would rme tye
left-hand i2 digits of tie into tte places at z (into t}• left-
i2 digits of the left-harri cr right-tmd crder ttere, i.e. into digits I to 12
or 2i to 32 (from the left) in that word). tye position rerk to T.'ed, x,
is acccrding to the corvention trat we an integer. Digit I in
40) tiere has the pxitiorøl
accu•nulatr is tte sign digit, while digit i 2, ,
value Hi-I)
```

<a id="planning-and-coding-027"></a>
## planning-and-coding-027 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 35); Volume I printed 25

Source: [physical PDF page 35](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=35); reading unit `p035`, lines 12–49.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-026](#planning-and-coding-026), [planning-and-coding-028](#planning-and-coding-028), [planning-and-coding-036](#planning-and-coding-036)

```text
25.
Tterefcre accum•lat« should actually contain not x itself but '2¯11 x (modulo
x should be stcred in the Term/ (at y, ct. abwe) as 2
x (rn4u10
Fran an engineer inq point of view it is preferable not to involve the
Sign digit of tte accu•nulat« into typse transfers, ard not to effect both transfers
(into tte left—hand orders and into right-hand orders) frcn the sare 12 accumu-
lator digits. This motivates ttp change which we in Table II, as against Table l,
for these cyders 18, 19: effect these two transfers fran the digits 9-20 and 29-40
(fran the left) of the accumulat«, respectively.
In view of clunges it is desirable to have in the accumulator
the 12 digits of x both at the digits 9 to 20, and at the digits 29 to 40, wten the
substitllt ions of the type under discussion are be inq effected. I.e. the acctnulator
should contain 2-
defirp accordingly:
position rrnrk x is always a •12 binary digit inteqer, i.e. a
(decirel) integer fran O to 2 2
wherever x has to be stcred in pemory, in any mnrer ooerated on by
rechire, it has to replaced by ttp, nttTber xo given abwe.
The syrbols intrcx4tred in Chapter 7 to denote. sta•age pcsitiorls for
tabular or distrib"ted sto-age (Engl iSh capitals with decira Is, cf. the beginning of
7.7) læal stæage (Raren ntmeral with decimals [±not ing operat ion alter-
native boxes] fol la€ed by an s and a decimal, cf. the latter part of 7.9) for
revote conrections (Greek letters Wlth decic-a Is, cf. Note I in 7.4) will be cons idered
to be pcsition rerks, i.e. integers x, and treated in sense Of tte
abwe rule.
8.3 take up Oir first actual ccHing prc±lan. This is a very
elerentary lem, of a purely algebra iCal character and present ing no logical
c.crrpl ications whatever.
1.
constants a, b, c, d, e and the variable u are stcyed in certain,
given, rerxxy locations. It is desired to fcym the express im
and to stcre it at amther, given, TerTKYY locatim.
The problem is so sirvle th2t it can be r•.æed directly, without a flog
diagram. my, &refore, attr ibute all strraqe to a •single stæaoe area A, ard all
coerational cyders to a s Ingle O*ration box 1 . (Both of are, in a way,
, sir-ce do draw a f loq diagram.
"f ictit ious"
```

<a id="planning-and-coding-028"></a>
## planning-and-coding-028 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 36); Volume I printed 26

Source: [physical PDF page 36](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=36); reading unit `p036`, lines 6–63.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-027](#planning-and-coding-027), [planning-and-coding-029](#planning-and-coding-029)

```text
26.
Åcco-dingly, let the constants a, b, c, d, e be stryed at A.I to 5,
the var iable at A .6, the (des ired) quantity v at A. 7. Fote that u is a free
var iable, a to e are constants whiöh rrey be viewed as free var iables, while v is
produced by the rechire itself and the content Of A. 7 at start is therefcye
irrelevant.
&/iously tte expressions that will have to be frred sm.cess ively are:
l) an, au b, au2 + bv
3)
Internediate, i.e. local , stæage is reeded fcy whichever of the two
quantities atra + b" + c and du + e is canptrted first, while tF•e seccyxi ore is ±tained.
?oever, at this stage Å.7 is still avai Jable (v is not fcræd) add my be utilized for
that stcraqe. It is corwenient when the division of 3) begins to have its dividerø
atv + bl' + in the accumulata-. '-knce I ) should it-mediately precede 3).
l) to 3) should be taken up in the cyder 2)' 3)•
Sale addif ional local storage is fæ a ærtain quantity in
transit, at a rorent when A. 7 is no longer avåi12ble. (This quantity is au + b, which
has to mwe frm Ac to R, while A .7 is crcupied by du + c. Cf. the crders I .8,9 belcv.)
This requires an additional posit ion A .8.
The entire caiing is static, and gey be arranged as
Sterage at the beginning:
8
2
3
5
6
7
8
IO
12
13
2
3
CcHed seqænce
(Cadim Column.)
S(A.6) xR—,
S(A.5)—» Ch +
s(A.7)
s(A.6) A
s(A.8)
S(Å.3) -+ +
S(A.7)
5
6
(prel iminary emnration), detailed firm:
(ExplanatTY Column. )
d
du +
au
au +
Ac
Ac
e
b
au2 + bu
av2 + bu +
au2 + b" + c.
du +- e
```

<a id="planning-and-coding-029"></a>
## planning-and-coding-029 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 37); Volume I printed 27

Source: [physical PDF page 37](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=37); reading unit `p037`, lines 7–51.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments. OCR reorders lines of the final-enumeration paragraph, including its parenthetical about the explanatory column; coordinator visual supplement is pending.

Related: [planning-and-coding-028](#planning-and-coding-028), [planning-and-coding-030](#planning-and-coding-030), [planning-and-coding-024](#planning-and-coding-024), [planning-and-coding-162](#planning-and-coding-162)

```text
27.
Note, that I , rarrespords to 2) abwe, to l), and l, 12-14
to 3)•
In all the codings which fol ia•/ we will tse the abbrev iated rotation Of the
Table II of orders. Ttpn tye above coded seqwnce (prel iminary enuærat_ ion) asscres
appearance:
Ac
Ac
IO
12
13
du + e
du + e
an + b
au + b
arp bu
at:2 + bu + c
The passage
their actual values, and Of
be O to 6, and let A. I-b
coltm is no
Ionoer reeded ) :
13 s
14 s
12 X
to final enurera+. ion.consists of ass inning A. I-S
to 7 words. Let latter
pairing the l} orders l,
7 to 14. Then the coded seqtpree beccns (the explanatory
IO
12
In an actt•al appl ication ot this rnfed seqterre typ constants (or
12, would,
parameters, free var iahles) a to e and t; , occupying the Icy-at ions 7,
of course, have to be replaced by their artual, nucer ical values. The other locatims,
i, 6, on the other harr*, will have to be ccried exactly as stard.
Trese rererks constants, paraneters, or free var iables)
apply, of course, equally to all c&ed seqlemes that Will set up in reneinder
of this report. (Cf., haever, the renerks on subroutiæs arvi or ccn,ining In
12, which have a certain significam.e in this respect.)
8.4 We intrcxftx:e rext a slight logical twist. into Pr&lem l.
Prrtlem 2.
Sane as FciJlem , with this change: u and v are stÜ•ed or to be
stTed at certa in ions m and n, which are not given in advame, but stcred at
certain, given, locations. —
```

<a id="planning-and-coding-162"></a>
## planning-and-coding-162 — 8.3: explanatory column omitted in final enumeration (visual transcription)

Source: [physical PDF page 37](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=37); reading unit `p037`, lines 53–53.

Attribution: Herman H. Goldstine and John von Neumann

Context: Supplement to the complete OCR page selection; preserves legible prose where OCR corrupts words. Neighboring source-page records retain the surrounding worked examples.

Transcription/context notes: Manual transcription from physical page 37, printed page 27. Number/range spacing normalized; tables before and after this paragraph remain in the original and OCR page record. This qualification concerns the final-enumeration stage of the worked example, not a universal prohibition on comments.

Related: [planning-and-coding-029](#planning-and-coding-029)

```text
The passage to the final enumeration consists of assigning A.1-8 their actual values, and of pairing the 14 orders I,1-14 to 7 words. Let the latter be 0 to 6, and let A.1-8 be 7 to 14. Then the coded sequence becomes (the explanatory column is no longer needed):
```

<a id="planning-and-coding-030"></a>
## planning-and-coding-030 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 38); Volume I printed 28

Source: [physical PDF page 38](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=38); reading unit `p038`, lines 10–65.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-029](#planning-and-coding-029), [planning-and-coding-031](#planning-and-coding-031)

```text
28.
This affects use Of stcrage. A f log diagram is still not
but we mtst recons ider the use of A. 1-8.
A .6,7 are no lorger rEeded fa- u, v, hc»ever, still need A. 7
local st«age (c.f. 8.3). Ldt. n, n be stred at A.9, IO, of course, in tte frm mo,
no (cf. 8.2).
When will pass fran the entTerati0n to the final Ore,
folloqing Observations will apply: First, A. 6 is miss ing, btrt this is irrelevant.
Second, the posit ions m, n are suppæed to be part of sure otter ine, already in
the rachire, therefore tipy need not concern us at this stage. Third, let LIS assvrre
that the ctxfed sequence is supposed to beg in at sorre posit im than O, say 100,
ard that it is suppæed to end at a prescribed position, say 50.
The abbreviated, prel iminary cryied sequence , 1—14 will therefore
First, the references to A .6 (which transfer n)
have to rrüified in two ways:
and to A. 7 (inasmuch as they transfer v, and are not die to use Of A. 7 fT
læal stTage) have to be Changed. _ u is needed it is advisable
to assign to it a fixed pßition A. II. ænce , 2, 6, IO will have tp refer to A. II
instead of A.6, ard rew orders will be reeded to get u fran m to A. II, and (replacing
I , ig) to get v frm Ac to n. Second, a rew order is reeded at erd Of ccHed
sequence to qet the control to the desired er*point 50.
The changes in 1,2, 6, IO are trivial.
I ,2 assmes
The transfer of u any take place at any tire befæe 1,2.
that d is in R, so this transfer must eitrer precede I too (since this troves d to
R), cr leave R undisturbed. R is indeed not disturbed but we place tre transfer
It can be ctr*ed as fol lays:
rout ire nevertteless before I
.2
.3
Sp
s
Ac
i ,O.3
Ac
A.II
u
Note that the sign of irrelevance in an order, like I ,0.3 abwe, does
not rean that tye entire i.e. the entire half-wo-d is irrelevant (aryl still
less, that the entire is irrelevant). It Beans that an cyder S(x)—» Ac
abbreviated x, is næded, but that x is irrelevant.
1,11.1 asstmes that v is in
The transfer of v replaces the Order I , 14.
AC, so the operations required by this transfer must eitter preæde 1,1-14 (s ince all
Of tyese are needed to prodlce v in Ac), leave AC Undisturbed. is d istlrbed ,
It is simplest to let
so it is recessary to place the trahsfer routine I , l.
it follo•/ imediately after Otr first trgnsfer rout ine, ie. irndiately after I , 0.4
abwe. It can be ccxied as
I ,0.5
.6
A. IO
sp
1,114
no
s
```

<a id="planning-and-coding-031"></a>
## planning-and-coding-031 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 39); Volume I printed 29

Source: [physical PDF page 39](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=39); reading unit `p039`, lines 7–43.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-030](#planning-and-coding-030), [planning-and-coding-032](#planning-and-coding-032)

```text
l, 14,
l, 14
endpoint SO.
1, 15
A.9
A.8
10
12
13
14
Firany, we reed an cyder after l, Iq,
This is, Of covrse:
can rav•rite the abbreviated,
Sta-age at beginnirg:
Coded seqtence (prel imirary enlT.erat ion):
29.
in turn, rust be rewritten as foilavs:
to mwe the control to the desired
prel imirarv coded seqterce:
1,0.3
A.II
A.II
sp
,0.3
A.II
Ac
du e
au b
atl + b
a112 + bu
aua + bu + C
The passage to final enwerat ion consists Of ass ignirg A. 1-5, 7-1 1
their act1Zl val•es, pair irg the 21 Tders 1.,0.1-15 to II wrds, aM then assigning
l, 0.1—15 ttpir actual valles. treat m, n like a toe As free var iab)es
corstants. The II in qtestion must begin' with 100, so trey will be 100 to 110.
Ttpn A. 1-5 may be Ill to I IS. aM A. 7-11 be 116-120. So b-e ±tain this coded
seq!erce :
```

<a id="planning-and-coding-032"></a>
## planning-and-coding-032 — 8.1-8.5: elementary examples and explanatory coding columns (physical page 40); Volume I printed 30

Source: [physical PDF page 40](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=40); reading unit `p040`, lines 6–100.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-031](#planning-and-coding-031), [planning-and-coding-033](#planning-and-coding-033)

```text
30.
100
50 C
i 06
118
119
112 h,
101 sp
120 s
109'Sp'
120 x
120 x
117 s
! 07
108
109
110
112
u3
117 P.
120 x
-s
115
116
117
118
119
120
no
Note, that the sign Of irrelevance in an cyder, like 101-left, near'S
that it is an crder x (i.e. Ac) with x arbitrary. This is exactly the sane
situation as in 109-r ight, which is —S, i.e. x S (i.e. At —+ S(x) ) with x irrelevant.
Or. the other hand, 110-right, rørked - -,
is acttelly entirely irrelevant, since this
half •wcrd was not needed for any of our cyders. Finally sign of irrelevame in a
full word, like 116 117 120, reans, of course, that entire content is
irrelevant. The simplest treatænt of all irrelevancies is to replace anythirq
that is irrelevant by O
8.5 coding Of any problern should be follc»ed by ar estirete of
tine that machine will constm•e in solving the prr±lem, i.e. in carrying OI't
the instrtct ions of coded seqtence.
In cyder to rrøke stch an est imate it is recessary to have
information about tip. duration of each step that is irvolved, i.e. tire required
by to carry out each ore Of the cyders OT Table II.
At the present stage
of Otr engireering develØne,nt tre cyder-tire est irrztes are recessar ily gresses.
Tte estiTBtes which follm' are rede in a guardedly optimistic spirit. Unless there
are sme strpriées in our engineer ing deuelopænts, they shoiJld be' ccyrect
within a rüierate errcy—factT
— say, within a factm 2.
In this sense OIT crd'.r-tilte est irates are as follo•vs:
TABLE Ill
2
3
5
6
7
xh-
25
30
30
30
30
35
8
9
12
13
xh-y
35
25
5
IOO
ISO
25
25
15
16
18
19
20
21
xCc
xCc'
xSp'
30
30
25
25
25
5
20 u for every wTd.
I microsecond, I m = mill
Considering cors iderable ies with which these estiffBtes
are affected, we might as well Ise follcving approx irate rule:
```

<a id="planning-and-coding-033"></a>
## planning-and-coding-033 — 8.6-8.8: numerical assumptions and annotated induction examples (physical page 41); Volume I printed 31

Source: [physical PDF page 41](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=41); reading unit `p041`, lines 17–64.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-034](#planning-and-coding-034), [planning-and-coding-032](#planning-and-coding-032)

```text
31.
Count 7S fcr every bord which contains two cyders, spbtract 25 if
Only ore is used, subtract 20 u fT every (Yder which refers to no remcry posit ion
x (i.e. A, R, L), add 70 g every mill tipl ication and 120 fa• every division.
this basis the caged seqænces obtaiæd in 8.3 aryl 8.4 should
requ ire
(7 x 75 -20+ 3 x 70+ 120) u = 835 u
and
(II 75 - 25 - 20+3 x 70+ 120) u = 1,110B
1.1 m,
respect ivel y.
8.6 The rext point to cons ider in Conrection with Our Of the
prd)lers I am is this:
WV. observed repeatedly that our rnachire will only deal with m•rrbers
lying between —l and l. Cydinarilv will interpret this to exclude. both erdpoints,
i.e. we will keep all absolute valves < l.
It shotlld be noted, hosever, that
precise &finition of the numtprs that Otr nachire can handle as digital aggregates
(cf. 5.7 in Part I of this repcrt) irr.ltdes -l and excl"des l.
This fact, that have a —l but not a f, is ocrasionally Of ir•po-tance.
Actually this is not often the case, irrieed extrenely less freqtently than one might
Its effect in dividing
think. Ttere is hardly ever a reed to stme a l:
is Oil, and tye sizes which we wish to ±serve. make it usual lv ircorvenient to nnnipl'late.
Fegarding pæ it ion marks, where I night play a role, cf. 8.2. Regardirrj ird'Cti0n
indices, cf. Pr±lem 3 in 8.7 as as various subseqtent *cblerns.) In those excep-
timal cases where I is actua Ily ar i tyret ically reeded, it is always possible to ad just
the iors so that — ' can be used instead. an example of this cf. Pr±lem 9
in 9.9, in particular treatmnt Of box Ill
— C. 2 acyl Ill, I—as as
similar ions in boxes VI, IX, XII, XV.) The cmplicatiors which arise in
this rranrer are very rare, and they mcur, regl igible, as exper ierx:e of our
Prcblerß i I lustrates.
It is in
In the present Case, we will keep all absolute valles < l.
this sense, tl•erefa-e, that ciserve that the above problgrs can only; be harvd led
Furthermre, our ymedure of 8.3 (and 8.4)
if their u and v lie betæen -l and l.
also requires that all data of moblem, i.e. the corstants a to e should lie
between -l l, as æll as åll interrediate results of the calculation, i.e.
ex"ess i ms
l) au, au + b, aua + b", + + c,
2) du, du + e.
assurre that is only knour to lie between -2P ard 2, v between
-2q and N, ard a toe -2r aM (p, q, r = O, l, 2,
Then the quan -
t ities a fo e and 'J, v simply cannot be stcred by the rechire, erd it is recessary
to sure otters instead, e.g.
```

<a id="planning-and-coding-034"></a>
## planning-and-coding-034 — 8.6-8.8: numerical assumptions and annotated induction examples (physical page 42); Volume I printed 32

Source: [physical PDF page 42](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=42); reading unit `p042`, lines 18–57.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-033](#planning-and-coding-033), [planning-and-coding-035](#planning-and-coding-035)

```text
impl ies
where
if
wtere s = O, l, ± 2,
32.
This, is nd ar answer to our groblem since the relationship
between and u' is not expressed with the help Of a' to e' in the sare ranner as the
relat ionship YEtween and v with the Yelp of a to e. have to prmeed sare-
what circtwspectlv.
This is not difficult. O-iginal relation
I ld
all? + bu + e
2-qv,
= 2-q-sc, d*
2P-sd, e
2¯Se,
can be freely chosen. We can use Otr freedm in chocs ing
s to force a* to e* as well as the express ions
into the interval —l,
l. Sime
we disregard tye last expression ir 1*),
if
< l, it Siff ices to secure
v'
all otters are taken care Of.
Sime
This n-eans that
s 2p-q + r
we rev choæe
s - (29
+1,
= p + thx (p -q, O) + r + 1.
This procedure is typ Of what has to be dorp in mcxe campl icated
sitllatiors. It calls sore remrks, which proceed to formulate.
First: a to e aM u are data, and it is therefore natural that
have to assume that sare info-mat ion, which is separate from this calculat ion, ex ists
(I.e. that they lie between -zr ard t, and between -2P and
regarding sizes.
2P, respect ively.) v, ho•ever, is determired by a to e ard '1, so its limits (-2G
29 should be derivable frm the infcyrrøt ion that ex ists comerninq a to e and u.
```

<a id="planning-and-coding-035"></a>
## planning-and-coding-035 — 8.6-8.8: numerical assumptions and annotated induction examples (physical page 43); Volume I printed 33

Source: [physical PDF page 43](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=43); reading unit `p043`, lines 6–55.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-034](#planning-and-coding-034), [planning-and-coding-036](#planning-and-coding-036)

```text
33.
In cases this information æed not be rrrre than was Stated abwe concerninq
tteir rarVs (-2r to 2r fr a to e, -2P to 2P for u), in otters it ray require addi-
inforret But in any case the problem of the sizes cf the
quantities which the calculatim will produce (as interred iate as final results),
should be viewed as a røttprretical pr±lem in its Ogn right. (Cf. discussion of
n f irst stage" preparirg a in 7.9.) This Of evaluatirg sizes
rrey be trivially sirole, as in tte present case; rr rderately as in
pr±lerrs require extensive calculations; Or rea Ily difficult, as e.g. in var ious
partial differential eqtntion It ray even be, frm tte mathemat ical point
Of viee,', Crux cf the whole pr±lem, i.e. the pr&lem my require rrore
effective calculatirg than this subsidiary, evaluational pr±lem, but tte latter ray
require rÜe rretherat ical insight than tip frrer. This can happen for very imp«tant
and pract iCal prcblerrs, e.g. it is so fr n simultareous lirear non-lirpar eqtztions
in n variables for large valæs of n. (Bé will disctss this particular subject
elsewrpre.) To we note that the estirTBt ion Of and Of the prec is ion
or signif icame that is ±taireble in the result, is quite clcsely cmnected with ttp
estirøtion. of sizes, and that our abwe remarks apply to these, too. (All of tipse
are cwered by tre "f irst Starn discussed in 7 9, as referred to abwe.)
Saxyd.• Urøer suitable cmditions it rrøy be possible to avoid tte
rattEretical that is required to control the sizes (as descr ibed above), by
irstrtrting tte rechire to rearrange calculation, either continuously (i.e.
every ntmter that is prodlK*d) at suitable selected critical rmznts, so that all
sca les are apprepr iately read justed and all numbers kept to the.permiss ible size
(i.e. betæen -l l). readjusting is, of course, wasteful in t irre
and reray ca*city, whi le tre critical (occas ional) read jtstinq reqelres mre
less rathmetical insight. The latter is greferabie, sime it is alrrost always
to reglæt R rrøtyeretical arulysis cf tte pr±len uMer considerat ion.
Examples af to code tie instrtrtions to sectre critical size
readjustrænts in various pr±lBTF will be niven sLbseqently .
(him: cf oontinuous readjtstrent can be ized
built into a mchire, as a floatiæ bimry mint. referred to ii already
in 6.6.7 in the first part of this rem. fæmnlated there various cr it Icisns
which caused to exclude this facility, at any rate, fran tte first rodel of
rechire. The abwe disctssiM reemptus izes this point: Ttvflæting point
%Wides cont inuous size readjust irg, while prefer critical readjustirq, and
that only to the extent tc which it is really reeded, i.e. irasrmrh as the sizes
are not foreseeable without undue effort. Besides the flætirg point
remesents an to rerder a rathemtical at least a
t cf r±lem unrecessary, arid we feel that this is a step in a dothtful
directim.
8.7 Let us exterd Foblers I 2 in a different respect.
This extension will bring in a simple iMuction, aM th'S the first carol icaticn of
a logical nature.
Prrilgr 3
Sare as Pr&lem I with this charw The calculation is desired for
I values of u: ut,
VI, reskctively. Each pair
ul, givirq trese v 's: v: ,
I) is s&ed to be stred at two Imations
```

<a id="planning-and-coding-036"></a>
## planning-and-coding-036 — 8.6-8.8: numerical assumptions and annotated induction examples (physical page 44); Volume I printed 34

Source: [physical PDF page 44](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=44); reading unit `p044`, lines 7–57.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-035](#planning-and-coding-035), [planning-and-coding-037](#planning-and-coding-037), [planning-and-coding-027](#planning-and-coding-027)

```text
34.
m + 2i-2, m + Zi—I, whole coverirg the interval Of locatiqns fran m to m ZI—I.
m aryl I are not given in advance, but stTed at certain, given, rtecxyy læat ions.
This is first ore of our Problers to require a f IO,' diagram. We
will tterefTe apply the Xirciples Of Chapter 7, ard n•xre particularly Of paragraph
7.9, to their full extent, arri avoid any sh«tcuts that pcssible in connection
with Our two previots problens.
Let A be storage area ccyrespond ing to tle interval Of locat ions
frm m to m + 21-1.
In this way its positions will be A. l,
21, where A. j ccyres
ponds to m + j-l (j =
, 21 These pos itions, hc»æver, are supposed to be part
of sme ottpr rout ire, already in "Echine, ard therefore reed not appear
pass (at the erd of the whole præedure) to the final enureration Of the coded
seq IEnce .
Let B be the stcrege area which holds the given data (the constants)
of m±lern: a to e and m, I. m is a position "hrk, we will therefore store
mo instead. I is really relevant in catination m + 21, which is a position
mrk (the stcxage area A is an interval that begins at m and ends just before m + 21),
we will t!erefore strye (m + 21)o instead of I. sta•e a toe at 3.1,
5 arx\
mo, (m + 21)0 at B. 6, 7. Finally, stTage is req"ired fm the induction var iable i.
i is real lv relevant in the c.a±inations m + 2 i-2, m + 2i-l, which are position narks
(fa- A.2i-l containing Ui and fcr A.2i designated fcy Vi), select m + 2i-2, and
will store (m + 2i-2)o instead. This will be stTed at C.
TYPse things being enrErstocH, car. prc"eed to drawing the
, I) and 3.1, ...,7
diagram. will use tablilated s&age. A. Zi-I (i =
e, m, I, respectively), while
are fixed st«age (the. ui and a,
I) ard C are var iable storage (tte v i and i,respectively).
A.2i (i = l,
TIE cmplete f 1m diagram is shogn in Figure 8. l.
FIG"RE 8.
1
2
2
v•lfoR
2
3
1.5
bu.+c
, A.2i
3
• fCR > L
FOR
2
A.
3
b
```

<a id="planning-and-coding-037"></a>
## planning-and-coding-037 — 8.6-8.8: numerical assumptions and annotated induction examples (physical page 45); Volume I printed 35

Source: [physical PDF page 45](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=45); reading unit `p045`, lines 9–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-036](#planning-and-coding-036), [planning-and-coding-038](#planning-and-coding-038)

```text
3b.
This deals with
(m + 2i-Z)o -
11,1
pr±lem.
We are left with the task of doing tte stat ic ceding.
the boxes I to Ill. begin with the preliminary enweratims.
The ccHing of I is Obv i01s:
111,22
8.8
8.1
alli + b
8.3
ca4ing of II is also quite simple, we must only (±serve that
(m + 21)o has sare sign as The follaqs•.
(n + 2i-2)0
(m + 21)0
FÉre e is the it ion at which want control to finish
The cniing of Ill is effected rainly after the pattern of Proble•n 2.
This appl ies to it inasmtr:h as it pro*lces v i, the additional task of
(m + 2i)o is tr ivial. There is, ho-ever. thlS to be noted:
In ttpse oprat ions
(m + 2i-2)o mt'st be lvsed to produce (m + 2 i-l (m 2i)o . rumber
'o is reeded. This mlSt be stored screwhere. This is not exaétly In:al
storage, because we are not dealing with a trans ient soace reqt:irerænt Of Ill .
It is fixed Storage, and we assign to it the posit im 8.8. typ cding can be
dore as follrxs•.
111,1
IO
12
17
18
20
21
2i-2
111,22
sp
Sp
Ac
(n + Zi-2)0
(m + 2i)o
(m + 2i)o
dui
alit
bui
+ bui * c
```

<a id="planning-and-coding-038"></a>
## planning-and-coding-038 — 8.6-8.8: numerical assumptions and annotated induction examples (physical page 46); Volume I printed 36

Source: [physical PDF page 46](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=46); reading unit `p046`, lines 7–97.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Connected exposition and worked examples of planning, explaining, and coding a computation; mathematical and machine details retain the context of the explanatory representations.

Transcription/context notes: Windows OCR supplement; spacing, letters, mathematical notation, code columns and diagram topology remain imperfect. Consult the physical PDF page for the actual layout. Flow diagrams, assertion/substitution boxes, storage tables and parallel explanatory columns are external representations, not evidence of inline source comments.

Related: [planning-and-coding-037](#planning-and-coding-037), [planning-and-coding-039](#planning-and-coding-039)

```text
Q
3
s
6
7
36.
111,22
Ill
20 h-
15 h
-s,
17 R
s
s
c
Å.2i
11,1
had to use local
s. 1-3.
We no•/ Pass to tee final enurerat ion, ass igning B. 1-8, C ard
s. 1-3 their actual values, oairing the 27 Orders II, ,
1 2, to
words, and ther ass igning l, l, 11,22 their artltal values. Let these words
be 0 to 13, then 8.1-8 rray be to 21. C rey be 22, Ill., s. 1-3 re_Y be 23-25, and we
can put e
eqwal to, sav 26. so we &tain this coded sequeme.•
19
22 s
22
26 cc,
22
3
23 s
, 22
21
h , 12 sp
21 h
22 S
, 23 X
8
9
12
13
16
(m 21)0
16 h
23
23 x
c
as
(7
[8
19
20
21
22
24
25
The dl•rat ions rtpv estirna+ed
1:..754, II: (2 x 75- 25)
: (12 x 75- 25+ 3 x 70+
Total: i + II + (II +111) x1-
fol lcws:
= 125
120) u = 1,205 J.
(75+ i25 + (125 + i,20S) 1)
= (13301 + 200) 1 m.
-We give nav an e\ample of to code instrtctions for a critical
read justnent, as rentioned in secorld remark in 8.6.
variables 1', v are st«ed in certain, given I mat ions. It is
des ired to fcrm and to determire its size, in t b? fol la•'irg sense: Fird the
_ • ) fcy which 2n¯i < I I < 2 n, and fcrm
integer r ( = O, l, + Z, •
w L . This will fail if eitter II or v is zero, sense this
is the case.
could also reqvire that other things, e.g. the npri-er of significant
digits in v, be deterniæd. we will not introduce ttese additional compl i-
cations here, they can be handled alory the sane I ir:es as the Mir Problem.
< I , hence
In Olr Tachire. 1', v 0 imply 2
-90 < 2+39, herre -38 S n 39 •
'We will therefrre signalize v = 0
2
O (ard v* 0) with n -SO. We will begin calcl'lat.ion
with n = 50, and
by sensing whetter v O and whet}er u O. This is derided by testing - O
If reither is the case, we bhether n is going to be O
ard
< O, rx not. After this
> O. This is dore bv testing l•'tether I ul - I
determire n by two obvious, alternative indnr.tions.
```

<a id="planning-and-coding-039"></a>
## planning-and-coding-039 — 8.8: critical readjustment flow diagram and explanatory coding columns (physical page 47); Volume I printed 37

Source: [physical PDF page 47](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=47); reading unit `p047`, lines 10–69.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-038](#planning-and-coding-038), [planning-and-coding-040](#planning-and-coding-040)

```text
Let u, v be stcxed at A. l,
and -30, 50, we store 2-39 n instead.
8.1,2. = O, i.e. when n =
z-n . In th.is case, then, tle content
the content Of P .2 by t.
37.
2. Sirw,e n has t 2e valles —38, -37,
..., 39
stcxe n and T n , when tiey are forced, at
-50 Or 50, be will not forra , ratter
of 3.2 is irrelevant.
In anv case, denote
In searching for n we will reed an indict ion var iable i, which will
wer O, -l, -2, to n if we have n $ O, ard wer l, 2, to n if have
n > O. It is com'enient to treat i tip sate way as n: Stcre 2-3 e i instead Of i.
Sime propose to Ilse distr ibÜted stcyage, we reed not enurrerate further stcrage
locat ions, are free to intrafire t;en as the need fcr tlpm arises, while we are
drawing f 10•,' diagram.
These indications should suffice to clar ify tte evol"tton aM the
significance of all parts Of f Irv diagram shcvn in Figure 8.2.
boxes I—XIV require static coding. Pefcre we do thåt,
free remarks, which embody primiples that will apply to Our filt"re
static coding Operati0% as well. They are folloqing:
First: fiked storage will be required. These are
certain nunbers to which specific reference will have to be specifical iy
2-39•50,
, O. We will tt•em at tte positions D. l, 2, 3, respectively.
We will state these expl ictly at tte points they beccne recessary, by inter-
ruptirg the ccHing col.mn there and stating the st«age.
Every box coding e itter ends with an '•nconditional transfer
cyder (type xC, xc') cr else it involves the assmpt ion that control goes on
(Erding with a condit ioral transfer cyder
fran there to a eef inite itior.
xCc, xCc' presents ar interned iate case: We have the first ore (Y
second ore Of the above alterrat ives accord ing to whether the transfer condit ion
If this latter alternar ive is present, Yen this position
is is not fulfilled.)
(i.e. its Ranar box mvrneral .arri its ntr±er within its box) has to be nap-ed at tte
end of box coding , with a reference "to
Third: It will be found corven ient to an extra operat ion
box, in addition to rent io,æd in the floe diagram. reason is, that two
operatims wh ich should be carr ied 01't in two operation boxes irrrpdiately preceding
a confluence, can be rerged and carr ied opt after cönflterce. (The two boxes
in qlesticr' are XIII, X I V, the box is XV.)
prcreed to carry net the static codirg of all bcües in ore,
contintns operat ion:
2
(to Ill, l)
2
3
(to v. l)
II,i
2-0 e 50
Ac
B.I
C
cc
2-3 e SO
2-9B •so
-lul
```

<a id="planning-and-coding-040"></a>
## planning-and-coding-040 — 8.8: critical readjustment flow diagram and explanatory coding columns (physical page 48); Volume I printed 38

Source: [physical PDF page 48](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=48); reading unit `p048`, lines 6–27.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-039](#planning-and-coding-039), [planning-and-coding-041](#planning-and-coding-041)

```text
38.
FIGURE 8.2
32.50
.SO t, 3.1
3.1
3.1—2
7
a-at, c.'
2
u.
2-39
3.1 2-3 g
.50
l)taB.l
12
12
(l -l) toB.l
roc.2
v
1 10
u
2
```

<a id="planning-and-coding-041"></a>
## planning-and-coding-041 — 8.8: critical readjustment flow diagram and explanatory coding columns (physical page 49); Volume I printed 39

Source: [physical PDF page 49](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=49); reading unit `p049`, lines 4–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-040](#planning-and-coding-040), [planning-and-coding-042](#planning-and-coding-042)

```text
-2-3 a•so
3.1
c.i
c.2
c.2
(to VI, l)
lul
lul-lvl
VII,I
(to x,l)
D.2
VII,)
0.2
8.1
(to VIII, l)
VIII,I
- IVI
c.2
(to XIII,I)
IX,I
c.i
c.i
VIII, I
c.2
c.2
c.2
XIV,I
D.2
c.2
c.2
Xl,l
c.2
Ac
3.1
c.i
8.1
C.I
3.1
Ac
c.2
Åc
Ac
c.2
2-3 g •
0.3
(to Xl,l)
Xl,l
(to Xli,l)
XII,I
XIII,I
(to xv,l)
```

<a id="planning-and-coding-042"></a>
## planning-and-coding-042 — 8.8: critical readjustment flow diagram and explanatory coding columns (physical page 50); Volume I printed 40

Source: [physical PDF page 50](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=50); reading unit `p050`, lines 6–162.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-041](#planning-and-coding-041), [planning-and-coding-043](#planning-and-coding-043)

```text
XIII,8
XIV,I
2-10
2
c.2
3
(to W, l)
2
8.2
t
3
roa proceed to tte f inal entrreration. must bmes
I-XV fcr this in such a nanrer, that the irriicatiors "to
. n are
Any Seq1Ence which .is rude recessary by an "to n will be narked by
a came, every seq1Ence wh ich is based on an arbitrary choice is merked by a
semicolon. In this mnner set the fol loging a-dering: l,
111, V, VI, X,
• IX; X I V, XV. crderirg is inverfect, inas-
Xl, XII; It; IV; VII, VIII, XIII,
much as XV should have been tte irmediate successT of XIII as well as of XIV,
sirce Only ore was possible, XIV. it is recessary to add at
er6 Of XIII an uncMditi0rBl trarsfer cyder to XV:
21
25 -26
13- 14
26 —27'
w, 1-3
28, 29
30,
51-71
VIII,l-3
XIN, 1-3
32, 33
34 -s
13 cc
25 cc,
2-3 e SO
xv,l
c
It rerrøins fcr to assign A. 1,2, 8.1,2, C. 1,2, D. 1-3 their actual
n, L—3, VII, 1—5,
valtes, to pair tie 56 It, 1-3, IV,l-3,
VIII, 1-3, IX,l-7, x,t-5, Xl,l-3, XII,l-7, XIII,l-3, XIV, 1-3, XV,l-3, to 28 we-ds,
XV,3 t}Eir val tps. These
ass igrTents are
ard then to assign I , I
sufficiently nmeroqs to justify raking a small table:
l, 1-2
IV,l-3
E -18
we
Obta i n
20 -21
ccx*ed seqpnce:
C
o
2
3
5
6
7
8
9
10
II
29
28
28
29
28
16
30
32
35
33
-M,
M,
cc,
s,
R,
x,
-h,
this
12
13
14
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
AX, 1-7
NV, 1-8
A. 1-2
B. 1-2
c. 1-2
D. 1-3
32
32
33
31
2-39
18 ct
, 32 S
33 s
36
33
33 S
30
30 s
29 h-M
33
33
34
e
30
35
32
32
33
32
26
3S
32
s,
c,
S,
s,
C',
h,
30 s
34 -
e
30 S
32
33 +
30
30 S
s,
s,
```

<a id="planning-and-coding-043"></a>
## planning-and-coding-043 — 8.9-8.10: correcting and changing diagrams and coded sequences (physical page 51); Volume I printed 41

Source: [physical PDF page 51](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=51); reading unit `p051`, lines 5–71.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-042](#planning-and-coding-042), [planning-and-coding-044](#planning-and-coding-044), [planning-and-coding-114](#planning-and-coding-114)

```text
141.
In est imating d•mations, we have to pay attention to sate points which
did not core up in Probla•as 1-3, rarely: The f los diagram of Figure 8.2 is never
traversed by the control C ir. its entirety. Tike course Of C is, instead, dependent
on behavicr of u, v and n. Specif ical ly, its covrse is as follcvs:
L, then
x: 1804
II (end),
Ill, trpn
tv (end),
V, VI,
VII, VIII xn, (n-l), XIII
(_r + ' ) , XII x XIV
n:
125
125
for
VII :
XII :
durations Of the individual boxes are:
125
180
255 u
XIII
75
125
dvrat ions :
Xlv:
125
255
225 u
, tten
xv :
1054
Eknce we have these total
for v O, u = O:
275 u
fcr O, u + O, n > O:
(380 (n
1080) g
(380 + 1060) u
8.9 It seers appropr iate to reke at this point a m to
errcrs that are discwered at anv stage of ca*ing, incll•ding the ibil ity
that ttey are d iscavered after the cod irg has been corvleted. Together with
correctirg actual errors, ore should also cons ider case where ccding is
proceeding, has been cmclWed, without farlt, when (for any reason whatever)
a da•.ision is rrøde to apply charges. Charges of both ty*5 (i.e. e i tyer
c&rectiors of actual errcwS voltntary trarsit ions ore. cTrect cade to
anotrer ore) fall clear lv into tyee classes: Onissiors of certain parts Of the
caied seqtence; insertions at a ærtain plaæs into a coded sequence; replacerent
Of a certain part of the ca4ed seqtence by anatter ded seqtence (the rew having•
the Sarre le-gth as the old, cr a ler length, or a greater length). The irnPT-
tant thing is, of cotrse, that it should be pæsiblp to effect such rutifications,
withoirt losing tne result of any of the dore on those parts of ttp coded
i.e. without anv recessity to "start all
seqterce which are not to be rulified
wer again' in whole Or in part.
nere is, of colrse, rw prÖ1em if the codirg rot yet prqressed
very far. Tie dyrømic stage, i.e. tye f Icy diagram, is easy to Omlsslms
can be effected by erasing or crossim out tie un&sirable regim, fol by
nshrtingn, I.e. takirp tie track directly frm its imediate to its
Imediate This r.y also be achieved by introdtrirg (f ixed)
rerate conrectiors. can be effected by drawirg the region separately,
arui tren detotring tte track to it ard back fran It. Again fixed remte cmrections
Replacerents can be effected by cmåininq ttese two techniques -s
my be helpful.
FINi&d that sirole erasirg redrawirp of tie affected region is not "act ical .
```

<a id="planning-and-coding-044"></a>
## planning-and-coding-044 — 8.9-8.10: correcting and changing diagrams and coded sequences (physical page 52); Volume I printed 42

Source: [physical PDF page 52](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=52); reading unit `p052`, lines 6–61.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-043](#planning-and-coding-043), [planning-and-coding-045](#planning-and-coding-045)

```text
142•
Even in static ccxiing Vere is no real gyoblem, as lorg as tre stage
of imi nary entneration has not been passed. Erasing Crcss ing Out, and re-
writing at the Sarre place else-nere, will take Care of everything cors ider ing
great flexibil ity of our. retha*s of (prel iminarv) enlmratim. (Cf. Note I in 7.4
the discussion of the prel imirøry entrerat ion in 7.9.)
The difficulties arise only when the final entreratim has already been
achieved, i.e. when the coded seqtence has already been formulated in its final fcrm,
when it has even Ipen put on. the regret ic wire or tape. In this Case, any unissim,
insertim, cr replacer-ent of any piece by one of different length, rray fcrce
rewritim of considerable potions of the cMed seqtence, wh ich trey I ie in any part of
it.
Indeed, it will change primrily the physical pcsit ions of the wcrds and tyeir
(final ) nuåers, inasmuch as they ie after the region Of ctenges. If the change
in length aml'nts to an Filber Of half words (orders),
it will even change the left
right position of all subseqoert half wcrds (orders) within tteir wcrds. Secondar ily,
it will change the x in all S(x) everw&ere in coded seq'eme, which refer to words
half wcyds whæe position was cterged pr irrør ily.
Let us discuss changes are effected on a cæ,ed seqænce that has
been fcrmulated (on paper) in its final enlJæration. We will afterwards toeh quite
br iefly upon the treatænt of Ehar*s in a sequence which has already reacted
rngretic wire or tape stage. This latter phase can only receive a prel imi nary
consi±ration in this report, since its exact treatment is affected by a mober of
er•gineering details which cannot be taker here. It will becare clear, hoever,
that treatrent of this prcblem is ir any event possible alonq essentially
sam lires as the treatænt Of the first rent iored pr&lem:
That Ore Of a cæed
seqtence fcrmulated (Or paper) in its final enurerat
The best way to deal with this problem is by reans of a specific
example. will Use the final cded solving Problem q, as given rear the
end of 8.8, fcy this purpæe. Ollr changes Will consist of ctrreo.tions Of actual
erra•s (we will introduce str.h erræs into that sequence), charges which ccyrespond
to voluntary transitions fran me ca-rect code to another Ore offer clearly no rew
problerrs .
We consider tterefTe final coded sequence 0-36 in 8.8. take
up several hypothet icål e-rrcrs and tteir corrections:
First: Assure tint by sme mistake three cyders wh ich do not belong
in this seqtence, had been placed into three half wcrd beginning with
, and onr actual cyders u-27' are at 15'-29,
the first half Of occwpy 14—15
Al) refererres,m ottEr hand, are
and the strage wc-yds 28-36 are at 30-38.
If is desired to remove the erroneous
ccyrect with respect to this pcsitiming.
crders, 114-15 (this is the old rotation).
cyder l" by an ux:ordit ional trarsfer
It suffices to replace
15
141, IS be left starding. After IS'
is irmediately transferred to 15' , where
C gets to 14, and dæs nothing there, but
it belongs.
Eü•ld.• Assure that by sane mistake the two 6', 7 are missing.
The act1Jal cyders 7 '—27 t are at 61—26', ard stcxace words 26-36 are at "7-35.
All references, the Otler hand, are ccyrect Wlth respect to this positioning.
```

<a id="planning-and-coding-045"></a>
## planning-and-coding-045 — 8.9-8.10: correcting and changing diagrams and coded sequences (physical page 53); Volume I printed 43

Source: [physical PDF page 53](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=53); reading unit `p053`, lines 7–55.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-044](#planning-and-coding-044), [planning-and-coding-046](#planning-and-coding-046)

```text
43.
It is desired to insert the missing or&és 6', 7 (this is old notat ion).
Chcx)se a locatim in the remæy, where an interval of sufficient
length begins. This ray be first position fol lcwing the cMed sequence in qtestion,
any Other pæ itim. We assurm færrer, and ch0(Se acccrdingly 36 (this is tre
rvntatim). displace the a-der iately preced ing tte missing in the
present case 6, and replace it by an vnconditional transfer
6
36 c,
Beginnin; with 36, we add tie reamed 6 as wel l. as missing (Xde-rs 6', 7
and cortll'de with an Iircondit icy',al transfer back to the crt-kr irmediately fol loging
upon missing ores. This gives
36
37
29 s ,
R,
32
(The 32 in cyder 36 is rew notat ion fæ old 33.) If seqterce contaired
any refererres to 6 (which does not happen to be the case here), they have to be
replaced by references to 36.
Third: Assme that certain cyders in the cded seqtencæ were
erroremsly rep laced biy other T ders. The nurter Of a-ders cr rrw,' not
be equal to the nn±er Of the cTrect Tders which displace. In latter case
entire subseqtent part Of coded seqterce is displaced, but that at
any rate all references are with respect to acttal posit ioning.
If the. seqence has the sam length as the erroreous ore,
can simply insert it in place of the latter. If tip ccrrect seqterce is
sba-ter, then insert it, and proceed fran On as in first case. If the
ccyrect seqlerre is lorger. then insert as mlCh of it as poss ible, and groceed
fran there on as in the secmd case.
It will clear fran tlE abwe, that changing coded which
already on the rragnetic wire ta;p can be effected acccrdirq to the sarre
% irciples. This requires, of course, a device which can sir91e wcxds on the
regret ic wire Or tape. We expect, that the rain itself, as well as
special typewr iter which meqætic wire tape under renual control ,
will able to do this. This rteans, ttet tte des ired charges can be effected
either by min rachire, with approgr iate instr1}Ct ions, by typewr iter,
latter procedure will pr±ably be preferred in rx:st cases. (Cf . ho•æver
Chapter 12 , f T a smewhat related situat ion where first grocedlre turrs
out to be preferable.)
8.10 Proble«s of a artificial Character, des iqæd
to illustrate certain sal ient points of onr rethod of coding, but only indirectly
and very imanpletely actual ical pr±lers. Fran ncv on will
lay a "eater stress the real ism of ottr examples. will still select tiem so
that tiey illustrate variow impcrtant aspects of our meth&, but we will
also oonsider it impa-tant tret ttey should represent actiel ard relevant methe-
rat ical Furttermcre, will proceed frm typical parts, wh ihh OCCIT
usually as parts of larger to irveas ingly Cmvletely fa•mulated self-
contaired
```

<a id="planning-and-coding-046"></a>
## planning-and-coding-046 — 8.10: square-root iteration, explanatory diagram and code (physical page 54); Volume I printed 44

Source: [physical PDF page 54](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=54); reading unit `p054`, lines 15–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-045](#planning-and-coding-045), [planning-and-coding-047](#planning-and-coding-047)

```text
with a the operation Of square rootirg. This is an
impa-tant pr±lan, because our nuchine is not ex*cted to contain a square root ing
cxgan, i.e. square rooting is mitted frm its list of basic aritywet ical cverations.
form v
Problem 5.
The variable u is stTed in a given memcry Imation. It is desired to
to it in anotter, given, rem«y location.
v should be (itaired by the operation z -i (z + +
This iterative process Can be written as fol
Two qtest ions remain: First, what should be valle Of initial
Secorxi, what i =
io should tte iteratim stop, . i.e. which z i be
ident if ied with ? The arswers are easy:
Ans•ær to the first question: S irx:e prefer to avoid adjustrents
Of size, it is desirable that all rumbers with which we deal lie betæen —l and l.
u will be tetæen -l and l, and it is recessary to have O, herEe O $ u < l.
Zi must be beWeen -l and l, it is desirable to have Zi. O, terce O $ Zi < l.
and Zi +
Corzequently ntnbers , whæe s izes must be watctpd are
The first requires u Zi, i.e. u < Zi < l. Tie secord one my be circtrvented, by
fcxming desired (Zi + h ) in this way: (Zi + k) = (h — Zi) +
Next clear lv
y-Erce - , i.e. all Zi vTwith the possible exception of zo. Choose
therefcre zo i.e. l. Then all Zi F, and so Zi > u (u < I
impl ies u < \.fi) as cksired. Zi v'iF gives , lerce Zi Zi + t, and so
and converging to
In choæ ing zo we may chocse any nurrber that is rel iably VT. The simplest choice
(l+u). Since this expression involves divisim,
IS zo = This gives -
we might as well begin with i = I aM ZI
Aroer to the second qtestiOn: t' is kno«l to within an errT
o 2-4 c, tercevq is krmn within
= tires this error, i .e.
du
```

<a id="planning-and-coding-047"></a>
## planning-and-coding-047 — 8.10: square-root iteration, explanatory diagram and code (physical page 55); Volume I printed 45

Source: [physical PDF page 55](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=55); reading unit `p055`, lines 9–51.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-046](#planning-and-coding-046), [planning-and-coding-048](#planning-and-coding-048)

```text
45.
u * C, as u varies tran I to 2-3 e, eu var ies fran to 2
.7X 2-21
u - C the abwe fcyrula breaks dogn, hoæver tte is clearly = 2-2
i.e.' Eo - 2-20. assume O, since trp case u E O Is quite harmless. shaJld
stop when Zi lies within Eu Ofvf. that the last step is ore frm
to z•
then we I Zi o + z - Eu
This neans
-F 12 , z
I Io 2-20 since Zi 0+2 -
is rpgligible cmxred to Zi -VT ,lZio- z i o +11 S 2-20
. thirvzi > z
ard
raking a safe werestirøte qfvæ
Usirg (*), it is easily sæn, that ( ) , tie equivalent
Zi 2-1 e ,
2 if I-r' I-re, fr ioz3
if 2-1 I-TN, for
• if 5-1 ,
u = T 40 O.
terre fcy vallB of u, specifically fcy .2 S u $ .875 reed 3-4 iteratims.
Cårqer ntners io of iteraticxs are ree&d wtpn u is smll, if u is of tte
2-2' io lies betæen j-3 and j-l.
It is tierefa•e debatable,
shouid Bot adjtst u first, by bringing it into "fava-able" rarge u ? .2 by
iterated rwltip1icatia•e with 22. In eur to simpl ify ratters, will not do
this, ard wate with u relyiry ( * • ) mly. TtE disaoantage thus
irrtrred is ærtainly wt seriotß.
This arrargeænt of tre iterative mmess has tte effect, that tiere
is no reed to sta•e the iteratim index i (but will, of cotrse, to refer. to
i in dræirg the f IO/ diawam). u at A, aM v v'ü; *en it is föned,
at B. tse distributed strage. In tte rec«fing refraired fram
tte strage location, which is reserved f« tte final result,
too. will u do this.
f 10-8 diagram should xesertt ro difficulties, it is stun
in Figtre 8.3
FARE 8.3
z,
a
z.
1
A
```

<a id="planning-and-coding-048"></a>
## planning-and-coding-048 — 8.10: square-root iteration, explanatory diagram and code (physical page 56); Volume I printed 46

Source: [physical PDF page 56](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=56); reading unit `p056`, lines 3–42.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-047](#planning-and-coding-047), [planning-and-coding-049](#planning-and-coding-049)

```text
(to II, l)
c.2
(to til, i)
Ill, I
c.3
111,2
(to 11.1)
boxes I-III require static coding. proceed in sane serse
as did in Pr±lvyrl q, and all bmes in ore, continuous oæration:
ZI
IO- 12
II s
12 h
c.2
c.3
c.2
Next, Ü•der the boxes, in sane sense as we did in coding
Ill results 'with ore 11 should have
Problem 4. Tre Tdering l, I l.
been the imediate successT Of Ill • This recessitates an extra Tder
111,4
11,1
To curlu±, have to assign A, B, C. 1-3 their acttnl valæs.
pair tte 16 rders l, 1—4, 11.1—8, Ill , IA to 8 wrds, and then assign
actual valæs. Thæe are expressed in this table:
2-5'
Kita in this cæed seqterce:
10 h,
ecc, .2C
as fol loqs:
Tre duratims •y be estiflBted
l: 130 u,
II: 380 g,
Ill: 150B
c. 1-3
12
Total: I + (11+ Ill) x Io =
• (130 + (380+ 150) io)
(530 io + 130) (.6 + . l) m.
As we saw abwe, a reasoæble mean value ftr i is This gives a duration of 2.5 m.
```

<a id="planning-and-coding-049"></a>
## planning-and-coding-049 — 9.1-9.5: human and machine number representations and reading conventions (physical page 57); Volume I printed 47

Source: [physical PDF page 57](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=57); reading unit `p057`, lines 7–55.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-048](#planning-and-coding-048), [planning-and-coding-050](#planning-and-coding-050)

```text
9.C CODING QF PROBLEMS DEALING WITH THE DIGITAL CHARACTER CF THE NUMBERS
PROCESSED BY THE MACHINE.
9.1 will code in this chapter several prålers, which fall into
two classes.
First: corwersion of ntr±ers given in the decimal system into
ttpir birnry fml' , and corversely.
Secæd.• TFE instrtrt ions which are recessary to rake tte rachire
with nurbers of mre than 40 digits.
Ttese probleflb are of corsiderable interest fcy a var iety of reasons,
ard it while to trese s«rewhat extens ively.
We note, to begin with, t\et both classes of problens furnish exanvles
Of prdlems and præedures that deviate fran the norral of algebra, and herte
differ very relevantly frm the pr±leßs that we have hardled so far. Indeed, up to
nog (as well as in all cases that we will consider after this ehapter) digit
aggreaate, which is the nurrber contained in a '.«d, was tte standard unit which we
mnipulated. We appl ied to stx:h units the elerentary oærat ions of aiitmetics
(additim, subtract ion, multiplication, division), but we TE/er caiired them in
any way except tirmgh these operations, aryl we never broke any such unit up into
sral ler parts.
In the pr±lerrs of this we will have to break up ntrbers
into treir digits, operate on these digits (T rather on certain digital aggregates)
individually, carbine numbers in rewways, etc.: that is, Otr operations will be in
rrøny impa•tant phases logical c00irEta• ial rather than algebraically
Next, we Feve to point out pract ical of the two
classes Of pr&lens to which have referred. The second Class can be disposed
of by a simpler discussion than tte first ore; ttprefTe we will ccrsider the
second class first.
9.2 Our stardard numbers have digits, rather. a sign
1.8 • 10-12.
and birury digits; HerCe they represent a relat ive precision of 2
C.OTIRrirg this to the length of interval which is available trem (f rm —l
.9 • At any rate, we
i.e., •length tte precision becones 2- •
to l;
Fave here a precis im Of about 12 decirrøls. This is a cons iderable mecisim,
and adeqtzte mcre than adequate f'X prchlems that are Of interest at this
nment. Yet there are even certain exceptims; e.g., surrraticn of certain
ser ies, the evaluztion of certain expressions by rectrsion fcrmulae, the integra-
t ion of scre rm—l i rear (total) ial eqtntions, etc. these
cases, wrere 12 decirals (cr their equivalents) are inadeqtzte, are likely to
becare rxre freqænt as more irwolved pr&lers are tackled in future.
It will beca•re increasingly difficult to chose an nappropr number
of dig its fcy an all-purpose rechine, especially siry:e an unuslzlly high nurrber Of
of digits (for standard mrter) would render it very' irefficient wtpn it deals
with that require ordirary (aM trese will inue
to corstitute tye m jr ity Of all appl icat ions). This inefficiercy would extend
to use of available reff0ry capacity, amount of equimpnt tied up in
parallel diqital chanrels of the machine, ard the tire required to perfcrm
multiplicatims divisions.
```

<a id="planning-and-coding-050"></a>
## planning-and-coding-050 — 9.1-9.5: human and machine number representations and reading conventions (physical page 58); Volume I printed 48

Source: [physical PDF page 58](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=58); reading unit `p058`, lines 5–57.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-049](#planning-and-coding-049), [planning-and-coding-051](#planning-and-coding-051)

```text
48 •
Consequently, it is imp«xtant that nechire should being
operated at varying mm-bers of digits; i.e. at varying levels of digital precision.
Orp might consider building in alterrhtive facil it ies for alterrative precis im
levels, control led by rranual switctes, or partly or wholly automtically.
prefer, hogever , tc achieve this without any phys ICal changes or extra Of
the L*Obirary digit rachine. This can be done purely logically; tret is, it is
possible to instrtct the to treat k words; i.e., k aggregates of a sign
arri 39 birBry digits, as if ttey here forming a number with a sign of 39 k binary
(k-l signs are wasted in this process.) This irrreases the precision to
ditiEs.
2-9 ; that is, to IO
; that is, to any desired level.
It dæs require,
hoæver, rw instrtrtions fcy the Øerations of arithmet ics (addition, subtract ion,
multipl ication, division), and it cannot fail to redtne tlE speed tte nerr«y
capacity of the rechirm W•vertheless, it is reasonable as an emergency
reasure, an except pr&lem requires unusual precision.
Ttese new ar ittnt iCal instrtctions are pro,'idfff by the probkrrs
Of our second class.
9.3 Our machine will operate in tte system. This is most
satisfactory from the point of view of its arithætical ard its strtrture,
but it creates certain problers in connection with its mactical tse.
' In rost cases the input data are given in tte deciml system, and
tre unput figures (the results) are Riso wanted in that system. It is therefore
imp«tant to be able fo effect the deciral-binary and the birzry-&cinel conversions
by fast, autMntic On harri, the use Of ttpse devices should be
opt i.e., rachine should be able to receive and to emit data in tte birEry
system, too. reasons ftv this requirerent deserve stated expl icitly.
The use of tte deciml system is only just if iable fcy inputs (data)
which crigir•ate (directly) in hlrrøn ims; i.e., where wire
tape tyut carries them has been prodtred manually (by typing): aM for outputs
(results) which are intended fT (direct) hurran serBing; i.e., wtere tie contents
of the mgrptic wire or tape in qtestion are to be t•ade readable in ordinary
sense (by pr inting). good deal of tte output of the rrachire is, horever,
in sane pr±lem
destired solely for use as stbseqtent input of the rechire
in later prob lem. this rater ial no conversion is reeded, sime it
reed be moved of tte birøry system. ThlB tl•e are, as a ratter of
principle, two categ«ig within the infrution st«ed on tte ragretic wires cr
tapes: First, infrnnt ion mtBt pass tyrough humn intel lects (at its Tig in
at its firel dispæition); secorrf, infmTBt ion rever reactes (directly)
a hurøn intellect and reßBins at all tines str ictly within rechire cycle.
Olly ttE first catego-y need be transferable to and frm decirøl notatim;
i it requires the cmvers'ions that we are goirp to cons ider. This
circunstanæ is of great iro«tance deal inq with these conversions, because
it sets fr tYem much less exigent standards of speed than would be desirable
otterw i se.
Indeed, infTrøtion af second categTY my be EOdtEed and
conswed at a rate which is only limited by speed af writing on rea4ing
from the mgretic wire or tape. This can probably be at rates Of SC—ICC
thousand digits per secoöd. my, at least at first, use a trore corset-vat ive
arrangerent of about 25 thousand digits per second. Even this reans, fr a
```

<a id="planning-and-coding-051"></a>
## planning-and-coding-051 — 9.1-9.5: human and machine number representations and reading conventions (physical page 59); Volume I printed 49

Source: [physical PDF page 59](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=59); reading unit `p059`, lines 6–60.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-050](#planning-and-coding-050), [planning-and-coding-052](#planning-and-coding-052)

```text
49.
digit mmber, arxå with reasonable tirre alloarces for certain checking feattres, etc. ,
about 2 m per ntrber. In rder that the convers ions do not s 10M da./n these pras.esses
appreciably, they would have to consur•e definitely less than I m each.
Inf(yret ion
of tte first on the other hard, should not be pranced constred faster
than the rate to that of printirg, typing, and WY-at is restrictive,
htrrøn nurderstarding". Our g O binary digit ntners carespond to ntrrbers with about
IO deci"Bl digits.
It is diff icult to assign a definite tire to this, since
one ray pr int reny digits in paral Thus, standard pr inter will print 80
decinel digits in satewhat less than a secorxi. Various ureonventional my
be a goaf deal faster. the ottpr hand, typing will hardly ever be faster than iO
deciml dig its per secorxi, and any form of "llrxierstard ing" (which should be
taken to mean at least critical reading) will be still Even the raking of
tables fcy publ ication reed not exceed this rate, and besides it is likely that tre
raking of voluminous tables in book fcrm will becme less important with tte
dicti(M of very high speed nechine c«rput ing. To the extent to which rachire is
Taking "tables" for its cyn use, ttey fall into the. secord catego-y•, i.e. they shalld
regain On wire tape reditn, and rever be converted into the decinnl system.
I-Ence, infTrøtion of tye first can be. hardled satisfactcxily with any
version mthods that are considerably shcrter than a secOM. An upper 1 imit Of 100 m
would seem than safe.
These comiderations Shu-I that our subdivision of the input
output of tye rrechine into the two categcries discussed abwe is
Indeed relevant, and that it is also impcytant to realize that desirability
of the corversion applies only to the first category. Ttese things being under-
stod, any cowersion tines up to ICO m turn out to be adequate.
The mchine will easily effect tte cmversionsl in qæstion at much
faster rates than this. With snall changes •in its cmtrols we could even keep
within the I m, which would be.desirable if all infrination were to be corverted,
blrt have seen that this ' is unrecessary. We will tterefcre rake no
at all. corveriion tires arrived at in this ranrEr will be cf tie
rder cf 5 m.
In Or&r to discuss these, Or-e rncre meparation is reCeSsary:
machire is to effect birery-deciml and cavers ions, tren we
must agræ on sare methd by *ich it can deciml digits; i.e., express
in a binary ion. This mist also be ccyrelated with variaJs character ist ics
of tye wire or tape rediuh: Hoq tte deciml infcrrøtion is stored on it, it can
be put On • it by ard extracted frun it by printim.
will pra:eed to consider ttese retters.
S. u In disctssing typing and printing, one should keep in mim
that, while it is recessary to able to perfrm t!ese operations in ttE dec imal
system, it Is quite desirable to have alter rative pmSibilitv of doinq than
in birery system. Sirte tte inrer funct ionirq of the mchire is binary, its
extersive use will sccessively lead to an ircreaiina familiarity with the birery
system, at least as far is thæe are correrred who are directly in
it; (Tek Irg arithretical and otter estirates for it; seNing, diagrsing
and crrectirg its rrelfurctiorz: etc.
It is likely that •rachine and the
practice ard thecry Of its functioninq will prCx{Lre genuirply birnry prc%lers.
It is therefore Prchable that it will gradually Cause, even in the interests Of
its users, a certain amunt of a shift fran decimal to binary præedures. Tbe
pr±lem Of typing, and (hlrran) readirg should ttprefcye be faced in the
birøry as well as in decirøl system.
```

<a id="planning-and-coding-052"></a>
## planning-and-coding-052 — 9.1-9.5: human and machine number representations and reading conventions (physical page 60); Volume I printed 50

Source: [physical PDF page 60](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=60); reading unit `p060`, lines 8–75.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-051](#planning-and-coding-051), [planning-and-coding-053](#planning-and-coding-053)

```text
50.
COTE i±r, first, tye binary case. rachire, as hell as tie wire
tape, treats a ntnber as an aggregate of birør.y digits, i.e., digits C l. TO
type in this fashion, and even to print and to have to read in this fashion,
would be definitely ireffieient, siree we are already conditiored to recongize ard
use about 80 different alpFzbetic, ntnrical and purx:ttntim syrbols. A str ing• of
digits is definitely to reranber arri to manipulate than a Of IC
symbols, even if the forger are only O's and I 's, while the latter ray be chosen
freely fran IC decimal digits C,
9 or frm 26 alphabetic syriols a, Z.
There is, hc»ever, an d! ious way to circmvent this incowenience.
Ilt consists Of choosirg a siitable k = l, 2, 3
, and of typirp, printing and
reading not in terns of individual birøry digits, but {f groups of k digits.
This annunts, of course, to wing effectively a base 2 systan instead of ttp
base 2 (binary) system, but sirre the conversions betæen these two are trivial
to the point of insignificarce, and sirre the nechire is birøry, this seems a
ratural thing to do. our reading habits ary ccmditionirv, 2k shoU1d
be of the order of IO to 80; sime it is to replace ttE ntröer IC of decirral diqits,
it is preferable to Mke it of the order of IO. k = 3 or k = seem tte
logical choices.
Fff k = 3, 2k 8, we can denote tiEse triads of binary digits by
the decimal digits O, 7. It is best to let every deciml digit O, ...,7
ctxrespord to its birøry express'im (as an integer). This is an advantage.
the other Yend, a pr inter that is crganized in this fashion would be unable to
pr int decimal digits 8, 9, and this is a which is unacceptabb ,
as will appear belo•t'.
Fa- k 14, 2k 16, we can deX'te tetrads Of binary digits by
9 and six other sy±ols; e.g., the letters a, f
deciral digits 0,
9 correspond to its binary expressim
It is best to let each deciml digit O,
(as an integer). Each letter a,
f may be treated as if it were corres-
15, and it Can be replaced by the
ponding nunber in the IO,
birøry expression of that mm-ber (as an integer). Thus we tw.•e to use the deciral
9 and the letters a, f together, which my a disadvantage:
digits O,
This disadvantage, hoever, is outweighed by the advantage ttet a printer which is
e. It can also
in this fashion can print all deciral digits O,
print the letters a, f, which are likely to be useful fr otter indications.
We choose accordingly k The sylTbols trat we ass ign to tte
2k
ocoo
0001
COIO
ocil
= 16 tetrads of binary digits are shoyn in Table IV.
TABLE
1100
1110
2
3
0100
0101
0110
0111
5
6
7
1000
1001
1010
1011
8
9
```

<a id="planning-and-coding-053"></a>
## planning-and-coding-053 — 9.1-9.5: human and machine number representations and reading conventions (physical page 61); Volume I printed 51

Source: [physical PDF page 61](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=61); reading unit `p061`, lines 8–59.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-052](#planning-and-coding-052), [planning-and-coding-054](#planning-and-coding-054)

```text
51.
In acttnl ervireering term this decision mans tte follo€ing thims:
First: The typewriter which is used to rodtze InfTretim manual ly
on the wire tape 16 keys, narked O, 9 and a, f. If any ore of these
keys is depressed, it prætx:es on the wire cr tape ccrrespordlng tetrad of binary
digits, as indicated in Table 'V.
Sa:om.• % inter which is used to corvert on tte wire
tape into readable print, can % int 16 symbols, the decirrøl digits O, 9 and
the letters a, f. It picks up the infm•røt ion on the wire, which is in tte
fa-m of binary digits, tetra&ise, aM upon having sersed any tetrad, it prints
c«respording syrbol, as iMicated in Tablé IV.
Ikrre, a 40 binary digit word, e.g. a full size ntrrber, c«respoMs
to IO tetr•ds, i.e. to IO synbols 0,
f; aM a 20 binary digit e.g.
an Tder, corresponds to 5 tetrads, i.e. to 5 -symbols. Within an order the 12.
first binary digits tte Imation mnber x (cf. Table II), aM tterefore
this x is separately represented by the 3 first tetrads, i.e. syrbols.
It is best to allot to every &cimlly expressed nurber, too, the
space of n. wc-d. a I logs fcr IO syiols, i.e. f« IO deciml digits.
Since It is desirable, hogev«, to leave space fo- a sign irdicatim, ttese are
not all available. Tte sign could be exressed by ore birury digit, but it
seers not to disrupt tte grouping in tetrads, we propose therefcre
to devote an entire tetrad to the sign.
In addition, it is. desirable to (Enote
tte two signs + aM - by a tetrad which differs in grint frap tre decirøl digits,
i.e. which is pr inted in our system as a letter. We essign therefore tentat ively
'letter a (tetrad to + and trp letter b (tetrad 101 1) to —
Thus a 4C
birgry digit wcyd Can express a decirel nucher which r.m3 ists of a sign and cf S
decirrzl digits.
It is indicated to asstrpe . the deciml ntners, as we did fT
the binary ores, trey lie behqeen -l ard l, i.e. that the decimal point
irmediately after the sign.
There is ore rrcre thing that reed be rentiored in cmrection with
the tse of the sign irdicatim in the decira) notation. Our binary notation
Yandled regative ntr±ers essentially by taking ttpm rrxiulo 2, i.e. a rrgat ive
- lal ! The flrst I expressed
a • was written as 2 + a-2- lal
the - sign, ard so.the digits to the right of the binary point were those of
, i.e. the cm.pleænts of the dig its cf lal (with a crrection of I in
the extrene right place).
(Cf. 5.7 ir Part I of this report.) 'In our dæiral
mtaticn it will mre corvønient to desigrnte any ntrber a (wyett*r rpgative
by Its sign ixiication,follaæd (to tte r Ight of decinel point) by tie
This is in lurrrony with the t_JSLnl notatiom in print, and it
digits Of lal .
presents certain advantages in the actual præess of cowersion (cf. 9.6, 9.7).
9.5 arlthretical conseqtgrces of ttese corrventims are nod
easy to formlate.
Tie rechire should be able to deal in two different .ways with
nurbers that lie -l ard I in terns of birery digit
First: In binary way: Sign digit arx! 39 binary digits.
```

<a id="planning-and-coding-054"></a>
## planning-and-coding-054 — 9.1-9.5: human and machine number representations and reading conventions (physical page 62); Volume I printed 52

Source: [physical PDF page 62](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=62); reading unit `p062`, lines 5–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-053](#planning-and-coding-053), [planning-and-coding-055](#planning-and-coding-055)

```text
52.
Seco•Ü.• In tte decimal or ratter in tte binary-deciral way:
Si gn
tetrad, which is 1010 fcy + and 1011 fcy — (both aggregates to be read as binary
numbers), and 9 decirøl digits, each of which is expressed by a tetrad, that is
sirvly its expression as a binary nurrber.
In to rrzke this double system of notations effective, must
provide appropr iate instructions for convers ions fran each Ore to the otter .
I.e. our problem of corwer%ion is to provide instrvctions fa- binary to binary-
decirøl ard tye binary—decinel to binary conversions.
It should be noted that these
conversions take place betæen two binary digit aggregates, and ttey are {o
perforned by our ptrely binary rechire.
At this point a qlEstion coreernirg precision presents itself.
are consider ing conversions between what is effectively a 9 decirBl digit nun-ber
and between a 39 binary digit number, i.e. a ntrrber given with tte precision
10-9 and a run-ber given with the prec is ion 2
- 1.8•10-12. The latter is 550
tires mre precise than ttp former, is this not a sign Of unbalarre? wish to
±serve that this is mt tlp case.
Indeed, the first rent ioned, lager precision in •ckcirral
nuåers, i in the input (data) and output (results); while the second
rrentioned, higher precision occurs in binary ntnbers, i.e. in the intervening
calculatiors. Verce observed disparity in precisions rreans only that we carry
in the calculations an excess precision factcr Of 550, i Of sl ightly less than
3 extra decimals, beyond the precision of the data and tre results. it is
clearly recessary to carry in any canpl icated calculation decirrels than tte
data or tte results require, in order to keep tte acctmulation Of round-off
errors dagn. a calculation Of such a carvlexity that just if ies the Ilse of a
very high speed electronic ing device, 3 extra decirrøls will probably not
be excessive fran this point of vie.•d. They ney even be inadequate, i.e. it mey
not. be pæsible to utilize in the data and tte results the full nu±er (9) of
available decimals.
Tlpse considerations conc11He our prel iminary discussion. add
only ore n-re re"Vk: With tte except ion of tie arrargemnts relative to the
and printer (cf. Table IV and the two rererks which ft)) lag), we did
not discuss physical features of the machire , but only arb itrary conventions, to
be effective by giving appropr iate instr1Ct ions to machire. A var iety Of
otyer conventions would be equally pæsible (e.g. different pos itioning of the
precision by using mre than om word fT a deciml and
deciml point,
for a binary ntnber, conversions into and fran other systeTs than the deciml
etc.), and could, if desired, be rede effective by appropriate instructims.
are Mly discussing ore example in this chapter, as a prototy*, although it
Seems to be and irrediately generally useful ore.
9.6 are rm in the position to discuss act nal cmversion
processes ard tteir coding, ThrotEhout this paragraph ard the rext ore will
have to use alternately binary and dec irnal notations. agree therefcre that a
digital seqærce with ro special narkings is to be read decimlly, e.g. 987016
or .75102; while ore which is werscored is to be read binarily, e.g.
. 11001. Thus, e.g. 10001, .14 - .ööTfiTj-rrr-:z-. . In the tetrad
notation Of Table IV the two latter binary nmoers M)uld read I I and .23d .
```

<a id="planning-and-coding-055"></a>
## planning-and-coding-055 — 9.6-9.7: binary/decimal conversion diagram and explanatory code (physical page 63); Volume I printed 53

Source: [physical PDF page 63](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=63); reading unit `p063`, lines 14–60.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-054](#planning-and-coding-054), [planning-and-coding-056](#planning-and-coding-056)

```text
53.
corsider first:
Prtilan 6.
nur+r a is stored, in its birury fTm, at a given rrenuy ion.
It is desired to its binary—eciml fcym a', and to stcre it at another, given,
locat ion.
Acc«ding to this a is a ruier, lying betheen -l and l.
As
pointed 0th at erd Of 9.4, must first sense the sign Of a, then corvert
lal ies betæen O ard l, and its decinøl expar•sim Can be by this
lat.
indictive
(l) = Jal,
(2)
ai+l
If is tie sign iMication of a,
at tie end of 9.14) is z', z z
tyen the &cirrøl exparsion Of a (cf. remrk
as (4 digit) bimry
If Kite ZI, Z2,
mmbers, tien this representation beccres
I Ifcr a O
tien z* , z z
ze is a seqærre of
40 binary digits. Let us viæ it as a binary ntmber betæen -l l, in the
of the crdinary conventims of Otr rrachire. Siree begins at any rate with l, it
will be regative, represents acttnl z
1.010 (birery, mdulo 2)
• (binary, rdu102 )
It is cmvenient to introdl.re
+ 2-2
= -l *2-2+2
-2-2•3
zo • 23 z* •
Zi represents actual
-5 ftr a < O
(3)
(5)
• . b inary ntner that want to i s
z • This can be &firpd indtet ively as f0110ß:
-5 fir a < O
Thic our &finitims, except that
the point of view of ocr actiZl
ar ith•æt ical
it is Üe crwenient to wite, from
pra:esses. (2) in this frm:
2'(2-2 ai + 2-3 q), osa
```

<a id="planning-and-coding-056"></a>
## planning-and-coding-056 — 9.6-9.7: binary/decimal conversion diagram and explanatory code (physical page 64); Volume I printed 54

Source: [physical PDF page 64](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=64); reading unit `p064`, lines 7–49.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-055](#planning-and-coding-055), [planning-and-coding-057](#planning-and-coding-057)

```text
54.
This Of (2' ) apans that the additW1 that is required in is
performed entirely within the range between -l l, indeed between O and l, and
i.e. trp
that the split into a "fractional part" ai+l
and an "integer partn z •
operat ion which recessar ily requires exceeding that is initiated by a multi—
pl ication by 24 alore, i.e. by a quadruple left shift. This latter operation, a
fourfold appl ication of the L of Table II, ically separates tye fractional
part.nd the integer part, referred to abwe: Tte fcyrer appears in the ,
the latter, mltipl ied by r s g, in the register. At tte saæ tine it should be noted,
that (g) iwolves no trtE addition, but if a: is in register, abwe
rrentionee fourfold appl ication of L of Table II WII I replace it by aM will at
too, ttereby fcrming typ desiréd
same tim introdlce there 2-3 Zi + t ,
TYpse cons iderations Shaq, by the way, that it is best to
9) in the register, and thæe of
s'rcessive valtps Of a! (for i O, l,
a i in the acctmulatcx. Siree tåe register will be required for any otler purpme,
will even find it pcssible to store the successive values of a! in tte register,
while additional dernnds that will have to be made on acctmulå& will make it
impossible to do the sare with ai and tie acctmulatcr.
iteration irdex i might be stored in fa-m r B i, but it is
smewhat preferable to stT9 it in tie form 2-3 e (8,i). (A corresponding trick would
have been equally appl icable in coding Problen 3.)
We can nag draw flag diagram, as Shaqn in Figure 9.1. note
that the stcraqe space indicated fcr ait, B. l, is actually the register (cf. abwe),
Perce B. I will not ap*ar as such in coding that fol As to tte final
storage of result, a', var ions alterretives are possible, ircluding leavirv it
in put it irstead into a definite rreffxry location, aryd chmse for
this 8.2.
FIGURE 9.
8.1 a 0'
3 z-39.e
to 2.2
2—39.
to 8.2
3.2 a'
e
PART OF
2--99. CINTESER PART
3 2-39 (7—0
2
```

<a id="planning-and-coding-057"></a>
## planning-and-coding-057 — 9.6-9.7: binary/decimal conversion diagram and explanatory code (physical page 65); Volume I printed 55

Source: [physical PDF page 65](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=65); reading unit `p065`, lines 4–40.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-056](#planning-and-coding-056), [planning-and-coding-058](#planning-and-coding-058)

```text
SS.
carry this out as in the
(to Ill,l)
(to IV, i)
c.2
(to IV,I)
IV,I
c.3
(to v,l)
10
12
V, 13
(to VI, l)
VI, I
(to V, l)
VII,'
The boxes I-VII require stat ic coding.
preceding xoblems:
8.2
c.3
8.2
VII, I
8.2
8.3
Ac
8.3
Ac
Ac
order the boxes, as in the preceding pr±lers. Ttp (Xtkrirg
II; results, with two imperfectiors: IV, V should have been
l, Ill,
IV, V, VII;
irmediate successa-s Of II, VI, respectively. Thls recessitates two extra a-ders
IV,I
VI,3
of these quantities in V,
Figure 9.1.
```

<a id="planning-and-coding-058"></a>
## planning-and-coding-058 — 9.6-9.7: binary/decimal conversion diagram and explanatory code (physical page 66); Volume I printed 56

Source: [physical PDF page 66](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=66); reading unit `p066`, lines 4–89.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-057](#planning-and-coding-057), [planning-and-coding-059](#planning-and-coding-059)

```text
1,1-2
Ill,]
2
•3
q
5
6
7
56.
must assign A, 8.2—3, C. 1-4 tteir actual valæs, pair 29
T&rs l. r-2, I ' .
31-10
12 -13
19 R, 15M
16 s , m
17 s , 16
R , 16 S
R,
assign I. I
-VII,
1-2, ILI , l, 'V, I-Y, v, l-
3 tteir actual valæs.
VI l-
Trese are
, 3, VII, 1-3 to IS wa-ds
exxessed in this table:
VI, 1-3
VII,1-3
8.2-3
131-14
15
16 -17
18 -21
, 13 w
16 h „
L
L
this
8
9
12
13
14
s.aqtrrce
L, 16 s
21 h-
17
17 s,
12 cc,
16 s
A,
18 R
15
16
19
20
21
-24 •6
2-3 G '8
2-3 e
durati&S nv be estimted as follo•s•.
t: 75 u, II: 75 v, Ill: W: ISOu, V: 285 u, VI: 125 u, VII'. 105 u.
10ta1: i + (V + VI) N 9 +
(7S + 75+ + (385 + 125) x 9+ IOS) 5m .
9.7 corsi&r rprt :
Pr01at 7.
ntrber a' is sta•ed, in its binarHecinl fcrm, at a given
locatim. It is to prodtee its binary fTm a, ard to stTe it at anott•Er,
given, læatim. —
to this a' is a lyirg —l
l. AS pointed out at erø 9.4, first sense the sign of a', which is
Étermirzd by digits '—4 frm tte left, ard tten cmvert I all , which is directly
gnen by the reminifÜ digits 540 frm the left. I a' I lies betwen O ard its
binary expansim can be as fol
, i.e. in a' (cf. abwe),
diglb 4 i+l to '1+4 frm left inl atl
re tte birury exxessim the &ciml digit Wi, Which is digit i frm ttE left in
tte deciml expamlm of a' (i =
9). Ikrce twe tte eqtEtiM
a'l = Wi: which •y be interpreted as a relatim is val ld in
biÜv syst*. it is to Kite It like thls:lal WI .
ttE recise deflnitim of tye opratlm L, digib
4i+l to 4i+4 (frm tte left) a', can be to as the digits (frm
tt•e left) In regist%, if a' is plu•d into sub Bted to
41+3 L. If treat a' as if it ære a bimry nmber, this to
perfrmlrg
```

<a id="planning-and-coding-059"></a>
## planning-and-coding-059 — 9.7: inverse conversion, implicit storage and explanatory code (physical page 67); Volume I printed 57

Source: [physical PDF page 67](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=67); reading unit `p067`, lines 8–61.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-058](#planning-and-coding-058), [planning-and-coding-060](#planning-and-coding-060)

```text
57.
(2)
1.011 t)
1+1
w* will ca-respord to -last three digits Of sign tetrad, i.e.,
2 = 3, a&crding to wyettpr the rumber represented by .a' (in its
binary-deciml is 0 T < O. It is, h&ever, to get the
sign indication frma' itself:
If a' is interpreted as a binary nt&r, tren
have
= 1.010 ... *)
t) -l + 2-2 * -r' •5
1.011
accTding to wtether the ntmber represented by a' (in its binary-decirrøl interpretation)
is e O. That is, this sign is tte oppæite of the sign of a' + in its
binary interpretat ion.
WI , we apmr always as digits 37-40 (fran left) in the
register; i.e., actually as the nunbers 2¯3ewt, , T 3 ewe. It is therefore
preferable to write
Io-i 2
be write
Io-i Wi in this form:
the equation lal
3 g •2-39 Wi.
100 —i
10 ai + w
In Tder to comentrate tip div isiots in ore place
Wi) : 2¯s• This can stated
as follcws:
(3)
(4)
a
In fire a ±tairs frm lal by noting that sign ofa
oppcxite of tte sign of a' + r • •S (birEry cf. abwe).
Again, IO ai is forned as 23 ai + 2 ai.
can tte flog diagræn, as sho€n in Figtre 9.2.
indEtion iMex i can treated as in preceding prcblan.
is tte
The
Tip special tse of the register whibhwasnzde in F±lem 6 is not
tere: a! tes to be in the accumulatT, siree wait to form the fra±tional
ard integer parts lof 24 a! , operatW' L will only effect such things if
start frm ttp accmulatæ; ai has to go twojgh the siru we have to
fm•n trtE urs (with carries) like 23 ai + 2 ai; ard reityer can æcupy the ECU-
rmJlatT cont intJ0ßly, siræ the acctmulator is reeded alternately for both as
as fT the sersing in conrect im with ional tramfer T&rs. Tiere are,
ærtain stcrage fumties, which are best hardled by tte accmwlatT
register, in a renner rot rrø& expl icit in the f diagram Tnus
is
best in tte accumjlatcr as as in 8.3 befcre use in Ill; lal
is
best stcred in register after IV, and Of a to 8.2 is Only (Tede
subseqtrntly in VI arø in VII.
5¯ä7üFy, redtced mdulo 2 into interval -l, l.
```

<a id="planning-and-coding-060"></a>
## planning-and-coding-060 — 9.7: inverse conversion, implicit storage and explanatory code (physical page 68); Volume I printed 58

Source: [physical PDF page 68](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=68); reading unit `p068`, lines 7–13.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-059](#planning-and-coding-059), [planning-and-coding-061](#planning-and-coding-061)

```text
FIGURE 9.2
3 a-29(s-L)
3.2
—FRA CT IONA L OF
•C INTEGER
8.2
.10*foB.2
```

<a id="planning-and-coding-061"></a>
## planning-and-coding-061 — 9.7: inverse conversion, implicit storage and explanatory code (physical page 69); Volume I printed 59

Source: [physical PDF page 69](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=69); reading unit `p069`, lines 4–40.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-060](#planning-and-coding-060), [planning-and-coding-062](#planning-and-coding-062)

```text
c.i
c.2
(to II, l)
11,1
12
13
14
15
16
18
(to 111.1)
(to IV,I)
IV,2
(to V, l)
c.5
TYE bmes I-VII require static cading.
problens:
c.i
8.2
c.2
8.2
8.2
8.2
c.3
8.3
carry this out as in the
22 i
tai + ai
VII, I
(to VI,I)
• ) Cf. tte definitions
Of
t Fese
quant it ies
II,
Figlre 9.2,
ard in (l)
```

<a id="planning-and-coding-062"></a>
## planning-and-coding-062 — 9.7: inverse conversion, implicit storage and explanatory code (physical page 70); Volume I printed 60

Source: [physical PDF page 70](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=70); reading unit `p070`, lines 6–111.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-061](#planning-and-coding-061), [planning-and-coding-063](#planning-and-coding-063)

```text
60.
(to VI 1,4)
VII,I
8.2
2
8.2
3
8.2
, II, Ill
8.3
c.i
46 s, 15
L,
L,
15 s
s,
21 h-
L,
42 s,
36 CC
L,
17 s
s
c
8.2
8.2
a - - Iai
VI,2
text, a-der boxes, as in preceding pro'iers. a-dering
, 'V, V, VI; VII results. with ore imperfectim, VII .4 should have been
irrediate str;cessor of VI.
This, necess itates ore extra Tder
c
*must 'assign A, F. 1-3, C. 1-5, s. I tteir actual vanes, pair
tte orders 1.1-9. II,
1-18, 111,1, 'V, 1,2, v,l-3, VI,l-2, VII, 1-5 to 20 words,
ard then assign - VI their actual values. wish to do this as a continua-
t ion of code of 9.6. will begin with tFe ru±er 22.
the contents Of C. coireick with those Of 20, 21 in code of 9.6,
contents of 3. 1-3 and af s. I are irrelevant like thæe of 16, 17 there.
two Of these ney be to coircide with 16, 17. Also a is in IS ard
in 16 there, while have at in A a in 8.2.
ident ify our A, B.I , 2 with 16, 17, 15 there. Stmning all trese
the follcying table:
l, 1-9
, 1-18
'V, 1-2
v, 1-3
22
23
26
27
28
29
16
17
IS
2-26
.35
35'
37-38
±tain this
30
31
48
32
20
33
17
34
35
36
37
VI , 1-2
8.1
8.2
coded
15
16
38'-39
16
15
seqterce :
15 s
ard the
al is
up, ±tain
things
43
20-21
u -45
46
15 S , ts -
38
39
41
42
146
c.2-3
41
2-39 10
TIE durat ions ray be est irrated as follaqs:
l: 290 u, .515u, lit: SO u, W: 195 V: u, VI: SS u, VII: 180 u.
Total: 1+ (II + 111) x 9+ IV*V+ ((VI + VII 4,5) VII) =
SO) x 9+ 125+ 180) 5,875 m.
Tay stnmzrize the results Of 9.6 ard 9.7 as follogs:
```

<a id="planning-and-coding-063"></a>
## planning-and-coding-063 — 9.8-9.9: double-precision addition and explanatory code (physical page 71); Volume I printed 61

Source: [physical PDF page 71](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=71); reading unit `p071`, lines 9–50.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-062](#planning-and-coding-062), [planning-and-coding-064](#planning-and-coding-064)

```text
The binary—decimal and the decirrøl-binary carvers ions can be prov'ided
fcy by instrtK:tions which require 47 wa-ds, i.e. l. Of total (selectron) nervy
capacity Of 4,096 conversions last 5 m arri 5.9 m, respect ively. This
is shTt cmpared to tye 100 m which, as was slum in 9.3, is a reasonable standard
for conversion durations.
9.8 præeed no•.' to the problerrs Of the second class referred to
in 9. I arri 9.2: pr±lems that ar ise when we uMertake to the mchire in
a Tanrer, that it deals effectively with nlöers Of "Ere than binary digits.
nere are various ways to deal with this situation, aM it is actual ly
advisable to s tldy every problem which requires mo-e than n«rrel (go binary digit)
precision as an individual case: The efficient way to keep track Of nurrer iCal
effects beyond the binary digit I imit vary considerably fran case to case.
On the otter hand, our interest is at present in giv ing examp les Of Our nethods
of coding in typical sitnatiors, than in devising particularly efficient ways to
hardle cases that require than mrrral precision. will therefTe restr ict
Our discussion to the mcst procedtre, although flexibil i ty ard
speed could pr&ably be secured in many actual irstames by different scheræs.
Tie procedtre to which alluded is that described in 9.2: By us inq
k words to express a norr&r, we ±tain numbers with (a sign arß) 39 k binary dig its.
will actl'ally restr ict otrselves to the case Of k = 2: Two words n1Krber Of
In this way the precision tpcares 3.3 • 10—24,
(a sign ard) 78 binary digits.
(considering that the length of avai interval —l,
I is 2) 2-7e- 1.6 • 10-24
will stcre every nunber in two strcessive wc-yds: The first word
contains the sign of the rumber in question and its- digits (from left);
in tte second word the sign digit egual to are then let the digits
0—78 (fran the left) of ntrber fol
Tye operations which have to be discussed are the fow basic operations
Of arithæt ics: Addition, subtract ion, multipl ication, divis
Let us consider addition and subtraction first:
Prrblg!' 8.
The (double precision) nunters a, b are sta•ed in two given pairs of
rrerrry locations.' arm a ± b (also double precisim) and stcre it at another given,
pair Of rprÜy
Let a be sta•ed at A. 1,2, b at A. 3, 4, direct a: b, wten fovrred,
back to A. l, 2. first and tte secoryi parts Of a, b, a2b by ä, b, ä¯Eb
and a, % , respectively.
It is easily seen that
wtpre E is the sign digit of a ± 6,
(2)
b + 2-3 E •
```

<a id="planning-and-coding-064"></a>
## planning-and-coding-064 — 9.8-9.9: double-precision addition and explanatory code (physical page 72); Volume I printed 62

Source: [physical PDF page 72](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=72); reading unit `p072`, lines 8–34.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-063](#planning-and-coding-063), [planning-and-coding-065](#planning-and-coding-065)

```text
62.
It should be renmbered, of course, that all these must be interpreted
2, and that the pcsitiorel val Le of the sign digit is 20. Since X, have
the sign digit O, a sign digit I in is equivalent to a Carry fran digit 40
to digit 39 (frm left).
can draw the diagram, as shmn in Figure 9.3.
It is
convenient to carry stcrage furrtions in a nenær not rude expl icit in
the flag diagram. Thus is best forrred and mved into A .2 already in the
course of II arri Ill, while is built up in tre acctrnulatr in the
course of IV, the grourxå for this can be effectively prepared (in the æcmulato-)
to.,rards the erri of I I and Trese arrangerrents have the effect, that reitYpr
8.1 nr 3.2 is actually required,
both represent effected at appropr iate
tires in the accumllator.
FIGIRE 9.3
2¯
1
-39 toB.2
2
3
2
-39 E —O
2
t, 8.2
2
1-4
```

<a id="planning-and-coding-065"></a>
## planning-and-coding-065 — 9.8-9.9: double-precision addition and explanatory code (physical page 73); Volume I printed 63

Source: [physical PDF page 73](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=73); reading unit `p073`, lines 5–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-064](#planning-and-coding-064), [planning-and-coding-066](#planning-and-coding-066)

```text
63.
static coding Of the boxes I—IV fol Thæe txders which deperxi
on the alternative +
, are "*ked in their + and in treir - fTm
(to II, l)
C.I
c.i
c.2
11,3
c.2
c.2
(to 'V, l)
111,1
c,3
111,2
c,3
II, 'V; Ill, and IV must also be
The of the boxes is l,
irmediate s!Ecessor af I II. This recessitates extra
13
12 -
mtst
1-3 11,1-3, I ,
actual valtps. These
assign A. 1-4, C. 1-3, their actual values, pair 13
II 1—3, IV,l-4 to 7 woräs, and then assign I , I - IV.4
are expressed in this table:
0-1
11-2'
IV,l-g
II, 1-3
EiiF¯
we this seqterre:
8
8
5 cc,
. definitims Of
these quantities in
IV,
c. 1-3
10
12
13
Figtre 9.3.
```

<a id="planning-and-coding-066"></a>
## planning-and-coding-066 — 9.8-9.9: double-precision addition and explanatory code (physical page 74); Volume I printed 64

Source: [physical PDF page 74](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=74); reading unit `p074`, lines 10–51.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-065](#planning-and-coding-065), [planning-and-coding-067](#planning-and-coding-067)

```text
64.
If both var iants (+ -) are to be in tte (which is
1 ikely to be the case, if they are reeded at all), their 7-13 can be campon. Indeed
1 1-13 are likely to occtr in otter ccxied sequenæé, too. So tte two variants are
likely to require togettpr 18 to 21 wcrds.
durations my be est irated as fol
l: 125 u, II: 125 u, Ill: 125 u, 'V: 150 u.
Total: I + (II Ill) + (125+ 125+. 150)
TO slim up:
The double precisim addition ard subtraction can be provided by
instructions which require 18 to 21 words, i.e. about of total (selectron)
capacity. operatims last m each.
These seqtEræs are comparable to A. l, A. 3 h A. 3 A.I S in
the case Of ordinary precisim, which constme 125 Thus double precision
addition amf subtractim by a factcr 3.2. TIP factT is actually sl ightly
higher, because the double precision system, as descr ibed abwe, is less flexible
than the a-dinary ore. Fbs•ever, as rent iored previously, there are Var ious ad
hæ nethcds to its flexibil ity, but do not propose to disctss tiprn Ypre.
9.9 corsider the multipl icat im:
Problem 9.
The (double m•ecision) nurrbers a, b are sta•ed in two given pairs Of
nerory læatiors. Fcym ab (also double precision) and stæe it at anot.ter, also
given, rremry location.—
As in 9.8, let a be stred at A. 1,2, b at A.3,g. It is mre convenient
to direct ab, wtpn firmed, to Denote again tFp first arri the parts of
a, b, ab by i, 'b, äb and ä, b, åb, respectively.
The multipl ication Tder (II, Table II) rultipliés two digit
quantities u, v by foemirg a 78 digit prodnct w. Tte sign and fre digits 1-39
are fcræd in accumulatcr, while the digits 40-78 (with a sign digit O) are
fa•red in register. T?ese are, of course, and respectively, as we
defired t.'em abwe. They are, hoever, stlbject to a subseqtent (round off)
Tdificat ion, as descr ibed in, ard discussed in conrect ion with, the multipl icat ion
order referred to abwe. We denote therefæe actual contents of the acctnu-
latcr and of register by and by is, Of cotrse, the quantity which
derated by IN in all past discuss ipns (as well as in all future discussims,
Outside this paragraph), prodlrt rounded to 39 digits, 5tTed in acctnu-
lator. Nag, ho€e r, it is recessary to 1Txye precise, to discrimirnte
between IN, W, w.
It is clear, that äb is essentially Äj, and is essentially
b + Ft + a. only things that these expressims do not account fcy, are
the carr ies in ab fran digit to digit 39. It is easily seen, these, too,
are caw letely accaJnted fa- by the follc»ing fcrmtllae:
```

<a id="planning-and-coding-067"></a>
## planning-and-coding-067 — 9.9-9.10: multiplication diagram, explanatory code and qualifications (physical page 75); Volume I printed 65

Source: [physical PDF page 75](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=75); reading unit `p075`, lines 21–59.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-066](#planning-and-coding-066), [planning-and-coding-068](#planning-and-coding-068)

```text
It should again be rerembered, that al tnese relat ions nwst be interpreted
mdulo 2, ard that tip pxitimal valle of a sign digit is 20.
can no.' drae/ flag diagram, as sha€n in Figure 9.4. There
will again be sare trarsient storage in the accunulata-, as as in A. 3, 4.
Sirte have discusæd similar situations in previous Pr±lens, we reed not
go no,' into this fully.
static ceding Of boxes I-XVI There will be Ore
deviat ion frm schere irriicated in Figtre äb is f Tred in X, tErx:e
at tte sane tire becares available. Sirrei b will be reeded in XVI,
will stcre it after X. Since A. 3 is reeded after X solely for tye
ptrpose it, can reffKve b, aryd st«e in A. 3.
(to Ill, l)
(2)
(3)
(5)
(6)
c.2
c.3
Wiere
€2
wtere Eo
wyere E.
wyere E 6
65.
is the sign digit Of a
is sign digit ofäb ,
is tte sign digit of + v,
is the Sign digit Of a
is sign digit of w + z ,
2-09 -€4
11,2
(to
c.2
c.3
(to IV,I)
IV,I
(to VI, l)
(to VII,I)
Ac
```

<a id="planning-and-coding-068"></a>
## planning-and-coding-068 — 9.9-9.10: multiplication diagram, explanatory code and qualifications (physical page 76); Volume I printed 66

Source: [physical PDF page 76](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=76); reading unit `p076`, lines 6–35.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-067](#planning-and-coding-067), [planning-and-coding-069](#planning-and-coding-069)

```text
66.
FIGURE 9.4
2¯3S
2
—2
2
3
2
3
3
3
A.
o:
2-93
+ Ere
5
7
4
2
3
5
a -as(-q e
3
3
¯ S E ¯ 32
2-
2-3 + E
2-33 2
3
2
```

<a id="planning-and-coding-069"></a>
## planning-and-coding-069 — 9.9-9.10: multiplication diagram, explanatory code and qualifications (physical page 77); Volume I printed 67

Source: [physical PDF page 77](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=77); reading unit `p077`, lines 4–35.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-068](#planning-and-coding-068), [planning-and-coding-070](#planning-and-coding-070)

```text
VI,I
c.2
c.3
(to VII,I)
VII, I
VIII, I
to IX, l)
VIII
(to X, l)
c.2
c.3
A.S
Xl,l
(to Xl l, l)
Xl,l
(to XIN, l)
xn, I
c.2
(to Xitt, l)
XIII,I
XIV,I
(to xv,l)
XIV
(to xvi,l)
w
xv,l
(to XVI, l)
c.2
c.3
—€2) 2¯sø
—€2 + E, —€0 +2¯9ø
—€2 +ea —e J +2¯sø
```

<a id="planning-and-coding-070"></a>
## planning-and-coding-070 — 9.9-9.10: multiplication diagram, explanatory code and qualifications (physical page 78); Volume I printed 68

Source: [physical PDF page 78](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=78); reading unit `p078`, lines 12–161.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-069](#planning-and-coding-069), [planning-and-coding-071](#planning-and-coding-071)

```text
68.
XVI,I
Ac
2
A.3
3
0-1
9-11
22'-24
26 27
28 - 31
18 -m
33 - 35
A,
26 cc
31 S
h,
17 cc
32 s,
h,
34 h-
20 CC
34 h-
32 h
32 s, 30
34 h-,
31 s
2-0 e
32 s
B
h
s
c
(-81 —€2 +Ea
Note, that the boxes VIII and XIV required no herre tipir
irmediate successcrs (X, I and XVI,I) must directly upm their irmed iate
predecessors. Hasever , ttese two bcxes have actual ly no irmediate pre&cessors,
VIII, I and XIV,I appear in the Cc cyders VII, 2 ard X 111,2. I-Eme they must be
replaced there by X, I and XVI,I .
The or±rir9 Of the boxes is l,
Ill, IV, VI, VII, 11, X, XII, XIII, XV
XVI; II; V; Xl (VIII and XIV mitted, cf. abode ) , ard IV, VII, X' II must also be
the imediate successæs af II ; V, Xl, respectively. This recessitates the extra
cyder s
11,4
v,3
Xl,3
cc
VII, I
cc
XIII,I
We must
nad assign A. 1-4, 9, C. 1-3 their actual vanes, pair the SS
II, , IV, 1-3, V, 1-3, VI, 1-6, VII, 1-2, IX, 1-5, X, 1-5,
cyders l,
1-3,
II, 1-3, XII, 1-6, XIII,
their actual
va ues.
1-2, XV, 1-5, XVI,l-4 to 28 words, arri then assign -
These
l, 1-3
o
2
3
14
s
6
7
8
9
are expressed in this table:
IX, 1-5
x, 1-5
XIII, 1-2
xv, 1-5
XVI,IA
this ccfrd seqlpme:
v, 1-3
, 1-3
A. 1-4
B
c. 1-3
24
25
26
27
29
31
32
33
34
35
32
31 h
31 s
28 R
22
30 x
31
h,
31 s
32
h,
31
35
32 s ,
we
31 x
, 34 h—
35 -
29 R
35 -
32 s
31 s
32 h
28 R
It
Obta i n
12
13
16
18
19
20
21
22
23
30
31
31 s
32
31
35
32 h
33
30 s
35 -
32 s
31 s
30 s
cc',
3
31 h
is likely that this will be stored in rrerm•• together with the
two var iants (+ and of 8. Herte 2E31, 33-35 Of this code can be cormon
12, reskctively, in the ccxie of • that xoblem. Also, 32 is
with 7-10, 13, II,
ikely to occur in otter coded seqoerces, foo. So this pr&lem IS likely to require
2B Or 29 additional wcrds.
```

<a id="planning-and-coding-071"></a>
## planning-and-coding-071 — 9.9-9.10: multiplication diagram, explanatory code and qualifications (physical page 79); Volume I printed 69

Source: [physical PDF page 79](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=79); reading unit `p079`, lines 8–45.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume I. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-070](#planning-and-coding-070)

```text
69.
The durations nay be est ineted as folloes:
l: 195 g, II: 150 u, Ill: 150 u, IV•. 195 g, V: 125 u, VI: 225 VII: 75 u,
'X: 200B, X: 250 Xl:
125 g, xn: 225 u, Xlit: 75 u, XV: 200 g, XVI.• 150 u.
Total: I + (l) t II) IV + (V Or VI)+ VII + (nothing IX) + X +
+ (Xl XII) + XIII + (nothing + XVI
average = (195 + 150+ 195 + 175 + 75+ 100 + 250 + 175 + 75 +
+ 100+ 150) 1,640 u r 1.6 m.
TO sum up:
Tte double precision multipl ication can prwided by instructions
which require 28 Or 29 bords in addition to thæe required by Problem 8 (dothle precision
addit ion and subtract ion) i.e. about an additional Of the total (selectron) rterÜY
capacity. operation lasts I m.
This seqtence is carvarable to A. I R, A.3 x, A. 3 S in case Of
precision, which cmstre 195 Thus the double prec isim sloqs multipl i-
cation by a fact« 8.4. In contrast with the situation descr ibed in conrection with
the precision addition aM subtract ion (cf. the erys cf 9.8), there is probably
no signif icant loss of flexibil ity involved in the present case.
9. IO Div is ion offers no part icular diff icult ies.
In a-der to ±tain a
dotble precision quotient Of a (represented by ä, i) by b (reresented by G, G) my
a a , by fcrmirg
first napprcx irreten &sired double precision quotient q
, and then refire the result by any ore of several
rdirzry precisiM qwtient qo
kno€n mthods. availabil Ity Of double %ecision addition, subtraction, ard
multipl ication rakes these ratters quite simie. do not propcse, ho•æver, to go
fwther into this subject.
my surmørize tte results M 9.8 aM 9.9 as follcys:
Double precision arithTtics, carer ising add ition, subtract im
multipl ication, can be provided by ions which require 146 to 50
i.e. 1.2% of the total (selectron) rrerr«y capacity. to trese charges addition
arxi subtraction are sloqed by a factr 3.2 ard multipliafim by a factcr 8.g, in
catVar ison to precision ions. Fur tterr«e tyere• is a certain I æs
in flexib il ity Of gse Of the two f irst rent Wed iOrs. It seems
tyerefore reasoreble to ex*ct an overall, average sloaing by a factæ between
6 8 in carpar ison to Ordinary precision cperations.
```

<a id="planning-and-coding-072"></a>
## planning-and-coding-072 — Volume II introductory remark: revised machine notation and unchanged uses (physical page 89)

Source: [physical PDF page 89](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=89); reading unit `p089`, lines 4–29.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-007](#planning-and-coding-007)

```text
INTRODUCTORY REMARK
We found it convenient to make scyræ minor- changes in the positioning of
the parts of all orders of Table II, and in the specific effect of two among then.
First:
We determine that in each order of Table II the rrMtÜry position
number x occupies not the 12 left-hand digits (cf. the second ranark Of 7 . 2, cf. also
8.2), but the 12 right-hand digits. I.e. the digits 9 to 20 or 29 to 40 ( frcxn the
left) for a left-hand or a right-hand order, respectively.
Second: We change the orders 18, 19 (the partial substi tution orders xSp,
xSp' ) , so that they substitute these new positions, and these crosswise.
I.e. 18
replaces the 12 right-hand digits of the left-hand order located at x (i.e. the digits
9 to 20 [from the left)) by the 12 digits 29 to 40 the left) in the accw•nuiator.
Similarly 19 replaces the 12 right-hand digits of the right-hand order at x
(i.e. the digits 29 to 40 (from the left]) by the 12 digits 9 to 20 ( frcxn the left)
in the accmmlator.
For the standard f a-m of a position mark, x
— 2- I g x + 2- 3 ax, as intro-
duced in 8.2, these changes compensate each other and have no effect. Iberefore all
the uses that we made so far of these orders are unaffected.
(h the other hand the new arrangernent permits certain arithmetical uses
of these orders, i.e. uses when the position x is not occupied by orders at all, but
when it is used as ( transient) storage for numbers. In this case the new
provides very convenient 20-digit shi fts, as well as certain other manipulations.
mse things will appear in mre detail in the discussion innediately preceding the
static coding in 10.7.
```

<a id="planning-and-coding-073"></a>
## planning-and-coding-073 — 10.1-10.3: integration examples and rationale for illustrative coding choice (physical page 91)

Source: [physical PDF page 91](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=91); reading unit `p091`, lines 12–44.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-074](#planning-and-coding-074)

```text
10.0
10.1
CODING OF SOME SIMPLE ANALYTICAL PROBLEMS
We will code in this chapter two problems which are typical
constituents of analytical problens, and in which the apprcximation character of
procedures is particularly emphasized. This is the process of numerical
integration and the process of interpolation, both for a tabulated one-variable
function. lhth problems allow a considerable number of variants, and we will, of
course, make no attempt to exhaust these. We will nevertheless vary the formulations
sonewhat, and discuss an actual total of six speci fic problems.
10.2
We consider first the integration problen.
We assunE that an integral z)dz is wanted, where Che function f (z)
is defined in Che z-interval O, l, and assumes values within the range of our machine,
, size < l. Actually f (z) will be supposed to be given at N+l equidistant places
in the interval O, l,
, the values f (h,m), h O, l, , N, are tabulated. We wish
to evaluate the integral by numerical integration forinulae with error terms of the
order of those in Simpson's fomula, i.e.,
niis is a method to derive such fomulae. Consider the expression
(1)
h+Fu
h-Fu
L (f(bål) - 2f(b) + ]
lhere will be h = O, l, .
Simple calculations, which we need not give here explicitly, give
CV(O) q (O) = O (indeed = O and for = I even = O), implying
(2)
•C u) = dul du du3
and further
(3)
_ + f'i(b.zu,']
3
```

<a id="planning-and-coding-074"></a>
## planning-and-coding-074 — 10.1-10.3: integration examples and rationale for illustrative coding choice (physical page 92)

Source: [physical PDF page 92](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=92); reading unit `p092`, lines 19–51.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-073](#planning-and-coding-073), [planning-and-coding-075](#planning-and-coding-075)

```text
-2-
(3) transforms into
(4)
Putting
Mff"' = Max
we see that (4) yields
(5)
and by (2)
(6)
- 2E)
3
30
Putting u l, and recalling we find:
_ - 2f(b) ? ]
f(z)dz ¯
(7)
Mff"'
(7-6k)
90
kitting E
= I and sunning over
k-Å>O and even) we get Simpson's formula:
h -1+1,
h - 1+1, 1+3
N,
(8)
Mflu,
90
f(t) + 4f(EL) + 2f(E2) + + +
+ 4f(kd) + + + f(k)
N
N
180 N'
```

<a id="planning-and-coding-075"></a>
## planning-and-coding-075 — 10.1-10.3: integration examples and rationale for illustrative coding choice (physical page 93)

Source: [physical PDF page 93](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=93); reading unit `p093`, lines 12–52.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-074](#planning-and-coding-074), [planning-and-coding-076](#planning-and-coding-076)

```text
(9)
-3-
= h and sunning over h = 1+1, X+2, .
Putting E
and of any parity)
we get the related fornala:
+ 22f(h) +
= [f(EL) + f(E2) + + f(EL)]
180
180 N'
We evaluate first by Simpson's fomula, i.e., by (8),
10.3
and in
order to simplify matters we put X = O, k = N. Hence N must be even in this case
PROBLEM Io:
O. l, is given to the eQtent that the values f(h/N),
The function f(z), z in
p It is
consecutive locations p, p+l, ,
O l, N, are stored at N + \
desired to evalu4te the integral J f(z)dz by means of the formula -
We could use either form of s right side for this evaluation. Using
the first form leads to an induction over the odd integers h 3, ,N-I, but requires
at each step the preliminary calculation of the expression
+ 4f(h/N) + f ( (h-I)/N) Using the second form leads to an induction
, N. and requires at each step the simpler expression
over the integers h O, l,
= or I or 2. This factor is best handled by
] multiplied by a factor
variable remte connections. A detai led comparison shows that the first method is about
rmre efficient, both regarding the space required by the coded sequence and the time
consurred by the actual calculation. We will nevertheless code this Probletn according to
the second method, because this offers a good opportunity to exemplify the use of vari-
able rerrnte connect ions.
the expression to be cauputed is
for
for
2
h O, N and
even
h odd
```

<a id="planning-and-coding-076"></a>
## planning-and-coding-076 — 10.1-10.3: integration examples and rationale for illustrative coding choice (physical page 94)

Source: [physical PDF page 94](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=94); reading unit `p094`, lines 7–35.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples and surrounding rationale of external explanatory notation, diagrams, and parallel coding columns. Mathematical and storage details retain the assumptions and dependencies of those representations.

Transcription/context notes: Read from physical page. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and other diagram topology. The original PDF remains necessary for the visual representation. No claim that these external explanations are inline source comments.

Related: [planning-and-coding-075](#planning-and-coding-075), [planning-and-coding-077](#planning-and-coding-077)

```text
Ibis urK)unts to the inductive
de fini ti m
2
f(b) for h = ,
Let A be the storage area corresponding to the interval of locations
from p top + N. In this way its positions will be A. O, l, where A. h corres-
ponds to p + and stores f(h/N). These positions, however, are supposed to be
parts of sortE other routine, already in the machine, and therefore they need not
appear when we pass (at the end of the whole procedure) to the final enumeration
Of the cded sequence. (Cf. the analogous situation in Problan 3.)
Let B be the storage area which holds the given data (the constants)
of the problem p, N. (It will actually be convenient to store p, N as Po,
(p4N-1) ). Storage will also have to be provided for various other quantities
it is ccmvenient to store 2Ä; the exi t-locations of the variable rernote
connections), these too will be accmodated in B. Next, the induction index h
must be stored. h is really relevant in the canbi_nation p + h, which is a position
mark (for A. h, storing f(hÄ)), so we will store (p+h)o instead. (Cf. the analo-
gous situation in Problem 3.) Ibis will be stored at C. Finally the quantities
which are processed during each inductive step will be stored in the storage area
D.
These things being understood, we can now draw the flu diagram, as
It will prove to be convenient to store (2/3N) f (hay)
shown in Figure IO. l.
after II as well as Ch (2/3N) f(hß) after Ill and IV (but not after V) not at D. 2,
but in the accumalator, and to transier it to D. 2 in VI only (but also in V). 'lhe
disposal of at, shun in IX, VIII, VI will be delayed until X, and they
will be held over in the accurmlator. Finally, the transfer of (A. h +1) into C is
better delayed fran X until after the Cc order in Xl, whereby it takes place only
On the - branch issuing frun XI, but this is the only branch on which it is needed.
```

<a id="planning-and-coding-077"></a>
## planning-and-coding-077 — 10.3-10.4: integration flow diagram and explanatory code (physical page 95; Volume II printed page 5)

Source: [physical PDF page 95](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=95); reading unit `p095`, lines 31–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-076](#planning-and-coding-076), [planning-and-coding-078](#planning-and-coding-078)

```text
10
1
+Ehfif(F) eoD.1
C (A.OI
6
8
8
-5-
6
FIG u RE
* O, N and even
4
6
8
8
to D Z
Ck-(N-1))
10.1
```

<a id="planning-and-coding-078"></a>
## planning-and-coding-078 — 10.3-10.4: integration flow diagram and explanatory code (physical page 96; Volume II printed page 6)

Source: [physical PDF page 96](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=96); reading unit `p096`, lines 44–74.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-077](#planning-and-coding-077), [planning-and-coding-079](#planning-and-coding-079)

```text
The static coding of the I-XI foilws:
(at)o
11,5
11,3
(to 11,1)
11,1
11,4
111,1
(to VI, 1)
(to VII, 1)
VI,2
(to X, l)
VII, 1
vil , 2
(to VIII, 1)
VIII, 1
11,5
11.3
p+h
( ÉN—I) o
(d2)o
Sp
Sp
c
Ac
(at) o
— f(h)
(ca)o
(p+h)o
(h-(N-I))
(C2)o
```

<a id="planning-and-coding-079"></a>
## planning-and-coding-079 — 10.3-10.4: integration flow diagram and explanatory code (physical page 97; Volume II printed page 7)

Source: [physical PDF page 97](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=97); reading unit `p097`, lines 4–71.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-078](#planning-and-coding-078), [planning-and-coding-080](#planning-and-coding-080)

```text
c
2
3
4
2
X1,3
4
5
6
7
(to 11, 1)
16 - 16
17 - 17
IX.1 2
9'- 13
11, 1-5
3-5
18 - 25
13'- 14
111,1,
14'- 15
HI, 1-3
, 1-2
27 -28
11,5
c
c
c
Sp
S
s
11,5
Ac
Ac
Ac
Ac
Ac
Ac
c
Jh-l
Jh-l
(p+h)o
Note, that box IV required no coding, hence i ts imediate successor (VI, l)
must follow directly upon its i mediate predecessor. bbwever, this lox has actually no
innediate predecessor; IV,I corresponds to Hence it be replaced there by VI, l.
111, VI, X, M; V, VII, VIII; (IV
ordering of the boxes is l, II;
omitted, cf. atove) and X, X. II must also be the in-rnediate successors of VIII, IN, XL,
respectively. Ihis necessi tates the extra orders
VIII, 2
IX,2
X1,8
11,1
CQ, correspond to Ill, l, VI. I (instead of IV,I), V, l.
In the
final enumeration the three a's rmst obtain nurrbers of the sane parity. This may
necessi tate the insertion of dunny (ineffective, Irrelevant) orders in appropriate
places, which we will mark
must now assign B. 1-8, C, D. 1-2 their actual values, pair the 35
orders 1.1-6, 11.1-5, 111,1, V, 1-2, VI,l-2, HI, 1-3. VIII ,1-2, 1-2, X, 1-4, Xl, 1-8
to 18 words, and then assign l, I-XI,8 their actual values. These are expressed in
this table:
1.1-6
X1,1-8
v, 1-2
VIII, 1-2
b. 1-8
26
```

<a id="planning-and-coding-080"></a>
## planning-and-coding-080 — 10.3-10.4: integration flow diagram and explanatory code (physical page 98; Volume II printed page 8)

Source: [physical PDF page 98](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=98); reading unit `p098`, lines 4–79.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-079](#planning-and-coding-079), [planning-and-coding-081](#planning-and-coding-081)

```text
NOW we
obtain
18
27 S
23 h-
19
26 s
20
26
21 x
17
28 s
27
27 s
VIII: 75
this
10
11
12
13
14
15
16
17
18
19
coded sequence:
5
Sp
4 Sp
5
Sp
28 h
26
The' durations
1: 225 u, 112 270 u, 111:
25 h
28 s
23 h
24
20
25 h
26
26 s
26
20
22
23
24
25
26
27
28
130
(p+N-1)
may be estimated as
30 u, V: 55 u, U: 75 u: VII: 125 J,
[X: 75 u, X: 150 u, XI: 300 u.
1 + 11 x (N+l) + 111 x 2 + VI x (N +1)
Total:
+ VIII x (N -1) + IX+(X + xn x(N+1) -
+ (V + VII)
= (225 + 270 (N+l) +60 + 75 (N+l) + + 75 (Y-I) + 75 + 450 (N+l))
(885 N + 1080) (.9N + 1.1) m.
10.4
We evaluate next by the formula (9), and this tirre we keep X, k
general. We had X, k
and k-X>O. This excludes k O as well as X N.
It is somewhat mre convenient to write X-I for X.
Thus (9) becones
( 10)
180 NE
180
Finally the requirerrent k-Z?O may be
Then X, k = X, and
dropped, since for k-X$ O
```

<a id="planning-and-coding-081"></a>
## planning-and-coding-081 — 10.4-10.5: second integration method and annotated orders (physical page 99; Volume II printed page 9)

Source: [physical PDF page 99](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=99); reading unit `p099`, lines 19–51.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-080](#planning-and-coding-080), [planning-and-coding-082](#planning-and-coding-082)

```text
_9_
N and X, k
. , N are subject to no further restrictions.
We state accordingly:
PROBLEM
Sane as hoblem IO, with this change. It is desired to evaluate the integral
interchange Z, k).
The expression
, ...,N) by means of the formula (IO) (for k for k < Z
to be computed is
where J'
then
and
for
is defined as follows: Rat
k
24N N
k
for k < X
Ihe last equation amunts to the inductive definition
o,
f(h) ,
"lhe storage areas A, B, C, D and the induction index h will be treated the
Sarre way as in Problem IO, but h runs now over , l,
We can now draw the flow diagram as shown in Figure 10.2.
It will be found
convenient to store the contents of E. 1-2, (p+kl )
, (pen )
in the same place where
(p+X) are originally stored, which proves to be a. 1-2. simpli fies II
and reduces tke mmry requiren*nts, but since we wish to have B. 1-2 at the end of
the routine in the sare state in which they were at the beginning, it requires restor-
ing B. 1-2 in IX. VIII, on the other hand, turns out to be entirely unnecessary.
```

<a id="planning-and-coding-082"></a>
## planning-and-coding-082 — 10.4-10.5: second integration method and annotated orders (physical page 100; Volume II printed page 10)

Source: [physical PDF page 100](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=100); reading unit `p100`, lines 19–31.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-081](#planning-and-coding-081), [planning-and-coding-083](#planning-and-coding-083)

```text
C (A.t')o
1
-10-
C (A.A+I).
FIGURE 10.2
D
o
(A.k'Z• C4.Kl GEA
4
4
4
D J"Jx,_
4
```

<a id="planning-and-coding-083"></a>
## planning-and-coding-083 — 10.4-10.5: second integration method and annotated orders (physical page 101; Volume II printed page 11)

Source: [physical PDF page 101](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=101); reading unit `p101`, lines 49–78.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-082](#planning-and-coding-082), [planning-and-coding-084](#planning-and-coding-084)

```text
The static ccxiing of the I-IX follows:
(p+k)o
11.1
(to 111, 1)
11, 1
111,
111,7
(to V, l)
(to VI,I)
VI,4
VII, 23
(a2)o
VII, 23
VII,I
VI,3
p+h
Sp
vlI.23
VII,23
Ac
VI,3
(ar)o
(p+k)
(p+k)
(p+k)
(p+it )
(p+Zt )
(p+h)
(p+h)
f(h)
```

<a id="planning-and-coding-084"></a>
## planning-and-coding-084 — 10.4-10.5: second integration method and annotated orders (physical page 102; Volume II printed page 12)

Source: [physical PDF page 102](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=102); reading unit `p102`, lines 17–66.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-083](#planning-and-coding-083), [planning-and-coding-085](#planning-and-coding-085)

```text
VII, 1
VII,9
10
11
12
13
14
15
16
17
19
20
21
22
23
VI,8
(to V, l)
f(Ld) _
VII,17
VII, 16
-12-
Ac
Ac
VII,6
VII,5
(p+h+l)
(p+h+l)
VII,6
VII,5
p+Z1 -l
VII,17
VII, 16
p+kl-l
s.
Sp
Sp
h-
Sp
Sp
c
s.
Ac
Ac
- f(L)
-L (f(Z-d)
24N
24N
(p+k'-l)
24N N
24N N
```

<a id="planning-and-coding-085"></a>
## planning-and-coding-085 — 10.4-10.5: second integration method and annotated orders (physical page 103; Volume II printed page 13)

Source: [physical PDF page 103](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=103); reading unit `p103`, lines 4–72.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-084](#planning-and-coding-084), [planning-and-coding-086](#planning-and-coding-086)

```text
VIII
(to e)
2
3
4
5
6
7
8
9 _ 13 t
parity of LX,I, I.e., to
s
s.
-13-
Ac
Ac
Ac
Ac
(p+X)
(p+k)
(p+X)
(p+kt)
(p+Zl)
(to e)
Note, that the box VIII required no coding, hence its in-mediate successor
(e) mst follow directly upon its immediate predecessor. However, this box has actually
no it-mediate predecessor; VIII, I corresponds to at, which may appear (by substitution at
11,2) in the C order VII, 23. Hence VIII, I must be replaced by e in at. •
'lhe ordering of the boxes is l, Ill, I V, V, VI; II; VII; IX (VIII omitted,
cf. above), and TV, V, e mast also be the irmediate successors of II, VI, [X, resvectively.
Ihis necessitates the extra orders:
11.3
VI, 10
LX,9
IV,I
c
i.e., to e (cf. above), corresponds to n, l.
corresponds to VIII, l,
This implies, as in the corresponding situation in Problem IO, that IX,I and e must have
in the final enumeration numbers of the same parity. need not be considered, since i t
represents a fixed rermte connection and therefore does not appear in the above detai led
coding.
s. I their actual values, pair the 63 orders
We nmst now assign B. 1-8, C, D,
1, 1-3, 11, 1-3, 111, 1-8, IV,1-4, V, 1-3, VI, 1-10, VII, 1-23, [X, 1-9 to 32 words, and then
are expressed iri this table:
assign I , I-IX,9 their actual values. These
1, 1-3
111, 1-8
n', 1-4
v, 1-3
e is supposed
32 - 39
40
41
42
to
0-1
51-7
have the
VI, 1-10
11, 1-3
VII, 1-23
rx, 1-9
b 1-8
14 - 15
15 t _
27 - 31
be unprimed.
```

<a id="planning-and-coding-086"></a>
## planning-and-coding-086 — 10.4-10.5: second integration method and annotated orders (physical page 104; Volume II printed page 14)

Source: [physical PDF page 104](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=104); reading unit `p104`, lines 4–113.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-085](#planning-and-coding-085), [planning-and-coding-087](#planning-and-coding-087)

```text
41 s
R,
41 h
40
40 s
33 h-
32
33
42
33
36
40
15 cat
10 sp
37 x
41 s
38 h
42 s
32 s
33 s
38 h-
18 sp
17
39 x
41 s
23 Spt
23 sp
32 h-
42 R
10
41 h
11
41 s
12
41 s
13
Now we obtain
32
14 cz,
42 s,
32 s,
33 s, 35
26 sp',
40 s,
this coded
14
15
16
17
18
19
20
21
22
23
24
25
26
27
sequence:
34
5
42
41 h
32
38 h
39 x
26 Spl
33
42
42 s,
41 - ,
29
30
31
33
34
35
36
37
38
39
40
41
32
33
42
(p+k)o
(p+X)c
270
24N
1: 125 u,
Ihe durations may be estimated as follows:
11: 125 4, 111: 300 u, IV: 150 u, V: 125 g, VI: 445 g, VII: 1015 u, n: 350 g.
1 + (11 or 111) + (Ik-xl +1) + VI x + VII + (VIII or IX)
Total:
rnaxirrmm (125 + 300 + 150 + 125 ('k-XI + e l) + 445 k -II + 1,015 350
(570 Ik-xl + 2,065)
maximum = (570 (IN-I) + 2,065) (570 N + 1,495) u z 6 N + 1.5) m.
We pass now to the interpolation problem.
10.5
Lagrange's interpolation forrmala expresses the unique polynomial P (x) of
degree M-l, which assumes given values at M given places , XM,
respectively:
(1)
P(x) P(XI,
There would be no difficulty in devising a (multiply inductive) routine
which evaluates the right hand sine of (l) directly. Ibis, however, seems inad-
visable, except for relatively small values of M. The reason is that the denominators
are likely to •be inadmissibly small.
```

<a id="planning-and-coding-087"></a>
## planning-and-coding-087 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 105; Volume II printed page 15)

Source: [physical PDF page 105](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=105); reading unit `p105`, lines 11–61.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-086](#planning-and-coding-086), [planning-and-coding-088](#planning-and-coding-088)

```text
-15-
Ibis point my deserve a somewhat more detailed analysis.
From our general conditions of storage and the speed of our arithmetical
organs one will be inclined to conclude that the space allotted to the storage of the
functions which are evaluated by interpolation should (in a given problem) be comparable
to the space occupied by the intervwlation routine itself. latter amounts to about
100 words. (Hohlem 12 occupies together with problem 13. a or 1.3. b or 13. c 99 or 101
or 106 words, respectively, cf. 10.7 or 10.8 or 10.9, respectively. Other possible
variants occupy very canparable amounts of space.) (he problem will frequently nse
interpolation on several functions. seems therefore reasonable to expect that each
of these functions will be given at
points.
(Ibis neans that the N ot
10.7 will be
26 not our present M! Note also, that the storage re;ßlired in this
connection is N in Problem 13. a, but 2N in Problems 13 .b and 13. c.)
Hence we may
expect that the points Xl,... , A, *ill be at distances of the order—' 2-6 between
nei ghbors.
• 2-s
Hence
and so
Bj/i)
F j ! (M-i) ! 2-501-1)
The round-off errors of our mul tiplication introduce into all these products absolute
errors of the Tder 2-40
(x.-x•), and with them the
Hence the denominators
jal
corresponding terms of the sum
in are affected with relative errors of the
-5(M-l)
i -l) • Ihe average affect of these
order 2-40.
relatiie errors is best estimated as the relative error
[25M-45
2*1-45
(2(M-1))!
(Äf-2) =
2*1-45
2
the other hand, an interpolation of degree l,
is likely to have a relative precision of the
length
C is a Mderately large numier. (The function that is being
to be reasonablv smoth. )
(NM-I))!
with an interval
where
order
interpolated is
```

<a id="planning-and-coding-088"></a>
## planning-and-coding-088 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 106; Volume II printed page 16)

Source: [physical PDF page 106](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=106); reading unit `p106`, lines 4–47.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-087](#planning-and-coding-087), [planning-and-coding-089](#planning-and-coding-089)

```text
Cmsequently the optimum relative precision € which can be obtained with
this procedure, and the optimum M that goes with it, are determined by these conditions:
. 2-5M
From this
fM
Now we have
(2(M-1))!
3
8• Io-a
4
10—2
5
5
6
1.8•103
7
6•10S
The plausible values of C are in the of M = 5, while M = 6 is somewhat
high and M = 4 and 7 are extremely low and high, respectively. Hence under these
conditions M = 5 (biquadratic interpolation) would seem to be norrnally optimal, with
M = 6 a scmewhat less probable possibility. We have
5
1.4•10-'
6
1.7•lO-e
It follows, therefore, that we rnay expect to obtain by a reasonable
applica€ion of this methcd relative precisions of the order IO - e •v 2-20
Ihis is,
however, only the relative precision as delimited by one particular source of errors:
Ihe arithrretical (round-off) errors of an The ultimate level of pre-
cision of the entire problem, in which this interpolation occurs, is therefore likely
to be a good deal less favorable.
Ihese things be ing understood, it seems likely that the resulting level
of precision will be acceptable in many classes of problems, especially amng those
which originate in physics. There are, on the other hand, nurnerous and important
problems where this is not desirable Or acceptable, especially since it represents
the loss of half the intrinsic precision of the 40 (binary) digit machine. It is
therefore worthwhile to look for alternative procedures.
The obvious nethod to avoid the loss of (relative) precision caused in
Hjfi)
the formula (l) by the smallness of a denominator
(x • is to divide
by its factors x•-x• (j -
l, and j i) singly and successively. This nust,
```

<a id="planning-and-coding-089"></a>
## planning-and-coding-089 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 107; Volume II printed page 17)

Source: [physical PDF page 107](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=107); reading unit `p107`, lines 10–58.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved. The mathematical identity is attributed in this source to A. C. Aitken; its use here is the source authors' discussion.

Related: [planning-and-coding-088](#planning-and-coding-088), [planning-and-coding-090](#planning-and-coding-090)

```text
-17-
however, be combined with a simi treatn•ent of the nunrrators
since
they rnay cause a comparable loss of (relative) precision by the npchanism. A
possible alternative to which eliminates both sources of error in the sense indi-
cated. is
(2)
(2) involves considerably rnore divisions than but this need not be the dcxninant
consideration. There exists, however, a third procedure, which has all the advantages
of (2), and is saTEwhat mre easily handled. its storage and induction prob-
lems ere mre instructive than those of (l) or (2), and for these reasons we propose
to use this third procedure as the basis of our discussion.
This procedure is based on A. C. Aitken's identity
P(XI, PF•••; Ix)
(3)
XM-XI
XM-XI
P(X2. P2
Since (3) replaces an M-point interpolation by two M-l point interplations, it is
It might seem, however, that
clearly a possible basis for an inductive procedure .
the reduction Årtm an M-point interpolation to me-point ones (i.e. to constants)
steps, which would be excessive, since (2) is clearly an M(M-I)
will involve 2
step process. However, (3) remves either extremity (Xl or XM) of the point systan
Xl,... , XM; hence iterating it can only lead to point systems x • ,
M(M+I )
i j, we will write j i+h-l), Of which there are only
2
n ot
2
counting the one-point systems. Hence (3) is likely to lead to saræthing like an
M(M-I)
step process.
2
Regarding the sizes Ve assume that Xl,... , Al as well as x and m, , FM
l. We need, furthem»re, that the differences Xi+h-Xi,
lie in the interval -l,
-l, l, and it is even necessary in view of
x-Xi, Pi+h-pi also lie in the interval
the particular algebraical ra.ltine that we use, Co have all di fferences pi+h-pi
(Cf. VII ,19.) I.e., we
(absolutely) smaller than the corresponding X i -Xi.
nmst use appropriate size adjusting factcrs for the p. to secuFe this 'Livßchitz
ccndition". Ihe sarne nust be postulated for the di fferences P? nf the
intemediate interpolation polynornials. All of this might be circumvented t.o
various extents in various ways, this wcmld lead us deeply into the problerrw
of polynmial interpolation which are not concern here.
We now state:
```

<a id="planning-and-coding-090"></a>
## planning-and-coding-090 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 108; Volume II printed page 18)

Source: [physical PDF page 108](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=108); reading unit `p108`, lines 12–65.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-089](#planning-and-coding-089), [planning-and-coding-091](#planning-and-coding-091)

```text
-18-
PROBLEM 12.
The variable values Xl, • • • •41
xm) and the function va lues
Pl.... , m are stored at two systans of M consecutive memry locations each:
M-l and p, p+l,
. , p*M-l. Ihe constants of the problem are p, q,
M, x, and they are stored at four given menory locations .
It is desired to inter-
polate this function for the value x of the variable, using Lagrange's fornaala.
ne process of rechaction based on the identity (3) is to be used.
It is clear from the previous
family of interpolants
discussion, that we have to form the
(4)
Pi(x)
Xi+h
- Pi+h— 1 x)
for i =
I x) instead of P (XI, Pl
h
Xi+h-Xi
.,M-i+l
Applying (3) to p (x
gl ves
or equivalently
Pi+h
h
Xi+h-Xi
(5)
Ccxnbi n in g
(6)
and
(7)
we have a
locations
pi and x•,
- Pi(x))
this with
tx) Pl(x)
P(x) = P(XI,
(doubly) inductive s&me to calculate p(x).
I-et A and B be the storage areas corresponding to the two intervals of
from p to p+M-l and from q to q+M-l. In this way their positions will be
and B. l, ... where A. i and B.i correspond to p+i-l and q+i-l, and store
respectively. As in the Problens 3, IO, and the posi tions of A and B
need not be shown in the final enurneration of the coded sequence.
primary inducticm will clearly begin with the m, , mi, i.e. ,
p} stored at A, and obtain frcn these p} then from
these the frun these the etc., etc
to
conclude with p} i.e., Kith the desired p(x). Ihese successive stages corres-
pnd to h = l, 2, 3,
respectively. IMs h is the primary induction index.
```

<a id="planning-and-coding-091"></a>
## planning-and-coding-091 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 109; Volume II printed page 19)

Source: [physical PDF page 109](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=109); reading unit `p109`, lines 9–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-090](#planning-and-coding-090), [planning-and-coding-092](#planning-and-coding-092)

```text
-19-
In passing f run h to i.e., from Pl(x), to
, the Pi (x) have to be formed successively for i
This i is the secondary induction index.
' • • • ' M-h+l(x)
There i s clearly need for a storage area C which holds Pl (x) P
at each stage h. As the transition to stage I takes place, each ph (x) will be re-
placed by P! +1 successively for all i = I
M-h. Hence the capacity required
= I the P i (x) p• a e still in A, and
for C is M-h*l during the stage h, but for h
need not appear in C. Hence the maximum capacity for C is M' l. Accordingly, let C
corresvond to the interval of locations fran r to r In this way i ts positions
ph(x). The positions
. , M-l, *here C.i corresponds to r+i-l, and stores
of the area C need not be shcyn in the final enumeration of the coded sequence . All
that is necessary is that they be avai lable (i e . anpty or irrelevantly occupied) when
the instructions of the coded sequence are being carried out by the machine.
As stated above, the occupying C.i have necessarily h > l. To give
more detail: moves into the location C.i at the end of the i -th step of stage
h-l, and remains there during the remainder (the M-h+l-i last steps) of stage h. I and
during the i first steps of stage h.
Further storage capacities are required as Ibe given data (the
constants) of the prcbhem, p, q, r, M, x, will be stored in the storage area D. (It
o, x. ) Storage will a Iso
will be convenient to store than as Po, (q-p-l)
have to be provided for various other fixed quantities (l , the exit-locations of the
variable rerrnte connections), these t m Rill be accocrnodated in D. Next, the two in-
duction indices h, i, will have to be stored. As before, they are both relevant as
position marks, and •it Wi II prove convenient to store in their place (M-h)o, (p+i)
(A. i + V ). These will be stored in the storage area E. Finally, the quanti-
(i.e.,
ties which are processed during each inductive Stép will be stored in the storage area
We can draw the f diagram, as Shown in Figure 10.3. The variable
remte connections a and are necessary, in order to make the di f fering treatments
In the first case the P) (x) are equal to
I and for h I possible:
requi red for h
p, and ccxne frcxn A, in the second case they cane from C (cf. above).
It should be
noted that in this si tuation our flc»• diagram rules imvx'se a rather detailed showing
of the contents of the stcrage area C.
Ihe actual coding cmtains a nurnber of minor deviations frcyn the flow
diagram, inasmuch as it is convenient to rmve a few operations trom the in which
they are shcyn to earlier box. Since we had instances of this already in earlier
problems, •e •ill not discuss it here in detail. Ch the other hand, sane further
condensations of the coding, • hich are possible, but deviate still further from the
flow diagram, will not be considered here.
```

<a id="planning-and-coding-092"></a>
## planning-and-coding-092 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 110; Volume II printed page 20)

Source: [physical PDF page 110](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=110); reading unit `p110`, lines 36–70.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-091](#planning-and-coding-091), [planning-and-coding-093](#planning-and-coding-093)

```text
1
2
-20-
3
and > I
4
(A.Z).t. E z
6
(x) for i Qi
f.ri:if M-h+l
(A.i+l)o
4
(M-h-2)
14 -
to F. I
to F.Z
8
E.I(M-A-I
2
x-XÜÅ
to c.i
- c.i'
fop I '"i
far
* •tx) for i' f, i
for
2 (A.i+2). Z
13
3
for i
8
14
(M-h-l). E.I
6
10.3
```

<a id="planning-and-coding-093"></a>
## planning-and-coding-093 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 111; Volume II printed page 21)

Source: [physical PDF page 111](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=111); reading unit `p111`, lines 14–46.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-092](#planning-and-coding-092), [planning-and-coding-094](#planning-and-coding-094)

```text
-21-
static coding of the boxes I-XI follcys:
D.3
(to 11, 1)
11,1
111, 1
IV,I
(to 111.4)
11,4
(ßl)o
111,6
111,3
IV,3
0.4
0.6
VI,4
Sp
Sp
c
Sp
(at)o
11.4
( 300
111,6
Ac
111.3
PIG)
if reached frcn 111,3
Pl(x) if reached from IV
(p+l)oif reached fran 111,4
(p+i) if reached from IX (i.e. y )
v,2
VI, 4
```

<a id="planning-and-coding-094"></a>
## planning-and-coding-094 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 112; Volume II printed page 22)

Source: [physical PDF page 112](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=112); reading unit `p112`, lines 11–55.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-093](#planning-and-coding-093), [planning-and-coding-095](#planning-and-coding-095)

```text
VII, 1
VII,7
10
12
13
14
15
16
17
19
v11,20
21
22
23
24
25
(to VII. 1)
VII, 14
D.4
VII,25
(q-p-l)o
VII,15
VII,21
VII,14
q+i-l
F.2
q+i-l
(to VIII, 1)
Sp
Sp
Sp
Sp
h-
s
VII,2S
VII, 15
VII,21
(r+i-l)
r+i-l
(q+i-l)
q+i-l
(q+i +M-2 )
(q+i+h-2) o
q+i+h-l
Xi+h-Xi
```

<a id="planning-and-coding-095"></a>
## planning-and-coding-095 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 113; Volume II printed page 23)

Source: [physical PDF page 113](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=113); reading unit `p113`, lines 4–76.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-094](#planning-and-coding-094), [planning-and-coding-096](#planning-and-coding-096)

```text
VIII, 1
2
3
4
5
6
7
(to
2
( to
111,5)
2
3
4
0.5
5
Xl,l
(to e)
( (12)0
2
11,4
( 32
D. IO
XI,3
D. 10
4
111,6
(to 11,1)
h
s
-23-
Ac
Ac
Ac
Ac
Ac
Ac
Ac
Ac
Ac
11,4
111,6
(p+i )
(p+i+h-M+l )
(p+i+h-M) o
(M-h-l)
(M-h-l)
(M-h-2)
(32) o
c
c
111; V. VII, VIII, rx; X;
Ihe ordering of the boxes is l, I l;
VI, and HI, e, II must also be the irmediate successors of VI, X, Xl, respectively,
and 111,4 and 111,5 must be the immediate successors of IV and IX, respectively.
This
necessi tales the extra orders
VI, 6
XI,5
and
VII,I
11,1
111,4
111,5
c
c
c
c
c
[V, l, V, l. VI, l, respectively.
91, correspond to Ill, l.
Hence in the final enumeration Ill, l, [V, I nust have the parity, and V, l,
VI, I mast have the same parity.
```

<a id="planning-and-coding-096"></a>
## planning-and-coding-096 — 10.5: interpolation assumptions, diagram and explanatory code (physical page 114; Volume II printed page 24)

Source: [physical PDF page 114](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=114); reading unit `p114`, lines 16–157.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-095](#planning-and-coding-095), [planning-and-coding-097](#planning-and-coding-097)

```text
Ihese
-24-
We mast now assign D. I-IO, E. 1-2, F. 1-2, g. I
their actual values, pair
35 —37 t
t _ 23
, 1-25
27 _28
IX, 1-3
48 -49
111, 1-6
29 -31 t
50 -51
IV, 1-4
32 -34'
10 -11
49 s
41 h-
42 h-
41 h-, 43 h
the 75 orders l, 1-6
rx, 1-3, x, 1-6, Xl,l
, 11, 1-4, 111, 1-6, V, 1-3. VI, 1-6, VII, 1-25, VIII, 1-7,
are expressed
-5 to 38 words,
in this table:
and then assigl l, I-Xl,5 their final values.
VI,1-6
1, 1-6
II, 1-4
v,l-3
10
n
13
14
15
16
17
VIII, 1-7
x, 1-6
M, 1-5, •
24 -27
Now we
obtain
38
39
41
41
49
43
thi s coded
19
20
21
23
24
25
26
27
28
29
30
31
32
33
34
35
sequen C e :
48 s
42 h
6 Sp
so s
43 h
23 sp'
44 h
21 sp'
h-
18 sp
D. 1-10
E. 1-2
F. 1-2
36
37
39
41
46
47
49
50
51
38 -47
52
36 $ ,
51 s
(M-1)0
160
52 s,
50 h-,
45
52 s
50 h
49
49 s,
42 h-,
29 cc,
50 s,
48 s,
32 cc,
46
47
51
52 +
52 x
42
h
48
51
42
h-
eC
as
11 C'
10 sp',
51 s, 49
41 h-,
42 h-,
49
18 spt',
38 h
42 h,
(q-p-l)o
3SO
'lhe durations may be estimated
1: 225 u, 11: 150 111: 225 u, w: 275 u,
VIII: 275 u, rx: 200 u, X: 225 u, 200
1 + 11 x (M-1) + x (M-2)
Total:
V: 125 u, VI: 225 u, VII: 1140 B,
+ (VII + VIII) WM-I) + + X x (M-1) x (M-2) =
= (225 + 150 (M-l) + 225 + 275 (M-2) + 125 (M-l) + 225
+ 1,415 M(M-I) + 200 + 225 (M-1) + 200 (M-2))
(920 V - 370M- 575) u -z(.9F - .4M- .6) m.
```

<a id="planning-and-coding-097"></a>
## planning-and-coding-097 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 115; Volume II printed page 25)

Source: [physical PDF page 115](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=115); reading unit `p115`, lines 18–65.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-096](#planning-and-coding-096), [planning-and-coding-098](#planning-and-coding-098)

```text
-25-
10.6
be now pass to the problen of interpolating a tabulated function
based on the ccxiing of Lagrange's interpolation forrmla in Probian 12.
PROBLEM 13.
Ihe variable values y l, • • • 'YN (y I <
< m) and the function values
ql,. , Ch, are stored at two systems of N consecutive mermry locatims each:
ä, ävl, —
and ö+l,..
,ö+N-l. •Ibe constants of the problem are F , N, M,
y, to be stored at five gi ven memry locations. It is desired to interpolate this
function for the value y of the variable, using Lagrange's formula for the M points
y. ner est to y.
Ihe probl«n should be treated differently, according to *hether the
b-a
are or are not to be equidistant.
PROBLEM 13. a.
are equidistant, i.e ,
a and b need be stored.
PROBLEM 13. b.
YI, •••DN, are unrestricted.
In this case
'XM equal
1, ,N-M+I
In
amounts to this:
both cases our purpose is to reduce froblem 13 to Problem 12, with
Yk+M_l, and m, equal to qk,... where
to
is so chosen that the Yk,.. . , Yk+M_l lie as close to y as possible.
We consider first Problem 13. a.
this case the definition of k, as formulated at the end of 10.6,
k+M-2
k.=-L (b-a) and Yk*M-l a +
(b-a)
Ihe one of Yk
should lie as close as possible to y . is equivalent to requiring that their
, lie as close as possible to y, i .e... that
2(N-1)
k lie as close as possible to (N-l) -
b-a
There are various ways to find this k k, based on iterative trial and
error procedures . Since we will have to use a method of this type in connect ion wi th
Boblan 13.b, we prefer a different one at this occasion.
Ibis method is based on the function which denotes the integer
closest to z. Ehltting
we have clearly
```

<a id="planning-and-coding-098"></a>
## planning-and-coding-098 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 116; Volume II printed page 26)

Source: [physical PDF page 116](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=116); reading unit `p116`, lines 9–59.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-097](#planning-and-coding-097), [planning-and-coding-099](#planning-and-coding-099)

```text
k•
-26-
for k • S I
for 1 S k $ N-M+I,
N-M+I for k• N-M+I
Now the rnultiplication order (II, Table II), permits us to obtain {z)
directly. Indeed, the round off rule (cf. the discussion of the order in question)
has the effect that when a product uv is forrned, the accunmlator will contain
- 2 g euv - {23 guv).
B (2 aguv), and the arithrnetical register will contain uv -
Hence putting u = 2-3 g (N-l) and v = - will produce 2-3 e {23 euv) 2-39k •
b-a 2(N-1)
in the accumulator.
After k • and k have been obtained, we can utilize the routine of Problem 12
to cornplete the task. This means, that we propose to use the coded sequence 0-52 of
10.5, and that we will adjust the ccxied sequence that Hill be formed here, so that it
can be used in c(lijunction with that one of IO. 5.
Wng the constants of Problem 12 only p, q, and x need be given values
which correspond to the new situation. x is clearly our present y. p, ,p4M-l are
the positions of the m, of Problem 12, i.e. ,
the posi tions of our present
qk,... i.e., they are Fifi-I, , p 4k •M-2. Hence p = Bik-I. q, , q+M-l are
the positions of the Xl,... of Problem 12, i.e.,
the positions of our present
Since we determined in the fornmlation of Problem 13. a, that only
y I = a and b will be stored, but not the entire sequence YI, , m, this means
that the desired sub-sequence Yk,. , Yk+M_l does not exist anywhere ab initio.
Onsequently q may have any value, all that is needed is that the posi-
,q4M-l should be available and ernpty (or irrelevantly occupied) when the
t ions q, .
coded sequence that we are going to formulate begins to operate. Ihis sequence must
then form
and place it into the position q+i-l for all i
It might seem wasteful to form x, first, then store it at q+i-l, and
finally obtain it from there by transfer when it is needed, i .e. during the period
VII, 1-19 of the cded sequence of 10.5. (he might think that it is sirQler to form
in VII, 1-19 as stated above; the quantities
when it is actually needed, i.e.,
) , and thus avoid
needed are more specifically Xi, Xi+h,
in the cmabinatron
Xi+h-Xi
the transfers and the storage.
It is easy to see, however, that the saving thus
effected is altogether negligible, essentially because the size of our problem is
proportional to M2 (cf. the end of 10.5), while the number of steps required in
forming and transferring the x•'s in the first rentioned way is only prorx»rtional
to M . (Remember that M is likely to be 7, cf. the beginning of 10.5.) It does
therefore hardly seem worthwhile to undertake those changes of the coded sequence
of 10.5 which the second procedure would necessitate, and we will adhere to the
first procedure.
```

<a id="planning-and-coding-099"></a>
## planning-and-coding-099 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 117; Volume II printed page 27)

Source: [physical PDF page 117](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=117); reading unit `p117`, lines 5–62.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-098](#planning-and-coding-098), [planning-and-coding-100](#planning-and-coding-100)

```text
-27 -
In assigning letters to the various storage Areas to be used, it be
remernbered chat the coded sequence that we are now developing is to be used in con-
8s a supplement to) the coded sequence of 10.5. Ihe latter
junction Nith (i.e.,
requires areas of various types: D-F, which are incorporated into its final
enurneration (they are 38-51 of the 0-52 of 10.5); A (i.e., p, ,p+M-l), which will
be of our present A (i.e. ,
of F, , F+N-I, i t will be ¯
....,p+k+M-2 ,
(i.e., q, ,
q+M-l), which may be at any available place; and C (i.e.,
which, too, may be at any available place. Iberefore we can, in assigning letters
to the various storage areas of the present coding, disregard those of 10.5, wich
the exception of B, C. Furthermre, there will be no need to refer here to C (of
IO. 5), since the coded sequence of 10.5 assumes the area C to be irrelevantly occupied.
It will be necessary, however, to refer to B (of 10.5), since it is supposed to cm-
Yk+i-l (i =
tain the x •
l, of the problem. We will therefore think of the
letters which are meant to designate storage areas of the coded sequence of 10.5 as
being prinEd. Ihis is, according to the above, an irmediate necessity for B. We
can now assign freely unprinrd letters to the storage areas of the present coding.
Let A be the storage area corresponding to the interval frcxn to
P+N-I. In this way its positions will be A. I , .,N, where A. i corresponds to
F+i-l and stcres q • . As in previous problems, the positions of A need not be
shown in the final enumeration of the c ded sequence.
Ihe given data of the problem are F, M, N, a, b, y, also the q, r of
r at 38,
the coded sequence of 10.5. M, r are already stored there (as (M-l)
and y, too (it coincides with x at 45). q, however, occurs only in with
(as po
(q-ö-k)oat 44) and p, of course, contains
(ö+k-l)o at
k (as (q-p-l)o =
41); end originates in the machine. Hence, 41, 44 mjst be left empty (or, rather,
irrelevantly occupied) when mir present coded sequence begins to operate, and they
rmst be appropriately substituted by its operations. q, however, mast be stored as
one of the cmstants of our present problem. Hence the consta nes requiring storage
(apart from M, r, y which we stored in 0-52, cf. ab cve) are q, N, a, b.
They will be stored in the stcrage area B. (It will be cmvenient to store them as
o, (q-l)o.
We will also need 2 -a e and I ; we will store the
former in B and get the latter frtxn 42.) Ihe induction index i is a position mark;
it will be stored as (qfi-l) (i.e., i) ) in the storage area C. quantities
which are processed during each inductive step will also be stored in the storage
area C.
(FÆ-I)O and
Chr task is to ca lculate k; to substitute po
(q-p-l)
o (ä-ö-k)o
Yei-I from A.k+i-l
into 41 and 44; and then to transfer x• =
to B'. i.
This latter operation is inductive. Finally, the control has t obe sent,
, but to the beginning of 0-52, i.e., to O
not to e
can now draw the f diagram, as shoal-I in Figure 10.4.
```

<a id="planning-and-coding-100"></a>
## planning-and-coding-100 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 118; Volume II printed page 28)

Source: [physical PDF page 118](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=118); reading unit `p118`, lines 32–58.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-099](#planning-and-coding-099), [planning-and-coding-101](#planning-and-coding-101)

```text
-28-
1
1
2 (B'.i)o
3
8
qi
(RO-I)
4
6
(b.'E+1)ø
x
for i
(B.'i+i).
41
(q — F — R). to 44
e'
refers
the B
O of
of 10.5.
o-sz
2
Numbers 0—52 refer to
o-sz
10.6.
FIGURE 10.4
```

<a id="planning-and-coding-101"></a>
## planning-and-coding-101 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 119; Volume II printed page 29)

Source: [physical PDF page 119](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=119); reading unit `p119`, lines 8–64.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-100](#planning-and-coding-100), [planning-and-coding-102](#planning-and-coding-102)

```text
-29-
Ihe actual coding will again deviate in sune minor respects from the flow
diagram, as in previous instences. In connection with this we will also need sarr
extra storage capacity in C (C. l. l).
A matter of smæwhat greater importance is this: We have noted before
that since our machine recoguizes nunbers between -l and I only, integers rmst be
stored in other form. Frequently the form of a position mark, , is per se
more natural than any other (cf. 8.2); occasionally 2-3 e x can be fitted mre easily
to the algebraical use to be made of (cf. I in the present coding); suætin•es
is rrnst convenient. (We of course, add to this list, but the three above forns
seem to be the basic Ones . ) Ihe transitions between these three forms are easily
effected by using rmrltiplications and divisions, but it seers natural to want to
achieve the transitions between the two first ones (I and in a mre direct
way.
This can be achieved by means of the partial substi tution orders 18, 19
of Table II (x Sp, x Spi ) , if they are as indicated in the itmæ-
diately preceding this chapter. We propse to use these orders now for arithnptical
rather than logi cal (substi tution) purposes, for positims x which cmtain no orders
at all, but which are storing numbers in transit. Specifically: With I in the
accumlator, x produces at the position x; with in the accunnJlator
x Sp produces 2-1 G x at the x, and a subsequent x h produces in Che
accumulator.
We mention that — can be obtained frm Io or 2- by dividing them
into or 2-3B, respectively: and this without mre than the usual loss in precision:
Indeed, our division p : O is precise within an error 2-3 e, no matter how small 0 is
(subject, of course, to the condition I c I > Ip ) , provided that p, o are given exactly.
(If they are not given exactly, then their errors are amplified by , F, respectively.
In this case a small o is dangerous, even though 1 01 > p I . ) In the present case
p, O are given exactly. Forming Io, Io, as well as 2-9 e 2-3%, involves no round-
offs.
These methods will be used
in our present coding: For transitions
between Io and 2-3 91, cf. 1,22-23, 111,3-4; VII, 1-3; For forming reciprocals:
from (N-l)o as Io.
in VIII,4-5,
and the very similar case of
f rom
2(N-1)
(M-3)o,
(N-1)0 as (M-3)o: 2(N-1)
in I 9-15. Regarding —
we also note this:
• (N-l)o first and
We need in VIII. We will form
afternrds. Forming I x (b-a) first and [l x (b-A)]: (N-l)o afterwards
would lead to a serious loss of precision, since I x (b-B) plays the role of p
10.5
above. and as it involves a round-off it is not given exactly, and hence
a loss of precision as indicated there.
to
We will have to refer in our present coding repeatedly to 0-52 an
It should therefore be remembered that this coded sequence is now
be changed insofar that 41, 44 are irrelevant and 45 cmtains y. 38,
as in 10.5.
my cause
supposed
43 contain
```

<a id="planning-and-coding-102"></a>
## planning-and-coding-102 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 120; Volume II printed page 30)

Source: [physical PDF page 120](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=120); reading unit `p120`, lines 11–41.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-101](#planning-and-coding-101), [planning-and-coding-103](#planning-and-coding-103)

```text
The static coding Of the I -X folicNs:
(N-L)O
42
10
12
13
14
15
16
17
18
19
20
21
22
23
24
25
2(N-1)
2(N-1)
2(N-l)
2(N-1)
2(N-1)
(M-3)
- 2(N-1)
2-39(N-1)
2-3 h,•
(to 11, 1)
11, 1
2-39
111, 1
```

<a id="planning-and-coding-103"></a>
## planning-and-coding-103 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 121; Volume II printed page 31)

Source: [physical PDF page 121](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=121); reading unit `p121`, lines 19–56.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-102](#planning-and-coding-102), [planning-and-coding-104](#planning-and-coding-104)

```text
(N-1)0
(N-M+I)
2-3Ø(N-M+1)
c 1.1
(to VI l)
(to V, 2)
(to VII, 1)
(to VII, 1)
s.
41
44
(to VIII, 1)
VIII, 1
42
c. 1.1
c. 1.1
10
111, 1
2 ¯3øk 2-3B
VI,
VII, 1
VII,4
VII,7
-31-
Ac
41
44
Ac
c. 1.1
Ac
-N4M-1)
2-39k 2-3Ø(N-M+1)
(F+k-l)
(F+f-l)
(q-l)o
(q-Ö-k)0
(q-Ö-k)c
2-S9(k-1)
```

<a id="planning-and-coding-104"></a>
## planning-and-coding-104 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 122; Volume II printed page 32)

Source: [physical PDF page 122](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=122); reading unit `p122`, lines 6–45.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-103](#planning-and-coding-103), [planning-and-coding-105](#planning-and-coding-105)

```text
-32-
VIII, 11
12
13
14
15
16
17
18
rx, 1)
s.
42
q+i-l
c. 1.1
Sp
IX,6
42
42
(to IX,I)
(q-1)0
(q+i-l)
q+i-l
(q+i)o
(q+i)o
(q+i)o
(q+i-M+l)
(i-M+2)
(i-M+I)
(i-M)O
Note, that the box VI required no coding, hence its inrnediate successor
(VII) rmst folk* directly upon its imnediate predecessor (Ill).
The ordering of the boxes is 1, 11, IV; 111, VII, VIII, rx, X; V and
VII. IX must also be the invnediate successors of V, X, respectively, and V, 2 rmst be
the immediate successor of I V. Ihis necessi tates the extra orders
and
rv,2
VII,I
v,2
As indicated in Figure 10.4
e' is O.
```

<a id="planning-and-coding-105"></a>
## planning-and-coding-105 — 10.6-10.7: combined interpolation routines and notation cross-references (physical page 123; Volume II printed page 33)

Source: [physical PDF page 123](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=123); reading unit `p123`, lines 5–191.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-104](#planning-and-coding-104), [planning-and-coding-106](#planning-and-coding-106)

```text
We trust now
82 orders I, 1-25, II, 1-3,
41 words, and then assigv
tion of the code of 10.5.
contents of C. 1-2, C. 1.1,
53 -65
65
67 - 67
68 -71
111, 1-7
51-52
94 h
50 h-
51
51 s
52 s,
42 h-
42 h-
71 c
52 h-
51 s
51 s
48 s,
68 cc
93 c
38 h-
VIII: 915 u,
-33-
assign B. 1-6, C. 1-2, 1.1, s. 1-2 their actual values, pair Che
111, 1-7, N, 1-2, V, 1-3, VII, 1-9, VIII ,1-18, n, 1-8, X, 1-7 to
l, I-X,7 their actual values. We wish to do this as a continua-
We will therefore begin wi th the number 53. Furthermore the
s. 1-2 are i rrelevant like those of 48-52 there. Hence thev
all
53
54
55
56
57
58
59
60
61
63
64
65
67
be made to coincide with these. We therefore identify them accordingly .
these things up, we obtain the folluing table:
1, 1-25
95
51 s
94
96
52
52 s
51 R
52
97
96
VII, 1-9
VIII, 1-18
rx, 1-8
x,1-7
71 1_75,
76 -84'
85
89 -92
Now we obtain
this
69
70
71
73
74
75
76
77
78
79
80
81
82
83
84
ccxied sequence:
A,
spi
45
96 h
38
51
96
52 x
48
42 h
92
51
98
51
S
51 h
95
51 s
96
50 s
48
S
42
h
50
48
51 h
41 s
99
44 s
94
42
51 X
50 R
97
94 h
99
49 s
85
88
89
91
93
94
96
v,1-3
B. 1-6
c. 1-2
C.I.I
s. 1-2
49
42
48
50
h,
49
99
42 h-,
85 c ,
48 s ,
(q-l)o
Sanming
92 -93
94 _ 99
48 -49
50
87
Sp
49 s
48 s
38
h-
42
h-
so
For the sake
which contains all changes
is 38-52:
of cmpleteness, we restate that part of 0-52 of 10.5
and all substi tutable constants of the problen.
38
39
40
41
42
10
43
44
45
46
47
350
49
50
52
Ihe durations may be estimated as
1: 1,220 u, 11: 125 J, 111: 275 u, W,
u: 300 u, X: 275 g.
fol lcws:
v: 125 u,
VII: 350
```

<a id="planning-and-coding-106"></a>
## planning-and-coding-106 — 10.8: non-equidistant interpolation and explanatory code (physical page 124; Volume II printed page 34)

Source: [physical PDF page 124](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=124); reading unit `p124`, lines 14–66.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-105](#planning-and-coding-105), [planning-and-coding-107](#planning-and-coding-107)

```text
Total:
-34-
1 or (111 + V) or 111) + (IX + X) x M
maximum (1,220 + 125 + 350 + 915 + 575 M)
(. 6M + 3) m.
- (575 M + 3,010)
Hence the cmplete interpolation procedure (10.5 plus 10.7) requires
(.9M2 +.2M + 2.4) m.
10.8 We consider next Problem 13. b. We are again looking for that
k for which lie as close toy as possible (cf. the end
of 10.6), i.e.,
for which the rennter one of Yk and Yk+M_l lies as close to y as
possible.
Since YI, are not equidistant, we cannot find k by an arithrnetical
cri Cerium, as in 10.7. We must proceed by trial and error, and we will ncv describe a
method which achieves this particularly efficiently.
in k =
We are then looking for a k k which minimizes = (y-Yk' Yk*M-l-y)
. ,N-M+I.
LRt us first note this: y-Yk > y-Yk+l, hence y-Yk > Yk_+M-y implies
y-Yk > h +1, and therefore > 11k +1. (h the other hand Yk+M_l-y < Yk+M-y, hence
y-Yk $ Yk+M-y inplies Yk+M-y, and therefore S Hence > or $
Yk + Yk+M- 2y < or O.
according to whether y-Yk > or $ Yk+M-y i.e.,
In order to keep the size betyeen -l and l, it is best to replace
Yk + Yk+M-Y - 2y by
(1)
Yk+M - y
2
2
z is nwnotone increasing in k. nerefore Zk < O implies Zh < O and hence >
fhr all h 'k, i.e., > g > .
> Similarly Zk ? O implies Zh O and
for
$ From these we
hence
i.e., $ $ .
infer
Zk < O implies > k,
(2)
O implies that we can choose $ k.
Consequently we can obtain by "bracketing" guided by the sigl of Zk.
Note that Zk can be forrned for k l, ,N-M only, but not for k = N-M+I.
Ihe "bracketing" must begin by testing the sign of Zk for k
1, if it is + , then E = l,
then we continue. Next we test the sign of Zk for k N-M, if it is - , then
if it is -,
= N-M+I, if it is + , then we continue. In this case we know that I < N.M. [hit
N-M. Gnsider more generally the case where we know. that k t < k S k t
•Ihis implies q-kt l.
If k + k
i- -i = l, then k -k
if k • -k: > l, then we continue.
```

<a id="planning-and-coding-107"></a>
## planning-and-coding-107 — 10.8: non-equidistant interpolation and explanatory code (physical page 125; Volume II printed page 35)

Source: [physical PDF page 125](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=125); reading unit `p125`, lines 11–73.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-106](#planning-and-coding-106), [planning-and-coding-108](#planning-and-coding-108)

```text
-35-
In this case we use the function which denotes the largest integer $ w. Put
(3)
then k > k?.
and test the sign of Zk for k k 9, if it is + Chen k S k.o, if it is -
= ki, ki+l = k? or k; +1
respecti ve ly.
We can therefore put k7+1
'Ihis ccynpletes the inductive step from i to i +1. Sooner or later, say for i = 1
hence ki
hbwever ,
of steps
k; ¯ I will occur, and the process will teminate.
Note, that ki+l-k7+l I(k+
- k7)-l. For i
i , however
-I-ki-1
N -M-l, therefore,
krki
210g (N-M-2) + 2.
, -k.¯ 2 (ki+l-k7+l - l,
krki 20
+1.
ne virtue of this I Ibracketing" method is, of course, that the number
it requires is of the order of 2 log N, and not, as it would be with most
other trial and error methods, of the order of N . (Note, that N is likely to be
large compared to M, which alone figures in the estimates of 10.5 and IO. 7. )
After has been obtained, we can utilize the routine of Problem 12
to cmplete the task, just as at the corresponding point of the discussion of
Proble•n 13. a in 10.7. This means that we propose to use the coded sequence 0-52
of 10.5, and that we will adjust the coded sequence which will be formed here,
just as in IO .7.
The situation with the constants of Problem 12 is somewhat simpler
than it was in 10.7. Again, p, q, and x need be given values which correspond to
p, ,p+M-l and q, ...,q+M-l are
the new si tuation. x is clearly our present y.
the positions of the , RI and Xl, , XM of Problem 12, i.e., the positions of
they are , F+k+M-2 and
our present qk , ,qk+M-l and i •e•
q+k l, ,ä+k+M-2. Hence p = F+k-l, q = ü+k-l. Ihe complicaticms in 10.7, connected
with q, or, more precisely, with the . , YR+M_I, do not arise here, since Problem
13. b provided for storing the entire sequence YI,... , YN•
In assigning letters to the various storage areas to be used, it must
be ranembered, just as at the correspcgiding point in IO. 7, that the coded sequence
as a supplanent
that we are now developing is to be used in conjunction with (i .e. ,
to) the coded sequence of 10.5. As in 10.7, we have to classify the storage areas
required by the latter, but this classi fication nov di ffers sunewhat from that one
in the final enumera-
of 10.7:
We have the storage areas D-F, which are incorporated
tion (they are 38-51 of the 0-52 of 10.5); A and B (i.e.,
p, . and
which he part of our present A and B (i.e., of F, . , F*N-I
and they
, r+M-2), which
, . . and C (i.e., r
and Ä+E-I
*ill be ¯
letters to the
may be at any avai lable place. Therefore, we can, in assi41ing
10.5, with the
various storage areas in the present coding, disregard those of
```

<a id="planning-and-coding-108"></a>
## planning-and-coding-108 — 10.8: non-equidistant interpolation and explanatory code (physical page 126; Volume II printed page 36)

Source: [physical PDF page 126](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=126); reading unit `p126`, lines 8–66.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-107](#planning-and-coding-107), [planning-and-coding-109](#planning-and-coding-109)

```text
-36-
exception of C. Furtheruore, there will again no need to refer here to C (of
IO. 5), since the coded seqænce of 10.5 assunps the area C to be irrelevantly
occupied. We will, at any rate, think of the letters which are neant to desig-
nate storage areas of the coded sequence of 10.5 as being prinpd. We can
assigi freely unprined letters to the storage areas of the present coding.
Let A and B be the storage areas corresponding to the intervals frcxn
to F*N-I and from t-0 In this way their will be A I
and B. l, , N, where A. i and B.i correspond to F+i-l and ä+i-l and store qi and
Yi. As in previous problerrs, the position of A and B need not be shown in the
final enunwration of the coded sequence.
The given data of the problem are F, ä, M, N, y, also r of the coded
sequence of 10.5. M, r are already stored there (as (M-l) ,
ro at 38, 43); and
y, too (it coincides with x at 45). The definitions of p, q involve k (p F+k-l,
q — ä+k-l), and k originates in the (Mchine. Ihe form in which p is stored accord-
at 41); while the form in which q is stored does
ingly involves k (as p
= (F+k-l)o
not happen to involve (as (q-p-l)o— (ä-ö-l) at 44). Hence 41 must be left empty
(or rather, irrelevently occupied) *hen our present coded serpence begins to operate,
and it rmst be appropriately substituted by its operation. 44 might be used to store
(ä-F-l) frun the start, but we prefer to leave it, too, empty (i.e.,
i rre levant ly
occupie8) and to substitute it in the process. Hence the constants requiring storage
(apart fran M, r, y which are stored in 0-52, cf. aEnve) are F, N. niey will
be stored in the storage area C. (It Wi II be convenient to store them as (F-l)
(N-l) . ) The exit-locations of the variable remote connections will also
be accmrrodGted in C. The induction index i need not be stored explicitly, since
the quantities k • , k: , k• contain all that is needed to keep track of the progress
of the induction. (The i i for which the "bracketing". i.e., the induction,
ends, is defined by -k
, cf. above.) k? , k: , ki are position marks, they
(i.e., (B. k?) o, (B.ki)o (B. < ) )
will be stored as
(q+ki-l)
, (Ä+k7-I) ,
in the storage area D. Finally, k, when forned (in the form (ä+k-l)
will be stored in D, replacing the corresponding expression of k • .
The index i runs frun I to i .
In drawing the flow diagram, it is
convenient to treat the two preliminary steps (the sensing of the sign of Zk
for k = I and k = N-M) as part of the sanE induction, and associate them
ideally with tvo values of i preceding i = l, i.e., with i -l and i = O.
-l, O k? may be defined as the value of k for which the sigu of Zk
For i
is being tested (this is its role for i l), i.e., as I, N-M, resErctively;
while k: , ki may rernain undefined for i
, i.e., (B.k) to
Chr task is to calculate k (in the form (ä+k-l)
(ü-ö-l)
into 41 and 44; and finally to
= (F+k-l) and (q-p-l)
substitute p
send the control, not to e, but to the beginning of 0-52, i.e. to O.
We can now draw the flcw diagram, as shown in Figure 10.5.
variable remote connections and are necessary in order to make the differ-
• -l, for i = O, and for i l, possible (cf. above).
ing treatnrnts for
```

<a id="planning-and-coding-109"></a>
## planning-and-coding-109 — 10.8: non-equidistant interpolation and explanatory code (physical page 127; Volume II printed page 37)

Source: [physical PDF page 127](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=127); reading unit `p127`, lines 3–35.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-108](#planning-and-coding-108), [planning-and-coding-110](#planning-and-coding-110)

```text
8
4
1
-37-
. - (B.I)O
. = (B.N-M)0
D.Z
3
3
Z (B.KPC
(B.
41
44
Kio
€0
1
(B.i)o to D.I
3
3
KF)J
D.I (B.kt
13
Note :
D.2 (B.x7)0
J (z.K7)0
ax
-3
refers to O of
0-52 IO.S.
m e O — re fer
to 0-52 in 10.6.
FIGURE
10.5
```

<a id="planning-and-coding-110"></a>
## planning-and-coding-110 — 10.8: non-equidistant interpolation and explanatory code (physical page 128; Volume II printed page 38)

Source: [physical PDF page 128](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=128); reading unit `p128`, lines 12–89.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-109](#planning-and-coding-109), [planning-and-coding-111](#planning-and-coding-111)

```text
-38-
Regarding the actual coding we make these observations: Since E , k •
-l, O, therefore the contents of D.2, 3 are irrelevant for
are undefined for i
-l, O (cf. the storage distribu ed at the middle bottom of Figure 10.5). Ihe
in X, with k? (kt+k7) , is best effected by detouring over
forming of (B. k?)
the quantities 2 -a 9 (+9-1), 2 - 30(ä4k7-l), 2-ae(ä+kt-l), because the operation m =
is rmst easily performed with the help of 2-3%), 2 - un: Indeed the right-shift R carries
the latter directly into the former. The transi tims between and (in both
di rections)are performed as discussed at the corresponding place in 10.7.
We will use 0-52 in 10.5 just as in 10.7, and the remarks which we made
11,14
there this
2
2
4
6
7
11,1
2
3
4
5
6
7
8
9
10
12
subject apply again.
The static coding of the boxes I-Xl follows:
(to 11,1)
(ßl)o
11,13
11,14
42
11,6
38
42
11,9
ä+kP-l
ä+kP+M- I
45
Sp
Sp
h
s
Sp
h
h
Sp
Ac
11,13
Ac
Ac
11,6
Ac
Ac
11,9
Ac
Ac
Ac
Ac
Ac
q
(ä+kk-l)
ä+k?-l
ä4k9+M-l
Ykp
2
Yk•04M
2
Yk0 + -
2
2
YkQ+M -Y
2
```

<a id="planning-and-coding-111"></a>
## planning-and-coding-111 — 10.8: non-equidistant interpolation and explanatory code (physical page 129; Volume II printed page 39)

Source: [physical PDF page 129](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=129); reading unit `p129`, lines 4–44.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-110](#planning-and-coding-110), [planning-and-coding-112](#planning-and-coding-112)

```text
11, 13
14
111, 1
11,14
-39-
Ac
(to Xl,l)
IV,I
IV,5
(to 11, 1)
10
11
(to l.x,l)
(32) o
11, 13
11, 14
38
c.7
11, 13
11, 14
38
42
c
Sp
Sp
Sp
Sp
11,13
Ac
11 , 14
11,13
Ac
( ä+N-M-l)
(ö+N-M-l )
(as)o
(+1)
(ä+N-2)
(ä*1N-M-l)
(5-1)
(fi*N-M)
fi+1N-M)
```

<a id="planning-and-coding-112"></a>
## planning-and-coding-112 — 10.8: non-equidistant interpolation and explanatory code (physical page 130; Volume II printed page 40)

Source: [physical PDF page 130](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=130); reading unit `p130`, lines 15–62.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-111](#planning-and-coding-111), [planning-and-coding-113](#planning-and-coding-113)

```text
-40-
VII,I
(to IX l)
VIII, 1
(to
IX,I)
LX,I
(to X, 1)
(to 11,1)
Xl,l
Xl,l
0.2
41
44
Ac
41
Ac
(ä+k•o-l)
(ä+k9-l)
(k7-kP o
(k7-k\+1)
(ä+ki¯- I )
2- a e(2ä+k )
2-3 a(q+kQ-l) z
å(ki++k7]
2 - lgfi+k?-l)
(Ä+kQ-l)
( ä+kiO- l)
(F-ä)o
(F+R-I )
(+1)
( ä-ö-l)
-l)
VIII,
VIII,
VI, 6
VII,3
'{111,3
The ordering of the boxes is l,
and II, XI, IX, IX, must also be the
X, respecti vely.
This necessi tates the
11; 111, M; IV; V, IX, X; VI; VII;
inmediate successors of TV, VI, VII,
extra orders
11, 1
Xl,l
11, 1
```

<a id="planning-and-coding-113"></a>
## planning-and-coding-113 — 10.8: non-equidistant interpolation and explanatory code (physical page 131; Volume II printed page 41)

Source: [physical PDF page 131](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=131); reading unit `p131`, lines 5–191.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-112](#planning-and-coding-112), [planning-and-coding-114](#planning-and-coding-114)

```text
-41-
As indicated in Figure 10.5, e' is O.
at, Sa, 92 , correspond to 111, 1, V, 1, VII. 1, IV,I, VI, 1,
WII, l, respectively. Hence in the final enumeration Ill, l, V, l, VII, I must have
the same parity and IV,I, VI, l, VIII, l, mist have the same parity.
We must ncw assign C. 1-9, D. 1-3,
s. I their actual values, pair the 78
orders 1,1-7. 11,1-14, 111, 1-3, IV,1-9, v, 1-11, VI, 1-6, VII, 1-3, VIII,1-3, n, 1-4,
X, 1-9, XL 1-9 to 39 words (actually two dunny orders, necessitated by the adjusting
of the parities of V, I and to those of Ill, I and I V, l, respectively, increase
this to 40) and then assign l, I-XI,9 their actual values. We wish to do this again
as a cmtinuation of the code of 10.5. We will therefore again begin with the
number 53. FurtherrM)re the cmtents of D .1-3, s. I are irrelevant like those of
48-52 there. Hence they may be made to coincide with four of these. We therefore
53 -56
741 _ 791
_ 63
80 —81
111, 1-3
63 _641
82 -86
65 -69
861-89
_ 74
89 1 _ 91
56
48 s,
48 s
56 C'
38 h
50 s ,
51 h
45 h-
38 h-
50 s
50 s
50 h-
95 h-
65 cc
(N-01)
50 h
41 s
44 s
identify them with
following table:
11, 1-14
48-51 there. Sunning a II these
v,l-ll
rx, 1-4
x, 1-9
VI, 1-6
VII ,1-3,•
things up, we obtain the
VIII, 1-3
D. 1-3
s.
Now we obtain
this coded sequence:
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
93
94
59
42
51 s
42
101
50 h
42
91 '-92'
93 -101
48 -50
51
48 s
95
38 h-
50 s
48
80 c
48
80 c
h,
R,
h,
62
, 63 Sp
42 h
48
60
95
, 101 h-
69
70
71
72
73
74
75
76
77
78
79
80
81
82
83
84
SPI'
62
63
38 h
62
63
42
95
49
42
49
51
R,
96
97
95 h
99
100
95
49 s
98 h
51
51
Sp
85
86
87
88
89
90
91
92
93
94
95
96
97
98
99
100
101
51 h
98 h
42 h
65
c,
49 s
63
69
(+1)
74
860
89
910
state of 0-52 of
The durations may be
10.5 rmxst
es tima ted
be
as
exactly as described
follows :
at the end of
1: 275 u, 11: 485 g, 111: 125 u, 350 u, V: 425 u, VI: 225 ,
VII: 125 u, VIII: 125 u ,
150 u, X: 330 u, Xl: 350 u.
```

<a id="planning-and-coding-114"></a>
## planning-and-coding-114 — 10.9: changing a coded problem and tabulating modifications (physical page 132; Volume II printed page 42)

Source: [physical PDF page 132](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=132); reading unit `p132`, lines 9–47.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-113](#planning-and-coding-113), [planning-and-coding-115](#planning-and-coding-115), [planning-and-coding-043](#planning-and-coding-043)

```text
-42-
Total:
I * or II x 2 or II x (i +1)] +
+ (VII or VIII) (i -1) +1XXi
(the two first al ternatives in each bracket
can be described by io = I and io — O)
[l II or (IV + VI) or V +
refer to two possibilities which
-1) + 150 i +330 G -1)
ma x i mum
maximum
- (275 + 485 G +1) + (775 + 125 (i
= (1,090 i +1,430) u.
(1,090 210g (N-M-2) + 3610) (1.1 (N-M-2) 3.6) m.
Hence the complete interpolation procedure (IO .5 plus 10.8) requires
.4M + 1.1 2 log (N-M-2) + 3) m.
(.9M2 -
10.9 To conclude, we take•up a variant of the group of Problems 12-13,
which illustrates the way in which minor changes in the organization of a problem can
be effected ex post, i.e., after the problen has been coded on a different basis.
(In this cmnection, cf. also the discussion of 8.9. )
The description of the function under consideration in Problems 12 and
the two sequences and Xl,... On one hand, and ql, and
13. b, i.e.,
on the other, were stored in two separate systems of consecutive memry
locations: p, ,p+M-l and q, ...,q+M-l On one hand, and F, and I
(Ihese are the two storage areas A and B of those two problems.) For
on the other.
Problem 13. a the situation is different, since here ql alone are stored (at
,F+N-I, storage area A).
the locations F,
Assume now, that these data are stored together with the p•, x. , or the
, with Pi,
qi, y • , alternating. I. e. , at the locations p, ,p+2M-l, or ¯
Xi at p+2i-2, p+2i-l,or qi, Yi at F*2i-2, F+2i-l.
Since this variant cannot arise for Problem 13. a (cf. above), and since
its discussion for Problem 13. b comprises the same for Problem 12 (because the coding
of the former requires conbining with the coding of the latter, cf. 10.8), therefore
we will discuss it for Problem 13. b.
```

<a id="planning-and-coding-115"></a>
## planning-and-coding-115 — 10.9: changing a coded problem and tabulating modifications (physical page 133; Volume II printed page 43)

Source: [physical PDF page 133](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=133); reading unit `p133`, lines 7–39.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-114](#planning-and-coding-114), [planning-and-coding-116](#planning-and-coding-116)

```text
We state accordingly:
PROBLEM 13. c.
Same as Problem 13 in its form 13. b, but the quantities and
are stored in one system of 2N consecutive rneawry locations:
p+2N-l in this order: ql,
We trust analyze the coded sequences 0-52 of 10.5 and 53-101 of 10.8
which correspond to Problems 12 and 13. b, and detemine what changes are necessi-
tated by the new fomulation, i by Problem 13. c.
let us consider the code of 10.8, i.e., of Problem 13. b, first. The
changes here are due to two Causes: First, y • is now stored at F+2i-l instead of
ä+i-l; second, since the cade of 10.5, i.e. , of Problem 12, will also undergo changes,
the substitutions into it will change.
Ihe first group is Tost simply handled in this way: Assume that is
odd. Replace the position marks (B. i ) , which should be (p+2i-l) instead of
(ä+i-l) , by their half values:
We note, for later
2
use, that this has the effect that D. 3 will contain in-mediately before Xl
(L ) ) instead of (B. k)
Returning to the general question: we must charge the coding of all
those places, where such a position mark is used to obtain the corresponding Yi.
The values Of these posi tion marks must be doubled before they are used in this
way. Apart from this, hcvever, we mast m ly see to it that is replaced by
. This affects C. 3 (Of 10.8), i .e., 95.
Ihe use of position marks in the akove sense occurs only in II, when
Yk and are obtained. This takes place at 11,6 and II, 9. Hoaever, the position
marks in question originate in the substitutions 11,2 and II, 5, and it is therefore
at these places that the changes have to apply.
We now formulate an adequate coding to replace 11.2-4, so as to give
11,2 and 11,5 the desired effect. Note that at this point D.I contains
(L (F+2kq-l)) + k 9-1) instead of (ä+kQ-l) (B. k?) . Hence after 11,1
2 (3+2<-1))
the accunmlator contains
```

<a id="planning-and-coding-116"></a>
## planning-and-coding-116 — 10.9: changing a coded problem and tabulating modifications (physical page 134; Volume II printed page 44)

Source: [physical PDF page 134](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=134); reading unit `p134`, lines 4–67.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-115](#planning-and-coding-115), [planning-and-coding-117](#planning-and-coding-117)

```text
11, 1.1
2
3
4
5
6
11,
38
38
42
42
6
Sp
h
h
11,6
Ac
Ac
Ac
F+2k?-1
( F+2k?+M-2)
(F+2k?+2M-3)
(F+2k.0+2M-2)
(F42k?+2M-1)
Thus we must replace the three orders II, 2-4 by the six orders II, l. 1-6.
Hence the third and second remarks of 8.9 apply: We replace II, 2-3 by II, 1. 1-2, then
11,4 by
11, 1.2,1
11,1.3
and let II, 1.3-6 be followed by
11, 1.7
11,5
Then II, l. 3-7 can be placed at the end of the entire coded sequence. We will give a
final that expresses these changes after we have performed all the changes
that are necessary.
Ihe second group must be considered in conjunction with the code of 10.5,
i.e., of Problem 12. In the code of 10.8 only XI is involved in the operations of
this group. In the code of 10.5 the si tuation is as follows: Replace the posi tion
, i.e., (F+2k+2i-4) ,
marks A. i, B.i (of 10.5), which should be (p+2i-2)
, (p+2i-l)
, (q+i-l) , i.e.,
(ö+2k+2i-3) ,
instead of (p+i-l)
(F+k+i-2) , (ä+k+i-2) ,
as nearly
by their half values as possible. Since is odd, we will use the half value of the
(L (F+2k+2i_3)) + i -2) . Ihen we must change the
secmd expression:
coding of all those places where such positim marks are used to obtain the corres-
ponding pi and y-: Ihe values of these pcsition marks must be doubled before they
We must
are used for a Yi, and then decreased by I before they are used fcr a p • .
also take care that the storage locations, which supply the modified (A .i) , (B. i)
posi tion marks, are properly supplied themselves. Apart from these, however, we
must only see to it that Xl (of 10.8) produces (I (ö+2k-l)) ( + k + i-2) I
instead Of
Since p, q, or F, ä, no longer appear inde-
pendently, it is not necessary to produce (ä-ö-l) in Xl.
Ihe use of position marks in the above sense occurs only in Ill, V,
and VII (of 10.5), when Pl, pi, and x • , are obtained. These take place at
Ill, 3, V, 2, and VII. 14, 15, 21. However, the position marks in question originate
in the substitutions Ill, 2, V, l, and VII, 8, 9, 13, and it is therefore at these
places that the changes have Co apply.
```

<a id="planning-and-coding-117"></a>
## planning-and-coding-117 — 10.9: changing a coded problem and tabulating modifications (physical page 135; Volume II printed page 45)

Source: [physical PDF page 135](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=135); reading unit `p135`, lines 6–83.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-116](#planning-and-coding-116), [planning-and-coding-118](#planning-and-coding-118)

```text
-45-
position marks (A. i)
, (B.i ) are supplied frcxn E. 2, which in
turn is supplied by II and IX (of 10%). II will ncv supply to E. 2
(ö*2k+1)) + r + i-2) I
(ö+k+i-2)011 2
o i -2 instead of (p+l)
The function of IX is actually performed by VIII, and it will rnaintain in E. 2
(L (ö+2E+2i-l)) ( g! + k + i-l)o instead of (p+i(l)
If we keep
these facts in mind when rmdifying Ill, V, VII, then we need not change II, rx
(i.e., VIII).
We ncN give adequate codings, to insert before 111,2 and before V, l,
and also to replace VII, 7 before VII, 8, 9, and to replace VII, 10-12 before VII, 13,
so as to give Ill, 2, V, l, and VII 13 the desired effect. Note that at these
points, as we observed above, D. 4 (i.e. , 41, substituted f rm Xl of 10.8) contains
(L (F+2E-l)) , and E. 2 contains (F+2E+l)) and (L respectively.
Hence before Ill, 2, V, l, and WI, 7, the accumulator
(L (ö+2k+2i-l)) and (L ( ö+2k+2i-l))
, respectively.
111, 1.1
2
v,o.l
2
VII,6.1
2
VII,9.1
2
3
4
h-
h
Ac
Ac
Ac
Ac
Ac
Ac
Ac
I (F+2E-l)) ,
contains
2
(ö+2k-1)
(F+2E-2)
(F+2Æ+2i-1)
(ö+2k+2i-2)
(K (F+2k+2i-1)-1)
(ö+2k+2i-3)
(h (F+2k+2i-l))
(h (F+2k-2i
-1)4M-1)
(h (F+2k+2i-
l)+h-l)
(F+2k+2i+2h-3)
Thus we
V, 0.1-2 before V, l; replace the order VII, 7 by the
the three orders VII, 10-12 by the four orders VII, 9.1-4. Hence the third and second
remarks of 8.9 apply again: We replace 111,1 by
rrust insert the orders Ill, l. 1-2 before 111,2; insert the orders
two orders VII, 6.1-2; and replace
111,0
111,1.0 c
and let Ill, 1.0 coincide with Ill, I and be followed
by Ill, l. 1-2 and Chen by
111, 1.3
Next we
and let
finally
111,2
replace V, I by
v,o.l
c
c
V, 0.1 be as specified above,
by
and be followed by V ,0.2,
then by V, l,
and
```

<a id="planning-and-coding-118"></a>
## planning-and-coding-118 — 10.9: changing a coded problem and tabulating modifications (physical page 136; Volume II printed page 46)

Source: [physical PDF page 136](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=136); reading unit `p136`, lines 4–58.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-117](#planning-and-coding-117), [planning-and-coding-119](#planning-and-coding-119)

```text
-46-
v,l.l
Finally we replace Yu , 7 and VII, 10-12 by VII ,6.1-2 and HI, 9. 1-4. It is best to
effect this as a replacenent of the entire piece VII, 7-12 by WI, 6. 1-2, VI 1,8-9,
HI, 9. 1-4 (a total of six orders to be replaced by a total cf ei*ut orders). Ihis
means that we replace WI, 7-11 by ,6.1-2, VII, 8-9, VII, 9.1, then we replace WI, 12
II, 2-3
11,1.2.1
VII, 7-8
VII, 9 IO
by
VII,9.1.1
VII, 9.2 C
and let VII, 9.2-4 be followed by
VII,9.2.5
VII, 13
c
nien Ill, l. 0-3; V, O. 1-2, V , l, V, 1. l; HI, 9.2-5 can be placed at the a-ld of the entire
coded sequence. We will give a final enurneration that expresses these changes after
we have rrforned all the changes that are necessary.
Returning to the second group in the coding of IO. Y, we note that it
affects only Xl (of 10.8). We saw above that XI trust produce (F+2k- l)) and
substitute it into 41, and that Chis is all that has to be done there. hever, we
noted before that D. 3 before XI contains precisely (I (F+2R-l)) . Hence XI, 1-9
(i.e., Xl in its entirety) may be replaced by
Xl,o.l
2
3
41
Ac
41
(FOR-I))
Hence we replace M, 1-3 by XIN. 1-3, and since operations of the code of 10.8 end at
this point, M, 4-9 may be left empty.
To conclude, we observe that C. 3 must contain (EZ.!) = - l)
2
instead of (+1) , and that nei ther nor are needed in any other form, so that
C. 9 may be left enpty.
We are now in possession of a complete list of all changes of bcxh
codes 0-52 of 10.5 and 53-101 of 10.8. We tah.llate the omissions and mdifications
first, and the additims afterwards.
Qnissions and Sbdifications:
(10.8) :
(10.5) •
Fran
111,1
VII, 11
VII , 12
To
11, 1.1-2
111,0
VII,6.1-2
VII, 8-9
vr1,9.1
VII, 9.1.
```

<a id="planning-and-coding-119"></a>
## planning-and-coding-119 — 10.9: changing a coded problem and tabulating modifications (physical page 137; Volume II printed page 47)

Source: [physical PDF page 137](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=137); reading unit `p137`, lines 7–107.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-118](#planning-and-coding-118), [planning-and-coding-120](#planning-and-coding-120)

```text
(hissions and Sbdi fications
M, 1-3
v, 0.1-2
66 C t
etc
L, 42 h
10 sp',
58
38 h
VII: 130
From
(cont. ) :
9.2-5
_ 47 _
To
Xl,o. 1-3
Enp ty
(10.8) :
Additions:
(10.8) :
ao.5) :
(10.5) :
(10.5) :
11, 1.3-7
111, 1.0-3
VII,
We can use five of the six anpty fields Xl,4-9 (from 10.8) to
11, 1.3-7 (frun 10.8)
say M, 4-8. C. 9 is the last word of the code: 101, hence we
can place Ill, l. 0-3;
begins there. They
111, 1.0-3
v,o.1-2
V, 0.1-2, V, l, V, 1.1, VII, 9.2-5 (from 10.5) in a sequence that
will then occupy these posi Lions:
101-102'
103-103 '
10.5. )
VII,2-5
105-106
v, 1.1
(All
0-52
5
10
14
15
16
17
57
these are from
we
and 53-101:
101 c,
103 c ,
L,
21 sp',
105 c ,
Ihe
(10.5) :
(10.8) :
can forrmlate the final fom
104
104'
of all
41 s
38 h
42 h
changes in the coded sequences
42 h-
18 SP'
49
59 Sp
58
65
66
67
68
69
38 h
42
95
101
102
103
104
105
106
412 0
42 h
L,
10 C'
48 h-
17 C'
following durations are
affected:
111:
+ 130
130
180
- 225
```

<a id="planning-and-coding-120"></a>
## planning-and-coding-120 — 10.9: changing a coded problem and tabulating modifications (physical page 138; Volume II printed page 48)

Source: [physical PDF page 138](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=138); reading unit `p138`, lines 7–15.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-119](#planning-and-coding-119), [planning-and-coding-121](#planning-and-coding-121)

```text
Total:
Total :
(10.5) :
(10.8) •
(130 + 130 (M-1) + 130 WM-I) )
(65 M2 +65 M) (.07 MQ + .07 M) m.
(180 (i + 1) - 225 i ) u = (-45 i +180)
maxirurn .2 m.
Hence there is no relevant change in the estimate at the end of 10.8.
```

<a id="planning-and-coding-121"></a>
## planning-and-coding-121 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 139; Volume II printed page 49)

Source: [physical PDF page 139](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=139); reading unit `p139`, lines 12–62.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-120](#planning-and-coding-120), [planning-and-coding-122](#planning-and-coding-122)

```text
-49 _
11.0 CODING OF SCHE COdBINAIORlAL (SORTING) PROBLEMS
11.1
In this chapter we consider probler•rs of a combinatorial, and
not analytical character. Ihis means, that the properly calculational (ari Ch-
metical) parts of the procedure will be very simple (indeed almst absent). and
the essential operations will be of a logical character. Sich problems are of
a not inconsiderable practi cal importance, since they include the category usu-
ally referred to as sorting problems. Ihey are, furthemore, of a conceptual
interest, for the fol lowing reason.
Any computing machine is organi zed around three vi tal organs: Thc
the I ogical control, and the ari organ. Ihe last mentioned
organ is an adder-subtractor-mul tiplier-divider, and the multiplier is usually
that aspect which primarily controls its speed (cf. the discussions of Part l. )
The efficiency of the machine on all analytical problerrs is clearly dependent
to a large extent on the efficiency of the arithmetical organ, and thus primari ly
of the nultiplier. the non-analytical, combinatorial problems, to which we
have referred, avoid the nmltiplier a Inost cunpletely. (Adding and subtracting
is hardly avoidable even in purely logical since the operations are
needed to construct the Eosi tion marks of mermry locations and to effect size
cmparisons of numbers, by which we have to express our logical alternati ves. )
Ginsequently these problems provide tests for the efficiency of the non-ari th-
retical parts of the machine: Ibe merrory and the logical control.
11.2
We will consider two typical sorting problems: "lhose of
meshing and of sorting proper. nere are, of course, many others, and many
variants for each problem, but these two should suffice to illustrate the main
methodical principles.
In order to fomulace our two problems, we need the defini tions which
fol low.
We operate with sequences of complexes. A complex X z (x; u l,
consists of p+l numbers: 'lhe principal number x and the subsidiary numbers
p is the order of the cornplex. A se uence S = (X (l)
consists of n complexes x (i)
n is the length of the
sequence. Ihroughout what fol lows we will never vary p, the (arhi trary but) fixed
order of all canplexes to be considered. We will, however, deal with sequences
of various lengths.
A sequence S
of its complexes X(i) -
x(n)) is a nono tone if the principal elements
u(i)) form a mnotone, non decreas-
1 ng sequence:
(1)
A serpence T (Y (1)
the sarne
(2)
(1)
(2)
Y is a permutation of another sequence S = (X (
length, if for a suitable pemmtation of the
```

<a id="planning-and-coding-122"></a>
## planning-and-coding-122 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 140; Volume II printed page 50)

Source: [physical PDF page 140](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=140); reading unit `p140`, lines 11–69.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-121](#planning-and-coding-121), [planning-and-coding-123](#planning-and-coding-123)

```text
-50-
Given two sequences S )
equal lengths n, m), their sum is the sequence T]
(of length n + m).
We can now state our two problerrE:
(Meshing)
PROBLEM 14.
Y(•)) (of not necessarily
Two (Mnotme sequences S, T. of lengths n, m, respectively, are stored
at two systems of n(p+l)
, m(p+l) ccmsecutive memory læations respectively:
An accomodatim f a sequence
, and t, til, .
of length n + m, cmsisting of (n + + l) consecutive memory locatims, is
, )-l. Ibe constants of the problem are p, n,
available:
m, s, t, r, to be stored at six given memry locatims. It is desired to find
a nonotme permutation R of the sum S, T], and to place it at the locations
( Sorting)
PROBLEM 15.
A sequence S (subject to no requirements of monotony whatever) is stored
at n(p+l) consecutive manory catims:
s, s The constants of
the problem are s, n, p, to stored at three given menory I cratims. It is
desired to find a rrnnotme pemutatim S• of S, and to replace S by it.
3 We consider first Problem 14, which is the simpler one, and whcse
solution can be c mveniently used in solving Prd)lem 15.
we have S 2 (X(l)
Y(.)) with X(i)
Z with zd)
and we wish to fomR= (Z
Wii 5), Pwhich is a M)notone F*rmutation of [S, T].
Forming H can be viewed as an inductive process: If Z (1)
for
a k I have already been forned, the inductive step c msists of foming
It is preferable to allow k = n+rn+l, too, in the sense that when this value
of k is reached, the process is teminated. Assume, therefore, that we have. fornpd
z(k-l)
for a k 1, . , n+m+l. It is clear, that we rny assure in addition,
that these 731 )
Z(k-l)
are the
for two suitable i
k' Jk with
(1)
Then we have the follcxing possibilities:
. together with the Y (1)
(a)
(b)
By (l) k = nhn+l, hence, as we cbserved abwe,
R is fully formed, and nothing remains to done.
(l) k n hence, as we observed above,
Not i
R is not fulhy formed, and must be fonned next. Clearly, we
as one of and
may choose
, we must decide which.
We introduce a quantity t.Jk, so that O for X ( and
= I for —Y (jk +1)
```

<a id="planning-and-coding-123"></a>
## planning-and-coding-123 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 141; Volume II printed page 51)

Source: [physical PDF page 141](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=141); reading unit `p141`, lines 10–72.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-122](#planning-and-coding-122), [planning-and-coding-124](#planning-and-coding-124)

```text
(b.3.1)
(b. 3.2)
(b.3.3)
-51.
O implies
Zi l,
I implies
+ l. is determined according to the following ru les:
= n, hence jk * m: S is exhausted, hence w
- m, hence i * n: T is exhausted, hence O.
n, jk * m: Neither S nor T is exhausted. We mast
distinguish further:
Necessarily GJ
> : Necessarily
= Both
O and = I are acceptable. We
choose
As pointed out above, (a), (b) describes an inductive process which runs
, n+m+l. It begins with k I and i k = jk O (rning to and
over k =
then progresses from k to k +1, forming the necessary i k , jk and as it along.
It is convenient to denote the locations s and t, where the storage of the
sequences S and T begins, by a coo-mon letter and to distinguish them by an index:
(2)
Grreslx'ndingly. let AO and Al be the storage areas corresqonding to the two inter-
vals of locations frans to s + and frans to s + m(p+l )-l.
In this way
their positions will be A 0.1, n(p+l) and AI. l, , m(p+l), where A O. a and A1. h
(i) for a
(i) for
correspond to s + a-I and s I + b-l, and store x
a * y (j) for b z )+l, v(j) for b +1,
respectively. Next, let B be the storage area intended for the sequence R, corres-
ponding to the interval of locations frotn r to r+(n+m) )-l.
In this way its
positions will be B.I
, where B.C correspnds to r+c-l, and is
(k) for c
intended to sta•e z
for C
respectively. As in several pre' ious the positions of AO Al, and B
need not be shown in the final enureration of the coded sequence.
Further storage capaci ties are needed as follows: The given data
(the constants) of the problem, s
, r, n, m, p, will be stored in the storage
area C. (It will be cmvenient to store them as (so)
(m(p+l ) )
o, (P+l)o•
in C.) Next the induction indices
We will also store
k, q' will have to be stored." It is convenient to store i ,
j , too, along
with k, while it turns out to be unnecessary to form and to score W explicitly.
Ihese indices i, j, k, q' are all relevant as position marks, and it will prove
convenient to sure in their place (so (p
(Al
(i.e. (AO . i (p )+l)
, (r *qi-I)
, (AW.h(p+l) + q') O,
(B. ) o; here Wi , and h
or j for = O or l, respectively) Note, that two posi tion mnrks that correspond
to q' are being stored. Ihe three first quantities will be stored in the storage
area D, and the two last ones in the storage area E.
```

<a id="planning-and-coding-124"></a>
## planning-and-coding-124 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 142; Volume II printed page 52)

Source: [physical PDF page 142](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=142); reading unit `p142`, lines 4–36.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved. The phrase about needing no further comments concerns the report's exposition of this diagram-to-code step; it is not an explicit claim about source-comment syntax. OCR omits the final word of the opening sentence; visually it is comments. Coordinator visual supplement is pending.

Related: [planning-and-coding-123](#planning-and-coding-123), [planning-and-coding-125](#planning-and-coding-125), [planning-and-coding-163](#planning-and-coding-163)

```text
-52-
We can now draw the flow diagram as sh(Nn in Figure II. l.
ccxiing obtains fran this without a need for further
static coding of the boxes I-X follcms.•
D.2
(to 11,1)
ne actual
11,1
111,1
(to 111,1)
(to V, 1)
(to VII, 1)
IV,I
c.2
VI,I
c.5
Ac
Ac
Ac
Ac
v,6
Ac
v,5
(so + i
(si +j(p+l))
(so +i(p+l))
s +i(p+l)
sl +j(p+l)
v,l
s
(to VII,I)
+j(p+l)
+i(p+l) h-
```

<a id="planning-and-coding-163"></a>
## planning-and-coding-163 — 11: actual coding without further comments, followed by the static coding table (visual transcription)

Source: [physical PDF page 142](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=142); reading unit `p142`, lines 38–40.

Attribution: Herman H. Goldstine and John von Neumann

Context: Supplement to the complete OCR page selection; preserves legible prose where OCR corrupts words. Neighboring source-page records retain the surrounding worked examples.

Transcription/context notes: Manual transcription from physical page 142, printed Volume II page 52. The OCR dropped the word comments; this supplement preserves the visible complete sentence. Here comments describes further exposition of the worked flow/coding example; no modern inline syntax is inferred. The following coding/explanatory table remains in the page OCR and original scan.

Related: [planning-and-coding-124](#planning-and-coding-124)

```text
We can now draw the flow diagram as shown in Figure 11.1. The actual coding obtains from this without a need for further comments.

The static coding of the boxes I-X follows:
```

<a id="planning-and-coding-125"></a>
## planning-and-coding-125 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 143; Volume II printed page 53)

Source: [physical PDF page 143](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=143); reading unit `p143`, lines 15–34.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-124](#planning-and-coding-124), [planning-and-coding-126](#planning-and-coding-126)

```text
-53-
3
0-+
3
3
3
10
4
10
z
z-
3
(A! t--.az
3
6
7
8
for
9
FIGURE 11.1
```

<a id="planning-and-coding-126"></a>
## planning-and-coding-126 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 144; Volume II printed page 54)

Source: [physical PDF page 144](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=144); reading unit `p144`, lines 4–83.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-125](#planning-and-coding-125), [planning-and-coding-127](#planning-and-coding-127)

```text
-54-
(p+1)O
2
3
4
VII,I
2
3
4
VIII,I
2
3
5
6
7
8
9
IX,I
2
3
4
5
6
7
8
9
10
(to VIII,I)
(to VIII,I)
(to rx,l)
(to X, l)
VIII,
VIII,
9
8
s
s
s
Sp
s
s
Sp
h
Sp
h
Sp
s
Ac
Ac
Ac
Ac
Ac
VIII, 9
Ac
VIII,8
Ac
Ac
Ac
rx, 10
Ac
Ac
IX,9
Ac
(so +i(p+l))
(so
(so
(sl +j(p+l))
(sl +j(p+l))
(r +k(p+l))
(r +k(p+l))
+h(p+l)
(sW+h(p+l )+qt ) 0
(sW+h(p+l )+q' ) o
w
s
1
IX,10
rx, 9
sW+h (p+l) + q'
s
```

<a id="planning-and-coding-127"></a>
## planning-and-coding-127 — 11.1-11.3: meshing, flow explanation and annotated code (physical page 145; Volume II printed page 55)

Source: [physical PDF page 145](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=145); reading unit `p145`, lines 4–163.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-126](#planning-and-coding-126), [planning-and-coding-128](#planning-and-coding-128)

```text
-55-
Ac
Ac
Ac
2
3
4
24 -26 '
VII ,1-4
_ 12
27 -29
12' _ 16,
30 -36
37 -39
7 -10
22 -24
40 -41
35 h, 37 S
-s
33 h-,
-s
39 h-
36 h
27 cc,
34 h-
40 s , 35 h
10 cc
40 s
(q • -p-I)O
h
11,1
(to IX,I)
ordering of the boxes is 1, 11, 111, V, VII, VIII, [X, X, and VII,
successors of IV, VI, X, respectively. This
VIII, IX rmst also be the innediate
necessitates the extra orders
D. 1—3, E. •1-2 their actual values, pair the 59
orders 1,1-6, 11,1-4, 111,1-4, IV,1-5, V,1-7, VI,1-5, VII,1-4, vill,1-9, IX, 1-10,
IV,5
VI,5
x,5
VII, 1
VIII,I
IX,I
c
c
We now assign C. 1-7,
X, 1-5 to 30 words and then assigl
l, I-X,5 their actual values.
Ihese arc expressed
in this table:
1,1-6
11, 1-4
111,1-4
v,1-7
Now
VIII, 1-9
IX,I-IO
x, 1-5
O
2
3
4
5
6
7
8
9
10
11
12
13
we obtain
30
, 37 s
31
, 38 s
32
, 39 s
, 30 h-
37
24 cc'
, 31 h-
38
34 27 Cc
37
9 Spl
38
9 Sp
38
38 s , 39
16
sp', 41 S
Ihe
dura Lions
this coded
14
15
16
17
18
19
20
21
22
23
24
25
26
27
sequence:
35 h
40
41
21
40
21
41
17 c,
31
37
39 s
16
Sp
36
h
41 s
36 h
40 s
38
W, 1-5
VI,1-s
D. 1-3
E.I-2
28
29
30
31
32
33
34
35
36
37
38
39
40
41
12 C'
(p+l)o
may be estimted as follows:
1: 225 u,
VIII: 350
Total :
150 u, 111: 150 u, 200 g, V: 275 g,
U, LX: 375 u, X: 200 u.
(11 + (111 or (111 + V) or IV) or VII) +
VIII + (LX + X) xp
200 u, VII: 150
x (n + (II + I V)
```

<a id="planning-and-coding-128"></a>
## planning-and-coding-128 — 11.4: sorting, reused routine and explanatory representations (physical page 146; Volume II printed page 56)

Source: [physical PDF page 146](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=146); reading unit `p146`, lines 6–64.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-127](#planning-and-coding-127), [planning-and-coding-129](#planning-and-coding-129)

```text
-56-
maximxm = (225 + (150 +425 +200 +350 +575 xp) (n + m) + 350)
((575 p + 1,125) (n + m) + 575)
This result will be analyzed further in 11.5.
11.4 We pass now to Problem 15, which will be solved, as indicated
above, with the help of the solution of Problem 14.
We have S (X (l)
x(n)) with x(i)
G)
u and we
wish to form an (X (l' C
x (n' ) ) , which is a mnotone permutation of S.
Ihis can be achieved in the following manner:
If a certain pemutation
. * (n' o)) of S has been found, which may not yet be fully monotone,
but in which at least two consecutive intervals
x(k+i-1'O) and
are (each one separately) monotme, then we can mesh
these (in the sense of Problem 14), and thereby obtain a new permutation
00)) of
, i.e. of S, for which the whole interval
X(k+i+j-V00)
is monotone. Thus we can convert two rmnotone
intervals of the lengths i, j into one of the length i + j. Ihe original S
is made up of mnotone intervals of length l, since each (separately) may
be viewed as such an interval. Hence we can, beginning with these mnotme
intervals of length l, build up monotone intervals of successively increasing
length, until the maximum length n is reached, i.e. the permutatia•-l of S at
hand is rnonotone as a whole.
This qualitative description can be formalized to an inductive process.
This process goes through the successive stages v -
In the stage
v a vermutation S"
) ) of S is at hand, which is made up of
consecutive intervals of length 2', which are (each one separately) monotme.
(Since n may not be divisible by v, the length of the last interval has to be
the remainder r of the divisi m of n by 2', r < 2'
If n is divisible by 2',
we should put r
O and rule this interval to be absent, hit we may just as
= 2 v, and still rule it to be the last interval.) Now a se ence of
well put r
steps of tKe nature described above will produce a new permutation of S"
i.e. of S, in which the mnotone intervals of length 2' in S" are pairwise
meshed to mnotme intervals of length 2' + 1 in (nae end-effect f v +1
can be described in the : ame terms as above for v.) This inductive process
begins with v and S •o S. It ends when a v with 2' > n has been reached,
the corresponding S • ' is the desired (monotme) S•. (Note, that at this point
It is the final interval of length r referred
there is only one interval:
to above, in this case with r = n . ) Using the function , which denotes the
smallest integer z, we may therefore say that this process terminates with
€2 log
log is, however, only the
Ihe induction over v
primary induction. For each v we have intervals of length 2' (cf. above),
these pairs, which have to be meshed to
intervals
of length 2' +1 (cf. above), in order to effect the inductive step fr•cln v tov + l.
```

<a id="planning-and-coding-129"></a>
## planning-and-coding-129 — 11.4: sorting, reused routine and explanatory representations (physical page 147; Volume II printed page 57)

Source: [physical PDF page 147](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=147); reading unit `p147`, lines 10–76.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-128](#planning-and-coding-128), [planning-and-coding-130](#planning-and-coding-130)

```text
-57-
If we enunærate these interval pairs by an index w z
then it becomes
clear chat we are dealing wi th a secmdary induction, of which w is the index.
We can now state the general inductive step with cmplete rigor:
Onsider av O, l, 2,
and assunr that the permutation
has already been formed. We effect a secondary induction
over a w = O, l, 2
Assume that a certain w has a Iready been reached. Ihen
2' + lw n. We ncN' have to two intervals of the length nw, i.e.
wi th
2' +lw+nw and
2' +lw+nw
with j
Ordinarily nw mw
- 2', i.e. this is the case when both these intervals can be
accomcdated in the interval l, . , n. Thus the condi tion fa• this case is
2 '+1 (w+l) S n. Otherwise, i.e. for (w+l) > n, we have two possibi lities:
First: nw = 2' if this interval can be acctmdated in the interval l,
if 2' +2' < n. is then chosen so as Co exhaust what is left of the interval
- * Thus the condition f this case is
I) > n + include (w+l)
= n, too, since the f Tmulae
of the present case coincide then with those af the previous one. Seccnd: Other-
wise, i.e. for 2' + lw + 2' > n, the seccnd interval is missing
= O. nw is then
chosen so as to exhaust what is left of the interval l, ... , n, i.e. nw = n -
Thus the condition for this case is 2' + lw + 2' > n (and, of c mrse, 2 ' + I w). We
may include 2' + 2' n, too, since the fornmlae of the present case coincide
then with those of the previous one. These rules can be surrrrEd up as follows:
(3)
2.
2'
raw z n
for
mw -
for
for
2'+lw +2' (2 2'+lw)
If 2' +1 (w+l) < n, then the (secmdary) induction over w continues to w + l; if
(w+l) n, then the induction over w s t +S. If the induction over w stops
with a w > O, then the (prirrnry) induction over v cmtinues to v + l; if the
induction over w stops with w 0, then the induction over v stops. At any race
these reshings form the F*rmutation
If the induction over v stops with
a certain v. then its S" +1
is the desired S
There ranains, finally, the necessity to specify the locations of S"
, which control the meshing pr cesses that lead from, S • ' to S" +1
and S" +1
Hi 1)-1,
Assume that S • ' occupies the interval of locations from a
to a
and S • •+1
similarly the interval of locations fran a
to a
Then the arshing process which corresponds to a piven w arshes the sequences that
+ (2' +lw and frcxn
+2' +lw(p+l) to' a
occupy the intervals from a
• (2' + lw to a
w and places the resulting
(,+1) +2' +lw(p+l) to a
4 (2' •lw*n
serpence into the interval from a
Ihe reshing process is that one of Problem 14.
```

<a id="planning-and-coding-130"></a>
## planning-and-coding-130 — 11.4: sorting, reused routine and explanatory representations (physical page 148; Volume II printed page 58)

Source: [physical PDF page 148](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=148); reading unit `p148`, lines 27–68.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-129](#planning-and-coding-129), [planning-and-coding-131](#planning-and-coding-131)

```text
-58-
We distinguish the constants of that problem by bars. The above specifications
of the locatims that are involved can then be expressed as follows:
(p+l),
(4)
Clearly the interval frun a to a ) + n(p+l ) -l and the interval fran a
to
must have no elernents in corrrrnn .
We need such an a ( ' )
to a ( v)
i.e. an interval from a
for every v for which S" is being formed. It is, however, sufficient to have
two such intervals which have no elerrents in caTTM)n, say from a to a +n(p+l
and from b to b We can then let a (v) alternate between the two values
a and b, i.e. we define
(5)
Hence a (O)
Consequently
(6)
= a for v even
b for v odd
but =
S, hence the statenent of Problem 15 requires a
"Ihs a is the s of Problem 14, and b is any such location such that the interval
frcyn a to a +n(p+l and the interval from b to b have no elenents in
connon.
We want the final S • to occupy the location of the original S, i.e.
—a for the final v with -S•
I .e. this v+l shmld
we want a
be even. We saw further above, that the induction over v can stop when the
induction over w stops with wzO, i . e. when 2 n. This v+l rnay odd; let
us therefore agree to perfomn one nore, seemingly step from v to
(7)
Hence this
integer
we will tenninate the induction over v when
n and v+l even, i.e. a
v is the smallest even with 2 n, i.e. 2k' for the smallest
with 22k'
n; i. e. 4 ? n. This neans that
2 < log .
```

<a id="planning-and-coding-131"></a>
## planning-and-coding-131 — 11.4: sorting, reused routine and explanatory representations (physical page 149; Volume II printed page 59)

Source: [physical PDF page 149](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=149); reading unit `p149`, lines 8–63.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-130](#planning-and-coding-130), [planning-and-coding-132](#planning-and-coding-132)

```text
-59-
In the coded sequence that we will develop for our problem, the coded
sequence that solves Problem 14 will occur as a part, as we have already pointed
out. is the sequence 0-43 in 11.3. We propse to use it and to
adjust the coded sequence that we are forming accordingly.
This is to what we did in 10.6 and 10.7 for the 13. a
and 13. b: niere the coded sequence formed in 10.5 for Problem 12 was used as part
of the coded sequences of the twos former problers. There is, however, this diffe-
rence: In 10.6, 10.7 the subsidiary sequence (of Problem 12) was attached to the
end of the min sequences (of 13. a, b), le nm' the subsidiary sequence
(of Problem 14) will occur in the interior of the main sequence (of Problem 15)
indeed it is a part of the inductive step in the double induction over v, w. 'lhe
Constants of Problem 14 have already been dealt with: ney must be substi tuted
according to (4) above.
In assiguing Letters to the various storage areas to be used, it nust
be just as at the corresponding points in 10.6, 10.7, that Che coded
sequence that we are now developing is to be used in cmjunction witb (i.e. as
an extension of) the coded seqtence of II. 3.
It is therefore again necessary
to classify the s t a-age areas required by the latter: We have the storage areas
C-E, which are incorporated in the final enunEration (they are 30-41 of the 0-41
of 11.1); and A o, Al and B (i.e.
S + fi (ö+l)-l; + G (ö+l)-l
and F, , F which will be part of our present A, B (i.e. of
b they will be a (t) +2' +lw(p+l),...,
, and b, ... ,
(2.41 w a
and +2' +lw(p+l),..
(01 +nw cf. (4) above).
lherefore we can, in assigfing Letters to the various storage areas in the present
coding, disregard those of 11.3.
A and B be the storage areas corresponding to the intervals frun a
In this way their positions will be
to and frun b to
A l, and where A. i and B.i respond to a+i-l and b+i-l.
A will store S at the beginning and S• at the end of the procedure. B may be at
any available place, and we assurre it to be irrelevantly occupied. In the course
of the procedure A and B are the alternate values of A ( ' ) (for a
= a and b,
while s (v)
i.e. for v even and odd, respectively), and SO )
is stored at A
S ('+1) is being forned. All these storages are arranged Like the stcr age of S
at AO in 11.3.
Ihe given data of the problem, a, b, n, p, will be stored in• the
(It will be convenient to store them
storage area C, with the exception of p.
A O will also be stored in C.) p is also needed in the
as b O,
coded sequence. of 11.3, and it is the only one of the constants of that problem
which is independent of the induction indices v, w. (Cf. (4) above.) Hence its
storage in that sequence, at 35 (as (p+l ) 0) is adequate for our present purpose.
Ihe other constants of that problem on v, w (cf. above), hence their
locations, 30-34, must be left empty (or, rather, irre levant ly occupied), when
our present coded sequence begins to operaté, and they mst be appropriately
substituted by its overation.
```

<a id="planning-and-coding-132"></a>
## planning-and-coding-132 — 11.4: sorting, reused routine and explanatory representations (physical page 150; Volume II printed page 60)

Source: [physical PDF page 150](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=150); reading unit `p150`, lines 5–83.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-131](#planning-and-coding-131), [planning-and-coding-133](#planning-and-coding-133)

```text
-60-
'lhe induction index v will be stored in D. (It will be convenient to
, ) along with it.) ne induction
form (2 l)) , and to store
index w is part of the expressions which have to be laced at 30 and 32 (GO)
) hence it
i.e. by (4) (a ( v) +2 '+lw (.p+l)) and (a
and (F) o,
requires no other storage.
We can now draw the flow diagram, as shovn in Figure 11.2. The actual
coding obtains fran this quite directly, in one instance (at the beginning of
box VI) the accumulator is used as storage between two boxes.
ne static of the boxes I-XIV follcns.
11,1)
2
2
3
4
5
6
(to
2
3
4
(to 111, 1)
111,1
2
3
111,4
5
IV,I
2
3
4
5
IV',6
7
35
30
32
30
(n(p+l))
0.2
31
30
33
34
s
s
s
h
s
s
Ac
Ac
Ac
Ac
30
Ac
32
Ac
Ac
Ac
Ac
Ac
Ac
31
Ac
33
Ac
34
(p+l)o
(2'+1w (p+l))
((2'+lw + 2') (p*l))
((2'+1w
+n(p+l))
( (n-2'+1w) (p+l))
( (n-2'+1w) (p+l))
0
```

<a id="planning-and-coding-133"></a>
## planning-and-coding-133 — 11.4: sorting, reused routine and explanatory representations (physical page 151; Volume II printed page 61)

Source: [physical PDF page 151](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=151); reading unit `p151`, lines 6–35.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-132](#planning-and-coding-132), [planning-and-coding-134](#planning-and-coding-134)

```text
-61.
1
3
2
3
3
3
10
to 30
A.
30 (Æ"'.IX
32
30(A .Z
32
8
e
11
to 33
8
8
8
b e m 14 )
7
33
ZV(p+/) Co 39 + Co 3+
7
Note
11.3.
v,
FIGURE 11.2
```

<a id="planning-and-coding-134"></a>
## planning-and-coding-134 — 11.4: sorting, reused routine and explanatory representations (physical page 152; Volume II printed page 62)

Source: [physical PDF page 152](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=152); reading unit `p152`, lines 26–64.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-133](#planning-and-coding-133), [planning-and-coding-135](#planning-and-coding-135)

```text
VI,I
VII,I
(to VIII, 1)
VII, 1
34
(to rx, 1)
33
30
31
(to VI, 1)
0-29
(a-a
(a-a
33
31
Ac
34
Ac
Ac
Ac
Ac
Ac
+ (2'+lw
((2'+l(w+1)-
( (n-2'+lw)
(at,) +2 •+lw(p+l))
( 2'+1w(p+l))
VIII,I
IX
XII,I
34
(Problem 14:
30
c.3
Xl,l
(to XIII,I)
(to xrv,l)
c.i
(to xrv, 1)
```

<a id="planning-and-coding-135"></a>
## planning-and-coding-135 — 11.4: sorting, reused routine and explanatory representations (physical page 153; Volume II printed page 63)

Source: [physical PDF page 153](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=153); reading unit `p153`, lines 4–85.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-134](#planning-and-coding-134), [planning-and-coding-136](#planning-and-coding-136)

```text
The ordering of the boxes is 1, 11, 111, V, VI, VIII, IX, X, XIII;
M, XIV; W; VII; XII, and rx, rx, XIV, 111, 11 rust also be the iædiate
successors of IV, VII, XII, XIII, XIV, respectively. In addition, LX cannot
be placed irmediately after VIII, since IX,I is O but IX must nevertheless
be the irrrrediate successor of VIII. All this necessitates the extra orders
XIII,I
30
2
3
4
30
5
32
6
7
8
32
(to
111,1)
XIV,I
2
3
4
D.2
5
s.
6
7
8
s.
9
(to
11, 1)
IV,8
h
h
s
h
h
s
s
-63-
Ac
Ac
30
Ac
Ac
32
Ac
Ac
Ac
(a(v+l) (p+l))
(2'+1(p+1))
VII,6
VIII,3
XII,6
XIII,9
xn', 10
0-41
IX,I
IX,I
XIV,I
111,1
11,1
c
c
Finally in order that X be the itmediate successor of IX, the e of
(in 26) nwst be equal to X, l.
We now assign C. 1-4, D. 1-3, s. I their actual values, pair the 76
orders 1, 1-6, 11, 1-4, 111, 1-5, rv,1-8, V, 1-5, VI,1-4, VII ,1-6, VIII, 1-3, X,1-6.
X1,1-4, MI, 1-6, XIII,1-9, XN, 1-10 to 38 words, and then assign - XIV,IO
their actual values. (IX is cynitted, since it is contained in 0-41. ) We wish
to do this as a continuation of the code of 11.3. We will therefore begin with
the number 42. Furthermore the contents of D. 1-3, s. I are irrelevant, like
those of 37-41 there. We saw, in addition, that 30-35 (gith the exceptions of
30.32) are also irrelevant. rmst, hcwever, make this reservation: 30-41
are needed whi le box IX and during this pericxi D. 1-3 are relevantly
s. I is relevantly occupied only while boxes X II, XIV
occupied, but not s. l.
operate, and during this period 30-35 and 37-41 are irrelevant. Hence only
s. I can be made to coincide with one of these, say wi 41. Sunning all these
things up, we obtain the following table:
```

<a id="planning-and-coding-136"></a>
## planning-and-coding-136 — 11.4: sorting, reused routine and explanatory representations (physical page 154; Volume II printed page 64)

Source: [physical PDF page 154](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=154); reading unit `p154`, lines 4–179.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Worked examples applying the external flow/storage/assertion and parallel explanatory-column method. Mathematical assumptions, notation changes, code variants and machine details are retained as the context of the representations, not as separate advice about inline comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment, arrows and diagram topology. Consult the original PDF for the actual representation. Mathematical correctness was not independently proved.

Related: [planning-and-coding-135](#planning-and-coding-135), [planning-and-coding-137](#planning-and-coding-137)

```text
42
44
47
49
51
52
53
54
55
56
42 -441
VIII,1-3
w, 1-8
45
VII, 1-6
II, 1-4
47 -49
111, 1-5
1-6
491_511
Xl, 1-4
63 -64'
v,1-5
52
VI, 1-4
xw,1-10
63 G,
30 h-
85 h,
84 h-
oc
85 h-
47 c
41 -M
41 s
65 c
82 h-
77 cc
33 s
84 s
85 h-
45 c
85 h
31 s
30 h-
X, 1-6
Kill, 1-9
coded sequence;
Now we
35
80
81
85
86
84
h,
70 cc.
84
82
h-,
84
85 h-,
obtain this
84 s
85 s
86 s
30 s
32 s
84
30
31 s
84 h
74
34 s
30
84 h
54
-55
55 _ 58
65
82 h
30
84 h
32
84 h
84 h
84 h
85
86
41
xn,
c. 1-4
D. 1-3
s.
72
73
74
75
76
77
78
79
80
81
84
85
86
33
s,
34 s
34 s,
80
70 —73'
74
77
80 -83
84 -86
41
83
86 h
57
58
59
61
62
63
64
65
67
69
70
71
84
84
h,
30 s
84 h
32 s ,
84
84
41 s
85 s,
86 s
82
For the sake of completeness, we
contains all changes and all substitutable
and 30-41:
26
30
31
32
55 ,
10 cc'
33
34
35
36
restate that part of 0-41
constants of the problem.
39
40
41
of 11.3, which
Ibis is 26
VII: 225 g,
375 u.
The durations may be estimated as follows:
1: 225 g, 11: 150B, 111: 200 u, IV: 300 u, V: 200 g, VI:
VIII: 125 g, X: 225 XI: 150 u, 225 g, XIII: 350 U,
[X: Ihe precise estimate at the end of 11.3 is
((575p 1,125) (nw + 575) u.
Total: put 2 < log nS , n = 2 < 'log - (2 log
- . Then the total is
150 u,
XIV:
O or l,
```

<a id="planning-and-coding-137"></a>
## planning-and-coding-137 — 11.4: sorting duration derivation completing the worked example (physical page 155; Volume II printed page 65)

Source: [physical PDF page 155](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=155); reading unit `p155`, lines 20–66.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume II. Completion of the sorting example.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-136](#planning-and-coding-136)

```text
-65-
(V •(VIC)
or vlll)))
Xlv•
(XC' or XIID
111
1 • 11
is majorized by
(225 + 'i 150 +
5 = - .06
(IVO or
+1X+X+
• ) "XII (+1)
200 +200 +150 +125 p + 1, 125) x
+ 100 -
x (n 575 + 225 + 350
200 375
- 375 + 225 (fi+l)) U.
Since (nw + ) = n, l, this is majorized hy
(225 + 'i
((575 p
1,125) n + 425} 75) g.
Since S ( n + 1) n + ü, this is majorized by
((575 p + 1,125) • 1,825 n + 2,250 v + 300) g.
We can write this in this form:
((575p• 1,200 (1 5)) n i) (.6 (p +2 (1 + 6)) n m,
where
= •2 Z 4 log n
1 52
1 83
25
is a snall and slowly changing quantity: For n 100; l, 000; IO, 000
6
(the last value is, of course, inccnpatible with the memry capacities which
appear to be practical in the near future) we have = 8; IO; 14 and hence
5 . 15; 09; .05, respectively.
At mst. once anx)ng the w in
We disregard this effect for IV, which
represents the shorter alternative. replace VII, XI by their alternatives,
VIII, XIII, respectively, inside the . 'Ihis necessitates the corrections
(Cf. the
VII-VIII = 100 g, XI-XIII -200 u, respectively, outside the
third and secmd terms from the right in the brackets ( .
of the next forrnula. )
Missing once annng the v in . We may therefore subtract XIV
375 u as
a correction outside the
```

<a id="planning-and-coding-138"></a>
## planning-and-coding-138 — 12.1-12.5: composing, naming and preparing reusable routines (physical page 165; Volume III printed page 1)

Source: [physical PDF page 165](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=165); reading unit `p165`, lines 4–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-139](#planning-and-coding-139), [planning-and-coding-025](#planning-and-coding-025)

```text
12.0 COMBINING ROUTINES
12. I Each one of the problems that we have coded in the past
Quapters 8 -l I had the following properties: ne problem was cmplete in the
sense, that it led fro-n certain unambiguously stated assumptions to a clearly
It was incanplete, htNever, in another sense:
defined result.
It was certain
in cases and very likely in others, that the problem in question in
actual practice not occur by itself, as an isolated entity, but rather as one
of the constituents of a larger and rmre cunplex problem. It is, of course,
justified and even necessary a didactical point of view, to treat such
partial problerns, problem fra5nents especially in the earlier stages of the
instructicm in the use of a code, or of coding per se. As the discussion ad-
vances, however, it increasingly desirable to turn one' s attention
more and more fran the fragments, the constituent parts, to the whole, In mar
present discussion, in particular, we have now reached a point where this change
of emphasis is indicated, and we proceed therefore accordingly.
lhere are, in principle, two ways to effect this shift of emphasis from
the parts to the whole.
first way is to utilize the experience gained in the coding of
simpler (partial) probleffks when one is ccHing mre ccxnplicated (rnore cmplete)
problems, but nevertheless to code all the parts of the complicated problem
explicitly, even if equivalent simple problems have been coded before.
The second way is to code simple (partial) problems first, irrespective
of the contexts (more complete problems) in which they may occur subsecpently, and
then to insert these coded sequences as wholes, when a canplicated problem occurs
of which they are parts.
We should i I lustrate both procedures with examples: Ibis is not easy
for the first one, its use is so •frequent that it is difficult to circum-
scribe i ts occurrences with any precision. Thus, if we had coded the calculation
of the general third order polynmial, then any subsequent calculation involving
(as a part) a third order polynomial, would offer such an example. Also, in view
of Problem l, any calculation involving a quotient of a second order and a first
order polynanial would be an example. Problem 3, where the whole of Problem I is
recoded as a part of the new ccxied sequence (but not Problem 2, where this is not
done) is a specific instance.
Examples of the second procedure are more clearly identifiable.
Problem 12 was used in this sense as a part of Problem 13. a and of Problem 13. b,
and also, after rndifications, as a part of Problem 13. c. Problem 14 was
In addition it is fairly clear that all of the
used as a part of Problem 15.
Problems 4-11 and 13-15 nmst be intended as parts of more complicated problerns,
and that it would be very convenient not to have to recode any one of them when
it is to be used as part of another problem, but to be able to use it more or
less unchanged, as a single entity.
```

<a id="planning-and-coding-139"></a>
## planning-and-coding-139 — 12.1-12.5: composing, naming and preparing reusable routines (physical page 166; Volume III printed page 2)

Source: [physical PDF page 166](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=166); reading unit `p166`, lines 4–53.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-138](#planning-and-coding-138), [planning-and-coding-140](#planning-and-coding-140), [planning-and-coding-159](#planning-and-coding-159)

```text
-2-
12.2 last remark defines the objective of this chapter'. We wish
to develop here arthods that will permit us to use the coded sequence of a problem,
when that problem occurs as part of a rrnre canplicated one, as a single entity, as
a whole, and avoid the need for recoding it each time when it occurs as a part in
a new context, i.e. in a new problem.
Ihe importance of being able to do this is very great. It is likely to
have a decisive influence on the ease and the efficiency with which a cornputing
autamt of the type that we contemplate will be operable. possibility should,
more than anything else, remove a bottleneck at the preparing, setting up, and
cofing of problems, which might otherwise be quite dangerous.
nlis principle mist, of course, be applied with certain comcm sense
limitations: niere will be whose coded sequences are so simple and so
short, that it is easier to reccxåe them each tire when they occur as parts of
another problem, than to substi tute them as single enti ties
i.e. where the work
of recoding the whole sequence is not sigui ficantly more than the work necessi tated
by the preparations and adjustnents that are required when the sequence is substi-
tuted as a single entity. (These and adjustrænts constitute one of
the main topics of this chapter, cf. 12 . 3-12. 5.) Thus the examples of the first
procedure discussed in 12.1 above are instances of problens that are nsimplell and
"short" in this sense.
For problerns of rædium or higher canplexity, hcxever, the principle
applies.
It is not easy narre a precise limit for the cmplexity, say in
terms of the numker of words that make up the coded sequence of the problem in
question. Indeed, this Ity•.er limit cannot fail to depend on the precise character-
istics of the canputing device under and quite particularly on the
properties of i ts inmlt organ. Also, it can hardly be viewed as a quite precisely
defined quantity under any conditions. As far as we can tell at this mment, it
is probably of the order of 15-20 words for a device of the type that we are
contemplating (cf. the fourth remark in 12.11).
These things being we may state that the pcssibility of
substituting the coded sequence of a simple (partial) problem as a single entity,
a whole, into that one of a more camplicated (more cmplete) problem, is of basic
importance for the ease and efficiency of running an automatic, high
ccrnputing establishnent in the way that seers reasonable to us. We are therefore
going to investigate the nethuås by which this can be duue.
12.3 We call the coded sequence of a problem a routine, and which
is forned with the purpose of possible substitution into other routines, a
subroutine. As nentioned above, we envisage that a properly organized autormtic,
high speed establishnent will include an extensive collection of such subroutines,
of lengths ranging fran about 15-20 words uv»ards. I.e. a "library" of records in
the form of the external "Edium, presumably magnetic wire or tavk. Ihe
character of the which can thus be disposed of in advance by of such
subroutines will vary over a very wide spctrum indeed a much wider one than is
now generally appreciated. Sone instances of this will appear in the subsequent
Qapters 13 and 14. Ihe discussions in those chapters will, in particular, give a
mre specific idea of what the possibilities are and what airs possess, in our
opinim, the proper proportions.
```

<a id="planning-and-coding-140"></a>
## planning-and-coding-140 — 12.1-12.5: composing, naming and preparing reusable routines (physical page 167; Volume III printed page 3)

Source: [physical PDF page 167](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=167); reading unit `p167`, lines 3–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-139](#planning-and-coding-139), [planning-and-coding-141](#planning-and-coding-141)

```text
Ikt us now see what the requirerænts and the difficulties of a general
technique are, if this technique is to adequate to effect the substitution of
subroutines into routines in the typical situations
12 . 4 The discussion of the precise way in which subroutines can be
used, i.e. substituted into other routines, centers around the changes which have
to be applied to a subroutine when it is used as a substituent.
These changes can classi fied as follows:
characteristics of the subroutine change fran one substi tution of
the subroutine (into a certain routine) to another one (into another routine), but
they remain fixed throughout all LEes of the subroutine within the sarr substitu-
tion (i.e. in connection with one, fixed routine). Ibese are the changes of the
first kind. Other characteristics of the subroutines may even vary in the course
of the successive uses of the subroutine wi thin the san-E substitution. These are
the changes of the second kind.
ntus the order position at which a subroutine begins is constant through-
out one substitution (i.e. routine, or, equivalently, one larger problem of which
the subroutine's problem is part), but it may have to vary from one such substitution
or problem to another.
Ihe first assertion is obviously in accord with what will be
considered norrrnl usage, the seccnd assertion, however, needs Sa-re further elaboration.
If a given subroutine could only be used with its beginning at one parti-
cular position in the rmmory, which rmst be chosen in advance of all its applications,
then i ts usefulness would be seriously limi Led. In particular, the use of several
subroutines within one routine would be subject to very severe limitations. Indeed,
two subroutines could only be used together, if the preassigned regions that they
occupy in the memory do not . intersect.
In any extensive Illibraryll of subroutines
it would be impossible to observe this for all combinations of subroutines simul-
taneous ly. the other hand, it will be hard to predict with what other subroutines
it guy be desirable to ccnbine a given subroutine in sorne fu ture problem. Further-
rrnre, it will Frobably be very important tio develop an extensive Illibraryl' of sub-
routines, and to be able to use it with great freedom. All solutions of this dilerma
that are based on fixed positioning of subroutines are likely to be c lurrsy and of
insufficient flexibility.
Hence we should postulate the variability of the ini tial a-der position
of a subroutine from one substi tution to another. Gnsequently this is an example
of a change of the first kind. This requires corresponding adjustnrnts of all
references rnade in orders of the subroutine to definite (order or storage) positions
Wi thin the subroutine. as they occur in the final form (the final enumeration) of its
coding. Ihese adjustments are, therefore, changes of the first kind.
parameters or free variables of the problem that is represented by
the subroutine (cf. 7.5) will, on the other hand, usually change from one use of
the subroutine (within the same substi tution, i.e. the same main routine or problem)
to another. •ne sarre is true for the order posi tion in the main routine, frun which
the control has to continue after the completion (of each particular use) of the
subroutine. Since the subroutine sends the control after i ts completion to e (this
```

<a id="planning-and-coding-141"></a>
## planning-and-coding-141 — 12.1-12.5: composing, naming and preparing reusable routines (physical page 168; Volume III printed page 4)

Source: [physical PDF page 168](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=168); reading unit `p168`, lines 4–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-140](#planning-and-coding-140), [planning-and-coding-142](#planning-and-coding-142)

```text
is the notation that we have used in all our up to now, and we propose to
continue using it in all subsequent codings), this observation can also be put as
follows: Ihe actual value of e will usually change from one use of the subroutine
to another.
These remarks imply, that the paraneters of the subroutines problem, as
well as the actual value of its e, will usually undergo changes of the second kind.
12.5 All the changes that the use of a subroutine in a given substi-
tution requires can be effected by the routine into which it is being substituted,
For changes of
i.e. by including apprcvriate coded instructions into that routine.
the second kind this is the only possible way. For changes of the first kind, how-
ever, it is not necessary to put this addi tional load on the main routine.
In this
case the changes can be effected as preparatory steps, kEfore the main routine it-
self is set in motion. Such preparations might be effected outside the machine
(possibly by manual procedures, and possibly by more or less automatic, special,
subsidiary equigrent).
It seems, however, much preferable to let the machine itself
do it by reans of an extra routine, which we call the preparatory routine. We will
speak accordingly of an internal preparation of subroutines, in contradistinction
to the first rwntioned outside process, the external preparation of subroutines.
We have no doubt that the internal preparation is preferable to the external one
in all but the very simplest cases.
Thus changes of the first kind are to be effected by preparatory routines,
which will be discussed further below. Ganges of the second kind, as we have
pointed out already, have to be effected by the main routine itself (into which the
subroutine is being substituted): &fore each use that the routine makes of the
subroutine, it must appropriately substitute the qunntities that undergo changes
of the second kind (the parameters of the subroutines problem and the actual value
of its e, cf. the discussion in 12.4), and then send the control to the beginning
of the subroutine (usually by an unconditional transfer order).
It may happen that
some of these quantities remain unchanged throughout a sequence of successive uses
of the subroutine.
In this case the corresponding substitutions need, of course,
be effected once, jointly for the entire sequence. If this sequence includes all
uses of the subroutine wi thin the routine, then the substitutions in question need
only be performed once in the entire routine, at any sufficiently early point in it.
In this last case we are, of ccmrse, really dealing with changes of the first kind,
and the quantities in question could be dealt with outside the main routine, by
preparatory routine. It is, however, sorretirrps preferable to view this case as
an extrenE, degenerate form of a change of the secmd kind, or at any rate to
treat it in that way.
"Olis discussion should, for the tinw being, suffice to clarify the
principles of the classification of subroutine changes, and of the effect which
they (specifically:
the changes of the second kind) have on the arrangements in
the main routine ( into which the subroutine is being substituted). We now pass
to the discussion of the preparatory routine, which effects the essential changes
of the fi rst kind: Ihe adjustrents that are required in the subroutine by the
variability of its initial order position.
```

<a id="planning-and-coding-142"></a>
## planning-and-coding-142 — 12.6-12.8: subroutine assumptions, descriptive conventions and diagram/code deviations (physical page 169; Volume III printed page 5)

Source: [physical PDF page 169](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=169); reading unit `p169`, lines 5–54.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-141](#planning-and-coding-141), [planning-and-coding-143](#planning-and-coding-143)

```text
-5-
12.6 Assurre that a gi ven subroutine has been coded under the assurnp-
Lion that it will at the order position a. (I.e. at the le ft-hand order of
the word a.
o simplify matters, we disregard the that it nay begin
at the right-hand order of the word a.
In our past ccxåings we had usually a O,
excepting Problem 2 where a ¯
100, Problens 13, a-c where a
52, and Problem 15
where a 42. ) 'lhe orders that are contained in this subroutine can be classified
as follows:
First: •nue order contains no reference to a position x. It is then
one of the orders IO, 20, 21 of Table II.
Second: order contains a reference to a trprrx»ry position x, but the
place of this x is irrelevantly occupied in the actual code of the subroutine.
In
this case the subroutine itself must substitute appropriately for x, before the
control gets to the order in question. I.e. earlier part of the subroutine
must form the substitution value for x, and substitute it. into the order.
Third: ne order contains a reference to a memory position x, the place
of this x is relevantly occupied in the actual code of the subroutine, and this
actual value of x corresponds to a posi Lion not in the subroutine.
Fourth: Sarre as the third case, except that the actual value of x
corresponds to a rrerory posi tion in the subroutine.
Fifth: of the preceding cases, but at s«re M' int the subroutine
treats the order or its x as if it were irrelevantly occupied, i.e. it substi tutes
there else. -
Assurre next, that the subroutine, although coded as if it Ergan at a, is
actually to be used beginning at ä. Ibis necessi Cates certain changes, which are
just the ones that the preparatory routine has to effect, in the sense of the con-
cluding remark of 12.5. (hr above classification of the orders of the subroutine
permits us to give nc»• an exact listing of these changes.
Orders of the first and of the third kind require clearly no change.
Ihe sane is true of the orders Of the second kind if they produce x's which
correspond to rremry positions not in the subroutine. And even if x 's are
produced which correspond to posi tiops in the subroutine, no change is
necessary if the following rule has been observed in coding the subroutine:
a was used explicitly in forming the x that corresponds to posi cions in the
subroutine, and it was stored not as the actual quantity a, but as a paratreter
of the subroutine's problem. If it is then understood, that this paranEter should
have the value ä, then it will adequately treated as a paraneter in the sense
of 12.5.
Indeed, it represents that degenerate form of a change of the seccvld
kind, which can also be viewed as a change of the first kind, as discussed in 12.5.
Thus it might be treated by a special step in the preparatory routine, but we
prefer to assurre, in order to simplify the present discussion, that it is handled
as a paramter (of the subroutine) by Che routine.
In this way the orders
of the second kind require no change either (by the preparatory routine
```

<a id="planning-and-coding-143"></a>
## planning-and-coding-143 — 12.6-12.8: subroutine assumptions, descriptive conventions and diagram/code deviations (physical page 170; Volume III printed page 6)

Source: [physical PDF page 170](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=170); reading unit `p170`, lines 6–47.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-142](#planning-and-coding-142), [planning-and-coding-144](#planning-and-coding-144)

```text
-6-
Orders of the fourth kind clearly require increasing their x by - a.
Orders of the fifth kind behave like a combination of an order of one of
the four first kinds with an order of the second kind. Since all of these orders
are covered by the that errErged from our discussion of the four first kinds
of orders, it ensues that the orders of the fifth kind are automtically covered, too,
by those rteasures.
nus the preparatory routine has precisely one task: To add ä - a to the
x of every order of the fcmrth kind in the subroutine.
12.7 Ihe next question is this : By what cri teria can the preparatory
routine recognize the orders of the fourth kind in the subroutine?
Let be the length of the subroutine. By this we the number of
words, both orders and storage, that make it up. We include in this count all
those words which have to be nuved together when the f inal code (final enumeration)
of the subroutine is moved (i.e. when its initial order position is moved fran a
to ä), and no others. Ihe count is, of course, made on the final enuneration.
In this sense a word counts fully, even if it contains a dummy order (e.g. 14 in
Problem 6, and 6 in Problem IO or 74, 91 in Problem 13. b). the other hand
storage pcxsi tions which are being referred to, but which are suppcrsed to be parts
of other routine, already in the rnachine (i.e. of the Min routine, or of an-
other subroutine) do not count (e.g. the storage area A in Problem 3 or the storage
area A in Problem IO).
or an order of the fourth kind x must have one of the values
-l, i.e. it must fulfill the condition
(1)
For an order of the third kind x will not fulfill this condition. For orders of
the first and of the second kind the place of x is inessentially occupied.
Concerning its relation to condi tion (l) we can make the two follcwing remarks:
First: We can stipulate, that in a orders where the ition of x is
inessentially occupied, x should actually be put in with a value x that violates
(l). This is a perfectly possible convention. The simplest ways to carry it
into effect are these:
let x always have the smal lest value or always have the largest value
that is cunpatible with its 12-digit character. the latter, cf.
section 6.2.) I.e. x
= O or x
= L-l, where L-l is the largest 12-digit integer:
L 212 4,096. nen all subroutines must fulfill a O or a respectively
(in order that (l) be violated).
= O in mst of our codes,
These rules are easy to observe. We chose a
hence we might prefer the second rule, but this is a quite unimportant preference.
```

<a id="planning-and-coding-144"></a>
## planning-and-coding-144 — 12.6-12.8: subroutine assumptions, descriptive conventions and diagram/code deviations (physical page 171; Volume III printed page 7)

Source: [physical PDF page 171](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=171); reading unit `p171`, lines 7–57.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-143](#planning-and-coding-143), [planning-and-coding-145](#planning-and-coding-145)

```text
Second: If an order of the first or of the second kind has an x which
fulfills (l), and the order is thereupon mistakenly taken (by the preparatory
routine) for one of the fourth kind, and its x is increased by ä
- a, this need
not matter either. Indeed: Ihe place x is i rrelevantly occupied, hence changes
which take place there before the subroutine >egins to operate do not matter.
There is, however, one vy»ssible canplication: Adding -
a to this (inessential)
x my produce a carry beyond the 12 digits that are assigned to x.
these 12 digits cf. above. and also orders 18, 19 of Table II and the second
remark anong the Introductory Remarks to Chapter IO. •me carry in question will
occur if a > O and x - a), or if -
a O and x <
cf. above.) Such a carry affects the other digits of the order, and thereby modi-
fies its neaning in an undesirable way. This complication can be averted by
special measures that paralyze carries of the Cype in question, but we will not
discuss this here. No precautions are needed, if we see to i t that no such
(I.e. if we observe -(ä -a) x - (ä -a) for the inessential
carries occur.
x, cf. above. )
In view of these observations we may accept (l) as the criterium
defining the orders of the fourth kind. We will therefore proceed on this basis.
12.8
We have to derive the preparatory routines which are needed to
make subroutines effective. For didactical reasons, we begin with a preparatory
routine which can only be used in conjunction with a single (but arbitrary) sub-
routine. Having derived such a single subrout ine preparatory rout ine, we can
then pass to the rrx»re general case of a preparatory routine which can be used in
conjunction with any number of subroutines. This is a general, or multiple
subroutine preparatory routine. Ihe point in all of this is, of course, that both
kinds of preparatory routines need only be coded once and in advance they can
then be used in conjunction with arbi trary subroutines.
We state now the problem of a single subroutine preparatory routine.
niis includes a description of the subroutine, in which we that the sub-
routine has been coded in confomity with the (not a priori necessary) conventions
that we found convenient to observe in our codings in these reM)rts.
It does not
seem necessary to discuss at this place possible deviations frcxn these conventions,
and the rather simple ways of dealing wich them.
PROBLEM 16.
A subroutine cmsisting of consecutive words, of which the k first
ones are ( two) order words, is given. (Concerning the definition of the length of
a subroutine, cf. the beginning of 12.7. subroutine under consideration may
also make use of stored quantities, or of avai lable storage capacity, outside this
sequence of words
or rather of the J -k last ones amng them. We need not
pay any attention to such outside positions in this problem.) This subroutine is
cded as i f it Ekgan at the position a. Actually, however, it is stored
It is desired to modify it so that
in the rrwrrx»ry, beginning at the position ä.
its coding conform with its actual position in the mermry. - -
```

<a id="planning-and-coding-145"></a>
## planning-and-coding-145 — 12.6-12.8: subroutine assumptions, descriptive conventions and diagram/code deviations (physical page 172; Volume III printed page 8)

Source: [physical PDF page 172](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=172); reading unit `p172`, lines 22–66.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-144](#planning-and-coding-144), [planning-and-coding-146](#planning-and-coding-146)

```text
-8-
(hr task consists in scanning the words frcxn to + k - l, to inspect
in each one of these words the two orders that it contains, to decide for each
order whether its x fulfills the condition (l) of 12.7; and in that (and c*lly in
that) case increase chis x by k ä -
Let the rremry positicm u be occupied by the word w . w is then an
aggregate of 40 binary digits:
w (40) ) .
nie two orders of which it consists are the two 20 digit aggregates
(w (21),
+ 2-39K
the two x in these
(cf. orders 18, 19
Reading
orders are the two 12 digit aggregates
{w (9), ..., w (20)), (29),
of Table II).
11
w , w as binary numbers with the binary point at the extreme
left (and an extra sign digit O), the condi tion (l) of 12.7 beccnes
(1)
and
(2)
2-12
a $ WI < 2-12 (a + X),
< 2-12 (a n.
Reading w as we ordinarily read binary aggregates, i.e. as a binary number with
the binary between the first and second digits from the left (the first
digit being the sign digit) we
(2) holds, we nmst increase w
can now express our task as follows: If (l) or
by 2- or 2 - 39k, respectively. I.e.
+2-1
v.
(3)
(4)
Note ,
if (l) holds,
othergise ,
if (2) holds,
otherwise.
that we may replace
2-12
for its use in (4), by
12 (a +1) ,
```

<a id="planning-and-coding-146"></a>
## planning-and-coding-146 — 12.6-12.8: subroutine assumptions, descriptive conventions and diagram/code deviations (physical page 173; Volume III printed page 9)

Source: [physical PDF page 173](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=173); reading unit `p173`, lines 10–59.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-145](#planning-and-coding-145), [planning-and-coding-147](#planning-and-coding-147), [planning-and-coding-148](#planning-and-coding-148)

```text
_9_
where
( wt(29), .
, 11
since w and w' have by (3) the same digits with the positional values 2-20
i.e. with the numbers 21,
40.
words w with which we have to deal are in the interval of rrærmry
I (i.e. a, . , ä+k - l, cf. above). [et this
locations a + k, ,
a + x + k - l, so
be the storage area O, we will index it witha u a + x, ,
that O. u corresponds to u, and stores . u has the character of an induction
index.
Further storage capaci ties are required as follows: u (as uo) in A, the
w under consideration (and wt after it) in B, the given data of the roblem,
a, y, k, x, in C. (It will be convenient to store them as 2-19 a, 2-1
1 9k. these quantities cf. also further below.) Stora will also
2.12 2-32)
have to be g•ovided for various other fixed quantities I
these too will be accomodated in C.
We can now draw the flow diagram, as shc»n in Figure 12.1.
In coding
it, we will encounter deviations and cornplications which should be ccmnented
a, I, k, x Mist occasionally be manipulated along the lines discussed
in connection with the coding of Problem 13. a. in the case of k transitions
to 2-39K and Co KO occur, and these would be rendered more di fficult if we had to
allow for the possibility v. < O. In order to avoid this rather irrelevant canpli-
cation, we
_ 2-19
(5)
i.e. ä?a.
This has the further consequence, that the di fficulties referred to in 12.7 can
be avoided by gi ving every irraevant x the value O (because of the second
rernark in 12.7) or the value L -l (because of the first remark in 12.7). We
= O, i.e. by coding every
also note this: (5) can be secured by putting all a
subroutine as if it at O, but we will not insist here that this convention
be made.
can be tested by
condi tions (l),
testing the signs of the
quan tl ties
- 2-12
_ 2 12 a, w, 11 _ +1)
or, equivalently. the signs of the quanti ties
- 2-19
2-19(a +1),
a,
2-7 will
```

<a id="planning-and-coding-147"></a>
## planning-and-coding-147 — 12.6-12.8: subroutine assumptions, descriptive conventions and diagram/code deviations (physical page 174; Volume III printed page 10)

Source: [physical PDF page 174](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=174); reading unit `p174`, lines 7–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-146](#planning-and-coding-146), [planning-and-coding-148](#planning-and-coding-148)

```text
It is easily seen that replacing 2-19 a,
-10-
2-19 (a +1) by ao
vi tiates these
sign-cri terla,
does not have
but replacing
wlu {w
. , (20)', w (21),
It is convenient to use WI + E in place of WI .
this effect.
quantities WI + e and w 'II
must be read as binary nurnbers with
the binary point at the extrare left, with an extra sign digit O. Indicating
this digit, too, we
(6)
With the same notations
(7)
have
, w (40) ) ,
In order to get the WI + E
b/ 2-32 u
to mltiply w , w'
{ o, w'(29), .
2212
of (6) from the w , wt of (7), it seerns sirrplest
respecti vely, and to pick up WI + E in the
register (cf. order II of Table II). There is, however, one minor cornplication
t II of but the
at this point; Ihe register conta ins not thew + E , w
aggregates
, w (40)
w'(40) l.
{ w'(29), w'(29), w'(30), .
simplest way to get from to (6) is to sense the sign of each quantity of
(6), and to add -l to it if it proves to be negative (i.e. if the sign digit is l).
We will do this; it requires an additional conditional transfer in connection wi th
each one of the two boxes Ill and VI. For this reason two boxes 111.1 and VI. l,
not shown in the flow diagram, will appear in our coding.
To conclude, it is convenient to change the posi tion of IX sorræwhat
(it follows upon VIII and ahsorhs part of it) and to absorb XI into X (it is
replaced by X, 9).
```

<a id="planning-and-coding-148"></a>
## planning-and-coding-148 — 12.8: preparatory routine flow diagram and explanatory code (physical page 175; Volume III printed page 11)

Source: [physical PDF page 175](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=175); reading unit `p175`, lines 3–15.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-147](#planning-and-coding-147), [planning-and-coding-149](#planning-and-coding-149), [planning-and-coding-146](#planning-and-coding-146)

```text
-11-
1
J
WY fop u
w„
4
4
4
4
6
Wv foe a•kS V <
otAerw;se
FIGURE IZ.I
```

<a id="planning-and-coding-149"></a>
## planning-and-coding-149 — 12.8: preparatory routine flow diagram and explanatory code (physical page 176; Volume III printed page 12)

Source: [physical PDF page 176](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=176); reading unit `p176`, lines 4–36.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-148](#planning-and-coding-148), [planning-and-coding-150](#planning-and-coding-150)

```text
-12-
static of the knxes I-Xl follows:
s.
(to 11, 1)
2-19
2-19 (a+k)
2- 39(a+K)
(a+x)o
11,1
2-32
111, 1
111,5
111.1, 1)
2-7
2-7
111.1, 1
11,3
(to 111,1)
11,3
111.1,
Sp
(10), ...,w (40)) =
(to VI, l)
2-191
IV,I
VI,I
(to V, l)
(to VI,I)
2-12
2-7(w1 + E )
2-7 (WI + E ) _ 2-19 a
-2-19(a+I)
+2-19K-
```

<a id="planning-and-coding-150"></a>
## planning-and-coding-150 — 12.8: preparatory routine flow diagram and explanatory code (physical page 177; Volume III printed page 13)

Source: [physical PDF page 177](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=177); reading unit `p177`, lines 7–42.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-149](#planning-and-coding-149), [planning-and-coding-151](#planning-and-coding-151)

```text
-13-
VI,I
Vl.l,l
(to VI. 1, 1)
VI, 1.1
VII,I
c.i
11.1)
= W'(29) +
W'(29)
VII, 1
2-7
2-7
c.6
rx, 1
(to VIII, 1)
s.
-2-19
2 19 (awl)
+2-39K
(to
LX,I
(to X l)
10
11
(to
Xl,l
(to
IX,4
s.
s.
s.
2-19(a+k)
2-19 (a+»ek)
(a+k+k )
(u-a-v.-k+l)
```

<a id="planning-and-coding-151"></a>
## planning-and-coding-151 — 12.8: preparatory routine flow diagram and explanatory code (physical page 178; Volume III printed page 14)

Source: [physical PDF page 178](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=178); reading unit `p178`, lines 4–81.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-150](#planning-and-coding-150), [planning-and-coding-152](#planning-and-coding-152)

```text
We must now assign A, B, C. 1-9, s. I their actual values, pair the 59
orders 1,1-5, 11, 1-4, 111,1-5, 1-5, IV, 1-2, V, 1-4, VI, 1-5, VI. 1,1-5, VII, 1-2,
VI Ili 1-6, M, 1-4, X, 1-12 to 30 words, and then assign l, I-X,12 their actual values.
w
e wish to place this code at the end of the nrmry, so that it should interfere
as little as possible with the merrory space that is normally occupied by other
subroutines and routines. [et us therefore consider the words in the rnemory
-14-
Note, chat the box Xl requi red no coding, hence its in-rrEdiate successor
VII, 1-2
_ 38
111, 1-5
VI,1-5
-s
33
(II) must follow directly upon its invnediate predecessor (X) .
nie ordering of the boxes is l, II, Ill, 111.1, u, VI. l, IX
V' VII, VIII, and VI, DC, II rmst also be the innediate successors of V,
respectively. Ihis necessi tates the extra orders
VIII, X,
VIII,6
x, 12
VI,I
rx, 1
11,1
c
c
c
backwards (beginning with the
reverse order referred to) by
table:
1, 1-5
11, 1-4
last
VI. 1,1-5
IX,l-4
x, 1-12
1-2
V, 1-4
word), and designate their numbers (in the
In this way we obtain the following
VIII, 1-6
s.
111.1,
33
32
25
Now we
obtain
this
coded sequence:
sp',
35 Q,
Tix,
Ihe
12
is
durations
19
16
may be estimated
150 u, III: 250 u, 111.1:
1: 200 4, 11:
VI: 250 u, VI. 1: 270 u, VII: 75 u, vill:
h,
as follows:
270 4,
225 u, n:
6
75 u, v:
150 u, x:
28
2-19
2-32
2-7
2-12
150 u,
450 u.
```

<a id="planning-and-coding-152"></a>
## planning-and-coding-152 — 12.9-12.10: multiple subroutines, explanatory code and setup context (physical page 179; Volume III printed page 15)

Source: [physical PDF page 179](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=179); reading unit `p179`, lines 13–72.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-151](#planning-and-coding-151), [planning-and-coding-153](#planning-and-coding-153)

```text
Total:
-15-
11+111 +111.1 or IV or IV+V)
+ Vl.l +
or VII or VII + VIII)
+1X+X
150 150
k
m ax in-um
200
+250+ 270 + 75 +225
+ 150* 450
k
(2,315k + 200) k + .2) m.
12.9 We now
requirerrents _ for such a
basic and simplest one.
tions involving the use
(Examples will occur in
PROBLEM 17
pass to the multiple subroutine preparatory routine. •ne
routine allow several variants. We will consider only the
It is actually quite adequate Co take care of mst situa-
of several subroutines even of very complicated ones.
our future codings, in particular in Chapters 13 and 14.)
SarrE as Problem 16 with this change: •nue man fication is desired for
. Ihe characteristic data for (in the sense of Problem
I subroutines ,
16) are a, , 1. , k. ,
Each 2, , is stored as its a , x. , and indicate (cf.
Problem lb, "e a. , } i , k. , K.I(i = l,
l) are stored at 41 suitable, consecu-
tive memry locations.
In order to be able to use the treat.rrEnt of Problem 16 in 12.8, we
assure in conformity with (5) in 12.8
(1)
v.. O for all i = I
(Cf. also the other pertinent remarks loc. cit. )
i is the induction index, running from I to l. For each value of i
we have to solve Problem 16. We can do this with the help of our ctÄ3ing of that
problem, but we mast substitute the data of the problem, a. , 1. , k. , k, , into the
Inspection of the coded sequence shows that tiese places
appr cpriate places.
are m, 5, 3, 9, respectively.
w
e propose to place the coded sequence that we are going to deve12p
irmrdiately before that one of Problem 16, i.e. irrrædiately before 42,
Let P be the number of the nerrnry location irmediately before Che coded sequence
if the length of that sequence is and
that we are going to develop -
the total nemry capacity is L t (both in terms of words), then
(2)
) e represents the
or frcxn VI via 5
w
e will use this
43 + 1'
possibility of going directly fran Ill via 4, 5 to VI,
to IX, respectively, with no other intervening.
sane notation in similar situaticms in the future.
```

<a id="planning-and-coding-153"></a>
## planning-and-coding-153 — 12.9-12.10: multiple subroutines, explanatory code and setup context (physical page 180; Volume III printed page 16)

Source: [physical PDF page 180](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=180); reading unit `p180`, lines 5–87.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-152](#planning-and-coding-152), [planning-and-coding-154](#planning-and-coding-154)

```text
-16-
We will place the a. , i. , k. , k. (i l), in the form 2•i9a., 2-191
, irmpdiately before these coded sequences, and in inverse a• der, i. e.
p-4i+å, P-4i +3, P-4i+2, P-4i+l, respectively.
11, 11
11,13
11,15
11, 17
2-19
2-19
2-19k.
at
induction index i will be stored in the form (P-4i+4)o in the stc age
area A. Ihe quantities P, I will be stored in the fom P , (P-41)0 in the storage
area B (IO will needed and taken frorn 2).
We can now draw the flow diagram, as shown in Figure 12.2. actual
coding obtains frcxn this quite directly, box V is abso&d into box II (it is
replaced by II, IO).
The static ctxiing of the I-V follows;
2
11,1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
(to 11, 1)
(to 111,1)
11, 11
13
11,
11,15
11,17
p_4i +4
iö
P-4i+2
3
-9
Sp
h-
Sp
h-
Sp
Sp
h-
s
s
s
s
s
Ac
Ac
Ac
Ac
Ac
Ac
(P-4i+4)
p_4i+4
(P-4i+3)
p-4i +3
(P-4i+2)
P-4i+2
(P-4i+1)
P-4i+1
(P-4i)o
(P-4i)o
2-19 a
2.191
2.191
2-19k
2-19k
```

<a id="planning-and-coding-154"></a>
## planning-and-coding-154 — 12.9-12.10: multiple subroutines, explanatory code and setup context (physical page 181; Volume III printed page 17)

Source: [physical PDF page 181](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=181); reading unit `p181`, lines 4–11.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-153](#planning-and-coding-153), [planning-and-coding-155](#planning-and-coding-155)

```text
-17-
1
6
Z- to 10
O . p —41+4
z-"lt
Note. •
FIGURE 12.2
```

<a id="planning-and-coding-155"></a>
## planning-and-coding-155 — 12.9-12.10: multiple subroutines, explanatory code and setup context (physical page 182; Volume III printed page 18)

Source: [physical PDF page 182](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=182); reading unit `p182`, lines 5–52.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-154](#planning-and-coding-154), [planning-and-coding-156](#planning-and-coding-156)

```text
Note, that box V required no coding, hence its innediate successor (II)
mst follow directly upon its impdiate predecessor (IV) .
The ordering of the boxes is l, II, Ill, I V, and II rmast also be the
innediate successor_Qf IV. In addition, Ill cannot be placed irmediately after
II, since 111,1 is 42 but Ill rmst nevertheless the successor of
II. All this necessi tates the extra orders
111
(to IV,I)
(P-41)0
IV,I
2
3
(to 11, 1)
2 h. , 56 sp
(Problem 16: - i.)
-18.
Ac
Ac
(P-41)0
11, 19
IV,4
111,1
11,1
c
Finally, in order that IV the imediate successor of Ill, the e of 42 -
(in 21) rrnst be equal to W, I.
We must now A, B. 1-2 their actual values, pair the 25 orders
l, 1-2, II, 1-19, I V, 1-4 to 13 words, and then assi"l l, I-I V, 4 their actual values.
(Ill is omitted, since it is contained in - I.) We wish to do this as a
(backward) continuation of the code of 12.8. In this way we obtain the following
table:
1, 1-2
11, 1-19
lv,1-4
57 -48
48'-G
B. 1-2
Thus, in tems of equation (2), 16 and
(2')
56
55
53
59 L' - 59
Now we obtain this coded
sequence:
51
43
57 c,
```

<a id="planning-and-coding-156"></a>
## planning-and-coding-156 — 12.9-12.10: multiple subroutines, explanatory code and setup context (physical page 183; Volume III printed page 19)

Source: [physical PDF page 183](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=183); reading unit `p183`, lines 10–44.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-155](#planning-and-coding-155), [planning-and-coding-157](#planning-and-coding-157)

```text
-19-
In addition in 42 - of 12 .d rust read
Ibe durations may be estimated as follus:
1: 75 g, 11: 725 IV: 150 u.
Ill: Ibe precise estimate at end of 12.7 is
Total :
maxirmm = (2, 315 k. + 200) u.
(11 + 111
(725 + 2,315 k. +200 + 150))
maximun = (75 +
(2,315 k. + 1,075 1 +75)
—€(2.3 k. +1.1 1) m.
is the total length of all subroutines. Hence it is necessarily
L I S L 212 = 4,096. A:tually it is unlikely to exceed, even in very c mplicated
L ZI, 000. 1.1 1 is negligible compared to 2.3 k.
problems, the order
1%nce
2,300 m 2.3 seconds
is a high estimate for the duration of this routine.
12. IO Having derived two typical coded sequences for preparatory
routines, it is appropriate to say a few words as to how their actual use can
be contemplated. We do not propose to present a discussion of this subject to
any degree of
we only wish to point out of the mst
essential aspects. Since the routine of Problem 17 is mre general than that
one of h•oblem 16, we will base our discussion on the forrær.
discussion of the use of preparatory subroutines is necessarily
a discussion of a certain use of the input organs of the machine.
We have
refrained in our reports. so far, frcxn making very detailed and specific assump-
tims regarding the characteristics of the input (as well as of the output)
organs. At the present juncture, however, certain assumptions regarding these
Organs are necessary. the basis of engineering up to date,
such assumptims are pssible on a realistic basis. that we are go Ing
to for-malate represent a very conservative, minin_un program.
```

<a id="planning-and-coding-157"></a>
## planning-and-coding-157 — 12.10-12.11: external setup instructions and qualifications on reuse (physical page 184; Volume III printed page 20)

Source: [physical PDF page 184](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=184); reading unit `p184`, lines 7–48.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-156](#planning-and-coding-156), [planning-and-coding-158](#planning-and-coding-158)

```text
-20-
mr assumptions are these:
As indicated in section 4.5, we incline towards the use of mgnetic
wire (soundtrack) as input (and output) nedium. We expect to use it at pulse
rates of about 25,000 pulses (i.e. binary digits) per second. We will certainly
use several input (and output) channels, but for the purposes of the present
discussion we a single one.
We assunr that the cmtents of a wire can be "fed' t into the machine,
i.e. transferred into its inner, selectron rærmry, under rnanual control. We
asstup that we can then describe by manual settings
l) to which position the first fran the wire
should go (the subsequent words on the wire should then
go in linear order into the successive, following nemry
posi ,
2) many words from the wire should so "fed".
We assure finally, that single words can also "fed" directly into
the machine by typing then with an appropriate "typewriter". (This I 'typewriter"
will prcxiuce electrical pulses, and will nearly the sane as the one used to
on the mgletic tape. ) We 8ssunp that we can determine the rrrmry
position to which the word goes by manual settings.
last assumption, i.e. the possibility of typing directly into the
næmry, is not absolutely necessary. It is alternative to the previously
mntioned "feeding" of words a magnetic wire. muen longer sequences of
words have to be fed, the wire is preferable to direct typing. hen single
words, irregularly distributed, have to be fed, ht»ever, then feeding fr«n
appropriate wires would still feasible, but definitely rmre awkward than
direct typing. In addition, the possibility of direct typing into the nemry
is probably very desirable in connection with testing procedures for the
machine. We are therefore assuming i ts availability.
nlese things being understood, we can describe the procedure of
placing a, presumably comB)site, routine into the It consists of
the following steps:
First: There are one or mre constituent routines: The main routine
and the subroutines, where it is ikrfectly possible that the subroutines hear
further subordination relationships to each other, i.e. are given as a hierarchy.
All Of these are coded and stored on separate pieces of magnetic wire.
These are successively fed into the machine, i.e. into the inner
nemry. •nue desired Y's i tions in the nemry are defined by manual settings.
• ) These operations should also be feasible under the "inner 'l, electronic
control of the machine. We will discuss this of the input-outmat
organ. and the logical, code orders which it, in a subsequent
paper (part III in this series).
```

<a id="planning-and-coding-158"></a>
## planning-and-coding-158 — 12.10-12.11: external setup instructions and qualifications on reuse (physical page 185; Volume III printed page 21)

Source: [physical PDF page 185](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=185); reading unit `p185`, lines 11–53.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-157](#planning-and-coding-157), [planning-and-coding-159](#planning-and-coding-159)

```text
-21-
Second: The multiple subroutine preparatory routine (Problem 17) is
also coded and stored on an individual magnetic wire. (It is, of course, asst_nned
to be part of the library of wires mentioned in section 4.6.)
m s is also fed into the rnachine, like the I 'constituent" routines of
the first overation, descriEed above. As observed in 12.8 and 12.9 it has to be
posi cioned at the end of the nemry.
Third: constants of the multiple subroutine preparatory routine,
i.e. of Problem 17 , are typed directly into the nermry. Ihey are the follcning
ones:
l) number of subroutines, l, which is put in the form (P-41)
into the position
L' - 43 -P + 16.
2) Ibe 41 data which characterize the I subroutines: a i , X. , k. , K.
, 2-191: , 2219k'
, ...,l), which are put in the form 2 •19
2 • 19k. into Che positions P-4i+4, P-4i+3, p-4i+å, p-4i+i,
respecti vely.
Fourth: ne machine is set goiug, with the c set manually at
the beginning of the preparatory routine (58 = P +1), and the adjust-
of all subroutines to their actual positions (in the sense of 12.5-12.7)
is thus effected.
Fifth: Any further adjustments which are necessitated by the
relationships of the subrmtines to each other (cf. the first operation, as
described above, and the fifth remark in 12. II) are made by typing directly
into the mermry.
After all these operations have been carried out, the machine is
ready to be set going on the (composite) routine of the problem itself Ihe
preparatory routine (in the 58 last Tenor y positi ms) and its data (in the 41
preceding positions) are now no longer needed. I.e. these positions may now
be viewed, f rm the point of view of the problem itself, as irrelevantly
occupied. They are acc a-ding ly avai lable for use in this sense.
We can now draw scyrr conclusions c mcerning the setting-up
12.11
procedure for a machine of the type cmtemplated, On the basis of the dis-
cussion of 12. IO. We state these in the form of five successive remarks.
First: Ihe pure machine t required to feed the (main and subsidiary)
routines of the problem into the n-Bchine may be estinuted as follows: A word
cmsists of pulses. For checking and marking purposes it will probably have to
With the systems that we are envisaging, a total
contain sorr additional pulses.
of, say, 60 pulses per word will not be exceeded. With the sgred of 25, 000 pulses
per second, as assunrd in 12. IO, this gives 2.4 m per word.
```

<a id="planning-and-coding-159"></a>
## planning-and-coding-159 — 12.10-12.11: external setup instructions and qualifications on reuse (physical page 186; Volume III printed page 22)

Source: [physical PDF page 186](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=186); reading unit `p186`, lines 4–52.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-158](#planning-and-coding-158), [planning-and-coding-160](#planning-and-coding-160), [planning-and-coding-139](#planning-and-coding-139)

```text
-22-
Thus the pure machine tine of the first and second operations of 12. IO
is 2.4 m per word.
Ihe pure machine time of the third OF*ration of 12.10 is, as we saw at
the end of 12. 9, 2.3 m per word.
We also observed at the end of 12.9, that even in very canplicated
problerrs the mynber of words thus involved is not likely to exceed 1000. This
puts on the total tine requirenrnt on these counts an upper limit of
— 4.7 seconds, i.e. of less than 5 secmds.
2.4 +2.3
Second: These tine requirements are obviously negl igihle compared to
the t irre c cmsuned by the attendant manual operations: Ihe placing of the magnetic
wires into the rnachine, the setting of the (rprrKJry) position definitions, etc.
It follows therefore, that there is no need and no justification for
any special routine-preparing equip-rent (other than the typing devices already
discussed) to complement a machine of the type that we contemplate.
Third: Assuming a composite routine made up of ten parts, i.e. of a
routine and nine subroutines, we have I = 9. This represents already a very high
level of complication. Ihe preparatory routine requires 58 + 41 words, i.e. for
I = 9 94 words. This represents 2.3% of the total (selectron) capacity,
= 2-12 = 4,096.
if we assume that the latter is L r
Fourth: Each subroutine requires the direct, manual typing of four
I. , k. , k.) , as well as one for all subroutines
words into the machine (for a. ,
together (for l).
In addition the changes of the second kind in the sense of
12.4, i.e. those which the main routine mmst effect on the subroutine, require
several words. Indeed, the sending of the control to the subroutine remaires
one order, i.e. half a word. Any number is sent there at the price of two
orders (bringing the nurnlkr to be substituted into the subroutine into the accu-
rmalator, substituting it into the subroutine) and of possibly one storage word
(for the nurnber to be substituted), i.e. of a total of one or two words. There
will usually be three or rmre such nunber substitutions (the e of the subroutine,
i.e. the nenury position in the main routine from where the control is to con-
tinue after the completion of the subroutine. and two or more data for the sub-
routine) . Thus five words for these changes is a conservative estimate.
A subroutine consurnes therefore ten words in extra instructions, by
It seems therefore, that the storage of a subroutine
a cmservatlve estimate.
in a library of wires, in the sense of section 4.6, and its corresponding
treat"Ent as an individual entity becoaes justified when its length in words
is significantly larger than IO. A minirrmrn length of 15-20 words would there-
fore seem reasonable.
To conclude this discussion, we observe that in making these estimates,
we disregarded all 0FRrations other than the actual, rnanual typing of words (on
w Ire or into the machine). This is legitimate, because the time and the "Emory
requirenrnts of the automatic operations that are involved are negligible, as we
saw in our three first remarks.
```

<a id="planning-and-coding-160"></a>
## planning-and-coding-160 — 12.10-12.11: external setup instructions and qualifications on reuse (physical page 187; Volume III printed page 23)

Source: [physical PDF page 187](../../../../papers/goldstine-von-neumann-planning-and-coding-1947.pdf#page=187); reading unit `p187`, lines 4–27.

Attribution: Herman H. Goldstine and John von Neumann

Context: Part II, Volume III. Reuse/composition of separately coded routines and their assumptions, followed by external flow diagrams, explanatory coding columns and setup instructions. Retained as connected code-explanation context, not a statement advocating inline source comments.

Transcription/context notes: Physical page read visually. Windows OCR may lose equations, letters, explanatory-column alignment and diagram topology; consult the original PDF. Mathematical correctness was not independently verified.

Related: [planning-and-coding-159](#planning-and-coding-159)

```text
- 23-
e pointed out in our description Of the first operation in 12.
that the various subroutines used in connection with a main routine, may bear further
subordination relationships to each other. In this case they will also contain actual
references to each other, and these will have to be adjusted to the actual positions
of the subroutines in question in the These adjustrrEnts may be made as
changes of the second kind, in the sense of 12 . 4, by the routines involved. They may
also be handled by special preparatory routines.
We expect, however, that it will he
simplest in rm'st cases to take care of them by direct typing into the IIEmry, as
indicated in the description of the fifth operation in 12.
The adjusting of the references of a subroutine to itself, to the actual
position of the subroutine in the rrErnory, might also have been made by direct typing
into the machine. We chose to do it autmatically, however, by of a prepara-
tory routine, because these references are very frequent: Ihe great majority of all
orders in a subroutine contain references to this same subroutine. References to
another subroutine, on the other hand, are likely to be rare and irregularly
distributed. Ihey are therefore less Hell suited to automatic treatnrnt, by a
special preparatory routine, than to ad hoc, manual treatrent, by direct typing
into the machine.
Actual examples of such situations in which it will also be seen that
the proportions of the various factors involved are of the nature that we have
anticipated here, will occur in the subsequent chapters, and in particular in
Chapters 13 and 14.
```
