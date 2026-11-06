# Software Engineering at Google: source passages

Generated from records.json and the pinned reading text. No ranking or recommendation is implied.

Extent: `local_html_book`. Text SHA-256: `e9e6e7c4ba6bc52703f03d5198c1d531bbd3cc5cf68f6d6ccbd30f4f52f4605b`.

[Selections](records.json) · [Coverage and gaps](coverage.json) · [Collection index](../../README.md)

- Local HTML files preserve source text; images require separate inspection. One inherited email-deobfuscation script is absent.
- The reading text linearizes HTML inline markup, table cells and lists and does not preserve every code indentation or table column. Original HTML remains the authority; structural checks covered the two ch07 tables and preformatted specimens in ch08/ch10/ch12/ch18, not every page rendered in a browser.
- Figure 17-4 has a horizontally clipped query. Its visible portion and embedded code are supplemented; absent text is not reconstructed. Figure 20-1 supplement omits UI controls and the naming-warning regular expression, distinguishing the human review comment from source comments.
- Figures 23-4 and 23-5 were visually inspected as context for tracked test disablement, but graph curves remain in the original images; no data values were inferred or fully transcribed.
- Independent fidelity/omission audit has not yet been performed by a separate agent.

<a id="software-engineering-at-google-ch01-001"></a>
## software-engineering-at-google-ch01-001 — Hyrum's Law and the limits of published contracts

Source: [ch01.html](../../../../books/software-engineering-at-google/ch01.html); reading unit `ch01`, lines 96–173.

Attribution: Titus Winters; Hyrum's Law attributed to Hyrum Wright

Context: Interface promises, observable behavior, and the hash-ordering example. Adjacent contract context, not an inline-comment prescription.

```text
Hyrum’s Law

If you are maintaining a

project that is used by

other engineers, the most important lesson about “it works” versus “it is maintainable” is what we’ve come to call
Hyrum’s Law
:

With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by
somebody.

In our experience, this axiom is a dominant factor in any discussion of changing software over time. It is conceptually akin to entropy: discussions of change and maintenance over time must be aware of Hyrum’s Law
8
 just as discussions of efficiency or thermodynamics must be mindful of entropy. Just because entropy never decreases doesn’t mean we shouldn’t try to be efficient. Just because Hyrum’s Law will apply when maintaining software doesn’t mean we can’t plan for it or try to better understand it. We can mitigate it, but we know that it can never be eradicated.

Hyrum’s Law represents the practical knowledge that—even with the best of intentions, the best engineers, and solid practices for code review—we cannot assume perfect adherence to published contracts or best practices. As an API owner, you will gain
some
 flexibility and freedom by being clear about interface promises, but in practice, the complexity and difficulty of a given change also depends on how useful a user finds some observable behavior of your API. If users cannot depend on such things, your API will be easy to change. Given enough time and enough users, even the most innocuous change
will
 break something;
9
 your analysis of the value of that change must incorporate the difficulty in investigating, identifying, and resolving those breakages.

Example: Hash Ordering

Consider the example of hash iteration ordering.

 If we insert five elements into a hash-based set, in what order do we get them out?

>>> for i in {"apple", "banana", "carrot", "durian", "eggplant"}: print(i)
...
durian
carrot
apple
eggplant
banana

Most programmers know that hash tables are non-obviously ordered. Few know the specifics of whether the particular hash table they are using is
intending
 to provide that particular ordering forever. This might seem unremarkable, but over the past decade or two, the computing industry’s experience using such types has evolved:

Hash flooding
10
 attacks provide an increased incentive for nondeterministic hash iteration.

Potential efficiency

 gains from research into improved hash algorithms or hash containers require changes to hash iteration order.

Per Hyrum’s Law, programmers will write programs that depend on the order in which a hash table is traversed, if

they have the ability to do so.

As a result, if you ask any expert “Can I assume a particular output sequence for my hash container?” that expert will presumably say “No.” By and large that is correct, but perhaps simplistic. A more nuanced answer is, “If your code is short-lived, with no changes to your hardware, language runtime, or choice of data structure, such an assumption is fine. If you don’t know how long your code will live, or you cannot promise that nothing you depend upon will ever change, such an assumption is incorrect.” Moreover, even if your own implementation does not depend on hash container order, it might be used by other code that implicitly creates such a dependency. For example, if your library serializes values into a Remote Procedure Call (RPC) response, the RPC caller might wind up depending on the order of those
values.

This is a very basic example of the difference between “it works” and “it is correct.” For a short-lived program, depending on the iteration order of your containers will not cause any technical problems. For a software engineering project, on the other hand, such reliance on a defined order is a risk—given enough time, something will make it valuable to change that iteration order. That value can manifest in a number of ways, be it efficiency, security, or merely future-proofing the data structure to allow for future changes. When that value becomes clear, you will need to weigh the trade-offs between that value and the pain of breaking your developers or customers.

Some languages specifically randomize hash ordering between library versions or even between execution of the same program in an attempt to prevent dependencies. But even this still allows for some Hyrum’s Law surprises: there is code that uses hash iteration ordering as an inefficient random-number generator. Removing such
randomness
 now would break those users. Just as entropy increases in every
thermodynamic
 system, Hyrum’s Law applies to every observable behavior.

Thinking over the differences between code written with a “works now” and a “works indefinitely” mentality, we can extract some clear relationships. Looking at code as an artifact with a (highly) variable lifetime requirement, we can begin to categorize programming styles: code that depends on brittle and unpublished features of its dependencies is

likely to be described as “hacky” or “clever,” whereas code

that follows best practices and has planned for the future is more likely to be described as “clean” and “maintainable.” Both have their purposes, but which one you select depends crucially on the expected life span of the code in question.

We’ve taken to saying, “It’s
programming
 if 'clever' is a compliment, but it’s
software engineering
 if 'clever' is an
accusation.”
```

<a id="software-engineering-at-google-ch01-002"></a>
## software-engineering-at-google-ch01-002 — Hyrum's Law naming note

Source: [ch01.html](../../../../books/software-engineering-at-google/ch01.html); reading unit `ch01`, lines 564–565.

Attribution: Titus Winters

Context: Footnote to the named law.

Related: [software-engineering-at-google-ch01-001](#software-engineering-at-google-ch01-001)

```text
8
To his credit, Hyrum tried really hard to humbly call this “The Law of Implicit Dependencies,” but “Hyrum’s Law” is the shorthand that most people at Google have settled on.
```

<a id="software-engineering-at-google-ch02-001"></a>
## software-engineering-at-google-ch02-001 — Documentation, ownership, and bus factor

Source: [ch02.html](../../../../books/software-engineering-at-google/ch02.html); reading unit `ch02`, lines 149–163.

Attribution: Brian Fitzpatrick

Context: Documentation as one part of sharing understanding of a codebase, alongside human collaboration.

```text
The Bus Factor

Bus factor (noun): the number of people that need to get hit by a bus before your project is completely doomed.

How dispersed is the knowledge and know-how in your project?

 If you’re the only person who understands how the prototype code works, you might enjoy good job security—but if you get hit by a bus, the project is toast. If you’re working with a colleague, however, you’ve doubled the bus factor. And if you have a small team designing and prototyping together, things are even better—the project won’t be marooned when a team member disappears. Remember: team members might not literally be hit by buses, but other unpredictable life events still happen. Someone might get married, move away, leave the company, or take leave to care for a sick relative. Ensuring that there is
at least
 good documentation in addition to a primary and a secondary owner for each area of responsibility helps future-proof your project’s success and increases your project’s bus factor. Hopefully most engineers recognize that it is better to be one part of a successful project than the critical part of a failed project.

Beyond the bus factor, there’s the issue of overall pace of progress. It’s easy to forget that working alone is often a tough slog, much slower than people want to admit. How much do you learn when working alone?

How fast do you move? Google and Stack Overflow are great sources of opinions and information, but they’re no substitute for actual human experience. Working with other people directly increases the collective wisdom behind the effort. When you become stuck on something absurd, how much time do you waste pulling yourself out of the hole? Think about how
different
 the experience would be if you had a couple of peers to look over your shoulder and tell you—instantly—how you goofed and how to get past the problem. This is exactly why teams sit together (or do pair programming) in software engineering companies. Programming is hard. Software engineering is even harder. You need that second pair of eyes.
```

<a id="software-engineering-at-google-ch02-002"></a>
## software-engineering-at-google-ch02-002 — Explaining unclear control flow in review feedback

Source: [ch02.html](../../../../books/software-engineering-at-google/ch02.html); reading unit `ch02`, lines 302–315.

Attribution: Brian Fitzpatrick

Context: Paired feedback examples concern understanding and clarifying source control flow, within advice on constructive criticism. These are review conversation, not inline code-comment specimens.

```text
The trick is to make sure you (and those around you) understand the difference between a constructive criticism of someone’s creative output and a flat-out assault against someone’s character. The latter is useless—it’s petty and nearly impossible to act on. The former can (and should!) be helpful and give guidance on how to improve. And, most important, it’s imbued with respect: the person giving the constructive criticism genuinely cares about the other person and wants them to improve themselves or their work. Learn to respect your peers and give constructive criticism politely. If you truly respect someone, you’ll be motivated to choose tactful, helpful phrasing—a skill acquired with much practice. We cover this much more in
Code Review
.

On the other side of the conversation, you need to learn to accept criticism as well. This means not just being humble about your skills, but trusting that the other person has your best interests (and those of your project!) at heart and doesn’t actually think you’re an idiot. Programming is a skill like anything else: it improves with practice. If a peer pointed out ways in which you could improve your juggling, would you take it as an attack on your character and value as a human being? We hope not. In the same way, your self-worth shouldn’t be connected to the code you write—or any creative project you build. To repeat ourselves:
you are not your code
. Say that over and over. You are not what you make. You need to not only believe it yourself, but get your coworkers to believe it, too.

For example, if you have an insecure collaborator, here’s what not to say: “Man, you totally got the control flow wrong on that method there.

You should be using the standard xyzzy code pattern like everyone else.” This feedback is full of antipatterns: you’re telling someone they’re “wrong” (as if the world were black and white), demanding they change something, and accusing them of creating something that goes against what everyone else is doing (making them feel stupid). Your coworker will immediately be put on the offense, and their response is bound to be overly
emotional.

A better way to say the same thing might be, “Hey, I’m confused by the control flow in this section here. I wonder if the xyzzy code pattern might make this clearer and easier to maintain?” Notice how you’re using humility to make the question about you, not them. They’re not wrong; you’re just having trouble understanding the code. The suggestion is merely offered up as a way to clarify things for poor little you while possibly helping the project’s long-term sustainability goals. You’re also not demanding anything—you’re giving your collaborator the ability to peacefully reject the suggestion. The discussion stays focused on the code itself, not on anyone’s value or coding skills.
```

<a id="software-engineering-at-google-ch03-001"></a>
## software-engineering-at-google-ch03-001 — Knowledge fragmentation and written knowledge trade-offs

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 17–107.

Attribution: Nina Chen and Mark Barolak

Context: The chapter's premises for sharing knowledge; documentation costs, tribal knowledge, and complementary human expertise.

```text
Challenges to Learning

Sharing expertise across an organization is not an easy task.

Without a strong culture of learning, challenges can emerge. Google has experienced a number of these challenges, especially as the company has scaled:

Lack of psychological safety

An environment in which people are afraid to take risks or make mistakes in front of others because they fear being punished for it. This often manifests as a culture of fear or a tendency to avoid transparency.

Information islands

Knowledge fragmentation that occurs in different parts of an organization that don’t communicate

with one another or use shared resources. In such an
environment,
 each group develops its own way of doing things.
1
 This often leads to the following:

Information fragmentation

Each island has an incomplete picture of the bigger whole.

Information duplication

Each island has reinvented its own way of doing something.

Information skew

Each island has its own ways of doing the same thing, and these might or might not conflict.

Single point of failure (SPOF)

A bottleneck that occurs when critical information is available from only a single person.

This is related to
bus factor
, which is discussed in more detail in
How to Work Well on Teams
.

SPOFs can arise out of good intentions: it can be easy to fall into a habit of “Let me take care of that for you.” But this approach optimizes for short-term efficiency (“It’s faster for me to do it”) at the cost of poor long-term scalability (the team never learns how to do whatever it is that needs to be done). This mindset also tends to lead to
all-or-nothing expertise
.

All-or-nothing expertise

A group of people that is split between people who know “everything” and novices, with little middle ground.

 This problem often reinforces itself if experts always do everything themselves and don’t take the time to develop new experts through mentoring or documentation. In this scenario, knowledge and responsibilities continue to accumulate on those who already have expertise, and new team members or novices are left to fend for themselves and ramp up more slowly.

Parroting

Mimicry without understanding. This is typically characterized by mindlessly copying patterns or code without understanding their purpose, often under the assumption that said code is needed for unknown reasons.

Haunted graveyards

Places, often in code, that people avoid touching or changing because they are afraid that something might go wrong.

Unlike the aforementioned
parroting
, haunted graveyards are characterized by people avoiding action because of fear and superstition.

In the rest of this chapter, we dive into strategies that Google’s engineering organizations have found to be successful in addressing these challenges.

Philosophy

Software engineering can be defined as the multiperson development of multiversion programs.
2
 People are at the core of software engineering: code is an important output but only a small part of building a product.

 Crucially, code does not emerge spontaneously out of nothing, and neither does expertise. Every expert was once a novice: an organization’s success depends on growing and investing in its people.

Personalized, one-to-one advice from an expert is always invaluable. Different team members have different areas of expertise, and so the best teammate to ask for any given question will vary.

 But if the expert goes on vacation or switches teams, the team can be left in the lurch. And although one person might be able to provide personalized help for one-to-many, this doesn’t scale and is limited to small numbers of “many.”

Documented knowledge, on the other hand, can better scale not just to the team but to the entire organization.

Mechanisms such as a team wiki enable many authors to share their expertise with a larger group. But even though written documentation is more scalable than one-to-one conversations, that scalability comes with some trade-offs: it might be more generalized and less applicable to individual learners’ situations, and it comes with the added maintenance cost required to keep information relevant and up to date over time.

Tribal knowledge exists in the gap between what individual team members know and what is documented.

 Human experts know these things that aren’t written down. If we document that knowledge and maintain it, it is now available not only to somebody with direct one-to-one access to the expert today, but to anybody who can find and view the documentation.

So in a magical world in which everything is always perfectly and immediately documented, we wouldn’t need to consult a person any more, right? Not quite. Written knowledge has scaling advantages, but so does targeted human help. A human expert can synthesize their expanse of knowledge. They can assess what information is applicable to the individual’s use case, determine whether the documentation is still relevant, and know where to find it. Or, if they don’t know where to find the answers, they might know who does.

Tribal and written knowledge complement each other. Even a perfectly expert team with perfect documentation needs to communicate with one another, coordinate with other teams, and adapt their strategies over time. No single knowledge-sharing approach is the correct solution for all types of learning, and the particulars of a good mix will likely vary based on your organization.

 Institutional knowledge evolves over time, and the knowledge-sharing methods that work best for your organization will likely change as it grows. Train, focus on learning and growth, and build your own stable of experts: there is no such thing as too much engineering expertise.
```

<a id="software-engineering-at-google-ch03-002"></a>
## software-engineering-at-google-ch03-002 — Understanding implementation context before changing code

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 235–255.

Attribution: Nina Chen and Mark Barolak; quoted Chesterton's fence passage attributed to G. K. Chesterton

Context: Legacy-code understanding, documenting reasoning for future readers, and rationale in style guides.

```text
Understand Context

Learning is not just about understanding new things; it also includes developing an understanding of the decisions behind the design and implementation of existing things.

Suppose that your team inherits a legacy codebase for a critical piece of infrastructure that has existed for many years. The original authors are long gone, and the code is difficult to understand. It can be tempting to rewrite from scratch rather than spend time learning the existing code. But instead of thinking “I don’t get it” and ending your thoughts there, dive deeper: what questions should you be asking?

Consider

the principle of “
Chesterton’s fence
”: before removing or changing something, first understand why it’s there.

In the matter of reforming things, as distinct from deforming them, there is one plain and simple principle; a principle which will probably be called a paradox. There exists in such a case a certain institution or law; let us say, for the sake of simplicity, a fence or gate erected across a road. The more modern type of reformer goes gaily up to it and says, "I don’t see the use of this; let us clear it away.” To which the more intelligent type of reformer will do well to answer: "If you don’t see the use of it, I certainly won’t let you clear it away. Go away and think. Then, when you can come back and tell me that you do see the use of it, I may allow you to destroy it."

This doesn’t mean that code can’t lack clarity or that existing design patterns can’t be wrong, but engineers have a tendency to reach for “this is bad!” far more quickly than is often warranted, especially for unfamiliar code, languages, or paradigms. Google is not immune to this. Seek out and understand context, especially for decisions that seem unusual. After you’ve understood the context and purpose of the code, consider whether your change still makes sense. If it does, go ahead and make it; if it doesn’t, document your reasoning for future readers.

Many Google style guides explicitly include context to help readers understand the rationale behind the style guidelines instead of just memorizing a list of arbitrary rules. More subtly, understanding the rationale behind a given guideline allows authors to make informed decisions about when the guideline shouldn’t apply or whether the guideline needs updating.

 See
Style Guides and Rules
.
```

<a id="software-engineering-at-google-ch03-003"></a>
## software-engineering-at-google-ch03-003 — Written answers and discussion archives

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 257–307.

Attribution: Nina Chen and Mark Barolak

Context: External explanation channels: group chats, mailing lists, and editable question-and-answer archives. Includes limits of immutable old answers.

```text
Scaling Your Questions: Ask the Community

Getting one-to-one help is high bandwidth but necessarily limited in scale.

 And as a learner, it can be difficult to remember every detail. Do your future self a favor: when you learn something from a one-to-one discussion,
write it down
.

Chances are that future newcomers will have the same questions you had. Do them a favor, too, and
share what you write down
.

Although sharing the answers you receive can be useful, it’s also beneficial to seek help not from individuals but from the greater community. In this section, we examine different forms of community-based learning. Each of these approaches—group chats, mailing lists, and question-and-answer systems—have different trade-offs and complement one another. But each of them enables the knowledge seeker to get help from a broader community of peers and experts and also ensures that answers are broadly available to current and future members of that community.

Group Chats

When you have a question, it can sometimes be difficult to get help from the right person.

Maybe you’re not sure who knows the answer, or the person you want to ask is busy. In these situations, group chats are great, because you can ask your question to many people at once and have a quick back-and-forth conversation with whoever is available. As a bonus, other members of the group chat can learn from the question and answer, and many forms of group chat can be automatically archived and searched later.

Group chats tend to be devoted either to topics or to teams. Topic-driven group chats are typically open so that anyone can drop in to ask a question. They tend to attract experts and can grow quite large, so questions are usually answered quickly. Team-oriented chats, on the other hand, tend to be smaller and restrict membership. As a result, they might not have the same reach as a topic-driven chat, but their smaller size can feel safer to a newcomer.

Although group chats are great for quick questions, they don’t provide much structure, which can make it difficult to extract meaningful information from a conversation in which you’re not actively involved. As soon as you need to share information outside of the group, or make it available to refer back to later, you should write a document or email a mailing list.

Mailing Lists

Most topics at Google have a topic-users@ or topic-discuss@ Google Groups mailing list that anyone at the company can join or email.

 Asking a question on a public mailing list is a lot like asking a group chat: the question reaches a lot of people who could potentially answer it and anyone following the list can learn from the answer. Unlike group chats, though, public mailing lists are easy to share with a wider audience: they are packaged into searchable archives, and email threads provide more structure than group chats. At Google, mailing lists are also indexed and can be discovered by Moma, Google’s intranet search engine.

When you find an answer to a question you asked on a mailing list, it can be tempting to get on with your work. Don’t do it! You never know when someone will need the same information
in the future
, so it’s a best practice to post the answer back to the list.

Mailing lists are not without their trade-offs. They’re well suited for complicated questions that require a lot of context, but they’re clumsy for the quick back-and-forth exchanges at which group chats excel. A thread about a particular problem is generally most useful while it is active. Email archives are immutable, and it can be hard to determine whether an answer discovered in an old discussion thread is still relevant to a present-day situation. Additionally, the signal-to-noise ratio can be lower than other mediums like formal documentation because the problem that someone is having with their specific workflow might not be applicable to you.

Email at Google

Google culture is infamously email-centric and email-heavy.

 Google engineers receive hundreds of emails (if not more) each day, with varying degrees of actionability. Nooglers can spend days just setting up email filters to deal with the volume of notifications coming from groups that they’ve been autosubscribed to; some people just give up and don’t try to keep up with the flow. Some groups CC large mailing lists onto every discussion by default, without trying to target information to those who are likely to be specifically interested in it; as a result, the signal-to-noise ratio can be a real problem.

Google tends toward email-based workflows by default. This isn’t necessarily because email is a better medium than other communications options—it often isn’t—rather, it’s because that’s what our culture is accustomed to. Keep this in mind as your organization considers what forms of communication to encourage or invest in.

YAQS: Question-and-Answer Platform

YAQS (“Yet Another Question System”) is a Google-internal version of a
Stack Overflow
–like website, making it easy for Googlers to link to existing or work-in-progress code as well as discuss confidential information.

Like Stack Overflow, YAQS shares many of the same advantages of mailing lists and adds refinements: answers marked as helpful are promoted in the user interface, and users can edit questions and answers so that they remain accurate and useful as code and facts change. As a result, some mailing lists have been superseded by YAQS, whereas others have evolved into more general discussion lists that are less focused on problem solving.
```

<a id="software-engineering-at-google-ch03-004"></a>
## software-engineering-at-google-ch03-004 — Office hours, classes, documentation, and changing topics

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 308–340.

Attribution: Nina Chen and Mark Barolak

Context: Comparison of teaching media and maintenance of explanations; external learning resources.

```text

Scaling Your Knowledge:
You Always Have Something to Teach

Teaching is not limited to experts, nor is expertise a binary state in which you are either a novice or an expert.

Expertise is a multidimensional vector of what you know: everyone has varying levels of expertise across different areas. This is one of the reasons why diversity is critical to organizational success: different people bring different perspectives and expertise to the table (see
Engineering for Equity
). Google engineers teach others in a variety of ways, such as office hours, giving tech talks, teaching classes, writing documentation, and reviewing code.

Office Hours

Sometimes it’s really important to have a human to talk to, and in those instances, office hours can be a good solution.

Office hours are a regularly scheduled (typically weekly) event during which one or more people make themselves available to answer questions about a particular topic. Office hours are almost never the first choice for knowledge sharing: if you have an urgent question, it can be painful to wait for the next session for an answer; and if you’re hosting office hours, they take up time and need to be regularly promoted. That said, they do provide a way for people to talk to an expert in person. This is particularly useful if the problem is still ambiguous enough that the engineer doesn’t yet know what questions to ask (such as when they’re just starting to design a new service) or whether the problem is about something so specialized that there just isn’t documentation on it.

Tech Talks and Classes

Google has a robust culture of both internal and external
5
 tech talks and classes. Our engEDU (Engineering Education) team

focuses on providing Computer Science education to many audiences, ranging from Google engineers to students around the world. At a more grassroots level, our g2g (Googler2Googler) program lets Googlers sign up to give or attend talks and classes from fellow Googlers.
6
 The program is wildly successful, with thousands of participating Googlers teaching topics from the technical (e.g., “Understanding Vectorization in Modern CPUs”) to the just-for-fun (e.g., "Beginner Swing Dance").

Tech talks typically consist of a speaker presenting directly to an audience. Classes, on the other hand, can have a lecture component but often center on in-class exercises and therefore require more active participation from attendees. As a result, instructor-led classes are typically more demanding and expensive to create and maintain than tech talks and are reserved for the most important or difficult topics. That said, after a class has been created, it can be scaled relatively easily because many instructors can teach a class from the same course materials. We’ve found that classes tend to work best when the following circumstances exist:

The topic is complicated enough that it’s a frequent source of misunderstanding. Classes take a lot of work to create, so they should be developed only when they’re addressing specific needs.

The topic is relatively stable. Updating class materials is a lot of work, so if the subject is rapidly evolving, other forms of sharing knowledge will have a better bang for the buck.

The topic benefits from having teachers available to answer questions and provide personalized help. If students can easily learn without directed help, self-serve mediums like documentation or recordings are more efficient. A number of introductory classes at Google also have self-study versions.
```

<a id="software-engineering-at-google-ch03-005"></a>
## software-engineering-at-google-ch03-005 — Documentation creation, discovery, maintenance, and incentives

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 344–394.

Attribution: Nina Chen and Mark Barolak

Context: Formal documentation, proximity to source, feedback mechanisms, and costs and benefits of writing explanations.

```text
Documentation

Documentation is written knowledge whose primary goal is to help its readers learn something.

Not all written knowledge is necessarily documentation, although it can be useful as a paper trail. For example, it’s possible to find an answer to a problem in a mailing list thread, but the primary goal of the original question on the thread was to seek answers, and only secondarily to document the discussion for others.

In this section, we focus on spotting opportunities for contributing to and creating formal documentation, from small things like fixing a typo to larger efforts such as documenting tribal knowledge.

Note

For a more comprehensive discussion of documentation, see
Documentation
.

Updating documentation

The first time you learn something is the best time to see ways that the existing documentation and training materials can be improved.

 By the time you’ve absorbed and understood a new process or system, you might have forgotten what was difficult or what simple steps were missing from the “Getting Started” documentation. At this stage, if you find a mistake or omission in the documentation, fix it! Leave the campground cleaner than you found it,
7
 and try to update the documents yourself, even when that documentation is owned by a different part of the organization.

At Google, engineers feel empowered to update documentation regardless of who owns it—and we often do—even if the fix is as small as correcting a typo. This level of community upkeep increased notably with the introduction of g3doc,
8
 which made it much easier for Googlers to find a documentation owner to review their suggestion. It also leaves an auditable trail of change history no different than that for code.

Creating documentation

As your proficiency grows, write your own documentation and update existing docs.

 For example, if you set up a new development flow, document the steps. You can then make it easier for others to follow in your path by pointing them to your document. Even better, make it easier for people to find the document themselves. Any
sufficiently
 undiscoverable or unsearchable documentation might as well not exist. This is another area in which g3doc shines because the documentation is predictably located right next to the source code, as opposed to off in an (unfindable) document or webpage somewhere.

Finally, make sure there’s a mechanism for feedback.

 If there’s no easy and direct way for readers to indicate that documentation is outdated or inaccurate, they are likely not to bother telling anyone, and the next newcomer will come across the same problem. People are more willing to contribute changes if they feel that someone will actually notice and consider their suggestions. At Google, you can file a documentation bug directly from the document itself.

In addition, Googlers can easily leave comments on g3doc pages. Other Googlers can see and respond to these comments and, because leaving a comment automatically files a bug for the documentation owner, the reader doesn’t need to figure out who to contact.

Promoting documentation

Traditionally, encouraging engineers to document their work can be difficult. Writing documentation takes time and effort that could be spent on coding, and the benefits that result from

 that work are not immediate and are mostly reaped by others. Asymmetrical trade-offs like these are good for the organization as a whole given that many people can benefit from the time investment of a few, but without good incentives, it can be challenging to encourage such behavior. We discuss some of these structural incentives in the section
Incentives and recognition
.

However, a document author can often directly benefit from writing documentation. Suppose that team members always ask you for help debugging certain kinds of production failures. Documenting your procedures requires an upfront investment of time, but after that work is done, you can save time in the future by pointing team members to the documentation and providing hands-on help only when needed.

Writing documentation also helps your team and organization scale. First, the information in the documentation becomes canonicalized as a reference: team members can refer to the shared document and even update it themselves. Second, the canonicalization may spread outside the team. Perhaps some parts of the documentation are not unique to the team’s configuration and become useful for other teams looking to resolve similar problems.
```

<a id="software-engineering-at-google-ch03-006"></a>
## software-engineering-at-google-ch03-006 — Code, readability, and implementation comments

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 396–418.

Attribution: Nina Chen and Mark Barolak

Context: Code as knowledge and comments transmitting knowledge to future readers; explicit maintenance and contradiction caveat.

```text
Code

At a meta level, code
is
 knowledge, so the very act of writing code can be considered a form of knowledge transcription.

Although knowledge sharing might not be a direct intent of production code, it is often an emergent side effect, which can be facilitated by code readability and clarity.

Code documentation is one way to share knowledge; clear documentation not only benefits consumers of the library, but also future maintainers.

Similarly, implementation comments transmit knowledge across time: you’re writing these comments expressly for the sake of future readers (including Future You!). In terms of trade-offs, code comments are subject to the same downsides as general documentation: they need to be actively maintained or they can quickly become out of date, as anyone who has ever read a comment that directly contradicts the code can attest.

Code reviews (see
Code Review
) are often a learning opportunity

 for both author(s) and reviewer(s). For example, a reviewer’s suggestion might introduce the author to a new testing pattern, or a reviewer might learn of a new library by seeing the author use it in their code.

Google standardizes mentoring through code review with the
readability process
, as detailed in

the case study at the end of this chapter.
```

<a id="software-engineering-at-google-ch03-007"></a>
## software-engineering-at-google-ch03-007 — Canonical references and hands-on codelabs

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 497–555.

Attribution: Nina Chen and Mark Barolak

Context: Costs, ownership, audience, discovery, and maintenance of shared documentation and example-code tutorials.

```text
Establishing Canonical Sources of Information

Canonical sources of

 information are

centralized, company-wide corpuses of information that provide a way to standardize and propagate expert knowledge. They work best for information that is relevant to all engineers within the organization, which is otherwise prone to information islands. For example, a guide to setting up a basic developer workflow should be made canonical, whereas a guide for running a local Frobber instance is more relevant just to the engineers working on Frobber.

Establishing canonical sources of information requires higher investment than maintaining more localized information such as team documentation, but it also has broader benefits. Providing centralized references for the entire organization makes broadly required information easier and more predictable to find and counters problems with information fragmentation that can arise when multiple teams grappling with similar problems produce their own—often conflicting—guides.

Because canonical information is highly visible and intended to provide a shared understanding at the organizational level, it’s important that the content is actively maintained and vetted by subject matter experts. The more complex a topic, the more critical it is that canonical content has explicit owners. Well-meaning readers might see that something is out of date but lack the expertise to make the significant structural changes needed to fix it, even if tooling makes it easy to suggest updates.

Creating and maintaining centralized, canonical sources of information is expensive and time consuming, and not all content needs to be shared at an organizational level. When considering how much effort to invest in this resource, consider your audience. Who benefits from this information? You? Your team? Your product area? All engineers?

Developer guides

Google has a broad and deep set of

official guidance

for engineers, including
style guides
, official software engineering best practices,
12
 guides for code review
13
 and testing,
14
 and Tips of the Week (TotW).
15

The corpus of information is so large that it’s impractical to expect engineers to read it all end to end, much less be able to absorb so much information at once. Instead, a human expert already familiar with a guideline can send a link to a fellow engineer, who then can read the reference and learn more. The expert saves time by not needing to personally explain a company-wide practice, and the learner now knows that there is a canonical source of trustworthy information that they can access whenever necessary. Such a process scales knowledge because it enables human experts to recognize and solve a specific information need by leveraging common, scalable
resources.

go/ links

go/ links (sometimes referred to as goto/ links) are Google’s internal URL shortener.
16
 Most Google-internal references

have

 at least one internal go/ link. For example, “go/spanner” provides information about Spanner, “go/python” is Google’s Python developer guide. The content can live in any repository (g3doc, Google Drive, Google Sites, etc.), but having a go/ link that points to it provides a predictable, memorable way to access it. This yields some nice benefits:

go/ links are so short that it’s easy to share them in conversation ("You should check out go/frobber!"). This is much easier than having to go find a link and then send a message to all interested parties. Having a low-friction way to share references makes it more likely that that knowledge will be shared in the first place.

go/ links provide a permalink to the content, even if the underlying URL changes. When an owner moves content to a different repository (for example, moving content from a Google doc to g3doc), they can simply update the go/ link’s target URL. The go/ link itself remains unchanged.

go/ links are so ingrained into Google culture that a virtuous cycle has emerged: a Googler looking for information about Frobber will likely first check go/frobber. If the go/ link doesn’t point to the Frobber Developer Guide (as expected), the Googler will generally configure the link themselves. As a result, Googlers can usually guess the correct go/ link on the first try.

Codelabs

Google codelabs are guided, hands-on

 tutorials that teach engineers

new concepts or processes by combining explanations, working best-practice example code, and code exercises.
17
 A canonical collection of codelabs for technologies broadly used across Google is available at go/codelab. These codelabs go through several rounds of formal review and testing before publication. Codelabs are an interesting halfway point between static documentation and instructor-led classes, and they share the best and worst features of each. Their hands-on nature makes them more engaging than traditional documentation, but engineers can still access them on demand and complete them on their own; but they are expensive to maintain and are not tailored to the learner’s specific needs.
```

<a id="software-engineering-at-google-ch03-008"></a>
## software-engineering-at-google-ch03-008 — Different update expectations for documentation and newsletters

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 571–575.

Attribution: Nina Chen and Mark Barolak

Context: Maintenance expectations for different written explanation media.

```text
Staying in the Loop

Some information is critical to do one’s job, such as knowing how to do a typical development workflow.

 Other information, such as updates on popular productivity tools, is less critical but still useful. For this type of knowledge, the formality of the information sharing medium depends on the importance of the information being delivered. For example, users expect official documentation to be kept up to date, but typically have no such expectation for newsletter content, which therefore requires less maintenance and upkeep from the owner.
```

<a id="software-engineering-at-google-ch03-009"></a>
## software-engineering-at-google-ch03-009 — Readability mentorship, benefits, costs, and reported research

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 615–709.

Attribution: Nina Chen and Mark Barolak

Context: Readability includes documentation; rationale, understandable code, counterarguments, and reported productivity study are retained together.

Transcription/context notes: Footnotes 19-22 qualify corpus size, monorepo scope, short-lived code exemptions, and study controls.

Related: [software-engineering-at-google-ch03-010](#software-engineering-at-google-ch03-010)

```text
Readability: Standardized Mentorship
Through Code Review

At Google, “readability” refers to more than just code

 readability; it is a standardized,

 Google-wide mentorship process for disseminating programming language best practices. Readability covers a wide breadth of expertise, including but not limited to language idioms, code structure, API design, appropriate use of common libraries, documentation, and test coverage.

Readability started as a one-person effort. In Google’s early days, Craig Silverstein (employee ID #3) would sit down in person with every new hire and do a line-by-line “readability review” of their first major code commit. It was a nitpicky review that covered everything from ways the code could be improved to whitespace conventions. This gave Google’s codebase a uniform appearance but, more important, it taught best practices, highlighted what shared infrastructure was available, and showed new hires what it’s like to write code at Google.

Inevitably, Google’s hiring rate grew beyond what one person could keep up with. So many engineers found the process valuable that they volunteered their own time to scale the program. Today, around 20% of Google engineers are participating in the readability process at any given time, as either reviewers or code authors.

What Is the Readability Process?

Code review is mandatory at Google. Every changelist (CL)
18
 requires
readability approval
, which indicates that someone who has
readability certification
 for that language has approved the CL.

 Certified authors implicitly provide readability approval of their own CLs; otherwise, one or more qualified reviewers must explicitly give readability approval for the CL. This requirement was added after Google grew to a point where it was no longer possible to enforce that every engineer received code reviews that taught best practices to the desired rigor.

Note

See
Code Review
 for an overview of the Google code review process and what Approval means in this context.

Within Google, having readability certification is commonly referred to as “having readability” for a language. Engineers with readability have demonstrated that they consistently write clear, idiomatic, and maintainable code that exemplifies Google’s best practices and coding style for a given language. They do this by submitting CLs through the readability process, during which a centralized group of
readability reviewers
 review the CLs and give feedback on how much it demonstrates the various areas of mastery. As authors internalize the readability guidelines, they receive fewer and fewer comments on their CLs until they eventually graduate from the process and formally receive readability. Readability brings increased responsibility: engineers with readability are trusted to continue to apply their knowledge to their own code and to act as reviewers for other engineers’ code.

Around 1 to 2% of Google engineers are readability reviewers. All reviewers are volunteers, and anyone with readability is welcome to self-nominate to become a readability reviewer. Readability reviewers are held to the highest standards because they are expected not just to have deep language expertise, but also an aptitude for teaching through code review. They are expected to treat readability as first and foremost a mentoring and cooperative process, not a gatekeeping or adversarial one. Readability reviewers and CL authors alike are encouraged to have discussions during the review process. Reviewers provide relevant citations for their comments so that authors can learn about the rationales that went into the style guidelines (“Chesterton’s fence”). If the rationale for any given guideline is unclear, authors should ask for clarification (“ask questions”).

Readability is deliberately a human-driven process that aims to scale knowledge in a standardized yet personalized way. As a complementary blend of written and tribal knowledge, readability combines the advantages of written documentation, which can be accessed with citable references, with the advantages of expert human reviewers, who know which guidelines to cite. Canonical guidelines and language recommendations are comprehensively documented—which is good!—but the corpus of information is so large
19
 that it can be overwhelming, especially to newcomers.

Why Have This Process?

Code is read far more than it is written, and this effect is magnified at Google’s scale and in our (very large) monorepo.
20
 Any engineer

can look at and learn from the wealth of knowledge that is the code of other teams, and powerful tools like
Kythe
 make it easy to find references throughout the entire codebase (see
Code Search
). An important feature of documented best practices (see
Style Guides and Rules
) is that they provide consistent standards for all Google code to follow. Readability is both an enforcement and propagation mechanism for these standards.

One of the primary advantages of the readability program is that it exposes engineers to more than just their own team’s tribal knowledge. To earn readability in a given language, engineers must send CLs through a centralized set of readability reviewers who review code across the entire company. Centralizing the process makes a significant trade-off: the program is limited to scaling linearly rather than sublinearly with organization growth, but it makes it easier to enforce consistency, avoid islands, and avoid (often unintentional) drifting from established norms.

The value of codebase-wide consistency cannot

 be overstated: even with tens of thousands of engineers writing code over decades, it ensures that code in a given language will look similar across the corpus. This enables readers to focus on what the code does rather than being distracted by why it looks different than code that they’re used to. Large-scale change authors (see
Large-Scale Changes
) can more easily make changes across the entire monorepo, crossing the boundaries of thousands of teams. People can change teams and be confident that the way that the new team uses a given language is not drastically different than their previous team.

These benefits come with some costs: readability is a heavyweight process compared to other mediums like documentation and classes because it is mandatory and enforced by Google tooling (see
Critique: Google’s Code Review Tool
). These costs are nontrivial and include the following:

Increased friction for teams that do not have any team members with readability, because they need to find reviewers from outside their team to give readability approval on CLs.

Potential for additional rounds of code review for authors who need readability review.

Scaling disadvantages of being a human-driven process. Limited to scaling linearly to organization growth because it depends on human reviewers doing specialized code reviews.

The question, then, is whether the benefits outweigh the costs. There’s also the factor of time: the full effect of the benefits versus the costs are not on the same timescale. The program makes a deliberate trade-off of increased short-term code-review latency and upfront costs for the long-term payoffs of higher-quality code, repository-wide code consistency, and increased engineer expertise. The longer timescale of the benefits comes with the expectation that code is written with a potential lifetime of years, if not decades.
21

As with most—or perhaps all—engineering processes, there’s always room for improvement. Some of the costs can be mitigated with tooling. A number of readability comments address issues that could be detected statically and commented on automatically by static analysis tooling. As we continue to invest in static analysis, readability reviewers can increasingly focus on higher-order areas, like whether a particular block of code is understandable by outside readers who are not intimately familiar with the codebase instead of automatable detections like whether a line has trailing whitespace.

But aspirations aren’t enough. Readability is a controversial program: some engineers complain that it’s an unnecessary bureaucratic hurdle and a poor use of engineer time.

Are readability’s trade-offs worthwhile? For the answer, we turned to our trusty Engineering Productivity Research (EPR) team.

The EPR team performed in-depth studies of readability, including but not limited to whether people were hindered by the process, learned anything, or changed their behavior after graduating. These studies showed that readability has a net positive impact on engineering velocity. CLs by authors with readability take statistically significantly less time to review and submit than CLs by authors who do not have readability.
22
 Self-reported engineer satisfaction with their code quality—lacking more objective measures for code quality—is higher among engineers who have readability versus those who do not. A significant majority of engineers who complete the program report satisfaction with the process and find it worthwhile. They report learning from reviewers and changing their own behavior to avoid readability issues when writing
and
 reviewing code.

Note

For an in-depth look at this study and Google’s internal engineering productivity research, see
Measuring Engineering Productivity
.

Google has a very strong culture of code review, and readability is a natural extension of that culture. Readability grew from the passion of a single engineer to a formal program of human experts mentoring all Google engineers. It evolved and changed with Google’s growth, and it will continue to evolve as Google’s needs change.
```

<a id="software-engineering-at-google-ch03-011"></a>
## software-engineering-at-google-ch03-011 — Knowledge-sharing references and terminology

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 753–788.

Attribution: Nina Chen and Mark Barolak

Context: Footnotes 7-17 accompany documentation upkeep, g3doc, recognition, reference tips, links, and codelabs.

Related: [software-engineering-at-google-ch03-005](#software-engineering-at-google-ch03-005), [software-engineering-at-google-ch03-007](#software-engineering-at-google-ch03-007)

```text
7
See
“The Boy Scout Rule”
 and Kevlin Henney,
97 Things Every Programmer Should Know
 (Boston: O’Reilly, 2010).
8
g3doc stands for “google3 documentation.” google3 is the name of the current incarnation of Google’s monolithic source repository.
9
Laszlo Bock,
Work Rules!: Insights from Inside Google That Will Transform How You Live and Lead
 (New York: Twelve Books, 2015).
10
Ibid.
11
Peer bonuses include a cash award and a certificate as well as being a permanent part of a Googler’s award record in an internal tool called gThanks.
12
Such as books about software engineering at Google.
13
See
Code Review
.
14
See
Testing Overview
.
15
Available for multiple languages. Externally available for C++ at
https://abseil.io/tips
.
16
go/ links are unrelated to the Go language.
17
External codelabs are available at
https://codelabs.developers.google.com
.
```

<a id="software-engineering-at-google-ch03-010"></a>
## software-engineering-at-google-ch03-010 — Readability scope, exemptions, and study controls

Source: [ch03.html](../../../../books/software-engineering-at-google/ch03.html); reading unit `ch03`, lines 795–808.

Attribution: Nina Chen and Mark Barolak

Context: Footnotes 19-22 to the readability discussion.

Related: [software-engineering-at-google-ch03-009](#software-engineering-at-google-ch03-009)

```text
19
As of 2019, just the Google C++ style guide is 40 pages long. The secondary material making up the complete corpus of best practices is many times longer.
20
For why Google uses a monorepo, see
https://cacm.acm.org/magazines/2016/7/204032-why-google-stores-billions-of-lines-of-code-in-a-single-repository/fulltext
. Note also that not all of Google’s code lives within the monorepo; readability as described here applies only to the monorepo because it is a notion of within-repository consistency.
21
For this reason, code that is known to have a short time span is exempt from readability requirements. Examples include the
experimental/
 directory (explicitly designated for experimental code and cannot push to production) and the
Area 120 program
, a workshop for Google’s experimental products.
22
This includes controlling for a variety of factors, including tenure at Google and the fact that CLs for authors who do not have readability typically need additional rounds of review compared to authors who already have readability.
```

<a id="software-engineering-at-google-ch07-001"></a>
## software-engineering-at-google-ch07-001 — Readability evaluation question and opposing expectations

Source: [ch07.html](../../../../books/software-engineering-at-google/ch07.html); reading unit `ch07`, lines 42–112.

Attribution: Ciera Jaspan

Context: Methodological context for the readability process discussed in chapter 3; this is not an isolated experiment on source-code comments.

Related: [software-engineering-at-google-ch03-009](#software-engineering-at-google-ch03-009)

```text
For this chapter, we follow one concrete example posed by the C++ and Java language teams at Google: readability. For most of Google’s existence, these teams have managed the readability process at Google. (For more on readability, see
Knowledge Sharing
.) The readability process was put in place in the early days of Google, before automatic formatters (
Style Guides and Rules
) and linters that block submission were commonplace (
Code Review
). The process itself is expensive to run because it requires hundreds of engineers performing readability reviews for other engineers in order to grant readability to them. Some engineers viewed it as an archaic hazing process that no longer held utility, and it was a favorite topic to argue about around the lunch table. The concrete question from the language teams was this: is the time spent on the readability process worthwhile?

Triage: Is It Even Worth Measuring?

Before we decide how to measure the productivity of engineers, we need to know when a metric is even worth measuring.

 The measurement itself is expensive: it takes people to measure the process, analyze the results, and disseminate them to the rest of the company. Furthermore, the measurement process itself might be onerous and slow down the rest of the engineering organization. Even if it is not slow, tracking progress might change engineers' behavior, possibly in ways that mask the underlying issues. We need to measure and estimate smartly; although we don’t want to guess, we shouldn’t waste time and resources measuring unnecessarily.

At Google, we’ve come up with a series of questions to help teams determine whether it’s even worth measuring productivity in the first place. We first ask people to describe what they want to measure in the form of a concrete question; we find that the more concrete people can make this question, the more likely they are to derive benefit from the process. When the readability team approached us, its question was simple: are the costs of an engineer going through the readability process worth the benefits they might be deriving for the company?

We then ask them to consider the following aspects of their question:

What result are you expecting, and why?

Even though we might like to pretend that we are neutral investigators, we are not. We do have preconceived notions about what ought to happen. By acknowledging this at the outset, we can try to address these biases and prevent post hoc explanations of the results.

When this question was posed to the readability team, it noted that it was not sure. People were certain the costs had been worth the benefits at one point in time, but with the advent of autoformatters and static analysis tools, no one was entirely certain. There was a growing belief that the process now served as a hazing ritual. Although it might still provide engineers with benefits (and they had survey data showing that people did claim these benefits), it was not clear whether it was worth the time commitment of the authors or the reviewers of the code.

If the data supports your expected result, what action will be taken?

We ask this because if no action will be taken, there is no point in measuring. Notice that an action might in fact be “maintain the status quo” if there is a planned change that will occur if we didn’t have this result.

When asked about this, the answer from the readability team was straightforward: if the benefit was enough to justify the costs of the process, they would link to the research and the data on the FAQ about readability and advertise it to set expectations.

If we get a negative result, will appropriate action be taken?

We ask this question because in many cases, we find that a negative result will not change a decision. There might be other inputs into a decision that would override any negative result. If that is the case, it might not be worth measuring in the first place. This is the question that stops most of the projects that our research team takes on; we learn that the decision makers were interested in knowing the results, but for other reasons, they will not choose to change course.

In the case of readability, however, we had a strong statement of action from the team. It committed that, if our analysis showed that the costs either outweighed the benefit or the benefits were negligible, the team would kill the process. As different programming languages have different levels of maturity in formatters and static analyses, this evaluation would happen on a per-language basis.

Who is going to decide to take action on the result, and when would they do it?

We ask this to ensure that the person requesting the measurement is the one who is empowered to take action (or is doing so directly on their behalf). Ultimately, the goal of measuring our software process is to help people make business decisions. It’s important to understand who that individual is, including what form of data convinces them. Although the best research includes a variety of approaches (everything from structured interviews to statistical analyses of logs), there might be limited time in which to provide decision makers with the data they need. In those cases, it might be best to cater to the decision maker. Do they tend to make decisions by empathizing through the stories that can be retrieved from interviews?
2
 Do they trust survey results or logs data? Do they feel comfortable with complex statistical analyses? If the decider doesn’t believe the form of the result in principle, there is again no point in measuring the process.

In the case of readability, we had a clear decision maker for each programming language. Two language teams, Java and C++, actively reached out to us for assistance, and the others were waiting to see what happened with those languages first.
3
 The decision makers trusted engineers’ self-reported experiences for understanding happiness and learning, but the decision makers wanted to see “hard numbers” based on logs data for velocity and code quality. This meant that we needed to include both qualitative and quantitative analysis for these metrics. There was not a hard deadline for this work, but there was an internal conference that would make for a useful time for an announcement if there was going to be a change. That deadline gave us several months in which to complete the work.

By asking these questions, we find that in many cases, measurement is simply not worthwhile…and that’s OK! There are many good reasons to not measure the impact of a tool or process on productivity. Here are some examples that we’ve seen:

You can’t afford to change the process/tools right now

There might be time constraints or financial constraints that prevent this. For example, you might determine that if only you switched to a faster build tool, it would save hours of time every week. However, the switchover will mean pausing development while everyone converts over, and there’s a major funding deadline approaching such that you cannot afford the interruption. Engineering trade-offs are not evaluated in a vacuum—in a case like this, it’s important to realize that the broader context completely justifies delaying action on a result.

Any results will soon be invalidated by other factors

Examples here might include measuring the software process of an organization just before a planned reorganization. Or measuring the amount of technical debt for a deprecated system.

The decision maker has strong opinions, and you are unlikely to be able to provide a large enough body of evidence, of the right type, to change their beliefs.

This comes down to knowing your audience. Even at Google, we sometimes find people who have unwavering beliefs on a topic due to their past experiences. We have found stakeholders who never trust survey data because they do not believe self-reports. We’ve also found stakeholders who are swayed best by a compelling narrative that was informed by a small number of interviews. And, of course, there are stakeholders who are swayed only by logs analysis. In all cases, we attempt to triangulate on the truth using mixed methods, but if a stakeholder is limited to believing only in methods that are not appropriate for the problem, there is no point in doing the work.

The results will be used only as vanity metrics to support something you were going to do anyway

This is perhaps the most common reason we tell people at Google not to measure a software process. Many times, people have planned a decision for multiple reasons, and improving the software development process is only one benefit of several. For example, the release tool team at Google once requested a measurement to a planned change to the release workflow system. Due to the nature of the change, it was obvious that the change would not be worse than the current state, but they didn’t know if it was a minor improvement or a large one. We asked the team: if it turns out to only be a minor improvement, would you spend the resources to implement the feature anyway, even if it didn’t look to be worth the investment? The answer was yes! The feature happened to improve productivity, but this was a side effect: it was also more performant and lowered the release tool team’s maintenance burden.

The only metrics available are not precise enough to measure the problem and can be confounded by other factors

In some cases, the metrics needed (see the upcoming section on how to identify metrics) are simply unavailable. In these cases, it can be tempting to measure using other metrics that are less precise (lines of code written, for example). However, any results from these metrics will be uninterpretable. If the metric confirms the stakeholders’ preexisting beliefs, they might end up proceeding with their plan without consideration that the metric is not an accurate measure. If it does not confirm their beliefs, the imprecision of the metric itself provides an easy explanation, and the stakeholder might, again, proceed with their plan.

When you are successful at measuring your software process, you aren’t setting out to prove a hypothesis correct or incorrect;
success means giving a stakeholder the data they need to make a decision
. If that stakeholder won’t use the data, the project is always a failure. We should only measure a software process when a concrete decision will be made based on the outcome. For the readability team, there was a clear decision to be made. If the metrics showed the process to be beneficial, they would publicize the result. If not, the process would be abolished. Most important, the readability team had the authority to make this decision.
```

<a id="software-engineering-at-google-ch07-002"></a>
## software-engineering-at-google-ch07-002 — Readability goals, signals, and measurement limits

Source: [ch07.html](../../../../books/software-engineering-at-google/ch07.html); reading unit `ch07`, lines 179–295.

Attribution: Ciera Jaspan

Context: Methodological context for the readability process discussed in chapter 3; this is not an isolated experiment on source-code comments.

Transcription/context notes: The original HTML table rows and columns were inspected. The reading text linearizes cells; blank cells in Table 7-2 continue prior categories/goals/signals. Consult original HTML tables for the full column alignment.

Related: [software-engineering-at-google-ch03-009](#software-engineering-at-google-ch03-009)

```text
Taking the readability example, let’s assume that the team was so focused on making the readability process fast and easy that it had forgotten the goal about code quality. The team set up tracking measurements for how long it takes to get through the review process and how happy engineers are with the process. One of our teammates proposes the following:

I can make your review velocity very fast: just remove code reviews entirely.

Although this is obviously an extreme example, teams forget core trade-offs all the time when measuring: they become so focused on improving velocity that they forget to measure quality (or vice versa). To combat this, our research team divides productivity into five core components. These five components are in trade-off with one another, and we encourage teams to consider goals in each of these components to ensure that they are not inadvertently improving one while driving others downward.

 To help people remember all five components, we use the mnemonic “QUANTS”:

Qu
ality of the code

What is the quality of the code produced?

 Are the test cases good enough to prevent regressions? How good is an architecture at mitigating risk and changes?

A
ttention from engineers

How frequently do engineers reach a state of flow?

 How much are they distracted by notifications? Does a tool encourage engineers to context switch?

I
n
tellectual complexity

How much cognitive load is required to complete a task?

 What is the inherent complexity of the problem being solved? Do engineers need to deal with unnecessary complexity?

T
empo and velocity

How quickly can engineers accomplish their tasks?

 How fast can they push their releases out? How many tasks do they complete in a given timeframe?

S
atisfaction

How happy are engineers with their tools?

How well does a tool meet engineers' needs? How satisfied are they with their work and their end product? Are engineers feeling burned out?

Going back to the readability example, our research team worked with the readability team to identify several productivity goals of the readability process:

Quality of the code

Engineers write higher-quality code as a result of the readability process; they write more consistent code as a result of the readability process; and they contribute to a culture of code health as a result of the readability process.

Attention from engineers

We did not have any attention goal for readability. This is OK! Not all questions about engineering productivity involve trade-offs in all five areas.

Intellectual complexity

Engineers learn about the Google codebase and best coding practices as a result of the readability process, and they receive mentoring during the readability
process.

Tempo and velocity

Engineers complete work tasks faster and more efficiently as a result of the readability process.

Satisfaction

Engineers see the benefit of the readability process and have positive feelings about participating in it.

Signals

A signal is the way in which we will know we’ve achieved our goal.

 Not all signals are measurable, but that’s acceptable at this stage.

 There is not a 1:1 relationship between signals and goals. Every goal should have at least one signal, but they might have more. Some goals might also share a signal.
Table 7-1
 shows some example signals for the goals of the readability process measurement.

Table 7-1.
Signals and goals

Goals

Signals

Engineers write higher-quality code as a result of the readability process.

Engineers who have been granted readability judge their code to be of higher quality than engineers who have not been granted readability.

			The readability process has a positive impact on code quality.

Engineers learn about the Google codebase and best coding practices as a result of the readability process.

Engineers report learning from the readability process.

Engineers receive mentoring during the readability process.

Engineers report positive interactions with experienced Google engineers who serve as reviewers during the readability process.

Engineers complete work tasks faster and more efficiently as a result of the readability process.

Engineers who have been granted readability judge themselves to be more productive than engineers who have not been granted readability.

			Changes written by engineers who have been granted readability are faster to review than changes written by engineers who have not been granted readability.

Engineers see the benefit of the readability process and have positive feelings about participating in it.

Engineers view the readability process as being worthwhile.

Metrics

Metrics are where we finally determine how we will measure the signal.

 Metrics are not the signal themselves; they are the measurable proxy of the signal. Because they are a proxy, they might not be a perfect measurement. For this reason, some signals might have multiple metrics as we try to triangulate on the underlying signal.

For example, to measure whether engineers' code is reviewed faster after readability, we might use a combination of both survey data and logs data. Neither of these metrics really provide the underlying truth. (Human perceptions are fallible, and logs metrics might not be measuring the entire picture of the time an engineer spends reviewing a piece of code or can be confounded by factors unknown at the time, like the size or difficulty of a code change.) However, if these metrics show different results, it signals that possibly one of them is incorrect and we need to explore further. If they are the same, we have more confidence that we have reached some kind of truth.

Additionally, some signals might not have any associated metric because the signal might simply be unmeasurable at this time. Consider, for example, measuring code quality. Although academic literature has proposed many proxies for code quality, none of them have truly captured it. For readability, we had a decision of either using a poor proxy and possibly making a decision based on it, or simply acknowledging that this is a point that cannot currently be measured. Ultimately, we decided not to capture this as a quantitative measure, though we did ask engineers to self-rate their code quality.
```

<a id="software-engineering-at-google-ch07-003"></a>
## software-engineering-at-google-ch07-003 — Readability study methods, metrics, and reported outcome

Source: [ch07.html](../../../../books/software-engineering-at-google/ch07.html); reading unit `ch07`, lines 297–468.

Attribution: Ciera Jaspan

Context: Methodological context for the readability process discussed in chapter 3; this is not an isolated experiment on source-code comments.

Transcription/context notes: The original HTML table rows and columns were inspected. The reading text linearizes cells; blank cells in Table 7-2 continue prior categories/goals/signals. Consult original HTML tables for the full column alignment.

Related: [software-engineering-at-google-ch03-009](#software-engineering-at-google-ch03-009)

```text
Following the GSM framework is a great way to clarify the goals for why you are measuring your software process and how it will actually be measured. However, it’s still possible that the metrics selected are not telling the complete story because they are not capturing the desired signal. At Google, we use qualitative data to validate our metrics and ensure that they are capturing the intended signal.

Using Data to Validate Metrics

As an example, we once created a metric for measuring each engineer’s median build latency; the

 goal

was to capture the “typical experience” of engineers’ build latencies. We then ran an
experience sampling study
. In this style of study, engineers are interrupted in context of doing a task of interest to answer a few questions. After an engineer started a build, we automatically sent them a small survey about their experiences and expectations of build latency. However, in a few cases, the engineers responded that they had not started a build! It turned out that automated tools were starting up builds, but the engineers were not blocked on these results and so it didn’t “count” toward their “typical experience.” We then adjusted the metric to exclude such builds.
5

Quantitative metrics are useful because they give you power and scale. You can measure the experience of engineers across the entire company over a large period of time and have confidence in the results. However, they don’t provide any context or narrative. Quantitative metrics don’t explain why an engineer chose to use an antiquated tool to accomplish their task, or why they took an unusual workflow, or why they circumvented a standard process.

 Only qualitative studies can provide this information, and only qualitative studies can then provide insight on the next steps to improve a process.

Consider now the signals presented in
Table 7-2
. What metrics might you create to measure each of those? Some of these signals might be measurable by analyzing tool and code logs. Others are measurable only by directly asking engineers. Still others might not be perfectly measurable—how do we truly measure code quality, for
example?

Ultimately, when evaluating the impact of readability on productivity, we ended up with a combination of metrics from three sources. First, we had a survey that was specifically about the readability process.

This survey was given to people after they completed the process; this allowed us to get their immediate feedback about the process. This hopefully avoids recall bias,
6
 but it does introduce both recency bias
7
 and sampling bias.
8
 Second, we used a large-scale quarterly survey to track items that were not specifically about readability; instead, they were purely about metrics that we expected readability should affect. Finally, we used fine-grained logs metrics from our developer tools to determine how much time the logs claimed it took engineers to complete specific tasks.
9

Table 7-2
 presents the complete list of metrics with their corresponding signals and goals.

Table 7-2.
Goals, signals, and metrics

QUANTS

Goal

Signal

Metric

Qu
ality of the code

Engineers write higher-quality code as a result of the readability process.

Engineers who have been granted readability judge their code to be of higher quality than engineers who have not been granted readability.

Quarterly Survey: Proportion of engineers who report being satisfied with the quality of their own code

The readability process has a positive impact on code quality.

Readability Survey: Proportion of engineers reporting that readability reviews have no impact or negative impact on code quality

Readability Survey: Proportion of engineers reporting that participating in the readability process has improved code quality for their team

Engineers write more consistent code as a result of the readability process.

Engineers are given consistent feedback and direction in code reviews by readability reviewers as a part of the readability process.

Readability Survey: Proportion of engineers reporting inconsistency in readability reviewers’ comments and readability criteria.

Engineers contribute to a culture of code health as a result of the readability process.

Engineers who have been granted readability regularly comment on style and/or readability issues in code reviews.

Readability Survey: Proportion of engineers reporting that they regularly comment on style and/or readability issues in code reviews

A
ttention from engineers

n/a

n/a

n/a

I
n
tellectual complexity

Engineers learn about the Google codebase and best coding practices as a result of the readability process.

Engineers report learning from the readability process.

Readability Survey: Proportion of engineers reporting that they learned about four relevant topics

Readability Survey: Proportion of engineers reporting that learning or gaining expertise was a strength of the readability process

Engineers receive mentoring during the readability process.

Engineers report positive interactions with experienced Google engineers who serve as reviewers during the readability process.

Readability Survey: Proportion of engineers reporting that working with readability reviewers was a strength of the readability process

T
empo/velocity

Engineers are more productive as a result of the readability process.

Engineers who have been granted readability judge themselves to be more productive than engineers who have not been granted readability.

Quarterly Survey: Proportion of engineers reporting that they’re highly productive

Engineers report that completing the readability process positively affects their engineering velocity.

Readability Survey: Proportion of engineers reporting that
not
 having readability reduces team engineering velocity

Changelists (CLs) written by engineers who have been granted readability are faster to review than CLs written by engineers who have not been granted readability.

Logs data: Median review time for CLs from authors with readability and without readability

CLs written by engineers who have been granted readability are easier to shepherd through code review than CLs written by engineers who have not been granted readability.

Logs data: Median shepherding time for CLs from authors with readability and without readability

CLs written by engineers who have been granted readability are faster to get through code review than CLs written by engineers who have not been granted readability.

Logs data: Median time to submit for CLs from authors with readability and without readability

The readability process does not have a negative impact on engineering velocity.

Readability Survey: Proportion of engineers reporting that the readability process negatively impacts their velocity

Readability Survey: Proportion of engineers reporting that readability reviewers responded promptly

Readability Survey: Proportion of engineers reporting that timeliness of reviews was a strength of the readability process

S
atisfaction

Engineers see the benefit of the readability process and have positive feelings about participating in it.

Engineers view the readability process as being an overall positive experience.

Readability Survey: Proportion of engineers reporting that their experience with the readability process was positive overall

Engineers view the readability process as being worthwhile

Readability Survey: Proportion of engineers reporting that the readability process is worthwhile

Readability Survey: Proportion of engineers reporting that the quality of readability reviews is a strength of the process

Readability Survey: Proportion of engineers reporting that thoroughness is a strength of the process

Engineers do not view the readability process as frustrating.

Readability Survey: Proportion of engineers reporting that the readability process is uncertain, unclear, slow, or frustrating

Quarterly Survey: Proportion of engineers reporting that they’re satisfied with their own engineering velocity

Taking Action and Tracking Results

Recall our

 original

goal in this chapter: we want to take action and improve productivity.

 After performing research on a topic, the team at Google always prepares a list of recommendations for how we can continue to improve.

 We might suggest new features to a tool, improving latency of a tool, improving documentation, removing obsolete processes, or even changing the incentive structures for the engineers. Ideally, these recommendations are “tool driven”: it does no good to tell engineers to change their process or way of thinking if the tools do not support them in doing so. We instead always assume that engineers will make the appropriate trade-offs if they have the proper data available and the suitable tools at their disposal.

For readability, our study showed that it was overall worthwhile: engineers who had achieved readability were satisfied with the process and felt they learned from it. Our logs showed that they also had their code reviewed faster and submitted it faster, even accounting for no longer needing as many reviewers. Our study also showed places for improvement with the process: engineers identified pain points that would have made the process faster or more pleasant. The language teams took these recommendations and improved the tooling and process to make it faster and to be more transparent so that engineers would have a more pleasant experience.
```

<a id="software-engineering-at-google-ch07-004"></a>
## software-engineering-at-google-ch07-004 — Readability study language scope, bias, and aggregate measurement notes

Source: [ch07.html](../../../../books/software-engineering-at-google/ch07.html); reading unit `ch07`, lines 490–507.

Attribution: Ciera Jaspan; footnote 4 quotes Edsger Dijkstra

Context: Methodological context for the readability process discussed in chapter 3; this is not an isolated experiment on source-code comments.

Related: [software-engineering-at-google-ch03-009](#software-engineering-at-google-ch03-009)

```text
2
It’s worth pointing out here that our industry currently disparages “anecdata,” and everyone has a goal of being “data driven.” Yet anecdotes continue to exist because they are powerful. An anecdote can provide context and narrative that raw numbers cannot; it can provide a deep explanation that resonates with others because it mirrors personal experience. Although our researchers do not make decisions on anecdotes, we do use and encourage techniques such as structured interviews and case studies to deeply understand phenomena and provide context to quantitative data.
3
Java and C++ have the greatest amount of tooling support. Both have mature formatters and static analysis tools that catch common mistakes. Both are also heavily funded internally. Even though other language teams, like Python, were interested in the results, clearly there was not going to be a benefit for Python to remove readability if we couldn’t even show the same benefit for Java or C++.
4
“From there it is only a small step to measuring ‘programmer productivity’ in terms of ‘number of lines of code produced per month.’ This is a very costly measuring unit because it encourages the writing of insipid code, but today I am less interested in how foolish a unit it is from even a pure business point of view. My point today is that, if we wish to count lines of code, we should not regard them as ‘lines produced’ but as ‘lines spent’: the current conventional wisdom is so foolish as to book that count on the wrong side of the ledger.” Edsger Dijkstra, on the cruelty of really teaching computing science,
EWD Manuscript 1036
.
5
It has routinely been our experience at Google that when the quantitative and qualitative metrics disagree, it was because the quantitative metrics were not capturing the expected result.
6
Recall bias is the bias from memory. People are more likely to recall events that are particularly interesting or frustrating.
7
Recency bias is another form of bias from memory in which people are biased toward their most recent experience. In this case, as they just successfully completed the process, they might be feeling particularly good about it.
8
Because we asked only those people who completed the process, we aren’t capturing the opinions of those who did not complete the process.
9
There is a temptation to use such metrics to evaluate individual engineers, or perhaps even to identify high and low performers. Doing so would be counterproductive, though. If productivity metrics are used for performance reviews, engineers will be quick to game the metrics, and they will no longer be useful for measuring and improving productivity across the organization. The only way to make these measurements work is to let go of the idea of measuring individuals and embrace measuring the aggregate effect.
```

<a id="software-engineering-at-google-ch08-001"></a>
## software-engineering-at-google-ch08-001 — Naming and the vocabulary of code

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 7–37.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
Most engineering organizations have rules governing their codebases—rules about where source files

 are stored, rules about the formatting of the code, rules about naming and patterns and exceptions and threads. Most software engineers are working within the bounds of a set of policies that control how they operate. At Google, to manage our codebase, we maintain a set of style guides that define our rules.

Rules are laws. They are not just suggestions or recommendations, but strict, mandatory laws. As such, they are universally enforceable—rules may not be disregarded except as approved on a need-to-use basis. In contrast to rules, guidance provides recommendations and best practices. These bits are good to follow, even highly advisable to follow, but unlike rules, they usually have some room for variance.

We collect the rules that we define, the do’s and don’ts of writing code that must be followed, in our programming style guides, which are treated as canon. “Style” might be a bit of a misnomer here, implying a collection limited to formatting practices. Our style guides are more than that; they are the full set of conventions that govern our code. That’s not to say that our style guides are strictly prescriptive; style guide rules may call for judgement, such as the rule to use names that are “
as descriptive as possible, within reason
.” Rather, our style guides serve as the definitive source for the rules to which our engineers are held accountable.

We maintain separate style guides for each of the programming languages used at Google.
1
 At a high level, all of the guides have similar

goals, aiming to steer code development with an eye to sustainability.

 At the same time, there is a lot of variation among them in scope, length, and content. Programming languages have different strengths, different features, different priorities, and different historical paths to adoption within Google’s ever-evolving repositories of code. It is far more practical, therefore, to independently tailor each language’s guidelines. Some of our style guides are concise, focusing on a few overarching principles like naming and formatting, as demonstrated in our Dart, R, and Shell guides. Other style guides include far more detail, delving into specific language features and stretching into far lengthier documents—notably, our C++, Python, and Java guides. Some style guides put a premium on typical non-Google use of the language—our Go style guide is very short, adding just a few rules to a summary directive to adhere to the practices outlined in the
externally recognized conventions
. Others include rules that fundamentally differ from external norms; our C++ rules disallow use of exceptions, a language feature widely used outside of Google code.

The wide variance among even our own style guides makes it difficult to pin down the precise description of what a style guide should cover. The decisions guiding the development of Google’s style guides stem from the need to keep our codebase sustainable. Other organizations’ codebases will inherently have different requirements for sustainability that necessitate a different set of tailored rules. This chapter discusses the principles and processes that steer the development of our rules and guidance, pulling examples primarily from Google’s C++, Python, and Java style guides.

Why Have Rules?

So why do we have rules?

The goal of having

 rules in place is to encourage “good” behavior and discourage “bad” behavior. The interpretation of “good” and “bad” varies by organization, depending on what the organization cares about. Such designations are not universal preferences; good versus bad is subjective, and tailored to needs. For some organizations, “good” might promote usage patterns that support a small memory footprint or prioritize potential runtime optimizations. In other organizations, “good” might promote choices that exercise new language features. Sometimes, an organization cares most deeply about consistency, so that anything inconsistent with existing patterns is “bad.” We must first recognize what a given organization values; we use rules and guidance to encourage and discourage behavior accordingly.

As an organization grows, the established rules and guidelines shape the common vocabulary of coding. A common vocabulary allows engineers to concentrate on what their code needs to say rather than how they’re saying it. By shaping this vocabulary, engineers will tend to do the "good" things by default, even subconsciously. Rules thus give us broad leverage to nudge common development patterns in desired directions.
```

<a id="software-engineering-at-google-ch08-002"></a>
## software-engineering-at-google-ch08-002 — Reader-first rules, explicit intent, and comment roles

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 67–133.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

Transcription/context notes: Original HTML preformatted specimens checked; derived text preserves words but fragments some inline markup and does not retain all indentation.

```text
Rules must pull their weight

Not everything should go into a style guide.

 There is a nonzero cost in asking all of the engineers in an organization to learn and adapt to any new rule that is set. With too many rules,
2
 not only will it become harder for engineers to remember all relevant rules as they write their code, but it also becomes harder for new engineers to learn their way. More rules also make it more challenging and more expensive to maintain the rule set.

To this end, we deliberately chose not to include rules expected to be self-evident. Google’s style guide is not intended to be interpreted in a lawyerly fashion; just because something isn’t explicitly outlawed does not imply that it is legal. For example, the C++ style guide has no rule against the use of
goto
. C++ programmers already tend to avoid it, so including an explicit rule forbidding it would introduce unnecessary overhead. If just one or two engineers are getting something wrong, adding to everyone’s mental load by creating new rules doesn’t scale.

Optimize for the reader

Another principle of our rules is to optimize for the reader of the code rather than the author.

Given the passage of time, our code will be read far more frequently than it is written. We’d rather the code be tedious to type than difficult to read. In our Python style guide, when discussing conditional expressions, we recognize that they are shorter than
if
 statements and therefore more convenient for code authors. However, because they tend to be more difficult for readers to understand than the more verbose
if
 statements,
we restrict their usage
. We value “simple to read” over “simple to write.” We’re making a trade-off here: it can cost more upfront when engineers must repeatedly type potentially longer, descriptive names for variables and types. We choose to pay this cost for the readability it provides for all future readers.

As part of this prioritization, we also require that engineers leave explicit evidence of intended behavior in their code. We want readers to clearly understand what the code is doing as they read it. For example, our Java, JavaScript, and C++ style guides mandate use of the override annotation or keyword whenever a method overrides a superclass method. Without the explicit in-place evidence of design, readers can likely figure out this intent, though it would take a bit more digging on the part of each reader working through the code.

Evidence of intended behavior becomes even more important when it might be surprising. In C++, it is sometimes difficult to track the ownership of a pointer just by reading a snippet of code. If a pointer is passed to a function, without being familiar with the behavior of the function, we can’t be sure what to expect. Does the caller still own the pointer? Did the function take ownership? Can I continue using the pointer after the function returns or might it have been deleted? To avoid this problem, our
C++
 style guide prefers the use of
std::unique_ptr
 when ownership transfer is intended.
unique_ptr
 is a construct that manages pointer ownership, ensuring that only one copy of the pointer ever exists. When a function takes a
unique_ptr
 as an argument and intends to take ownership of the pointer, callers must explicitly invoke move semantics:

// Function that takes a Foo* and may or may not assume ownership of
// the passed pointer.
void TakeFoo(Foo* arg);

// Calls to the function don’t tell the reader anything about what to
// expect with regard to ownership after the function returns.
Foo* my_foo(NewFoo());
TakeFoo(my_foo);

Compare this to the following:

// Function that takes a std::unique_ptr<Foo>.
void TakeFoo(std::unique_ptr<Foo> arg);

// Any call to the function explicitly shows that ownership is
// yielded and the unique_ptr cannot be used after the function
// returns.
std::unique_ptr<Foo> my_foo(FooFactory());
TakeFoo(std::move(my_foo));

Given the style guide rule, we guarantee that all call sites will include clear evidence of ownership transfer whenever it applies. With this signal in place, readers of the code don’t need to understand the behavior of every function call. We provide enough information in the API to reason about its interactions. This clear documentation of behavior at the call sites ensures that code snippets remain readable and understandable. We aim for local reasoning, where the goal is clear understanding of what’s happening at the call site without needing to find and reference other code, including the function’s implementation.

Most style guide rules covering comments are also designed to support this goal of in-place evidence for readers.

Documentation

comments (the block comments prepended to a given file, class, or function) describe the design or intent of the code that follows.

 Implementation comments (the comments interspersed throughout the code itself) justify or highlight non-obvious choices, explain tricky bits, and underscore important parts of the code. We have style guide rules covering both types of
comments,
 requiring engineers to provide the explanations another engineer might be looking for when reading through the code.
```

<a id="software-engineering-at-google-ch08-003"></a>
## software-engineering-at-google-ch08-003 — Consistency, naming, obfuscation, and readability

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 135–258.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

Transcription/context notes: Original HTML preformatted specimens checked; derived text preserves words but fragments some inline markup and does not retain all indentation.

```text
Be consistent

Our view on consistency within our codebase is similar to the philosophy we apply to our Google offices.

 With a large, distributed engineering population, teams are frequently split among offices, and Googlers often find themselves traveling to other sites. Although each office maintains its unique personality, embracing local flavor and style, for anything necessary to get work done, things are deliberately kept the same. A visiting Googler’s badge will work with all local badge readers; any Google devices will always get WiFi; the video conferencing setup in any conference room will have the same interface. A Googler doesn’t need to spend time learning how to get this all set up; they know that it will be the same no matter where they are. It’s easy to move between offices and still get work done.

That’s what we strive for with our source code. Consistency is what enables any engineer to jump into an unfamiliar part of the codebase and get to work fairly quickly. A local project can have its unique personality, but its tools are the same, its techniques are the same, its libraries are the same, and it all Just Works.

Advantages of consistency

Even though it might feel restrictive for an

office to be disallowed from customizing a badge reader or video conferencing interface, the consistency benefits far outweigh the creative freedom we lose. It’s the same with code: being consistent may feel constraining at times, but it means more engineers get more work done with less effort:
3

When a codebase is internally consistent in its style and norms, engineers writing code and others reading it can focus on what’s getting done rather than how it is presented. To a large degree, this consistency allows for expert chunking.
4
 When we solve our problems with the same interfaces and format the code in a consistent way, it’s easier for experts to glance at some code, zero in on what’s important, and understand what it’s doing. It also makes it easier to modularize code and spot duplication. For these reasons, we focus a lot of attention on consistent naming conventions, consistent use of common patterns, and consistent formatting and structure. There are also many rules that put forth a decision on a seemingly small issue solely to guarantee that things are done in only one way. For example, take the choice of the number of spaces to use for indentation or the limit set on line length.
5
 It’s the consistency of having one answer rather than the answer itself that is the valuable part here.

Consistency enables scaling.

 Tooling is key for an organization to scale, and consistent code makes it easier to build tools that can understand, edit, and generate code. The full benefits of the tools that depend on uniformity can’t be applied if everyone has little pockets of code that differ—if a tool can keep source files updated by adding missing imports or removing unused includes, if different projects are choosing different sorting strategies for their import lists, the tool might not be able to work everywhere. When everyone is using the same components and when everyone’s code follows the same rules for structure and organization, we can invest in tooling that works everywhere, building in automation for many of our maintenance tasks. If each team needed to separately invest in a bespoke version of the same tool, tailored for their unique environment, we would lose that advantage.

Consistency helps when scaling the human part of an organization, too. As an organization grows, the number of engineers working on the codebase increases. Keeping the code that everyone is working on as consistent as possible enables better mobility across projects, minimizing the ramp-up time for an engineer switching teams and building in the ability for the organization to flex and adapt as headcount needs fluctuate. A growing organization also means that people in other roles interact with the code—SREs, library engineers, and code janitors, for example. At Google, these roles often span multiple projects, which means engineers unfamiliar with a given team’s project might jump in to work on that project’s code. A consistent experience across the codebase makes this efficient.

Consistency also ensures resilience to time. As time passes, engineers leave projects, new people join, ownership shifts, and projects merge or split. Striving for a consistent codebase ensures that these transitions are low cost and allows us nearly unconstrained fluidity for both the code and the engineers working on it, simplifying the processes necessary for long-term maintenance.

At Scale

A few years ago, our C++ style guide promised to almost never change style guide rules

 that would make old code inconsistent: “In some cases, there might be good arguments for changing certain style rules, but we nonetheless keep things as they are in order to preserve consistency.”

When the codebase was smaller and there were fewer old, dusty corners, that made sense.

When the codebase grew bigger and older, that stopped being a thing to prioritize. This was (for the arbiters behind our C++ style guide, at least) a conscious change: when striking this bit, we were explicitly stating that the C++ codebase would never again be completely consistent, nor were we even aiming for that.

It would simply be too much of a burden to not only update the rules to current best practices, but to also require that we apply those rules to everything that’s ever been written.

 Our Large Scale Change tooling and processes allow us to update almost all of our code to follow nearly every new pattern or syntax so that most old code exhibits the most recent approved style (see
Large-Scale Changes
). Such mechanisms aren’t perfect, however; when the codebase gets as large as it is, we can’t be sure every bit of old code can conform to the new best practices. Requiring perfect consistency has reached the point where there’s too much cost for the value.

Setting the standard

When we advocate for consistency, we tend to

 focus on internal consistency. Sometimes, local conventions spring up before global ones are adopted, and it isn’t reasonable to adjust everything to match. In that case, we advocate a hierarchy of consistency: “Be consistent” starts locally, where the norms within a given file precede those of a given team, which precede those of the larger project, which precede those of the overall codebase. In fact, the style guides contain a number of rules that explicitly defer to local conventions,
6
 valuing this local consistency over a scientific technical choice.

However, it is not always enough for an organization to create and stick to a set of internal conventions. Sometimes, the standards adopted by the external community should be taken into account.

Counting Spaces

The Python style guide at Google initially mandated two-space indents for all of our Python code.

The standard Python style guide, used by the external Python community, uses four-space indents. Most of our early Python development was in direct support of our C++ projects, not for actual Python applications. We therefore chose to use two-space indentation to be consistent with our C++ code, which was already formatted in that manner. As time went by, we saw that this rationale didn’t really hold up. Engineers who write Python code read and write other Python code much more often than they read and write C++ code. We were costing our engineers extra effort every time they needed to look something up or reference external code snippets. We were also going through a lot of pain each time we tried to export pieces of our code into open source, spending time reconciling the differences between our internal code and the external world we wanted to join.

When the time came for
Starlark
 (a Python-based language designed at Google to serve as the build description language) to have its own style guide, we chose to change to using four-space indents to be consistent with the outside world.
7

If conventions already exist, it is usually a good idea for an organization to be consistent with the outside world. For small, self-contained, and short-lived efforts, it likely won’t make a difference; internal consistency matters more than anything happening outside the project’s limited scope. Once the passage of time and potential scaling become factors, the likelihood of your code interacting with outside projects or even ending up in the outside world increase. Looking long-term, adhering to the widely accepted standard will likely pay off.

Avoid error-prone and surprising constructs

Our style guides restrict the use of some of the more surprising, unusual, or tricky constructs in the languages that we use.

 Complex features often have subtle pitfalls not obvious at first glance.

Using these features without thoroughly understanding their complexities makes it easy to misuse them and introduce bugs. Even if a construct is well understood by a project’s engineers, future project members and maintainers are not guaranteed to have the same understanding.

This reasoning is behind our Python style guide ruling to avoid using
power features
 such as reflection.

The reflective Python functions
hasattr()
 and
getattr()
 allow a user to access attributes of objects using strings:

if hasattr(my_object, 'foo'):
some_var = getattr(my_object, 'foo')

Now, with that example, everything might seem fine. But consider this:

some_file.py
:

A_CONSTANT = [
'foo',
'bar',
'baz',
]

other_file.py
:

values = []
for field in some_file.A_CONSTANT:
values.append(getattr(my_object, field))

When searching through code, how do you know that the fields
foo
,
bar
, and
baz
 are being accessed here? There’s no clear evidence left for the reader. You don’t easily see and therefore can’t easily validate which strings are used to access attributes of your object. What if, instead of reading those values from
A_CONSTANT
, we read them from a Remote Procedure Call (RPC) request message or from a data store? Such obfuscated code could cause a major security flaw, one that would be very difficult to notice, simply by validating the message incorrectly. It’s also difficult to test and verify such code.

Python’s dynamic nature allows such behavior, and in very limited circumstances, using
hasattr()
 and
getattr()
 is valid. In most cases, however, they just cause obfuscation and introduce bugs.

Although these advanced language features might perfectly solve a problem for an expert who knows how to leverage them, power features are often more difficult to understand and are not very widely used. We need all of our engineers able to operate in the codebase, not just the experts. It’s not just support for the novice software engineer, but it’s also a better environment for SREs—if an SRE is debugging a production outage, they will jump into any bit of suspect code, even code written in a language in which they are not fluent. We place higher value on simplified, straightforward code that is easier to understand and maintain.
```

<a id="software-engineering-at-google-ch08-004"></a>
## software-engineering-at-google-ch08-004 — Practical exceptions and required in-code documentation

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 260–342.

Attribution: Shaindel Schwartz; opening quotation attributed to Ralph Waldo Emerson

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
Concede to practicalities

In the words of Ralph Waldo Emerson: “
A foolish consistency is the hobgoblin of little minds
.” In

our

quest

for a consistent, simplified codebase, we do not want to blindly ignore all else. We know that some of the rules in our style guides will encounter cases that warrant exceptions, and that’s OK. When necessary, we permit concessions to optimizations and practicalities that might otherwise conflict with our rules.

Performance matters.

 Sometimes, even if it means sacrificing consistency or readability, it just makes sense to accommodate performance optimizations. For example, although our C++ style guide prohibits use of exceptions, it includes a rule that allows the use of
noexcept
, an exception-related language specifier that can trigger compiler optimizations.

Interoperability also matters.

 Code that is designed to work with specific non-Google pieces might do better if tailored for its target. For example, our C++ style guide includes an exception to the general CamelCase naming guideline that permits use of the standard library’s snake_case style for entities that mimic standard library features.
8
 The C++ style guide also allows
exemptions for Windows programming
, where compatibility with platform features requires multiple inheritance, something explicitly forbidden for all other C++ code. Both our Java and JavaScript style guides explicitly state that generated code, which frequently interfaces with or depends on components outside of a project’s ownership, is out of scope for the guide’s rules.
9
 Consistency is vital;

adaptation is key.

The Style Guide

So, what does go into a language style guide?

There are roughly three categories into which all style guide rules fall:

Rules to avoid dangers

Rules to enforce best practices

Rules to ensure consistency

Avoiding danger

First and foremost, our style guides include rules about language features that either must or must not be done for technical reasons.

 We have rules about how to use static members and variables; rules about using lambda expressions; rules about handling exceptions; rules about building for threading, access control, and class inheritance. We cover which language features to use and which constructs to avoid. We call out standard vocabulary types that may be used and for what purposes. We specifically include rulings on the hard-to-use and the hard-to-use-correctly—some language features have nuanced usage patterns that might not be intuitive or easy to apply properly, causing subtle bugs to creep in. For each ruling in the guide, we aim to include the pros and cons that were weighed with an explanation of the decision that was reached. Most of these decisions are based on the need for resilience to time, supporting and encouraging maintainable language usage.

Enforcing best practices

Our style guides also include rules enforcing some best practices of writing source code.

 These rules help keep the codebase healthy and maintainable. For example, we specify where and how code authors must include comments.
10
 Our rules for comments cover general conventions for commenting and extend to include specific cases that must include in-code documentation—cases in which intent is not always obvious, such as fall-through in switch statements, empty exception catch blocks, and template metaprogramming. We also have rules detailing the structuring of source files, outlining the organization of expected content. We have rules about naming: naming of packages, of classes, of functions, of variables. All of these rules are intended to guide engineers to practices that support healthier, more sustainable code.

Some of the best practices enforced by our style guides are designed to make source code more readable. Many formatting rules fall under this category. Our style guides specify when and how to use vertical and horizontal whitespace in order to improve readability. They also cover line length limits and brace alignment. For some languages, we cover formatting requirements by deferring to autoformatting tools—gofmt for Go, dartfmt for Dart. Itemizing a detailed list of formatting requirements or naming a tool that must be applied, the goal is the same: we have a consistent set of formatting rules designed to improve readability that we apply to all of our code.

Our style guides also include limitations on new and not-yet-well-understood language features.

The goal is to preemptively install safety fences around a feature’s potential pitfalls while we all go through the learning process. At the same time, before everyone takes off running, limiting use gives us a chance to watch the usage patterns that develop and extract best practices from the examples we observe. For these new features, at the outset, we are sometimes not sure of the proper guidance to give. As adoption spreads, engineers wanting to use the new features in different ways discuss their examples with the style guide owners, asking for allowances to permit additional use cases beyond those covered by the initial restrictions. Watching the waiver requests that come in, we get a sense of how the feature is getting used and eventually collect enough examples to generalize good practice from bad. After we have that information, we can circle back to the restrictive ruling and amend it to allow wider use.

Case Study: Introducing std::unique_ptr

When C++11 introduced
std::unique_ptr
, a smart pointer type that expresses exclusive ownership of a dynamically allocated object and deletes the object

 when the
unique_ptr
 goes out of scope, our style guide initially disallowed usage. The behavior of the
unique_ptr
 was unfamiliar to most engineers, and the related move semantics that the language introduced were very new and, to most engineers, very confusing. Preventing the introduction of
std::unique_ptr
 in the codebase seemed the safer choice. We updated our tooling to catch references to the disallowed type and kept our existing guidance recommending other types of existing smart pointers.

Time passed. Engineers had a chance to adjust to the implications of move semantics and we became increasingly convinced that using
std::unique_ptr
 was directly in line with the goals of our style guidance. The information regarding object ownership that a
std::unique_ptr
 facilitates at a function call site makes it far easier for a reader to understand that code. The added complexity of introducing this new type, and the novel move semantics that come with it, was still a strong concern, but the significant improvement in the long-term overall state of the codebase made the adoption of
std::unique_ptr
 a worthwhile trade-off.
```

<a id="software-engineering-at-google-ch08-010"></a>
## software-engineering-at-google-ch08-010 — Documented consistency decisions and limits of style guides

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 344–360.

Attribution: Shaindel Schwartz

Context: Context for naming, indentation, and import-order decisions, followed by what a style guide does not teach.

Related: [software-engineering-at-google-ch08-003](#software-engineering-at-google-ch08-003), [software-engineering-at-google-ch08-005](#software-engineering-at-google-ch08-005)

```text
Building in consistency

Our style guides also contain rules that cover a lot of the smaller stuff.

For these rules, we make and document a decision primarily to make and document a decision. Many rules in this category don’t have significant technical impact. Things like naming conventions, indentation spacing, import ordering: there is usually no clear, measurable, technical benefit for one form over another, which might be why the technical community tends to keep debating them.
11
 By choosing one, we’ve dropped out of the endless debate cycle and can just move on. Our engineers no longer spend time discussing two spaces versus four. The important bit for this category of rules is not
what
 we’ve chosen for a given rule so much as the fact that we
have
 chosen.

And for everything else...

With all that, there’s a lot that’s not in our style guides.

 We try to focus on the things that have the greatest impact on the health of our codebase. There are absolutely best practices left unspecified by these documents, including many fundamental pieces of good engineering advice: don’t be clever, don’t fork the codebase, don’t reinvent the wheel, and so on. Documents like our style guides can’t serve to take a complete novice all the way to a master-level understanding of software engineering—there are some things we assume, and this is intentional.
```

<a id="software-engineering-at-google-ch08-005"></a>
## software-engineering-at-google-ch08-005 — Retaining the reasons behind rules

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 362–390.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
Changing the Rules

Our style guides aren’t static.

As with most things, given the passage of time, the landscape within which a style guide decision was made and the factors that guided a given ruling are likely to change. Sometimes, conditions change enough to warrant reevaluation. If a new language version is released, we might want to update our rules to allow or exclude new features and idioms. If a rule is causing engineers to invest effort to circumvent it, we might need to reexamine the benefits the rule was supposed to provide. If the tools that we use to enforce a rule become overly complex and burdensome to maintain, the rule itself might have decayed and need to be revisited. Noticing when a rule is ready for another look is an important part of the process that keeps our rule set relevant and up to date.

The decisions behind rules captured in our style guides are backed by evidence. When adding a rule, we spend time discussing and analyzing the relevant pros and cons as well as the potential consequences, trying to verify that a given change is appropriate for the scale at which Google operates. Most entries in Google’s style guides include these considerations, laying out the pros and cons that were weighed during the process and giving the reasoning for the final ruling. Ideally, we prioritize this detailed reasoning and include it with every rule.

Documenting the reasoning behind a given decision gives us the advantage of being able to recognize when things need to change. Given the passage of time and changing conditions, a good decision made previously might not be the best current one. With influencing factors clearly noted, we are able to identify when changes related to one or more of these factors warrant reevaluating the rule.

Case Study: CamelCase Naming

At Google, when we defined our initial style guidance for Python code, we chose to use CamelCase naming style instead of snake_case naming style for method names.

Although the public Python style guide (
PEP 8
) and most of the Python community used snake_case naming, most of Google’s Python usage at the time was for C++ developers using Python as a scripting layer on top of a C++ codebase. Many of the defined Python types were wrappers for corresponding C++ types, and because Google’s C++ naming conventions follow CamelCase style, the cross-language consistency was seen as key.

Later, we reached a point at which we were building and supporting independent Python applications. The engineers most frequently using Python were Python engineers developing Python projects, not C++ engineers pulling together a quick script. We were causing a degree of awkwardness and readability problems for our Python engineers, requiring them to maintain one standard for our internal code but constantly adjust for another standard every time they referenced external code. We were also making it more difficult for new hires who came in with Python experience to adapt to our codebase norms.

As our Python projects grew, our code more frequently interacted with external Python projects. We were incorporating third-party Python libraries for some of our projects, leading to a mix within our codebase of our own CamelCase format with the externally preferred snake_case style. As we started to open source some of our Python projects, maintaining them in an external world where our conventions were nonconformist added both complexity on our part and wariness from a community that found our style surprising and somewhat weird.

Presented with these arguments, after discussing both the costs (losing consistency with other Google code, reeducation for Googlers used to our Python style) and benefits (gaining consistency with most other Python code, allowing what was already leaking in with third-party libraries), the style arbiters for the Python style guide decided to change the rule. With the restriction that it be applied as a file-wide choice, an exemption for existing code, and the latitude for projects to decide what is best for them, the Google Python style guide was updated to permit snake_case naming.

The Process

Recognizing that

things will need to change, given the long lifetime and ability to scale that we are aiming for, we created a process for updating our rules. The process for changing our style guide is solution based. Proposals for style guide updates are framed with this view, identifying an existing problem and presenting the proposed change as a way to fix it. “Problems,” in this process, are not hypothetical examples of things that could go wrong; problems are proven with patterns found in existing Google code. Given a demonstrated problem, because we have the detailed reasoning behind the existing style guide decision, we can reevaluate, checking whether a different conclusion now makes more sense.
```

<a id="software-engineering-at-google-ch08-011"></a>
## software-engineering-at-google-ch08-011 — Naming waivers and contextual exceptions

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 408–418.

Attribution: Shaindel Schwartz

Context: Exceptions to naming and conversion rules illustrate when local consistency gives way to codebase-wide constraints.

Related: [software-engineering-at-google-ch08-004](#software-engineering-at-google-ch08-004)

```text
Exceptions

Yes, our rules are law, but yes, some rules warrant exceptions.

Our rules are typically designed for the greater, general case. Sometimes, specific situations would benefit from an exemption to a particular rule. When such a scenario arises, the style arbiters are consulted to determine whether there is a valid case for granting a waiver to a particular rule.

Waivers are not granted lightly. In C++ code, if a macro API is introduced, the style guide mandates that it be named using a project-specific prefix. Because of the way
C++
 handles macros, treating them as members of the global namespace, all macros that are exported from header files must have globally unique names to prevent collisions. The style guide rule regarding macro naming does allow for arbiter-granted exemptions for some utility macros that are genuinely global. However, when the reason behind a waiver request asking to exclude a project-specific prefix comes down to preferences due to macro name length or project consistency, the waiver is rejected. The integrity of the codebase outweighs the consistency of the project here.

Exceptions are allowed for cases in which it is gauged to be more beneficial to permit the rule-breaking than to avoid it. The C++ style guide disallows implicit type conversions, including single-argument constructors. However, for types that are designed to transparently wrap other types, where the underlying data is still accurately and precisely represented, it’s perfectly reasonable to allow implicit conversion. In such cases, waivers to the no-implicit-conversion rule are granted. Having such a clear case for valid exemptions might indicate that the rule in question needs to be clarified or amended. However, for this specific rule, enough waiver requests are received that appear to fit the valid case for exemption but in fact do not—either because the specific type in question is not actually a transparent wrapper type or because the type is a wrapper but is not actually needed—that keeping the rule in place as-is is still worthwhile.
```

<a id="software-engineering-at-google-ch08-006"></a>
## software-engineering-at-google-ch08-006 — Programming guidance and explanation resources

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 420–459.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
Guidance

In addition to rules, we curate programming guidance in various forms, ranging from long, in-depth discussion of complex topics to short, pointed advice on best practices that we endorse.

Guidance represents the collected wisdom of our engineering experience, documenting the best practices that we’ve extracted from the lessons learned along the way. Guidance tends to focus on things that we’ve observed people frequently getting wrong or new things that are unfamiliar and therefore subject to confusion. If the rules are the “musts,” our guidance is the “shoulds.”

One example of a pool of guidance that we cultivate is a set of primers for some of the predominant languages that we use. While our style guides are prescriptive, ruling on which language features are allowed and which are disallowed, the primers are descriptive, explaining the features that the guides endorse. They are quite broad in their coverage, touching on nearly every topic that an engineer new to the language’s use at Google would need to reference. They do not delve into every detail of a given topic, but they provide explanations and recommended use. When an engineer needs to figure out how to apply a feature that they want to use, the primers aim to serve as the go-to guiding reference.

A few years ago, we began publishing a series of C++ tips that offered a mix of general language advice and Google-specific tips. We cover hard things—object lifetime, copy and move semantics, argument-dependent lookup; new things—C++ 11 features as they were adopted in the codebase, preadopted C++17 types like
string_view
,
optional
, and
variant
; and things that needed a gentle nudge of correction—reminders not to use
using
 directives, warnings to remember to look out for implicit
bool
 conversions. The tips grow out of actual problems encountered, addressing real programming issues that are not covered by the style guides. Their advice, unlike the rules in the style guide, are not true canon; they are still in the
category
 of advice rather than rule. However, given the way they grow from observed patterns rather than abstract ideals, their broad and direct applicability set them apart from most other advice as a sort of “canon of the common.” Tips are narrowly focused and relatively short, each one no more than a few minutes’ read. This “Tip of the Week” series has been extremely successful internally, with frequent citations during code reviews and technical discussions.
12

Software engineers come in to a new project or codebase with knowledge of the programming language they are going to be using, but lacking the knowledge of how the programming language is used within Google. To bridge this gap, we maintain a series of “<Language>@Google 101” courses for each of the primary programming languages in use. These full-day courses focus on what makes development with that language different in our codebase. They cover the most frequently used libraries and idioms, in-house preferences, and custom tool usage. For a C++ engineer who has just become a Google C++ engineer, the course fills in the missing pieces that make them not just a good engineer, but a good Google codebase engineer.

In addition to teaching courses that aim to get someone completely unfamiliar with our setup up and running quickly, we also cultivate ready references for engineers deep in the codebase to find the information that could help them on the go. These references vary in form and span the languages that we use. Some of the useful references that we maintain internally include the following:

Language-specific advice for the areas that are generally

 more difficult to get correct (such as concurrency and hashing).

Detailed breakdowns of new features that are introduced with a language update and

advice on how to use them within the codebase.

Listings of key abstractions and

 data structures provided by our libraries.

This keeps us from reinventing structures that already exist and provides a response to, “I need a thing, but I don’t know what it’s called in our libraries.”
```

<a id="software-engineering-at-google-ch08-007"></a>
## software-engineering-at-google-ch08-007 — Documentation, automated rules, and limits of enforcement

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 461–493.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
Applying the Rules

Rules, by their nature, lend greater value when they are enforceable.

Rules can be enforced socially, through teaching and training, or technically, with tooling. We have various formal training courses at Google that cover many of the best practices that our rules require. We also invest resources in keeping our documentation up to date to ensure that reference material remains accurate and current.

 A key part of our overall training approach when it comes to awareness and understanding of our rules is the role that code reviews play. The readability process that we run here at Google—where engineers new to Google’s development environment for a given language are mentored through code reviews—is, to a great extent, about cultivating the habits and patterns required by our style guides (see details on the readability process in
Knowledge Sharing
). The process is an important piece of how we ensure that these practices are learned and applied across project boundaries.

Although some level of training is always necessary—engineers must, after all, learn the rules so that they can write code that follows them—when it comes to checking for compliance, rather than exclusively depending on engineer-based verification, we strongly prefer to automate enforcement with tooling.

Automated rule enforcement ensures that rules are not dropped or forgotten as time passes or as an organization scales up. New people join; they might not yet know all the rules. Rules change over time; even with good communication, not everyone will remember the current state of everything. Projects grow and add new features; rules that had previously not been relevant are suddenly applicable. An engineer checking for rule compliance depends on either memory or documentation, both of which can fail. As long as our tooling stays up to date, in sync with our rule changes, we know that our rules are being applied by all our engineers for all our projects.

Another advantage to automated enforcement is minimization of the variance in how a rule is interpreted and applied. When we write a script or use a tool to check for compliance, we validate all inputs against a single, unchanging definition of the rule. We aren’t leaving interpretation up to each individual engineer. Human engineers view everything with a perspective colored by their biases. Unconscious or not, potentially subtle, and even possibly harmless, biases still change the way people view things. Leaving enforcement up to engineers is likely to see inconsistent interpretation and application of the rules, potentially with inconsistent expectations of accountability. The more that we delegate to the tools, the fewer entry points we leave for human biases to enter.

Tooling also makes enforcement scalable. As an organization grows, a single team of experts can write tools that the rest of the company can use. If the company doubles in size, the effort to enforce all rules across the entire organization doesn’t double, it costs about the same as it did before.

Even with the advantages we get by incorporating tooling, it might not be possible to automate enforcement for all rules. Some technical rules explicitly call for human judgment. In the C++ style guide, for example: “Avoid complicated template metaprogramming.” “Use
auto
 to avoid type names that are noisy, obvious, or unimportant—cases where the type doesn’t aid in clarity for the reader.” “Composition is often more appropriate than inheritance.” In the Java style guide: “There’s no single correct recipe for how to [order the members and initializers of your class]; different classes may order their contents in different ways.” “It is very rarely correct to do nothing in response to a caught exception.” “It is extremely rare to override
Object.finalize
.” For all of these rules, judgment is required and tooling can’t (yet!) take that place.

Other rules are social rather than technical, and it is often unwise to solve social problems with a technical solution. For many of the rules that fall under this category, the details tend to be a bit less well defined and tooling would become complex and expensive. It’s often better to leave enforcement of those rules to humans. For example, when it comes to the size of a given code change (i.e., the number of files affected and lines modified) we recommend that engineers favor smaller changes. Small changes are easier for engineers to review, so reviews tend to be faster and more thorough. They’re also less likely to introduce bugs because it’s easier to reason about the potential impact and effects of a smaller change. The definition of small, however, is somewhat nebulous. A change that propagates the identical one-line update across hundreds of files might actually be easy to review. By contrast, a smaller, 20-line change might introduce complex logic with side effects that are difficult to evaluate. We recognize that there are many different measurements of size, some of which may be subjective—particularly when taking the complexity of a change into account. This is why we do not have any tooling to autoreject a proposed change that exceeds an arbitrary line limit. Reviewers can (and do) push back if they judge a change to be too large. For this and similar rules, enforcement is up to the discretion of the engineers authoring and reviewing the code. When it comes to technical rules, however, whenever it is feasible, we favor technical enforcement.

Error Checkers

Many rules covering language usage can be enforced with static analysis tools.

 In fact, an

 informal survey of the C++ style guide by some of our C++ librarians in mid-2018 estimated that roughly 90% of its rules could be automatically verified. Error-checking tools take a set of rules or patterns and verify that a given code sample fully complies. Automated verification removes the burden of remembering all applicable rules from the code author. If an engineer only needs to look for violation warnings—many of which come with suggested fixes—surfaced during code review by an analyzer that has been tightly integrated into the development workflow, we minimize the effort that it takes to comply with the rules. When we began using tools to flag deprecated functions based on source tagging, surfacing both the warning and the suggested fix in-place, the problem of having new usages of deprecated APIs disappeared almost overnight. Keeping the cost of compliance down makes it more likely for engineers to happily follow through.
```

<a id="software-engineering-at-google-ch08-008"></a>
## software-engineering-at-google-ch08-008 — Formatting and reading unfamiliar code

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 509–558.

Attribution: Shaindel Schwartz; gofmt case study by Sameer Ajmani

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
Code Formatters

At Google, we generally use automated style checkers and formatters to enforce consistent formatting within our code.

The question of line lengths has stopped being interesting.
13
 Engineers just run the style checkers and keep moving forward. When formatting is done the same way every time, it becomes a non-issue during code review, eliminating the review cycles that are otherwise spent finding, flagging, and fixing minor style nits.

In managing the largest codebase ever, we’ve had the opportunity to observe the results of formatting done by humans versus formatting done by automated tooling. The robots are better on average than the humans by a significant amount. There are some places where domain expertise matters—formatting a matrix, for example, is something a human can usually do better than a general-purpose formatter. Failing that, formatting code with an automated style checker rarely goes wrong.

We enforce use of these formatters with presubmit checks: before code can be submitted, a service checks whether running the formatter on the code produces any diffs. If it does, the submit is rejected with instructions on how to run the formatter to fix the code. Most code at Google is subject to such a presubmit check. For our code, we use
clang-format
 for C++; an in-house wrapper around
yapf
 for Python;
gofmt
 for Go; dartfmt for Dart; and
buildifier
 for our
BUILD
 files.

Case Study: gofmt

Sameer Ajmani

Google released the

 Go programming language as

open source on November 10, 2009. Since then, Go has grown as a language for developing services, tools, cloud infrastructure, and open source software.
14

We knew that we needed a standard format for Go code from day one. We also knew that it would be nearly impossible to retrofit a standard format after the open source release. So the initial Go release included gofmt, the standard formatting tool for Go.

Motivations

Code reviews are a software engineering best practice, yet too much time was spent in review arguing over formatting. Although a standard format wouldn’t be everyone’s favorite, it would be good enough to eliminate this wasted time.
15

By standardizing the format, we laid the foundation for tools that could automatically update Go code without creating spurious diffs: machine-edited code would be indistinguishable from human-edited code.
16

For example, in the months leading up to Go 1.0 in 2012, the Go team used a tool called gofix to automatically update pre-1.0 Go code to the stable version of the language and libraries. Thanks to gofmt, the diffs gofix produced included only the important bits: changes to uses of the language and APIs. This allowed programmers to more easily review the changes and learn from the changes the tool made.

Impact

Go programmers expect that
all
 Go code is formatted with gofmt. gofmt has no configuration knobs, and its behavior rarely changes. All major editors and IDEs use gofmt or emulate its behavior, so nearly all Go code in existence is formatted identically. At first, Go users complained about the enforced standard; now, users often cite gofmt as one of the many reasons they like Go. Even when reading unfamiliar Go code, the format is familiar.
```

<a id="software-engineering-at-google-ch08-012"></a>
## software-engineering-at-google-ch08-012 — Tooling costs, cognitive chunking, and naming exceptions

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 616–648.

Attribution: Shaindel Schwartz

Context: Footnotes 2-9 qualify formatting costs, reader chunking, language conventions, Abseil naming, and generated-code exemptions.

Related: [software-engineering-at-google-ch08-003](#software-engineering-at-google-ch08-003), [software-engineering-at-google-ch08-004](#software-engineering-at-google-ch08-004), [software-engineering-at-google-ch08-008](#software-engineering-at-google-ch08-008)

```text
2
Tooling matters here. The measure for “too many” is not the raw number of rules in play, but how many an engineer needs to remember. For example, in the bad-old-days pre-clang-format, we needed to remember a ton of formatting rules. Those rules haven’t gone away, but with our current tooling, the cost of adherence has fallen dramatically. We’ve reached a point at which somebody could add an arbitrary number of formatting rules and nobody would care, because the tool just does it for you.
3
Credit to H. Wright for the real-world comparison, made at the point of having visited around 15 different Google offices.
4
"Chunking" is a cognitive process that groups pieces of information together into meaningful “chunks” rather than keeping note of them individually. Expert chess players, for example, think about configurations of pieces rather than the positions of the individuals.
5
See
4.2 Block indentation: +2 spaces
,
Spaces vs. Tabs
,
4.4 Column limit:100
 and
Line Length
.
6
Use of const
, for example.
7
Style formatting for BUILD files implemented with Starlark is applied by buildifier. See
https://github.com/bazelbuild/buildtools
.
8
See
Exceptions to Naming Rules
. As an example, our open sourced Abseil libraries use snake_case naming for types intended to be replacements for standard types. See the types defined in
https://github.com/abseil/abseil-cpp/blob/master/absl/utility/utility.h
. These are C++11 implementation of C++14 standard types and therefore use the standard’s favored snake_case style instead of Google’s preferred CamelCase form.
9
See
Generated code: mostly exempt
.
```

<a id="software-engineering-at-google-ch08-009"></a>
## software-engineering-at-google-ch08-009 — Comment-guideline source references

Source: [ch08.html](../../../../books/software-engineering-at-google/ch08.html); reading unit `ch08`, lines 649–656.

Attribution: Shaindel Schwartz

Context: Style-guide context for code explanation, naming, readability, and required comments.

```text
10
See
https://google.github.io/styleguide/cppguide.html#Comments
,
http://google.github.io/styleguide/pyguide#38-comments-and-docstrings
, and
https://google.github.io/styleguide/javaguide.html#s7-javadoc
, where multiple languages define general comment rules.
```

<a id="software-engineering-at-google-ch09-001"></a>
## software-engineering-at-google-ch09-001 — OWNERS files as code-ownership documentation

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 121–149.

Attribution: Hyrum Wright

Context: Code-review context; review discussion and change descriptions are distinct from source-code comments.

```text
Ownership

Hyrum Wright

When working on a small team in

 a dedicated repository, it’s common to grant the entire team access to everything in the repository.

After all, you know the other engineers, the domain is narrow enough that each of you can be experts, and small numbers constrain the effect of potential errors.

As the team grows larger, this approach can fail to scale. The result is either a messy repository split or a different approach to recording who has what knowledge and responsibilities in different parts of the repository. At Google, we call this set of knowledge and responsibilities
ownership
 and the people to exercise them
owners
. This concept is different than possession of a collection of source code, but rather implies a sense of stewardship to act in the company’s best interest with a section of the codebase. (Indeed, “stewards” would almost certainly be a better term if we had it to do over again.)

Specially named OWNERS files list usernames of people who have ownership responsibilities for a directory and its children. These files may also contain references to other OWNERS files or external access control lists, but eventually they resolve to a list of individuals. Each subdirectory may also contain a separate OWNERS file, and the relationship is hierarchically additive: a given file is generally owned by the union of the members of all the OWNERS files above it in the directory tree. OWNERS files may have as many entries as teams like, but we encourage a relatively small and focused list to ensure responsibility is clear.

Ownership of Google’s code conveys approval rights for code within one’s purview, but these rights also come with a set of responsibilities, such as understanding the code that is owned or knowing how to find somebody who does. Different teams have different criteria for granting ownership to new members, but we generally encourage them not to use ownership as a rite of initiation and encourage departing members to yield ownership as soon as is practical.

This distributed ownership structure enables many of the other practices we’ve outlined in this book. For example, the set of people in the root OWNERS file can act as global approvers for large-scale changes (see
Large-Scale Changes
) without having to bother local teams. Likewise, OWNERS files act as a kind of documentation, making it easy for people and tools to find those responsible for a given piece of code just by walking up the directory tree. When new projects are created, there’s no central authority that has to register new ownership privileges: a new OWNERS file is sufficient.

This ownership mechanism is simple, yet powerful, and has scaled well over the past two decades. It is one of the ways that Google ensures that tens of thousands of engineers can operate efficiently on billions of lines of code

 in a single

repository.
```

<a id="software-engineering-at-google-ch09-002"></a>
## software-engineering-at-google-ch09-002 — Code comprehension and consistency

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 204–236.

Attribution: Tom Manshreck and Caitlin Sadowski

Context: Code-review context; review discussion and change descriptions are distinct from source-code comments.

```text
Surprisingly enough, checking for code correctness is not the primary benefit Google accrues from the process of code review. Checking for code correctness generally ensures that a change works, but more importance is attached to ensuring that a code change is understandable and makes sense over time and as the codebase itself scales. To evaluate those aspects, we need to look at factors other than whether the code is simply logically “correct” or understood.

Comprehension of Code

A code review typically is the first opportunity for someone other than the author to inspect a change.

This perspective allows a reviewer to do something that even the best engineer cannot do: provide feedback unbiased by an author’s perspective.
A code review is often the first test of whether a given change is understandable to a broader audience
. This perspective is vitally important because code will be read many more times than it is written, and understanding and comprehension are critically important.

It is often useful to find a reviewer who has a different perspective from the author, especially a reviewer who might need, as part of their job, to maintain or use the code being proposed within the change. Unlike the deference reviewers should give authors regarding design decisions, it’s often useful to treat questions on code comprehension using the maxim “the customer is always right.” In some respect, any questions you get now will be multiplied many-fold over time, so view each question on code comprehension as valid. This doesn’t mean that you need to change your approach or your logic in response to the criticism, but it does mean that you might need to explain it more clearly.

Together, the code correctness and code comprehension checks are the main criteria for an LGTM from another engineer, which is one of the approval bits needed for an approved code review. When an engineer marks a code review as LGTM, they are saying that the code does what it says and that it is understandable. Google, however, also requires that the code be sustainably maintained, so we have additional approvals needed for code in certain cases.

Code Consistency

At scale, code that you write will be depended on, and eventually maintained, by someone else.

 Many others will need to read your code and understand what you did. Others (including automated tools) might need to refactor your code long after you’ve moved to another project. Code, therefore, needs to conform to some standards of consistency so that it can be understood and maintained. Code should also avoid being overly complex; simpler code is easier for others to understand and maintain as well. Reviewers can assess how well this code lives up to the standards of the codebase itself during code review. A code review, therefore, should act to ensure
code health
.

It is for maintainability that the LGTM state of a

code review (indicating code correctness and comprehension) is separated from that of readability approval. Readability approvals can be granted only by individuals who have successfully gone through the process of code readability training in a particular programming language. For example, Java code requires approval from an engineer who has “Java readability.”

A readability approver is tasked with reviewing

code to ensure that it follows agreed-on best practices for that particular programming language, is consistent with the codebase for that language within Google’s code repository, and avoids being overly complex. Code that is consistent and simple is easier to understand and easier for tools to update when it comes time for refactoring, making it more resilient. If a particular pattern is always done in one fashion in the codebase, it’s easier to write a tool to refactor it.

Additionally, code might be written only once, but it will be read dozens, hundreds, or even thousands of times. Having code that is consistent across the codebase improves comprehension for all of engineering, and this consistency even affects the process of code review itself. Consistency sometimes clashes with functionality; a readability reviewer may prefer a less complex change that may not be functionally “better” but is easier to understand.

With a more consistent codebase, it is easier for engineers to step in and review code on someone else’s projects. Engineers might occasionally need to look outside the team for help in a code review. Being able to reach out and ask experts to review the code, knowing they can expect the code itself to be consistent, allows those engineers to focus more properly on code correctness and comprehension.
```

<a id="software-engineering-at-google-ch09-003"></a>
## software-engineering-at-google-ch09-003 — Review discussions as historical explanation

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 254–268.

Attribution: Tom Manshreck and Caitlin Sadowski

Context: Code-review context; review discussion and change descriptions are distinct from source-code comments.

```text
Knowledge Sharing

One of the most important, but underrated, benefits of code review is in knowledge sharing.

 Most authors pick reviewers who are experts, or at least knowledgeable, in the area under review. The review process allows reviewers to impart domain knowledge to the author, allowing the reviewer(s) to offer suggestions, new techniques, or advisory information to the author. (Reviewers can even mark some comments “FYI,” requiring no action; they are simply added as an aid to the author.) Authors who become particularly proficient in an area of the codebase will often become owners as well, who then in turn will be able to act as reviewers for other engineers.

Part of the code review process of feedback and confirmation involves asking questions on why the change is done in a particular way. This exchange of information facilitates knowledge sharing. In fact, many code reviews involve an exchange of information both ways: the authors as well as the reviewers can learn new techniques and patterns from code review. At Google, reviewers may even directly share suggested edits with an author within the code review tool itself.

An engineer may not read every email sent to them, but they tend to respond to every code review sent. This knowledge sharing can occur across time zones and projects as well, using Google’s scale to disseminate information quickly to engineers in all corners of the codebase. Code review is a perfect time for knowledge transfer: it is timely and actionable. (Many engineers at Google “meet” other engineers first through their code reviews!)

Given the amount of time Google engineers spend in code review, the knowledge accrued is quite significant. A Google engineer’s primary task is still programming, of course, but a large chunk of their time is still spent in code review. The code review process provides one of the primary ways that software engineers interact with one another and exchange information about coding techniques. Often, new patterns are advertised within the context of code review, sometimes through refactorings such as large-scale changes.

Moreover, because each change becomes part of the codebase, code review acts as a historical record. Any engineer can inspect the Google codebase and determine when some particular pattern was introduced and bring up the actual code review in
question
. Often, that archeology provides insights to many more engineers than the original author and reviewer(s).
```

<a id="software-engineering-at-google-ch09-007"></a>
## software-engineering-at-google-ch09-007 — Questions about intent and the author responsibility for understandable code

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 276–288.

Attribution: Tom Manshreck and Caitlin Sadowski

Context: The review-practice context distinguishes professional review comments and explanation of a code approach from source-code comments.

Related: [software-engineering-at-google-ch09-004](#software-engineering-at-google-ch09-004)

```text
Be Polite and Professional

As pointed out in the Culture section of this book, Google heavily fosters a culture of trust and respect.

This filters down into our perspective on code review. A software engineer needs an LGTM from only one other engineer to satisfy our requirement on code comprehension, for example. Many engineers make comments and LGTM a change with the understanding that the change can be submitted after those changes are made, without any additional rounds of review. That said, code reviews can introduce anxiety and stress to even the most capable engineers. It is critically important to keep all feedback and criticism firmly in the professional realm.

In general, reviewers should defer to authors on particular approaches and only point out alternatives if the author’s approach is deficient. If an author can demonstrate that several approaches are equally valid, the reviewer should accept the preference of the author. Even in those cases, if defects are found in an approach, consider the review a learning opportunity (for both sides!). All comments should remain strictly professional. Reviewers should be careful about jumping to conclusions based on a code author’s particular approach. It’s better to ask questions on why something was done the way it was before assuming that approach is wrong.

Reviewers should be prompt with their feedback. At Google, we expect feedback from a code review within 24 (working) hours. If a reviewer is unable to complete a review in that time, it’s good practice (and expected) to respond that they’ve at least seen the change and will get to the review as soon as possible. Reviewers should avoid responding to the code review in piecemeal fashion. Few things annoy an author more than getting feedback from a review, addressing it, and then continuing to get unrelated further feedback in the review process.

As much as we expect professionalism on the part of the reviewer, we expect professionalism on the part of the author as well. Remember that you are not your code, and that this change you propose is not “yours” but the team’s. After you check that piece of code into the codebase, it is no longer yours in any case. Be receptive to
questions
 on your approach, and be prepared to explain why you did things in certain ways. Remember that part of the responsibility of an author is to make sure this code is understandable and maintainable for the future.
```

<a id="software-engineering-at-google-ch09-004"></a>
## software-engineering-at-google-ch09-004 — Change descriptions and implementation comments

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 314–326.

Attribution: Tom Manshreck and Caitlin Sadowski

Context: Code-review context; review discussion and change descriptions are distinct from source-code comments.

```text
Write Good Change Descriptions

A change description should indicate its type of change on the first line, as a summary.

 The first line is prime real estate and is used to provide summaries within the code review tool itself, to act as the subject line in any associated emails, and to become the visible line Google engineers see in a history summary within Code Search (see
Code Search
), so that first line is important.

Although the first line should be a summary of the entire change, the description should still go into detail on what is being changed
and why
. A description of “Bug fix” is not helpful to a reviewer or a future code archeologist. If several related modifications were made in the change, enumerate them within a list (while still keeping it on message and small). The description is the historical record for this change, and tools such as Code Search allow you to find who wrote what line in any particular change in the codebase. Drilling down into the original change is often useful when trying to fix a bug.

Descriptions aren’t the only opportunity for adding documentation to a change. When writing a public API, you generally don’t want to leak implementation details, but by all means do so within the actual implementation, where you should comment liberally. If a reviewer does not understand why you did something, even if it is correct, it is a good indicator that such code needs better structure or better comments (or both). If, during the code review process, a new decision is reached, update the change description, or add appropriate comments within the implementation. A code review is not just something that you do in the present time; it is something you do to record what you did for posterity.
```

<a id="software-engineering-at-google-ch09-005"></a>
## software-engineering-at-google-ch09-005 — Documentation and tests in new and changed code

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 372–408.

Attribution: Tom Manshreck and Caitlin Sadowski

Context: Code-review context; review discussion and change descriptions are distinct from source-code comments.

```text
Greenfield Code Reviews

The least common type of code review is that of entirely new code, a so-called
greenfield review
.

 A greenfield review is the most important time to evaluate whether the code will stand the test of time: that it will be easier to maintain as time and scale change the underlying assumptions of the code. Of course, the introduction of entirely new code should not come as a surprise. As mentioned earlier in this chapter, code is a liability, so the introduction of entirely new code should generally solve a real problem rather than simply provide yet another alternative.

At Google, we generally require new code and/or projects to undergo an extensive design review, apart from a code review. A code review is not the time to debate design decisions already made in the past (and by the same token, a code review is not the time to introduce the design of a proposed API).

To ensure that code is sustainable, a greenfield review should ensure that an API matches an agreed design (which may require reviewing a design document) and is tested
fully
, with all API endpoints having some form of unit test, and that those tests fail when the code’s assumptions change. (See
Testing Overview
).

The code should also have proper owners (one of the first reviews in a new project is often of a single OWNERS file for the new directory), be sufficiently commented, and provide supplemental documentation, if needed.

 A greenfield review might also necessitate the introduction of a project into the continuous integration system. (See
Continuous Integration
).

Behavioral Changes, Improvements, and Optimizations

Most changes at Google generally fall into the broad category of modifications to existing code within the codebase.

 These additions may include modifications to API endpoints,

 improvements to existing implementations, or optimizations for other factors such as performance.

 Such changes are the bread and butter of most software engineers.

In each of these cases, the guidelines that apply to a greenfield review also apply: is this change necessary, and does this change improve the codebase? Some of the best modifications to a codebase are actually deletions! Getting rid of dead or obsolete code is one of the best ways to improve the overall code health of a codebase.

Any behavioral modifications

should necessarily include revisions to appropriate tests for any new API behavior. Augmentations to the implementation should be tested in a Continuous Integration (CI) system to ensure that those modifications don’t break any underlying assumptions of the existing tests. As well, optimizations should of course ensure that they don’t affect those tests and might need to include performance benchmarks for the reviewers to consult. Some optimizations might also require benchmark tests.
```

<a id="software-engineering-at-google-ch09-006"></a>
## software-engineering-at-google-ch09-006 — Readability definition and documentation-review exceptions

Source: [ch09.html](../../../../books/software-engineering-at-google/ch09.html); reading unit `ch09`, lines 468–473.

Attribution: Tom Manshreck and Caitlin Sadowski

Context: Code-review context; review discussion and change descriptions are distinct from source-code comments.

```text
3
At Google, “readability” does not refer simply to comprehension, but to the set of styles and best practices that allow code to be maintainable to other engineers. See
Knowledge Sharing
.
4
Some changes to documentation and configurations might not require a code review, but it is often still preferable to obtain such a review.
```

<a id="software-engineering-at-google-ch10-001"></a>
## software-engineering-at-google-ch10-001 — Documentation scope, costs, and benefits

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 7–74.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Of the complaints most engineers have about writing, using, and maintaining code, a singular common frustration

is the lack of quality documentation. “What are the side effects of this method?” “I got an error after step 3.” “What does this acronym mean?” “Is this document up to date?” Every software engineer has voiced complaints about the quality, quantity, or sheer lack of documentation throughout their career, and the software engineers at Google are no different.

Technical writers and project managers may help, but software engineers will always need to write most documentation themselves. Engineers, therefore, need the proper tools and incentives to do so effectively. The key to making it easier for them to write quality documentation is to introduce processes and tools that scale with the organization and that tie into their existing workflow.

Overall, the state of engineering documentation in the late 2010s is similar to the state of software testing in the late 1980s. Everyone recognizes that more effort needs to be made to improve it, but there is not yet organizational recognition of its critical benefits. That is changing, if slowly. At Google, our most successful efforts have been when documentation is
treated like code
 and incorporated into the traditional engineering workflow, making it easier for engineers to write and maintain simple
documents.

What Qualifies as Documentation?

When we refer to “documentation,” we’re talking about every

 supplemental text that an engineer needs to write to do their job: not only standalone documents, but code comments as well. (In fact, most of the documentation an engineer at Google writes comes in the form of code comments.) We’ll discuss the various types of engineering documents further in this chapter.

Why Is Documentation Needed?

Quality documentation has tremendous benefits for an engineering organization. Code and APIs become more comprehensible, reducing mistakes.

 Project teams are more focused when their design goals and team objectives are clearly stated. Manual processes are easier to follow when the steps are clearly outlined. Onboarding new members to a team or code base takes much less effort if the process is clearly
documented.

But because documentation’s benefits are all necessarily downstream, they generally don’t reap immediate benefits to the author. Unlike testing, which (as we’ll see) quickly provides benefits to a programmer, documentation generally requires more effort up front and doesn’t provide clear benefits to an author until later. But, like investments in testing, the investment made in documentation will pay for itself over time. After all, you might write a document only once,
1
 but it will be read hundreds, perhaps thousands of times afterward; its initial cost is amortized across all the future readers. Not only does documentation scale over time, but it is critical for the rest of the organization to scale as well. It helps answer questions like these:

Why were these design decisions made?

Why did we implement this code in this manner?

Why did
I
 implement this code in this manner, if you’re looking at your own code two years later?

If documentation conveys all these benefits, why is it generally considered “poor” by engineers? One reason, as we’ve mentioned, is that the benefits aren’t
immediate
, especially to the writer. But there are several other reasons:

Engineers often view writing as a separate skill than that of programming. (We’ll try to illustrate that this isn’t quite the case, and even where it is, it isn’t necessarily a separate skill from that of software engineering.)

Some engineers don’t feel like they are capable writers. But you don’t need a robust command of English
2
 to produce workable documentation. You just need to step outside yourself a bit and see things from the audience’s perspective.

Writing documentation is often more difficult because of limited tools support or integration into the developer workflow.

Documentation is viewed as an extra burden—something else to maintain—rather than something that will make maintenance of their existing code easier.

Not every engineering team needs a technical writer (and even if that were the case, there aren’t enough of them). This means that engineers will, by and large, write most of the documentation themselves. So, instead of forcing engineers to become technical writers, we should instead think about how to make writing documentation easier for engineers. Deciding how much effort to devote to documentation is a decision your organization will need to make at some point.

Documentation benefits several different groups. Even to the writer, documentation provides the following benefits:

It helps

 formulate an API. Writing documentation is one of the surest ways to figure out if your API makes sense. Often, the writing of the documentation itself leads engineers to reevaluate design decisions that otherwise wouldn’t be questioned. If you can’t explain it and can’t define it, you probably haven’t designed it well enough.

It provides a road map for maintenance and a historical record. Tricks in code should be avoided, in any case, but good comments help out a great deal when you’re staring at code you wrote two years ago, trying to figure out what’s wrong.

It makes your code look more professional and drive traffic. Developers will naturally assume that a well-documented API is a better-designed API. That’s not always the case, but they are often highly correlated. Although this benefit sounds cosmetic, it’s not quite so: whether a product has good documentation is usually a pretty good indicator of how well a product will be maintained.

It will prompt fewer questions from other users. This is probably the biggest benefit over time to someone writing the documentation. If you have to explain something to someone more than once, it usually makes sense to document that process.

As great as these benefits are to the writer of documentation, the lion’s share of documentation’s benefits will naturally accrue to the reader. Google’s C++ Style Guide notes the maxim “
optimize for the reader
.” This maxim applies not just to code, but to the comments around code, or the documentation set attached to an API. Much like testing, the effort you put into writing good documents will reap benefits many times over its lifetime. Documentation is critical over time, and reaps tremendous benefits for especially critical code as an organization scales.

```

<a id="software-engineering-at-google-ch10-002"></a>
## software-engineering-at-google-ch10-002 — Treating documentation as code and the wiki case study

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 75–145.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Documentation Is Like Code

Software engineers who write in a single, primary programming language still often reach for different languages to solve specific problems.

An engineer might write shell scripts or Python to run command-line tasks, or they might write most of their backend code in C++ but write some middleware code in Java, and so on. Each language is a tool in the toolbox.

Documentation should be no different: it’s a tool, written in a different language (usually English) to accomplish a particular task. Writing documentation is not much different than writing code. Like a programming language, it has rules, a particular syntax, and style decisions, often to accomplish a similar purpose as that within code: enforce consistency, improve clarity, and avoid (comprehension) errors. Within technical documentation, grammar is important not because one needs rules, but to standardize the voice and avoid confusing or distracting the reader. Google requires a certain comment style for many of its languages for this reason.

Like code, documents should also have owners. Documents without owners become stale and difficult to maintain. Clear ownership also makes it easier to handle documentation through existing developer workflows: bug tracking systems, code review tooling, and so forth. Of course, documents with different owners can still conflict with one another.

 In those cases, it is important to designate
canonical
 documentation: determine the primary source and consolidate other associated documents into that primary source (or deprecate the duplicates).

The prevalent

 usage of “go/ links” at Google (see
Knowledge Sharing
) makes this process easier. Documents with straightforward go/ links often become the canonical source of truth. One other way to promote canonical documents is to associate them directly with the code they document by placing them directly under source control and alongside the source code itself.

Documentation is often so tightly coupled to code that it should, as much as possible, be treated
as code
. That is, your documentation should:

Have internal policies or rules to be followed

Be placed under source control

Have clear ownership responsible for maintaining the docs

Undergo reviews for changes (and change
with
 the code it documents)

Have issues tracked, as bugs are tracked in code

Be periodically evaluated (tested, in some respect)

If possible, be measured for aspects such as accuracy, freshness, etc. (tools have still not caught up here)

The more engineers treat documentation as “one of” the necessary tasks of software development, the less they will resent the upfront costs of writing, and the more they will reap the long-term benefits. In addition, making the task of documentation easier reduces those upfront costs.

Case Study: The Google Wiki

When Google was much smaller and leaner, it had few technical writers. The easiest way to share information

was through our own internal wiki (GooWiki).

 At first, this seemed like a reasonable approach; all engineers shared a single documentation set and could update it as needed.

But as Google scaled, problems with a wiki-style approach became apparent. Because there were no true owners for documents, many became obsolete.
3
 Because no process was put in place for adding new documents, duplicate documents and document sets began appearing. GooWiki had a flat namespace, and people were not good at applying any hierarchy to the documentation sets. At one point, there were 7 to 10 documents (depending on how you counted them) on setting up Borg, our production compute environment, only a few of which seemed to be maintained, and most were specific to certain teams with certain permissions and assumptions.

Another problem with GooWiki became apparent over time: the people who could fix the documents were not the people who used them. New users discovering bad documents either couldn’t confirm that the documents were wrong or didn’t have an easy way to report errors. They knew something was wrong (because the document didn’t work), but they couldn’t “fix” it. Conversely, the people best able to fix the documents often didn’t need to consult them after they were written. The documentation became so poor as Google grew that the quality of documentation became Google’s number one developer complaint on our annual developer surveys.

The way to improve the situation was to move important documentation under the same sort of source control that was being used to track code changes.

 Documents began to have their own owners, canonical locations within the source tree, and processes for identifying bugs and fixing them; the documentation began to dramatically improve. Additionally, the way documentation was written and maintained began to look the same as how code was written and maintained. Errors in the documents could be reported within our bug tracking software. Changes to the documents could be handled using the existing code review process. Eventually, engineers began to fix the documents themselves or send changes to technical writers (who were often the owners).

Moving documentation to source control was initially met with a lot of controversy. Many engineers were convinced that doing away with the GooWiki, that bastion of freedom of information, would lead to poor quality because the bar for documentation (requiring a review, requiring owners for documents, etc.) would be higher. But that wasn’t the case. The documents became better.

The introduction of Markdown as a common documentation formatting language also helped

 because it made it easier for engineers to understand how to edit documents without needing specialized expertise in HTML or CSS.

Google eventually introduced its own framework for embedding documentation within code:
g3doc
. With that framework, documentation improved further, as documents existed side by side with the source code within the engineer’s development environment. Now, engineers could update the code and its associated documentation in the same change (a practice for which we’re still trying to improve adoption).

The key difference was that maintaining documentation became a similar experience to maintaining code: engineers filed bugs, made changes to documents in changelists, sent changes to reviews by experts, and so on. Leveraging of existing developer workflows, rather than creating new ones, was a key benefit.
```

<a id="software-engineering-at-google-ch10-003"></a>
## software-engineering-at-google-ch10-003 — Audiences and separation of customer and provider information

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 147–207.

Attribution: Tom Manshreck; Blaise Pascal quotation

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Know Your Audience

One of the most important mistakes that engineers make when writing documentation is to write only for themselves.

It’s natural to do so, and writing for yourself is not without value: after all, you might need to look at this code in a few years and try to figure out what you once meant. You also might be of approximately the same skill set as someone reading your document. But if you write only for yourself, you are going to make certain assumptions, and given that your document might be read by a very wide audience (all of engineering, external developers), even a few lost readers is a large cost. As an organization grows, mistakes in documentation become more prominent, and your assumptions often do not apply.

Instead, before you begin writing, you should (formally or informally) identify the audience(s) your documents need to satisfy. A design document might need to persuade decision makers. A tutorial might need to provide very explicit instructions to someone utterly unfamiliar with your codebase. An API might need to provide complete and accurate reference information for any users of that API, be they experts or novices. Always try to identify a primary audience and write to that audience.

Good documentation need not be polished or “perfect.” One mistake engineers make when writing documentation is assuming they need to be much better writers. By that measure, few software engineers would write. Think about writing like you do about testing or any other process you need to do as an engineer. Write to your audience, in the voice and style that they expect. If you can read, you can write. Remember that your audience is standing where you once stood, but
without your new domain knowledge
. So you don’t need to be a great writer; you just need to get someone like you as familiar with the domain as you now are. (And as long as you get a stake in the ground, you can improve this document over time.)

Types of Audiences

We’ve pointed out that you should write at the skill level and domain knowledge appropriate for your audience.

But who precisely is your audience? Chances are, you have multiple audiences based on one or more of the following criteria:

Experience level (expert programmers, or junior engineers who might not even be familiar—gulp!—with the language).

Domain knowledge (team members, or other engineers in your organization who are familiar only with API endpoints).

Purpose (end users who might need your API to do a specific task and need to find that

 information quickly, or software gurus who are responsible for the guts of a particularly hairy implementation that you hope no one else needs to
maintain).

In some cases, different audiences require different writing styles, but in most cases, the trick is to write in a way that applies as broadly to your different audience groups as possible. Often, you will need to explain a complex topic to both an expert and a novice. Writing for the expert with domain knowledge may allow you to cut corners, but you’ll confuse the novice; conversely, explaining everything in detail to the novice will doubtless annoy the expert.

Obviously, writing such documents is a balancing act and there’s no silver bullet, but one thing we’ve found is that it helps to keep your documents
short
. Write descriptively enough to explain complex topics to people unfamiliar with the topic, but don’t lose or annoy experts. Writing a short document often requires you to write a longer one (getting all the information down) and then doing an edit pass, removing duplicate information where you can. This might sound tedious, but keep in mind that this expense is spread across all the readers of the documentation.

 As Blaise Pascal once said, “If I had more time, I would have written you a shorter letter.” By keeping a document short and clear, you will ensure that it will satisfy both an expert and a novice.

Another important audience distinction is based on how a user encounters a
document:

Seekers
 are engineers who
know what they want
 and want to know if what they are looking at fits the bill.

A key pedagogical device for this audience is
consistency
. If you are writing reference documentation for this group—within a code file, for example—you will want to have your comments follow a similar format so that readers can quickly scan a reference and see whether they find what they are looking for.

Stumblers
 might not know exactly what they want.

They might have only a vague idea of how to implement what they are working with. The key for this audience is
clarity
. Provide overviews or introductions (at the top of a file, for example) that explain the purpose of the code they are looking at. It’s also useful to identify when a doc is
not
 appropriate for an audience. A lot of documents at Google begin with a “TL;DR statement” such as “TL;DR: if you are not interested in C++ compilers at Google, you can stop reading now.”

Finally, one important audience distinction is between that of a customer (e.g., a user of an API) and that of a

provider (e.g., a member of the project team).

 As much as possible, documents intended for one should be kept apart from documents intended for the other. Implementation details are important to a team member for maintenance purposes; end users should not need to read such information. Often, engineers denote design decisions within the reference API of a library they publish. Such reasonings belong more appropriately in specific documents (design documents) or, at best, within the implementation details of code hidden behind an interface.
```

<a id="software-engineering-at-google-ch10-004"></a>
## software-engineering-at-google-ch10-004 — Documentation types and reference comments

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 209–259.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Documentation Types

Engineers write various different types of documentation as part of their work: design

 documents, code comments, how-to documents, project pages, and more. These all count as “documentation.” But it is important to know the different types, and to
not mix types
. A document should have, in general, a singular purpose, and stick to it. Just as an API should do one thing and do it well, avoid trying to do several things within one document. Instead, break out those pieces more logically.

There are several main types of documents that software engineers often need to write:

Reference documentation, including code comments

Design documents

Tutorials

Conceptual documentation

Landing pages

It was common in the early days of Google for teams to have monolithic wiki pages with bunches of links (many broken or obsolete), some conceptual information about how the system worked, an API reference, and so on, all sprinkled together. Such documents fail because they don’t serve a single purpose (and they also get so long that no one will read them; some notorious wiki pages scrolled through several dozens of screens). Instead, make sure your document has a singular purpose, and if adding something to that page doesn’t make sense, you probably want to find, or even create, another document for that purpose.

Reference Documentation

Reference

 documentation is the most common type that engineers

 need to write; indeed, they often need to write some form of reference documents every day. By reference documentation, we mean anything that documents the usage of code within the codebase.

 Code comments are the most common form of reference documentation that an engineer must maintain. Such comments can be divided into two basic camps: API comments versus implementation comments.

 Remember the audience differences between these two: API comments don’t need to discuss implementation details or design decisions and can’t assume a user is as versed in the API as the author.

Implementation comments, on the other hand, can assume a lot more domain knowledge of the reader, though be careful in assuming too much: people leave projects, and sometimes it’s safer to be methodical about exactly why you wrote this code the way you did.

Most reference documentation, even when provided as separate documentation from the code, is generated from

comments within the codebase itself. (As it should; reference documentation should be single-sourced as much as possible.) Some languages such as Java or Python have specific commenting frameworks (Javadoc, PyDoc, GoDoc) meant to make generation of this reference documentation easier.

Other languages, such as C++, have no standard “reference documentation” implementation, but because C++ separates out its API surface (in header or
.h
 files) from the implementation (
.cc
 files), header files are often a natural place to document a C++ API.

Google takes this approach: a C++ API deserves to have its reference documentation live within the header file. Other reference documentation is embedded directly in the Java, Python, and Go source code as well. Because Google’s Code Search browser (see
Code Search
) is so robust, we’ve found little benefit to providing separate generated reference documentation. Users in Code Search not only search code easily, they can usually find the original definition of that code as the top result. Having the documentation alongside the code’s definitions also makes the documentation easier to discover and maintain.

We all know that code comments are essential to a well-documented API. But what precisely is a “good” comment? Earlier in this chapter, we identified two major audiences for reference documentation: seekers and stumblers. Seekers know what they want; stumblers don’t. The key win for seekers is a consistently commented codebase so that they can quickly scan an API and find what they are looking for. The key win for stumblers is clearly identifying the purpose of an API, often at the top of a file header. We’ll walk through some code comments in the subsections that follow. The code commenting guidelines that follow apply to C++, but similar rules are in place at Google for other languages.
```

<a id="software-engineering-at-google-ch10-005"></a>
## software-engineering-at-google-ch10-005 — File and class comment requirements and specimens

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 261–299.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
File comments

Almost all

 code files at Google

must contain a file comment. (Some header files that contain only one utility function, etc., might deviate from this standard.) File comments should begin with a header of the following form:

// -----------------------------------------------------------------------------
// str_cat.h
// -----------------------------------------------------------------------------
//
// This header file contains functions for efficiently concatenating and appending
// strings: StrCat() and StrAppend(). Most of the work within these routines is
// actually handled through use of a special AlphaNum type, which was designed
// to be used as a parameter type that efficiently manages conversion to
// strings and avoids copies in the above operations.
…

Generally, a file comment should begin with an outline of what’s contained in the code you are reading. It should identify the code’s main use cases and intended audience (in the preceding case, developers who want to concatenate strings). Any API that cannot be succinctly described in the first paragraph or two is usually the sign of an API that is not well thought out. Consider breaking the API into separate components in those cases.

Class comments

Most modern programming

languages are object oriented.

 Class comments are therefore important for defining the API “objects” in use in a codebase. All public classes (and structs) at Google must contain a class comment describing the class/struct, important methods of that class, and the purpose of the class. Generally, class comments should be “nouned” with documentation emphasizing their object aspect. That is, say, “The Foo class contains x, y, z, allows you to do Bar, and has the following Baz aspects,” and so on.

Class comments should generally begin with a comment of the following form:

// -----------------------------------------------------------------------------
// AlphaNum
// -----------------------------------------------------------------------------
//
// The AlphaNum class acts as the main parameter type for StrCat() and
// StrAppend(), providing efficient conversion of numeric, boolean, and
// hexadecimal values (through the Hex type) into strings.

```

<a id="software-engineering-at-google-ch10-006"></a>
## software-engineering-at-google-ch10-006 — Function comments and boilerplate alternatives

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 300–344.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Function comments

All free functions, or public methods of a class, at Google must also contain a function comment

describing what the function
does
.

 Function comments should stress the
active
 nature of their use, beginning with an indicative verb describing what the function does and what is returned.

Function comments should generally begin with a comment of the following form:

// StrCat()
//
// Merges the given strings or numbers, using no delimiter(s),
// returning the merged result as a string.
…

Note that starting a function comment with a declarative verb introduces consistency across a header file. A seeker can quickly scan an API and read just the verb to get an idea of whether the function is appropriate: “Merges, Deletes, Creates,” and so on.

Some documentation styles (and some documentation generators) require various forms of boilerplate on function comments, like "Returns:", "Throws:", and so forth, but at Google we haven’t found them to be necessary. It is often clearer to present such information in a single prose comment that’s not broken up into artificial section boundaries:

// Creates a new record for a customer with the given name and address,
// and returns the record ID, or throws `DuplicateEntryError` if a
// record with that name already exists.

int

AddCustomer
(
string
 name
,

string
 address
);

Notice how the postcondition, parameters, return value, and exceptional cases are naturally documented together (in this case, in a single sentence), because they are not independent of one another. Adding explicit boilerplate sections would make the comment more verbose and

repetitive, but

 no clearer (and arguably less clear).
```

<a id="software-engineering-at-google-ch10-007"></a>
## software-engineering-at-google-ch10-007 — Design documents and trade-offs

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 346–356.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Design Docs

Most teams at Google require an approved design document before starting work on any major project.

 A software engineer typically writes the proposed design document using a specific design doc template approved by the team. Such documents are designed to be collaborative, so they are often shared in Google Docs, which has good collaboration tools. Some teams require such design documents to be discussed and debated at specific team meetings, where the finer points of the design can be discussed or critiqued by experts. In some respects, these design discussions act as a form of code review before any code is written.

Because the development of a design document is one of the first processes an engineer undertakes before deploying a new system, it is also a convenient place to ensure that various concerns are covered. The canonical design document templates at Google require engineers to consider aspects of their design such as security implications, internationalization, storage requirements and privacy concerns, and so on. In most cases, such parts of those design documents are reviewed by experts in those domains.

A good design document should cover the goals of the design, its implementation strategy, and propose key design decisions with an emphasis on their individual trade-offs. The best design documents suggest design goals and cover alternative designs, denoting their strong and weak points.

A good design document, once approved, also acts not only as a historical record, but as a measure of whether the project successfully achieved its goals. Most teams archive their design documents in an appropriate location within their team documents so that they can review them at a later time. It’s often useful to review a design document before a product is launched to ensure that the stated goals when the design document was written remain the stated goals at launch (and if they do not, either the document or the product can be adjusted accordingly).
```

<a id="software-engineering-at-google-ch10-008"></a>
## software-engineering-at-google-ch10-008 — Tutorials and paired procedure examples

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 358–421.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

Transcription/context notes: The chapter explicitly calls its Documentation Philosophy section personal opinion. Tutorial numbering and some syntax-highlighting whitespace are not retained by the plain-text extraction; consult original HTML.

```text
Tutorials

Every software engineer, when they join a new team, will want to get up to speed as quickly as possible.

 Having a tutorial that walks someone through the setup of a new project is invaluable; “Hello World” has established itself as one of the best ways to ensure that all team members start off on the right foot.

This goes for documents as well as code. Most projects deserve a “Hello World” document that assumes nothing and gets the engineer to make something “real” happen.

Often, the best time to write a tutorial, if one does not yet exist, is when you first join a team. (It’s also the best time to find bugs in any existing tutorial you are following.) Get a notepad or other way to take notes, and write down everything you need to do along the way, assuming no domain knowledge or special setup constraints; after you’re done, you’ll likely know what mistakes you made during the process—and why—and can then edit down your steps to get a more streamlined tutorial. Importantly, write
everything
 you need to do along the way; try not to assume any particular setup, permissions, or domain knowledge. If you do need to assume some other setup, state that clearly in the beginning of the tutorial as a set of prerequisites.

Most tutorials require you to perform a number of steps, in order. In those cases, number those steps explicitly. If the focus of the tutorial is on the
user
 (say, for external developer documentation), then number each action that a user needs to undertake. Don’t number actions that the system may take in response to such user actions.

It is critical and important to number explicitly every step when doing this. Nothing is more annoying than an error on step 4 because you forget to tell someone to properly authorize their username, for example.

Example: A bad tutorial

Download the package from our server at http://example.com

Copy the shell script to your home directory

Execute the shell script

The foobar system will communicate with the authentication system

Once authenticated, foobar will bootstrap a new database named “baz”

Test “baz” by executing a SQL command on the command line

Type: CREATE DATABASE my_foobar_db;

In the preceding procedure, steps 4 and 5 happen on the server end. It’s unclear whether the user needs to do anything, but they don’t, so those side effects can be mentioned as part of step 3. As well, it’s unclear whether step 6 and step 7 are different. (They aren’t.) Combine all atomic user operations into single steps so that the user knows they need to do something at each step in the process. Also, if your tutorial has user-visible input or output, denote that on separate lines (often using the convention of a
monospaced bold
 font).

Example: A bad tutorial made better

Download the

package from our server at
http://example.com
:

$ curl -I
http://example.com

Copy the shell script to your home directory:

$ cp foobar.sh ~

Execute the shell script in your home directory:

$ cd ~; foobar.sh

The foobar system will first communicate with the authentication system. Once authenticated, foobar will bootstrap a new database named “baz” and open an input shell.

Test “baz” by executing a SQL command on the command line:

baz:$ CREATE DATABASE my_foobar_db;

Note how each step requires specific user intervention. If, instead, the tutorial had a focus on some other aspect (e.g., a document about the “life of a server”), number those steps from the perspective of that focus (what the server does).
```

<a id="software-engineering-at-google-ch10-009"></a>
## software-engineering-at-google-ch10-009 — Conceptual documentation and limits of inline placement

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 423–441.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Conceptual Documentation

Some code requires deeper explanations or insights than can be obtained simply by reading the reference documentation.

 In those cases, we need conceptual documentation to provide overviews of the APIs or systems. Some examples of conceptual documentation might be a library overview for a popular API, a document describing the life cycle of data within a server, and so on. In almost all cases, a conceptual document is meant to augment, not replace, a reference documentation set. Often this leads to duplication of some information, but with a purpose: to promote clarity. In those cases, it is not necessary for a conceptual document to cover all edge cases (though a reference should cover those cases religiously). In this case, sacrificing some accuracy is acceptable for clarity. The main point of a conceptual document is to impart understanding.

“Concept” documents are the most difficult forms of documentation to write. As a result, they are often the most neglected type of document within a software engineer’s toolbox. One problem engineers face when writing conceptual documentation is that it often cannot be embedded directly within the source code because there isn’t a canonical location to place it.

Some APIs have a relatively broad API surface area, in which case, a file comment might be an appropriate place for a “conceptual” explanation of the API. But often, an API works in conjunction with other APIs and/or modules. The only logical place to document such complex behavior is through a separate conceptual document. If comments are the unit tests of documentation, conceptual documents are the integration tests.

Even when an API is appropriately scoped, it often makes sense to provide a separate conceptual document. For example, Abseil’s
StrFormat
 library covers a variety of concepts that accomplished users of the API should understand. In those cases, both internally and externally, we provide a
format concepts document
.

A concept document needs to be useful to a broad audience: both experts and novices alike. Moreover, it needs to emphasize
clarity
, so it often needs to sacrifice completeness (something best reserved for a reference) and (sometimes) strict accuracy. That’s not to say a conceptual document should intentionally be inaccurate; it just means that it should focus on common usage and leave rare usages or side effects for reference documentation.
```

<a id="software-engineering-at-google-ch10-010"></a>
## software-engineering-at-google-ch10-010 — Landing pages and competing audiences

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 443–455.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Landing Pages

Most engineers are members of a team, and most teams have a “team page” somewhere on their company’s intranet.

Often, these sites are a bit of a mess: a typical landing page might contain some interesting links, sometimes several documents titled “read this first!”, and some information both for the team and for its customers. Such documents start out useful but rapidly turn into disasters; because they become so cumbersome to maintain, they will eventually get so obsolete that they will be fixed by only the brave or the desperate.

Luckily, such documents look intimidating, but are actually straightforward to fix: ensure that a landing page clearly identifies its purpose, and then include
only
 links to other pages for more information. If something on a landing page is doing more than being a traffic cop, it is
not doing its job
. If you have a separate setup document, link to that from the landing page as a separate document. If you have too many links on the landing page (your page should not scroll multiple screens), consider breaking up the pages by taxonomy, under different sections.

Most poorly configured landing pages serve two different purposes: they are the “goto” page for someone who is a user of your product or API, or they are the home page for a team. Don’t have the page serve both masters—it will become confusing. Create a separate “team page” as an internal page apart from the main landing page. What the team needs to know is often quite different than what a customer of your API needs to know.
```

<a id="software-engineering-at-google-ch10-011"></a>
## software-engineering-at-google-ch10-011 — Documentation review and canonical developer guides

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 457–499.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Documentation Reviews

At Google, all code needs to be reviewed, and our code review process is well understood and accepted.

 In general, documentation also needs review (though this is less universally accepted). If you want to “test” whether your documentation works, you should generally have someone else review it.

A technical document benefits from three different types of reviews, each emphasizing different aspects:

A technical review, for accuracy.

This review is usually done by a subject matter expert, often another member of your team. Often, this is part of a code review itself.

An audience review, for clarity.

This is usually someone unfamiliar with the domain. This might be someone new to your team or a customer of your API.

A writing review, for consistency.

 This is often a technical writer or volunteer.

Of course, some of these lines are sometimes blurred, but if your document is high profile or might end up being externally published, you probably want to ensure that it receives more types of reviews. (We’ve used a similar review process for this book.) Any document tends to benefit from the aforementioned reviews, even if some of those reviews are ad hoc. That said, even getting one reviewer to review your text is preferable to having no one review it.

Importantly, if documentation is tied into the engineering workflow, it will often improve over time. Most documents at Google now implicitly go through an audience review because at some point, their audience will be using them, and hopefully letting you know when they aren’t working (via bugs or other forms of feedback).

Case Study: The Developer Guide Library

As mentioned earlier, there were problems associated with having most (almost all) engineering documentation contained within a shared wiki: little ownership of important documentation, competing documentation, obsolete information, and difficulty in filing bugs or issues with documentation. But this problem was not seen in some documents: the Google C++ style guide was owned by a select group of senior engineers (style arbiters) who managed it. The document was kept in good shape because certain people cared about it. They implicitly owned that document. The document was also canonical: there was only one C++ style guide.

As previously mentioned, documentation that sits directly within source code is one way to promote the establishment of canonical documents; if the documentation sits alongside the source code, it should usually be the most applicable (hopefully). At Google, each API usually has a separate
g3doc
 directory where such documents live (written as Markdown files and readable within our Code Search browser). Having the documentation exist alongside the source code not only establishes de facto ownership, it makes the documentation seem more wholly “part” of the code.

Some documentation sets, however, cannot exist very logically within source code. A “C++ developer guide” for Googlers, for example, has no obvious place to sit within the source code.

There is no master “C++” directory where people will look for such information. In this case (and others that crossed API boundaries), it became useful to create standalone documentation sets in their own depot. Many of these culled together associated existing documents into a common set, with common navigation and look-and-feel. Such documents were noted as “Developer Guides” and, like the code in the codebase, were under source control in a specific documentation depot, with this depot organized by topic rather than API. Often, technical writers managed these developer guides, because they were better at explaining topics across API boundaries.

Over time, these developer guides became canonical. Users who wrote competing or supplementary documents became amenable to adding their documents to the canonical document set after it was established, and then deprecating their competing documents. Eventually, the C++ style guide became part of a larger “C++ Developer Guide.” As the documentation set became more comprehensive and more authoritative, its quality also improved. Engineers began logging bugs because they knew someone was maintaining these documents. Because the documents were locked down under source control, with proper owners, engineers also began sending changelists directly to the technical writers.

The

 introduction of go/ links (see
Knowledge Sharing
) allowed most documents to, in effect, more easily establish themselves as canonical on any given topic. Our C++ Developer Guide became established at “go/cpp,” for example. With better internal search, go/ links, and the integration of multiple documents into a common documentation set, such canonical documentation sets became more authoritative and robust over time.
```

<a id="software-engineering-at-google-ch10-012"></a>
## software-engineering-at-google-ch10-012 — Documentation philosophy, framing, and useful redundancy

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 501–543.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

Transcription/context notes: The chapter explicitly calls its Documentation Philosophy section personal opinion. Tutorial numbering and some syntax-highlighting whitespace are not retained by the plain-text extraction; consult original HTML.

```text
Documentation Philosophy

Caveat: the following section is more of a treatise on technical writing

 best practices (and personal opinion) than of “how Google does it.” Consider it optional for software engineers to fully grasp, though understanding these concepts will likely allow you to more easily write technical information.

WHO, WHAT, WHEN, WHERE, and WHY

Most technical documentation answers a “HOW” question.

How does this work? How do I program to this API? How do I set up this server? As a result, there’s a tendency for software engineers to jump straight into the “HOW” on any given document and ignore the other questions associated with it: the WHO, WHAT, WHEN, WHERE, and WHY.

It’s true that none of those are generally as important as the HOW—a design document is an exception because an equivalent aspect is often the WHY—but without a proper framing of technical documentation, documents end up confusing. Try to address the other questions in the first two paragraphs of any
document:

WHO was discussed previously: that’s the audience. But sometimes you also need to explicitly call out and address the audience in a document. Example: “This document is for new engineers on the Secret Wizard project.”

WHAT identifies the purpose of this document: “This document is a tutorial designed to start a Frobber server in a test environment.” Sometimes, merely writing the WHAT helps you frame the document appropriately. If you start adding information that isn’t applicable to the WHAT, you might want to move that information into a separate document.

WHEN identifies when this document was created, reviewed, or updated. Documents in source code have this date noted implicitly, and some other publishing schemes automate this as well. But, if not, make sure to note the date on which the document was written (or last revised) on the document itself.

WHERE is often implicit as well, but decide where the document should live. Usually, the preference should be under some sort of version control, ideally
with the source code it documents
. But other formats work for different purposes as well. At Google, we often use Google Docs for easy collaboration, particularly on design issues. At some point, however, any shared document becomes less of a discussion and more of a stable historical record. At that point, move it to someplace more permanent, with clear ownership, version control, and responsibility.

WHY sets up the purpose for the document. Summarize what you expect someone to take away from the document after reading it. A good rule of thumb is to establish the WHY in the introduction to a document. When you write the summary, verify whether you’ve met your original expectations (and revise
accordingly).

The Beginning, Middle, and End

All documents—indeed, all parts of documents—have a beginning, middle, and end.

Although it sounds amazingly

 silly, most documents should often have, at a minimum, those three sections. A document with only one section has only one thing to say, and very few documents have only one thing to say. Don’t be afraid to add sections to your document; they break up the flow into logical pieces and provide readers with a roadmap of what the document covers.

Even the simplest document usually has more than one thing to say. Our popular “
C++
 Tips of the Week” have traditionally been very short, focusing on one small piece of advice. However, even here, having sections helps. Traditionally, the first section denotes the problem, the middle section goes through the recommended solutions, and the conclusion summarizes the takeaways. Had the document consisted of only one section, some readers would doubtless have difficulty teasing out the important points.

Most engineers loathe redundancy, and with good reason.

 But in documentation, redundancy is often useful. An important point buried within a wall of text can be difficult to remember or tease out. On the other hand, placing that point at a more prominent location early can lose context provided later on. Usually, the solution is to introduce and summarize the point within an introductory paragraph, and then use the rest of the section to make your case in a more detailed fashion. In this case, redundancy helps the reader understand the importance of what is being stated.
```

<a id="software-engineering-at-google-ch10-013"></a>
## software-engineering-at-google-ch10-013 — Completeness, accuracy, clarity, and misplaced details

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 545–559.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

Transcription/context notes: The chapter explicitly calls its Documentation Philosophy section personal opinion. Tutorial numbering and some syntax-highlighting whitespace are not retained by the plain-text extraction; consult original HTML.

```text
The Parameters of Good Documentation

There are usually three aspects of good

documentation: completeness, accuracy, and clarity.

 You rarely get all three within the same document; as you try to make a document more “complete,” for example, clarity can begin to suffer. If you try to document every possible use case of an API, you might end up with an incomprehensible mess.

 For programming languages, being completely accurate in all cases (and documenting all possible side effects) can also affect clarity. For other documents, trying to be clear about a complicated topic can subtly affect the accuracy of the document; you might decide to ignore some rare side effects in a conceptual document, for example, because the point of the document is to familiarize someone with the usage of an API, not provide a dogmatic overview of all intended behavior.

In each case, a “good document” is defined as the document that is
doing its intended job
. As a result, you rarely want a document doing more than one job. For each document (and for each document type), decide on its focus and adjust the writing appropriately. Writing a conceptual document? You probably don’t need to cover every part of the API. Writing a reference? You probably want this complete, but perhaps must sacrifice some clarity. Writing a landing page? Focus on organization and keep discussion to a minimum. All of this adds up to quality, which, admittedly, is stubbornly difficult to accurately measure.

How can you quickly improve the quality of a document? Focus on the needs of the audience. Often, less is more. For example, one mistake engineers often make is adding design decisions or implementation details to an API document. Much like you should ideally separate the interface from an implementation within a well-designed API, you should avoid discussing design decisions in an API document. Users don’t need to know this information. Instead, put those decisions in a specialized document for that purpose (usually a design doc).
```

<a id="software-engineering-at-google-ch10-014"></a>
## software-engineering-at-google-ch10-014 — Stale documents and freshness metadata comment

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 561–576.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
Deprecating Documents

Just like old code can cause problems, so can old documents.

 Over time, documents become stale, obsolete, or (often) abandoned. Try as much as possible to avoid abandoned documents, but when a document no longer serves any purpose, either remove it or identify it as obsolete (and, if available, indicate where to go for new information). Even for unowned documents, someone adding a note that “This no longer works!” is more helpful than saying nothing and leaving something that seems authoritative but no longer works.

At Google, we often attach “freshness dates” to documentation. Such documents note the last time a document was reviewed, and metadata in the documentation set will send email reminders when the document hasn’t been touched in, for example, three months. Such freshness dates, as shown in the following example—and tracking your documents as bugs—can help make a documentation set easier to maintain over time, which is the main concern for a document:

<!--*
# Document freshness: For more information, see
go/fresh-source
.
freshness: { owner: `username` reviewed: '2019-02-27' }
*-->

Users who own such a document have an incentive to keep that freshness date current (and if the document is under source control, that requires a code review). As a result, it’s a low-cost means to ensure that a document is looked over from time to time. At Google, we found that including the owner of a document in this freshness date within the document itself with a byline of “Last reviewed by...” led to increased adoption as well.
```

<a id="software-engineering-at-google-ch10-015"></a>
## software-engineering-at-google-ch10-015 — Technical writers, documentation limitations, and concluding positions

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 578–608.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
When Do You Need Technical Writers?

When

 Google was young and growing, there weren’t enough technical writers in software engineering. (That’s still the case.) Those projects deemed important tended to receive a technical writer, regardless of whether that team really needed one.

 The idea was that the writer could relieve the team of some of the burden of writing and maintaining documents and (theoretically) allow the important project to achieve greater velocity. This turned out to be a bad assumption.

We learned that most engineering teams can write documentation for themselves (their team) perfectly fine; it’s only when they are writing documents for another audience that they tend to need help because it’s difficult to write to another audience. The feedback loop within your team regarding documents is more immediate, the domain knowledge and assumptions are clearer, and the perceived needs are more obvious. Of course, a technical writer can often do a better job with grammar and organization, but supporting a single team isn’t the best use of a limited and specialized resource; it doesn’t scale. It introduced a perverse incentive: become an important project and your software engineers won’t need to write documents. Discouraging engineers from writing documents turns out to be the opposite of what you want to do.

Because they are a limited resource, technical writers should generally focus on tasks that software engineers
don’t
 need to do as part of their normal duties. Usually, this involves writing documents that cross API boundaries. Project Foo might clearly know what documentation Project Foo needs, but it probably has a less clear idea what Project Bar needs. A technical writer is better able to stand in as a person unfamiliar with the domain. In fact, it’s one of their critical roles: to challenge the assumptions your team makes about the utility of your project. It’s one of the reasons why many, if not most, software engineering technical writers tend to focus on this specific type of API documentation.

Conclusion

Google has made good strides in addressing documentation quality over the past decade, but to be frank, documentation at Google is not yet a first-class citizen. For comparison, engineers have gradually accepted that testing is necessary for any code change, no matter how small. As well, testing tooling is robust, varied and plugged into an engineering workflow at various points. Documentation is not ingrained at nearly the same level.

To be fair, there’s not necessarily the same need to address documentation as with testing. Tests can be made atomic (unit tests) and can follow prescribed form and function. Documents, for the most part, cannot. Tests can be automated, and schemes to automate documentation are often lacking. Documents are necessarily subjective; the quality of the document is measured not by the writer, but by the reader, and often quite asynchronously. That said, there is a recognition that documentation is important, and processes around document development are improving. In this author’s opinion, the quality of documentation at Google is better than in most software engineering shops.

To change the quality of engineering documentation, engineers—and the entire engineering organization—need to accept that they are both the problem and the solution. Rather than throw up their hands at the state of documentation, they need to realize that producing quality documentation is part of their job and saves them time and effort in the long run. For any piece of code that you expect to live more than a few months, the extra cycles you put in documenting that code will not only help others, it will help you maintain that code as well.

TL;DRs

Documentation is hugely important over time and scale.

Documentation changes should leverage the existing developer workflow.

Keep documents focused on one purpose.

Write for your audience, not yourself.
```

<a id="software-engineering-at-google-ch10-016"></a>
## software-engineering-at-google-ch10-016 — Maintenance and deprecated-wiki footnotes

Source: [ch10.html](../../../../books/software-engineering-at-google/ch10.html); reading unit `ch10`, lines 610–615.

Attribution: Tom Manshreck

Context: Documentation chapter; includes code comments, their relationship to other documentation, qualifications, and examples.

```text
1
OK, you will need to maintain it and revise it occasionally.
2
English is still the primary language for most programmers, and most technical documentation for programmers relies on an understanding of English.
3
When we deprecated GooWiki, we found that around 90% of the documents had no views or updates in the previous few months.
```

<a id="software-engineering-at-google-ch11-001"></a>
## software-engineering-at-google-ch11-001 — Commented introductory test example

Source: [ch11.html](../../../../books/software-engineering-at-google/ch11.html); reading unit `ch11`, lines 90–108.

Attribution: Adam Bender

Context: Testing chapter context for explanation through tests and accompanying comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Write, Run, React

In its purest form, automating

 testing consists of three activities: writing tests, running tests, and reacting to test failures. An automated test is a small bit of code, usually a single function or method, that calls into an isolated part of a larger system that you want to test. The test code sets up an expected environment, calls into the system, usually with a known input, and verifies the result. Some of the tests are very small, exercising a single code path; others are much larger and can involve entire systems, like a mobile operating system or web browser.

An example test
 presents a deliberately simple test in Java using no frameworks or testing libraries. This is not how you would write an entire test suite, but at its core every automated test looks similar to this very simple example.

Example 11-1.
An example test

// Verifies a Calculator class can handle negative results.
public void main(String[] args) {
   Calculator calculator = new Calculator();
   int expectedResult = -3;
   int actualResult = calculator.subtract(2, 5); // Given 2, Subtracts 5.
   assert(expectedResult == actualResult);
}
```

<a id="software-engineering-at-google-ch11-002"></a>
## software-engineering-at-google-ch11-002 — Tests as executable documentation and design feedback

Source: [ch11.html](../../../../books/software-engineering-at-google/ch11.html); reading unit `ch11`, lines 132–161.

Attribution: Adam Bender

Context: Testing chapter context for explanation through tests and accompanying comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Benefits of Testing Code

To developers coming

 from organizations that

 don’t have a strong testing culture, the idea of writing tests as a means of improving productivity and velocity might seem antithetical. After all, the act of writing tests can take just as long (if not longer!) than implementing a feature would take in the first place. On the contrary, at Google, we’ve found that investing in software tests provides several key benefits to developer
productivity:

Less debugging

As you would expect, tested code has fewer defects when it is submitted. Critically, it also has fewer defects throughout its existence; most of them will be caught before the code is submitted. A piece of code at Google is expected to be modified dozens of times in its lifetime. It will be changed by other teams and even automated code maintenance systems. A test written once continues to pay dividends and prevent costly defects and annoying debugging sessions through the lifetime of the project. Changes to a project, or the dependencies of a project, that break a test can be quickly detected by test infrastructure and rolled back before the problem is ever released to production.

Increased confidence in changes

All software changes. Teams with good tests can review and accept changes to their project with confidence because all important behaviors of their project are continuously verified. Such projects encourage refactoring. Changes that refactor code while preserving existing behavior should (ideally) require no changes to existing tests.

Improved documentation

Software documentation is notoriously unreliable. From outdated requirements to missing edge cases, it is common for documentation to have a tenuous relationship to the code. Clear, focused tests that exercise one behavior at a time function as executable documentation. If you want to know what the code does in a particular case, look at the test for that case. Even better, when requirements change and new code breaks an existing test, we get a clear signal that the “documentation” is now out of date. Note that tests work best as documentation only if care is taken to keep them clear and concise.

Simpler reviews

All code at Google is reviewed by at least one other engineer before it can be submitted (see
Code Review
 for more details). A code reviewer spends less effort verifying the code works as expected if the code review includes thorough tests that demonstrate code correctness, edge cases, and error conditions. Instead of the tedious effort needed to mentally walk each case through the code, the reviewer can verify that each case has a passing test.

Thoughtful design

Writing tests for new code is a practical means of exercising the API design of the code itself. If new code is difficult to test, it is often because the code being tested has too many responsibilities or difficult-to-manage dependencies. Well-designed code should be modular, avoiding tight coupling and focusing on specific responsibilities. Fixing design issues early often means less rework later.
```

<a id="software-engineering-at-google-ch11-003"></a>
## software-engineering-at-google-ch11-003 — Obvious tests and future readers

Source: [ch11.html](../../../../books/software-engineering-at-google/ch11.html); reading unit `ch11`, lines 273–287.

Attribution: Adam Bender

Context: Testing chapter context for explanation through tests and accompanying comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Properties common to all test sizes

All tests should strive to be hermetic: a test should contain all of the information necessary to set up, execute, and tear down its environment.

 Tests should assume as little as possible about the outside environment, such as the order in which the tests are run. For example, they should not rely on a shared database. This constraint becomes more challenging with larger tests, but effort should still be made to ensure isolation.

A test should contain
only
 the information required to exercise the behavior in question. Keeping tests clear and simple aids reviewers in verifying that the code does what it says it does.

Clear code also aids in diagnosing failure when they fail. We like to say that “a test should be obvious upon inspection.” Because there are no tests for the tests themselves, they require manual review as an important check on correctness. As a corollary to this, we also
strongly discourage the use of control flow statements like conditionals and loops in a test
. More complex test flows risk containing bugs themselves and make it more difficult to determine the cause of a test failure.

Remember that tests are often revisited only when something breaks. When you are called to fix a broken test that you have never seen before, you will be thankful someone took the time to make it easy to understand. Code is read far more than it is written, so make sure you write the test you’d like to read!
```

<a id="software-engineering-at-google-ch11-004"></a>
## software-engineering-at-google-ch11-004 — Testing education includes documentation benefits

Source: [ch11.html](../../../../books/software-engineering-at-google/ch11.html); reading unit `ch11`, lines 476–488.

Attribution: Adam Bender

Context: Testing chapter context for explanation through tests and accompanying comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Orientation Classes

Even though much of the early

 engineering staff at Google eschewed testing, the pioneers of automated testing at Google knew that at the rate the company was growing, new engineers would quickly outnumber existing team members. If they could reach all the new hires in the company, it could be an extremely effective avenue for introducing cultural change. Fortunately, there was, and still is, a single choke point that all new engineering hires pass through: orientation.

Most of Google’s early orientation program concerned things like medical benefits and how Google Search worked, but starting in 2005 it also began including an hour-long discussion of the value of automated testing.
9
 The class covered the various benefits of testing, such as increased productivity, better documentation, and support for refactoring. It also covered how to write a good test. For many Nooglers (new Googlers) at the time, such a class was their first exposure to this material. Most important, all of these ideas were presented as though they were standard practice at the company. The new hires had no idea that they were being used as trojan horses to sneak this idea into their unsuspecting teams.

As Nooglers joined their teams following orientation, they began writing tests and questioning those on the team who didn’t. Within only a year or two, the population of engineers who had been taught testing outnumbered the pretesting culture engineers. As a result, many new projects started off on the right foot.

Testing has now become more widely practiced in the industry, so most new hires arrive with the expectations of automated testing firmly in place. Nonetheless, orientation classes continue to set expectations about testing and connect what Nooglers know about testing outside of Google to the challenges of doing so in our very large and very complex codebase.
```

<a id="software-engineering-at-google-ch12-001"></a>
## software-engineering-at-google-ch12-001 — Tests as documentation and the cost of unclear tests

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 17–55.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
After preventing bugs, the most important purpose of a test is to improve engineers’ productivity.

Compared to broader-scoped tests, unit tests have many properties that make them an excellent way to optimize productivity:

They tend to be small according to Google’s definitions of test size.

 Small tests are fast and deterministic, allowing developers to run them frequently as part of their workflow and get immediate feedback.

They tend to be easy to write at the same time as the code they’re testing, allowing engineers to focus their tests on the code they’re working on without having to set up and understand a larger system.

They promote high levels of test coverage because they are quick and easy to write. High test coverage allows engineers to make changes with confidence that they aren’t breaking anything.

They tend to make it easy to understand what’s wrong when they fail because each test is conceptually simple and focused on a particular part of the system.

They can serve as documentation and examples, showing engineers how to use the part of the system being tested and how that system is intended to work.

Due to their many advantages, most tests written at Google are unit tests, and as a rule of thumb, we encourage engineers to aim for a mix of about 80% unit tests and 20% broader-scoped tests. This advice, coupled with the ease of writing unit tests and the speed with which they run, means that engineers run a
lot
 of unit tests—it’s not at all unusual for an engineer to execute thousands of unit tests (directly or indirectly) during the average workday.

Because they make up such a big part of engineers’ lives, Google puts a lot of focus on
test maintainability
. Maintainable tests

 are ones that "just work": after writing them, engineers don’t need to think about them again until they fail, and those failures indicate real bugs with clear causes. The bulk of this chapter focuses on exploring the idea of maintainability and techniques for achieving it.

The Importance of Maintainability

Imagine this scenario: Mary wants to add a simple

 new feature to the product and is able to implement it quickly, perhaps requiring only a couple dozen lines of code. But when she goes to check in her change, she gets a screen full of errors back from the automated testing system. She spends the rest of the day going through those failures one by one. In each case, the change introduced no actual bug, but broke some of the assumptions that the test made about the internal structure of the code, requiring those tests to be updated. Often, she has difficulty figuring out what the tests were trying to do in the first place, and the hacks she adds to fix them make those tests even more difficult to understand in the future. Ultimately, what should have been a quick job ends up taking hours or even days of busywork, killing Mary’s productivity and sapping her morale.

Here, testing had the opposite of its intended effect by draining productivity rather than improving it while not meaningfully increasing the quality of the code under test. This scenario is far too common, and Google engineers struggle with it every day. There’s no magic bullet, but many engineers at Google have been working to develop sets of patterns and practices to alleviate these problems, which we encourage the rest of the company to follow.

The problems Mary ran into weren’t her fault, and there was nothing she could have done to avoid them: bad tests must be fixed before they are checked in, lest they impose a drag on future engineers. Broadly speaking, the issues she encountered fall into two categories. First, the tests she was working with were
brittle
: they broke in response to a harmless and unrelated change that introduced no real bugs. Second, the tests were
unclear
: after they were failing, it was difficult to determine what was wrong, how to fix it, and what those tests were supposed to be doing in the first place.
```

<a id="software-engineering-at-google-ch12-002"></a>
## software-engineering-at-google-ch12-002 — Public-API tests as examples and contracts

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 111–230.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Test via Public APIs

Now that we

 understand

our goal, let’s look at some practices for making sure that tests don’t need to change unless the requirements of the system being tested change. By far the most important way to ensure this is to write tests that invoke the system being tested in the same way its users would; that is, make calls against its public API
rather than its implementation details
. If tests work the same way as the system’s users, by definition, change that breaks a test might also break a user. As an additional bonus, such tests can serve as useful examples and documentation for users.

Consider
A transaction API
, which validates a transaction and saves it to a database.

Example 12-1.
A transaction API

public void processTransaction(Transaction transaction) {
  if (isValid(transaction)) {
    saveToDatabase(transaction);
  }
}

private boolean isValid(Transaction t) {
  return t.getAmount() < t.getSender().getBalance();
}

private void saveToDatabase(Transaction t) {
  String s = t.getSender() + "," + t.getRecipient() + "," + t.getAmount();
  database.put(t.getId(), s);
}

public void setAccountBalance(String accountName, int balance) {
  // Write the balance to the database directly
}

public void getAccountBalance(String accountName) {
  // Read transactions from the database to determine the account balance
}

A tempting way to test this code would be to remove the "private" visibility modifiers and test the implementation logic directly, as demonstrated in
A naive test of a transaction API’s implementation
.

Example 12-2.
A naive test of a transaction API’s implementation

@Test
public void emptyAccountShouldNotBeValid() {
  assertThat(processor.isValid(newTransaction().setSender(EMPTY_ACCOUNT)))
      .isFalse();
}

@Test
public void shouldSaveSerializedData() {
  processor.saveToDatabase(newTransaction()
      .setId(123)
      .setSender("me")
      .setRecipient("you")
      .setAmount(100));
  assertThat(database.get(123)).isEqualTo("me,you,100");
}

This test interacts with the transaction processor in a much different way than its real users would: it peers into the system’s internal state and calls methods that aren’t publicly exposed as part of the system’s API. As a result, the test is brittle, and almost any refactoring of the system under test (such as renaming its methods, factoring them out into a helper class, or changing the serialization format) would cause the test to break, even if such a change would be invisible to the class’s real users.

Instead, the same test coverage can be achieved by testing only against the class’s public API, as shown in
Testing the public API
.
2

Example 12-3.
Testing the public API

@Test
public void shouldTransferFunds() {
  processor.setAccountBalance("me", 150);
  processor.setAccountBalance("you", 20);

  processor.processTransaction(newTransaction()
      .setSender("me")
      .setRecipient("you")
      .setAmount(100));

  assertThat(processor.getAccountBalance("me")).isEqualTo(50);
  assertThat(processor.getAccountBalance("you")).isEqualTo(120);
}

@Test
public void shouldNotPerformInvalidTransactions() {
  processor.setAccountBalance("me", 50);
  processor.setAccountBalance("you", 20);

  processor.processTransaction(newTransaction()
      .setSender("me")
      .setRecipient("you")
      .setAmount(100));

  assertThat(processor.getAccountBalance("me")).isEqualTo(50);
  assertThat(processor.getAccountBalance("you")).isEqualTo(20);
}

Tests using only public APIs are, by definition, accessing the system under test in the same manner that its users would. Such tests are more realistic and less brittle because they form explicit contracts: if such a test breaks, it implies that an existing user of the system will also be broken. Testing only these contracts means that you’re free to do whatever internal refactoring of the system you want without having to worry about making tedious changes to tests.

It’s not always clear what constitutes a "public API," and the question really gets to the heart of what a "unit" is in unit testing.

 Units can be as small as an individual function or as broad as a set of several related packages/modules. When we say "public API" in this context, we’re really talking about the API exposed by that unit to third parties outside of the team that owns the code. This doesn’t always align with the notion of visibility provided by some programming languages; for example, classes in Java might define themselves as "public" to be accessible by other packages in the same unit but are not intended for use by other parties outside of the unit. Some languages like Python have no built-in notion of visibility (often relying on conventions like prefixing private method names with underscores), and build systems like
Bazel
 can further restrict who is allowed to depend on APIs declared public by the programming language.

Defining an appropriate scope for a unit

 and hence what should be considered the public API is more art than science, but here are some rules of thumb:

If a method or class exists only to support one or two other classes (i.e., it is a "helper class"), it probably shouldn’t be considered its own unit, and its functionality should be tested through those classes instead of directly.

If a package or class is designed to be accessible by anyone without having to consult with its owners, it almost certainly constitutes a unit that should be tested directly, where its tests access the unit in the same way that the users would.

If a package or class can be accessed only by the people who own it, but it is designed to provide a general piece of functionality useful in a range of contexts (i.e., it is a "support library"), it should also be considered a unit and tested directly. This will usually create some redundancy in testing given that the support library’s code will be covered both by its own tests and the tests of its users. However, such redundancy can be valuable: without it, a gap in test coverage could be introduced if one of the library’s users (and its tests) were ever removed.

At Google, we’ve found that engineers sometimes need to be persuaded that testing via public APIs is better than testing against implementation details. The reluctance is understandable because it’s often much easier to write tests focused on the piece of code you just wrote rather than figuring out how that code affects the system as a whole. Nevertheless, we have found it valuable to encourage such practices, as the extra upfront effort pays for itself many times over in reduced maintenance burden. Testing against public APIs won’t completely prevent brittleness, but it’s the most important thing you can do to ensure that your tests fail only in the event of meaningful changes to your system.
```

<a id="software-engineering-at-google-ch12-003"></a>
## software-engineering-at-google-ch12-003 — Test clarity, complete context, and paired examples

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 301–377.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Writing Clear Tests

Sooner or later, even if we’ve completely

avoided

 brittleness, our tests will fail. Failure

 is a good

thing—test failures provide useful signals to engineers, and are one of the main ways that a unit test provides value.

 Test failures happen for one of two reasons:
3

The system under test has a problem or is incomplete. This result is exactly what tests are designed for: alerting you to bugs so that you can fix them.

The test itself is flawed. In this case, nothing is wrong with the system under test, but the test was specified incorrectly. If this was an existing test rather than one that you just wrote, this means that the test is brittle. The previous section discussed how to avoid brittle tests, but it’s rarely possible to eliminate them entirely.

When a test fails, an engineer’s first job is to identify which of these cases the failure falls into and then to diagnose the actual problem. The speed at which the engineer can do so depends on the test’s
clarity
. A clear test is one whose purpose for existing and reason for failing is immediately clear to the engineer diagnosing a failure. Tests fail to achieve clarity when their reasons for failure aren’t obvious or when it’s difficult to figure out why they were originally written. Clear tests also bring other benefits, such as documenting the system under test and more easily serving as a basis for new tests.

Test clarity becomes significant over time. Tests will often outlast the engineers who wrote them, and the requirements and understanding of a system will shift subtly as it ages. It’s entirely possible that a failing test might have been written years ago by an engineer no longer on the team, leaving no way to figure out its purpose or how to fix it. This stands in contrast with unclear production code, whose purpose you can usually determine with enough effort by looking at what calls it and what breaks when it’s removed. With an unclear test, you might never understand its purpose, since removing the test will have no effect other than (potentially) introducing a subtle hole in test coverage.

In the worst case, these obscure tests just end up getting deleted when engineers can’t figure out how to fix them. Not only does removing such tests introduce a hole in test coverage, but it also indicates that the test has been providing zero value for perhaps the entire period it has existed (which could have been years).

For a test suite to scale and be useful over time, it’s important that each individual test in that suite be as clear as possible. This section explores techniques and ways of thinking about tests to achieve clarity.

Make Your Tests Complete and Concise

Two high-level properties that

help tests achieve

clarity are
completeness and conciseness
. A

test is
complete
 when its body contains all of the information a reader needs in order to understand how it arrives at its result. A test is
concise
 when it contains no other distracting or irrelevant information.
An incomplete and cluttered test
 shows a test that is neither complete nor concise:

Example 12-6.
An incomplete and cluttered test

@Test
public void shouldPerformAddition() {
  Calculator calculator = new Calculator(new RoundingStrategy(),
      "unused", ENABLE_COSINE_FEATURE, 0.01, calculusEngine, false);
  int result = calculator.calculate(newTestCalculation());
  assertThat(result).isEqualTo(5); // Where did this number come from?
}

The test is passing a lot of irrelevant information into the constructor, and the actual important parts of the test are hidden inside of a helper method. The test can be made more complete by clarifying the inputs of the helper method, and more concise by using another helper to hide the irrelevant details of constructing the calculator, as illustrated in
A complete, concise test
.

Example 12-7.
A complete, concise test

@Test
public void shouldPerformAddition() {
  Calculator calculator = newCalculator();
  int result = calculator.calculate(newCalculation(2, Operation.PLUS, 3));
  assertThat(result).isEqualTo(5);
}

Ideas we discuss later, especially around code sharing, will tie back to completeness and conciseness.

 In particular, it can often be worth violating the DRY (Don’t Repeat Yourself) principle if it leads to clearer tests. Remember: a
test’s body should contain all of the information needed to understand it without containing any irrelevant or distracting information
.
```

<a id="software-engineering-at-google-ch12-004"></a>
## software-engineering-at-google-ch12-004 — Behavior-focused tests and natural-language readability

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 379–467.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Test Behaviors, Not Methods

The first instinct of many engineers is to try to match the structure of their tests to the structure of their code such that every production method has a corresponding test method.

  This pattern can be convenient at first, but over time it leads to problems: as the method being tested grows more complex, its test also grows in complexity and becomes more difficult to reason about. For example, consider the snippet of code in
A transaction snippet
, which displays the results of a transaction.

Example 12-8.
A transaction snippet

public void displayTransactionResults(User user, Transaction transaction) {
  ui.showMessage("You bought a " + transaction.getItemName());
  if (user.getBalance() < LOW_BALANCE_THRESHOLD) {
    ui.showMessage("Warning: your balance is low!");
  }
}

It wouldn’t be uncommon to find a test covering both of the messages that might be shown by the

method, as

presented in
A method-driven test
.

Example 12-9.
A method-driven test

@Test
public void testDisplayTransactionResults() {
  transactionProcessor.displayTransactionResults(
      newUserWithBalance(
          LOW_BALANCE_THRESHOLD.plus(dollars(2))),
      new Transaction("Some Item", dollars(3)));

  assertThat(ui.getText()).contains("You bought a Some Item");
  assertThat(ui.getText()).contains("your balance is low");
}

With such tests, it’s likely that the test started out covering only the first method. Later, an engineer expanded the test when the second message was added (violating the idea of unchanging tests that we discussed earlier). This modification sets a bad precedent: as the method under test becomes more complex and implements more functionality, its unit test will become increasingly convoluted and grow more and more difficult to work with.

The problem is that framing tests around methods can naturally encourage unclear tests because a single method often does a few different things under the hood and might have several tricky edge and corner cases.

There’s a better way: rather than writing a test for each method, write a test for each
behavior.
4
 A behavior is any guarantee that a system makes about how it will respond to a series of inputs while in a particular state.
5
 Behaviors can often be expressed using the words
"given," "when," and "then"
: “
Given
 that a bank

account is empty,
when
 attempting to withdraw money from it,
then
 the transaction is rejected." The mapping between methods and behaviors is many-to-many: most nontrivial methods implement multiple behaviors, and some behaviors rely on the interaction of multiple methods. The previous example can be rewritten using behavior-driven tests, as presented in
A behavior-driven test
.

Example 12-10.
A behavior-driven test

@Test
public void displayTransactionResults_showsItemName() {
  transactionProcessor.displayTransactionResults(
      new User(), new Transaction("Some Item"));
  assertThat(ui.getText()).contains("You bought a Some Item");
}

@Test
public void displayTransactionResults_showsLowBalanceWarning() {
  transactionProcessor.displayTransactionResults(
      newUserWithBalance(
          LOW_BALANCE_THRESHOLD.plus(dollars(2))),
      new Transaction("Some Item", dollars(3)));
  assertThat(ui.getText()).contains("your balance is low");
}

The extra boilerplate required to split apart the single test is
more than worth it
, and the resulting tests are much clearer than the original test. Behavior-driven tests tend to be clearer than method-oriented tests for several
reasons.
 First, they read more like natural language, allowing them to be naturally understood rather than requiring laborious mental parsing. Second, they more clearly express
cause and effect
 because each test is more limited in scope. Finally, the fact that each test is short and descriptive makes it easier to see what functionality is already tested and encourages engineers to add new streamlined test methods instead of piling onto existing methods.
```

<a id="software-engineering-at-google-ch12-005"></a>
## software-engineering-at-google-ch12-005 — Given/when/then comments, omission in trivial tests, and complex examples

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 469–548.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Structure tests to emphasize behaviors

Thinking about tests as being coupled to behaviors instead of methods significantly affects how they should be structured.

 Remember that every behavior has three parts: a "given" component that defines how the system is set up, a "when" component that defines the action to be taken on the system, and a "then" component that validates the result.
6
 Tests are clearest when this structure is explicit.

 Some frameworks like
Cucumber
 and
Spock
 directly bake in given/when/then. Other languages can use whitespace and optional comments to make the structure stand out, such as that shown in
A well-structured test
.

Example 12-11.
A well-structured test

@Test
public void transferFundsShouldMoveMoneyBetweenAccounts() {
  // Given two accounts with initial balances of $150 and $20
  Account account1 = newAccountWithBalance(usd(150));
  Account account2 = newAccountWithBalance(usd(20));

  // When transferring $100 from the first to the second account
  bank.transferFunds(account1, account2, usd(100));

  // Then the new account balances should reflect the transfer
  assertThat(account1.getBalance()).isEqualTo(usd(50));
  assertThat(account2.getBalance()).isEqualTo(usd(120));
}

This level of description isn’t always necessary in trivial tests, and it’s usually sufficient to omit the comments and rely on whitespace to make the sections clear. However, explicit comments can make more sophisticated tests easier to understand. This pattern makes it possible to read tests at three levels of granularity:

A reader can start by looking at the test method name (discussed below) to get a rough description of the behavior being tested.

If that’s not enough, the reader can look at the given/when/then comments for a formal description of the behavior.

Finally, a reader can look at the actual code to see precisely how that behavior is expressed.

This pattern is

most commonly violated by interspersing assertions among multiple calls to the system under test (i.e., combining the "when" and "then" blocks). Merging the "then" and "when" blocks in this way can make the test less clear because it makes it difficult to distinguish the action being performed from the expected result.

When a test does want to validate each step in a multistep process, it’s acceptable to define alternating sequences of when/then blocks. Long blocks can also be made more descriptive by splitting them up with the word "and."
Alternating when/then blocks within a test
 shows what a relatively complex, behavior-driven test might look like.

Example 12-12.
Alternating when/then blocks within a test

@Test
public void shouldTimeOutConnections() {
  // Given two users
  User user1 = newUser();
  User user2 = newUser();

  // And an empty connection pool with a 10-minute timeout
  Pool pool = newPool(Duration.minutes(10));

  // When connecting both users to the pool
  pool.connect(user1);
  pool.connect(user2);

  // Then the pool should have two connections
  assertThat(pool.getConnections()).hasSize(2);

  // When waiting for 20 minutes
  clock.advance(Duration.minutes(20));

  // Then the pool should have no connections
  assertThat(pool.getConnections()).isEmpty();

  // And each user should be disconnected
  assertThat(user1.isConnected()).isFalse();
  assertThat(user2.isConnected()).isFalse();
}

When writing such tests, be careful to ensure that you’re not inadvertently testing multiple behaviors at the same time. Each test should cover only a single behavior, and the vast majority of unit tests require only one "when" and one "then" block.
```

<a id="software-engineering-at-google-ch12-006"></a>
## software-engineering-at-google-ch12-006 — Test names communicating behavior and intent

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 550–613.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Name tests after the behavior being tested

Method-oriented

 tests are usually named

after the method being tested (e.g., a test for the
updateBalance
 method is usually called
testUpdateBalance
). With more focused behavior-driven tests, we have a lot more flexibility and the chance to convey useful information in the test’s name. The test name is very important: it will often be the first or only token visible in failure reports, so it’s your best opportunity to communicate the problem when the test breaks. It’s also the most straightforward way to express the intent of the test.

A test’s name should summarize the behavior it is testing. A good name describes both the actions that are being taken on a system
and the expected outcome
. Test names will sometimes include additional information like the state of the system or its environment before taking action on it. Some languages and frameworks make this easier than others by allowing tests to be nested within one another and named using strings, such as in
Some sample nested naming patterns
, which uses
Jasmine
.

Example 12-13.
Some sample nested naming patterns

describe("multiplication", function() {
  describe("with a positive number", function() {
    var positiveNumber = 10;
    it("is positive with another positive number", function() {
      expect(positiveNumber * 10).toBeGreaterThan(0);
    });
    it("is negative with a negative number", function() {
      expect(positiveNumber * -10).toBeLessThan(0);
    });
  });
  describe("with a negative number", function() {
    var negativeNumber = 10;
    it("is negative with a positive number", function() {
      expect(negativeNumber * 10).toBeLessThan(0);
    });
    it("is positive with another negative number", function() {
      expect(negativeNumber * -10).toBeGreaterThan(0);
    });
  });
});

Other languages

require us to encode all of this information in a method name, leading to method naming patterns like that shown in
Some sample method naming patterns
.

Example 12-14.
Some sample method naming patterns

multiplyingTwoPositiveNumbersShouldReturnAPositiveNumber
multiply_positiveAndNegative_returnsNegative
divide_byZero_throwsException

Names like this are much more verbose than we’d normally want to write for methods in production code, but the use case is different: we never need to write code that calls these, and their names frequently need to be read by humans in reports. Hence, the extra verbosity is warranted.

Many different naming strategies are acceptable so long as they’re used consistently within a single test class. A good trick if you’re stuck is to try starting the test name with the word "should." When taken with the name of the class being tested, this naming scheme allows the test name to be read as a sentence. For example, a test of a
BankAccount
 class named
shouldNotAllowWithdrawalsWhenBalanceIsEmpty
 can be read as "BankAccount should not allow withdrawals when balance is empty." By reading the names of all the test methods in a suite, you should get a good sense of the behaviors implemented by the system under test. Such names also help ensure that the test stays focused on a single behavior: if you need to use the word "and" in a test name, there’s a good chance that you’re actually testing multiple behaviors and should be writing multiple tests!
```

<a id="software-engineering-at-google-ch12-007"></a>
## software-engineering-at-google-ch12-007 — Simple tests and the commented URL example

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 615–663.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Don’t Put Logic in Tests

Clear tests are trivially correct upon inspection; that is, it is obvious that a test is doing the correct thing just from glancing at it.

 This is possible in test code because each test needs to handle only a particular set of inputs, whereas production code must be generalized to handle any input.

For production code, we’re able to write tests that ensure complex logic is correct. But test code doesn’t have that luxury—if you feel like you need to write a test to verify your test, something has gone wrong!

Complexity is most often introduced in the form of
logic
. Logic is defined via the imperative parts of programming languages such as operators, loops, and conditionals.

 When a piece of code contains logic, you need to do a bit of mental computation to determine its result instead of just reading it off of the screen.

 It doesn’t take much logic to make a test more difficult to reason about. For example, does the test in
Logic concealing a bug

look correct to you
?

Example 12-15.
Logic concealing a bug

@Test
public void shouldNavigateToAlbumsPage() {
  String baseUrl = "http://photos.google.com/";
  Navigator nav = new Navigator(baseUrl);
  nav.goToAlbumPage();
  assertThat(nav.getCurrentUrl()).isEqualTo(baseUrl + "/albums");
}

There’s not much logic here: really just one string concatenation. But if we simplify the test by removing that one bit of logic, a bug immediately becomes clear, as demonstrated in
A test without logic reveals the bug
.

Example 12-16.
A test without logic reveals the bug

@Test
public void shouldNavigateToPhotosPage() {
  Navigator nav = new Navigator("http://photos.google.com/");
  nav.goToPhotosPage();
  assertThat(nav.getCurrentUrl()))
      .isEqualTo("http://photos.google.com//albums"); // Oops!
}

When the whole string is written out, we can see right away that we’re expecting two slashes in the URL instead of just one. If the production code made a similar mistake, this test would fail to detect a bug. Duplicating the base URL was a small price to pay for making the test more descriptive and meaningful (see the discussion of DAMP versus DRY tests later in this chapter).

If humans are bad at spotting bugs from string concatenation, we’re even worse at spotting bugs that come from more sophisticated programming constructs like loops and conditionals. The lesson is clear: in test code, stick to straight-line code over clever logic, and consider tolerating some duplication when it makes the test more descriptive and meaningful. We’ll discuss ideas around duplication and code sharing later in this chapter.
```

<a id="software-engineering-at-google-ch12-008"></a>
## software-engineering-at-google-ch12-008 — Failure messages as explanations

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 665–717.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Write Clear Failure Messages

One last aspect of clarity has to do not with how a test is written, but with what an engineer sees when it fails.

In an ideal world, an engineer could diagnose a problem just from reading its failure message in a log or report without ever having to look at the test itself. A good failure message contains much the same information as the test’s name: it should clearly express the desired outcome, the actual outcome, and any relevant parameters.

Here’s an example of a bad failure message:

Test failed: account is closed

Did the test fail because the account was closed, or was the account expected to be closed and the test failed because it wasn’t? A better failure message clearly distinguishes the expected from the actual state and gives more context about the result:

Expected an account in state CLOSED, but got account:
    <{name: "my-account", state: "OPEN"}

Good libraries can help make it easier to write useful failure messages.

 Consider the assertions in
An assertion using the Truth library
 in a Java test, the first of which

uses classical JUnit asserts, and the second of which uses
Truth
, an assertion library developed by Google:

Example 12-17.
An assertion using the Truth library

Set<String> colors = ImmutableSet.of("red", "green", "blue");
assertTrue(colors.contains("orange"));  // JUnit
assertThat(colors).contains("orange");  // Truth

Because the first assertion only receives a Boolean value, it is only able to give a generic error message like "expected <true> but was <false>," which isn’t very informative in a failing test output. Because the second assertion explicitly receives the subject of the assertion, it is able to give
a much more useful error message
:
"AssertionError:
 <[red, green, blue]> should have contained <orange>."

Not all

 languages have

 such helpers available, but it should always be possible to manually specify the important information in the failure message. For example, test assertions in Go conventionally look like
A test assertion in Go
.

Example 12-18.
A test assertion in Go

result := Add(2, 3)
if result != 5 {
  t.Errorf("Add(2, 3) = %v, want %v", result, 5)
}
```

<a id="software-engineering-at-google-ch12-009"></a>
## software-engineering-at-google-ch12-009 — DAMP, DRY, and local understanding

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 719–834.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Tests and Code Sharing: DAMP, Not DRY

One final

 aspect of

writing clear tests and avoiding brittleness has to do with code sharing.

Most software attempts to achieve a principle called DRY—"Don’t Repeat Yourself." DRY states

that software is easier to maintain if every concept is canonically represented in one place and code duplication is kept to a minimum. This approach is especially valuable in making changes easier because an engineer needs to update only one piece of code rather than tracking down multiple references. The downside to such consolidation is that it can make code unclear, requiring readers to follow chains of references to understand what the code is doing.

In normal production code, that downside is usually a small price to pay for making code easier to change and work with. But this cost/benefit analysis plays out a little differently in the context of test code. Good tests are designed to be stable, and in fact you usually
want
 them to break when the system being tested changes. So DRY doesn’t have quite as much benefit when it comes to test code. At the same time, the costs of complexity are greater for tests: production code has the benefit of a test suite to ensure that it keeps working as it becomes complex, whereas tests must stand by themselves, risking bugs if they aren’t self-evidently correct. As mentioned earlier, something has gone wrong if tests start becoming complex enough that it feels like they need their own tests to ensure that they’re working properly.

Instead of

 being completely DRY, test code should

often strive to be
DAMP
—that is, to promote "Descriptive And Meaningful Phrases." A little bit of duplication is OK in tests so long as that duplication makes the test simpler and clearer.

 To illustrate,
A test that is too DRY
 presents some tests that are far too DRY.

Example 12-19.
A test that is too DRY

@Test
public void shouldAllowMultipleUsers() {
  List<User> users = createUsers(false, false);
  Forum forum = createForumAndRegisterUsers(users);
  validateForumAndUsers(forum, users);
}

@Test
public void shouldNotAllowBannedUsers() {
  List<User> users = createUsers(true);
  Forum forum = createForumAndRegisterUsers(users);
  validateForumAndUsers(forum, users);
}

// Lots more tests...

private static List<User> createUsers(boolean... banned) {
  List<User> users = new ArrayList<>();
  for (boolean isBanned : banned) {
    users.add(newUser()
        .setState(isBanned ? State.BANNED : State.NORMAL)
        .build());
  }
  return users;
}

private static Forum createForumAndRegisterUsers(List<User> users) {
  Forum forum = new Forum();
  for (User user : users) {
    try {
      forum.register(user);
    } catch(BannedUserException ignored) {}
  }
  return forum;
}

private static void validateForumAndUsers(Forum forum, List<User> users) {
  assertThat(forum.isReachable()).isTrue();
  for (User user : users) {
    assertThat(forum.hasRegisteredUser(user))
        .isEqualTo(user.getState() == State.BANNED);
  }
}

The problems

 in this code should be apparent based on the previous discussion of clarity. For one, although the test bodies are very concise, they are not complete: important details are hidden away in helper methods that the reader can’t see without having to scroll to a completely different part of the file.

Those helpers are also full of logic that makes them more difficult to verify at a glance (did you spot the bug?). The test becomes much clearer when it’s rewritten to use DAMP, as shown in
Tests should be DAMP
.

Example 12-20.
Tests should be DAMP

@Test
public void shouldAllowMultipleUsers() {
  User user1 = newUser().setState(State.NORMAL).build();
  User user2 = newUser().setState(State.NORMAL).build();

  Forum forum = new Forum();
  forum.register(user1);
  forum.register(user2);

  assertThat(forum.hasRegisteredUser(user1)).isTrue();
  assertThat(forum.hasRegisteredUser(user2)).isTrue();
}

@Test
public void shouldNotRegisterBannedUsers() {
  User user = newUser().setState(State.BANNED).build();

  Forum forum = new Forum();
  try {
    forum.register(user);
  } catch(BannedUserException ignored) {}

  assertThat(forum.hasRegisteredUser(user)).isFalse();
}

These tests have more duplication, and the test bodies are a bit longer, but the extra verbosity is worth it. Each individual test is far more meaningful and can be understood entirely without leaving the test body. A reader of these tests can feel confident that the tests do what they claim to do and aren’t hiding any bugs.

DAMP is not a replacement for DRY; it is complementary to it.

Helper methods and test infrastructure can still help make tests clearer by making them more concise, factoring out repetitive steps whose details aren’t relevant to the particular behavior being tested. The important point is that such refactoring should be done with an eye toward making tests more descriptive and meaningful, and not solely in the name of reducing repetition. The rest of this section will explore common patterns for sharing code across tests.
```

<a id="software-engineering-at-google-ch12-010"></a>
## software-engineering-at-google-ch12-010 — Descriptive names, shared values, and commented helpers

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 836–935.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Shared Values

Many tests are structured

 by defining a set of shared

values to be used by tests and then by defining the tests that cover various cases for how these values interact.
Shared values with ambiguous names
 illustrates what such tests look like.

Example 12-21.
Shared values with ambiguous names

private static final Account ACCOUNT_1 = Account.newBuilder()
    .setState(AccountState.OPEN).setBalance(50).build();

private static final Account ACCOUNT_2 = Account.newBuilder()
    .setState(AccountState.CLOSED).setBalance(0).build();

private static final Item ITEM = Item.newBuilder()
    .setName("Cheeseburger").setPrice(100).build();

// Hundreds of lines of other tests...

@Test
public void canBuyItem_returnsFalseForClosedAccounts() {
  assertThat(store.canBuyItem(ITEM, ACCOUNT_1)).isFalse();
}

@Test
public void canBuyItem_returnsFalseWhenBalanceInsufficient() {
  assertThat(store.canBuyItem(ITEM, ACCOUNT_2)).isFalse();
}

This strategy can make tests very concise, but it causes problems as the test suite grows. For one, it can be difficult to understand why a particular value was chosen for a test. In
Shared values with ambiguous names
, the test names fortunately clarify which scenarios are being tested, but you still need to scroll up to the definitions to confirm that
ACCOUNT_1
 and
ACCOUNT_2
 are appropriate for those scenarios. More descriptive constant names (e.g.,
CLOSED_ACCOUNT
 and
ACCOUNT_WITH_LOW_BALANCE
) help a bit, but they still make it more difficult to see the exact details of the value being tested, and the ease of reusing these values can encourage engineers to do so even when the name doesn’t exactly describe what the test needs.

Engineers are usually drawn to using shared constants because constructing individual values in each test can be verbose.

A better way to accomplish this goal is to construct data
using helper methods
 (see
Shared values using helper methods
) that require the test author to specify only values they care about, and setting reasonable defaults
7
 for all other values. This construction is trivial to do in languages that support named parameters, but languages without named parameters

 can use constructs such as the
Builder
 pattern to emulate them (often with the assistance of tools such as
AutoValue
):

Example 12-22.
Shared values using helper methods

# A helper method wraps a constructor by defining arbitrary defaults for
# each of its parameters.
def newContact(
    firstName="Grace", lastName="Hopper", phoneNumber="555-123-4567"):
  return Contact(firstName, lastName, phoneNumber)

# Tests call the helper, specifying values for only the parameters that they
# care about.
def test_fullNameShouldCombineFirstAndLastNames(self):
  def contact = newContact(firstName="Ada", lastName="Lovelace")
  self.assertEqual(contact.fullName(), "Ada Lovelace")

// Languages like Java that don’t support named parameters can emulate them
// by returning a mutable "builder" object that represents the value under
// construction.
private static Contact.Builder newContact() {
  return Contact.newBuilder()
    .setFirstName("Grace")
    .setLastName("Hopper")
    .setPhoneNumber("555-123-4567");
}

// Tests then call methods on the builder to overwrite only the parameters
// that they care about, then call build() to get a real value out of the
// builder.
@Test
public void fullNameShouldCombineFirstAndLastNames() {
  Contact contact = newContact()
      .setFirstName("Ada")
      .setLastName("Lovelace")
      .build();
  assertThat(contact.getFullName()).isEqualTo("Ada Lovelace");
}

Using helper methods to construct these values allows each test to create the exact values it needs without having to worry about specifying irrelevant information or conflicting with other tests.
```

<a id="software-engineering-at-google-ch12-011"></a>
## software-engineering-at-google-ch12-011 — Shared setup, helper methods, and test intent

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 937–1028.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Shared Setup

A related way tha

t tests shared code is via setup/initialization logic.

Many test frameworks allow engineers to define methods to execute before each test in a suite is run. Used appropriately, these methods can make tests clearer and more concise by obviating the repetition of tedious and irrelevant initialization logic. Used inappropriately, these methods can harm a test’s completeness by hiding important details in a separate initialization method.

The best use case for setup methods is to construct the object under tests and its collaborators. This is useful when the majority of tests don’t care about the specific arguments used to construct those objects and can let them stay in their default states. The same idea also applies to stubbing return values for test doubles, which is a concept that we explore in more detail in
Test Doubles
.

One risk in using setup methods is that

they can lead to unclear tests if those tests begin to depend on the particular values used in setup. For example, the test in
Dependencies on values in setup methods
 seems incomplete because a reader of the test needs to go hunting to discover where the string "Donald Knuth" came from.

Example 12-23.
Dependencies on values in setup methods

private NameService nameService;
private UserStore userStore;

@Before
public void setUp() {
  nameService = new NameService();
  nameService.set("user1", "Donald Knuth");
  userStore = new UserStore(nameService);
}

// [... hundreds of lines of tests ...]

@Test
public void shouldReturnNameFromService() {
  UserDetails user = userStore.get("user1");
  assertThat(user.getName()).isEqualTo("Donald Knuth");
}

Tests like these that explicitly care about particular values should state those values directly, overriding the default defined in the setup method if need be. The resulting test contains slightly more repetition, as shown in
Overriding values in setup methods
, but the result is far more descriptive and meaningful.

Example 12-24.
Overriding values in setup methods

private NameService nameService;
private UserStore userStore;

@Before
public void setUp() {
  nameService = new NameService();
  nameService.set("user1", "Donald Knuth");
  userStore = new UserStore(nameService);
}

@Test
public void shouldReturnNameFromService() {
  nameService.set("user1", "Margaret Hamilton");
  UserDetails user = userStore.get("user1");
  assertThat(user.getName()).isEqualTo("Margaret Hamilton");
}

Shared Helpers and Validation

The last common way that code is shared across tests is via "helper methods" called from the body of the test methods.

 We already discussed how helper methods can be a useful way for concisely constructing test values—this usage is warranted, but other types of helper methods can be dangerous.

One common type of helper is a method that performs a common set of assertions against a system under test.

 The extreme example is a
validate
 method called at the end of every test method, which performs a set of fixed checks against the system under test. Such a validation strategy can be a bad habit to get into because tests using this approach are less behavior driven. With such tests, it is much more difficult to determine the intent of any particular test and to infer what exact case the author had in mind when writing it. When bugs are introduced, this strategy can also make them more difficult to localize because they will frequently cause a large number of tests to start failing.

More focused validation methods can still be useful, however. The best validation helper methods assert a
single conceptual fact
 about their inputs, in contrast to general-purpose validation methods that cover a range of conditions. Such methods can be particularly helpful when the condition that they are validating is conceptually simple but requires looping or conditional logic to implement that would reduce clarity were it included in the body of a test method. For example, the helper method in
A conceptually simple test
 might be useful in a test covering several different cases around account access.

Example 12-25.
A conceptually simple test

private void assertUserHasAccessToAccount(User user, Account account) {
  for (long userId : account.getUsersWithAccess()) {
    if (user.getId() == userId) {
      return;
    }
  }
  fail(user.getName() + " cannot access " + account.getName());
}
```

<a id="software-engineering-at-google-ch12-012"></a>
## software-engineering-at-google-ch12-012 — Concluding clarity positions

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 1050–1079.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Conclusion

Unit tests are one of the most powerful tools that we as software engineers have to make sure that our systems keep working over time in the face of unanticipated changes. But with great power comes great responsibility, and careless use of unit testing can result in a system that requires much more effort to maintain and takes much more effort to change without actually improving our confidence in said
system.

Unit tests at Google are far from perfect, but we’ve found tests that follow the practices outlined in this chapter to be orders of magnitude more valuable than those that don’t. We hope they’ll help you to improve the quality of your own tests!

TL;DRs

Strive for unchanging tests.

Test via public APIs.

Test state, not interactions.

Make your tests complete and concise.

Test behaviors, not methods.

Structure tests to emphasize behaviors.

Name tests after the behavior being tested.

Don’t put logic in tests.

Write clear failure messages.

Follow DAMP over DRY when sharing

 code for tests.
```

<a id="software-engineering-at-google-ch12-013"></a>
## software-engineering-at-google-ch12-013 — Public-interface, behavior, structure, and helper footnotes

Source: [ch12.html](../../../../books/software-engineering-at-google/ch12.html); reading unit `ch12`, lines 1085–1104.

Attribution: Erik Kuefler

Context: Unit-testing explanation and comment context; paired examples and qualifications are retained.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
2
This is sometimes called the "
Use the front door first principle
."
3
These are also the same two reasons that a test can be "flaky." Either the system under test has a nondeterministic fault, or the test is flawed such that it sometimes fails when it should pass.
4
See
https://testing.googleblog.com/2014/04/testing-on-toilet-test-behaviors-not.html
 and
https://dannorth.net/introducing-bdd
.
5
Furthermore, a
feature
 (in the product sense of the word) can be expressed as a collection of behaviors.
6
These components are sometimes referred to as "arrange," "act," and "assert."
7
In many cases, it can even be useful to slightly randomize the default values returned for fields that aren’t explicitly set. This helps to ensure that two different instances won’t accidentally compare as equal, and makes it more difficult for engineers to hardcode dependencies on the defaults.
```

<a id="software-engineering-at-google-ch13-001"></a>
## software-engineering-at-google-ch13-001 — Mocking-framework explanation and comment specimens

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 197–264.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Mocking Frameworks

A
mocking framework
 is a

software

library that makes it easier to create test doubles within tests; it allows you to replace an object with a
mock
, which is a test double whose behavior is specified inline in a test. The use of mocking frameworks reduces boilerplate because you don’t need to define a new class each time you need a test
double.

Mocking frameworks
 demonstrates the

use of
Mockito
, a mocking framework for Java. Mockito creates a test double for
CreditCardService
 and instructs it to return a specific value.

Example 13-6.
Mocking frameworks

class PaymentProcessorTest {
  ...
  PaymentProcessor paymentProcessor;

  // Create a test double of CreditCardService with just one line of code.

@Mock CreditCardService mockCreditCardService
;
  @Before public void setUp() {
    // Pass in the test double to the system under test.
    paymentProcessor = new PaymentProcessor(
mockCreditCardService
);
  }
  @Test public void chargeCreditCardFails_returnFalse() {
    // Give some behavior to the test double: it will return false
    // anytime the chargeCreditCard() method is called. The usage of
    // “any()” for the method’s arguments tells the test double to
    // return false regardless of which arguments are passed.
    when(
mockCreditCardService.chargeCreditCard(
any(), any())
       .thenReturn(
false
);
    boolean success = paymentProcessor.makePayment(CREDIT_CARD, AMOUNT);
    assertThat(success).isFalse();
  }
}

Mocking frameworks

 exist for most

major programming languages.

 At Google, we use Mockito for Java,
the googlemock component of Googletest
 for C++, and
unittest.mock
 for Python.

Although mocking frameworks facilitate easier usage of test doubles, they come with some significant caveats given that their overuse will often make a codebase more difficult to maintain. We cover some of these problems later in this chapter.
```

<a id="software-engineering-at-google-ch13-002"></a>
## software-engineering-at-google-ch13-002 — Faking, stubbing, and interaction-test comment specimens

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 274–391.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Faking

A
fake
 is a lightweight implementation of an API that behaves similar

to the real implementation but isn’t suitable

for production; for example, an in-memory database.
A simple fake
 presents an example of faking.

Example 13-7.
A simple fake

// Creating the fake is fast and easy.
AuthorizationService
fakeAuthorizationService
 =
    new FakeAuthorizationService();
AccessManager accessManager = new AccessManager(
fakeAuthorizationService
):

// Unknown user IDs shouldn’t have access.
assertFalse(accessManager.userHasAccess(USER_ID));

// The user ID should have access after it is added to
// the authorization service.

fakeAuthorizationService
.addAuthorizedUser(new User(USER_ID));
assertThat(accessManager.userHasAccess(USER_ID)).isTrue();

Using a fake is often the ideal technique when you need to use a test double, but a fake might not exist for an object you need to use in a test, and writing one can be challenging because you need to ensure that it has similar behavior to the real implementation, now and in the future.

Stubbing

Stubbing
 is the process of giving behavior to a function that otherwise has no behavior on its own—you specify to the function exactly what values to return (that is, you
stub
 the return values).

Stubbing
 illustrates stubbing.

The
when(...).thenReturn(...)
 method calls from the Mockito mocking framework specify the behavior of the
lookupUser()
 method.

Example 13-8.
Stubbing

// Pass in a test double that was created by a mocking framework.
AccessManager accessManager = new AccessManager(
mockAuthorizationService
):

// The user ID shouldn’t have access if null is returned.
when(
mockAuthorizationService
.lookupUser(USER_ID)).thenReturn(null);
assertThat(accessManager.userHasAccess(USER_ID)).isFalse();

// The user ID should have access if a non-null value is returned.
when(
mockAuthorizationService
.lookupUser(USER_ID)).thenReturn(USER);
assertThat(accessManager.userHasAccess(USER_ID)).isTrue();

Stubbing is typically done

through mocking frameworks to reduce boilerplate that would otherwise be needed for manually creating new classes that hardcode return values.

Although stubbing can be a quick and simple technique to apply, it has limitations, which we’ll discuss later in this chapter.

Interaction Testing

Interaction testing
 is a way to validate
how
 a function is called without actually calling the implementation of the function.

A test should fail if a function isn’t called the correct way—for example, if the function isn’t called at all, it’s called too many times, or it’s called with the wrong arguments.

Interaction testing
 presents an instance of interaction testing. The
verify(...)
 method from the Mockito mocking framework is used to validate that
lookupUser()
 is called as expected.

Example 13-9.
Interaction testing

// Pass in a test double that was created by a mocking framework.
AccessManager accessManager = new AccessManager(
mockAuthorizationService
);
accessManager.userHasAccess(USER_ID);

// The test will fail if accessManager.userHasAccess(USER_ID) didn’t call
// mockAuthorizationService.lookupUser(USER_ID).
verify(
mockAuthorizationService
).lookupUser(USER_ID);

Similar to stubbing, interaction testing is typically done through mocking frameworks.

 This reduces boilerplate compared to manually creating new classes that contain code to keep track of how often a function is called and which arguments were passed in.

Interaction testing is sometimes called
mocking
. We avoid this terminology in this chapter because it can be confused with mocking frameworks, which can be used for stubbing as well as for interaction testing.

As discussed later in this chapter, interaction testing is useful in certain situations but should be avoided when possible because overuse can easily result in brittle tests.
```

<a id="software-engineering-at-google-ch13-003"></a>
## software-engineering-at-google-ch13-003 — DoNotMock annotation communicates API-owner intent

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 439–469.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Case Study: @DoNotMock

At Google, we’ve seen enough tests that over-rely on mocking frameworks to motivate

 the creation of the
@DoNotMock
 annotation in Java, which is available as part of the
ErrorProne
 static analysis tool.

 This annotation is a way for

API owners to declare, "this type should not be mocked because better alternatives exist.”

If an engineer attempts to use a mocking framework to create an instance of a class or interface that has been annotated as
@DoNotMock
, as demonstrated in
The @DoNotMock annotation
, they will see an error directing them to use a more suitable test strategy, such as a real implementation or a fake. This annotation is most commonly used for value objects that are simple enough to use as-is, as well as for APIs that have well-engineered fakes available.

Example 13-10.
The @DoNotMock annotation

@DoNotMock("Use SimpleQuery.create() instead of mocking.")
public abstract class Query {
  public abstract String getQueryValue();
}

Why would an API owner care? In short, it severely constrains the API owner’s ability to make changes to their implementation over time. As we’ll explore later in the chapter, every time a mocking framework is used for stubbing or interaction testing, it duplicates behavior provided by the API.

When the API owner wants to change their API, they might find that it has been mocked thousands or even tens of thousands of times throughout Google’s codebase! These test doubles are very likely to exhibit behavior that violates the API contract of the type being mocked—for instance, returning null for a method that can never return null. Had the tests used the real implementation or a fake, the API owner could make changes to their implementation without first fixing thousands of flawed tests.
```

<a id="software-engineering-at-google-ch13-004"></a>
## software-engineering-at-google-ch13-004 — Commented fake-filesystem implementation

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 564–608.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Faking

If using a real implementation is not feasible within a test, the best option is often to use a fake in its place.

A fake is preferred over other test double techniques because it behaves similarly to the real implementation: the system under test shouldn’t even be able to tell whether it is interacting with a real implementation or a fake.
A fake file system
 illustrates a fake file system.

Example 13-11.
A fake file system

// This fake implements the FileSystem interface. This interface is also
// used by the real implementation.
public class
FakeFileSystem
 implements
FileSystem
 {
  // Stores a map of file name to file contents. The files are stored in
  // memory instead of on disk since tests shouldn’t need to do disk I/O.
  private Map<String, String>
files
 = new HashMap<>();
  @Override
  public void
writeFile
(String fileName, String contents) {
    // Add the file name and contents to the map.

files
.add(fileName, contents);
  }
  @Override
  public String
readFile
(String fileName) {
    String contents =
files
.get(fileName);
    // The real implementation will throw this exception if the
    // file isn’t found, so the fake must throw it too.
    if (contents == null) { throw new FileNotFoundException(fileName); }
    return contents;
  }
}
```

<a id="software-engineering-at-google-ch13-008"></a>
## software-engineering-at-google-ch13-008 — API contracts represented by fakes and contract tests

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 634–670.

Attribution: Andrew Trenk and Dillon Bly

Context: Adjacent discussion of executable representations of promised behavior, fidelity limits, unsupported paths, and tests for divergence; no claim that these are inline comments.

```text
The Fidelity of Fakes

Perhaps the most important concept surrounding

 the creation of fakes is
fidelity
; in other words, how

closely the behavior of a fake matches the behavior of the real implementation. If the behavior of a fake doesn’t match the behavior of the real implementation, a test using that fake is not useful—a test might pass when the fake is used, but this same code path might not work properly in the real implementation.

Perfect fidelity is not always feasible. After all, the fake was necessary because the real implementation wasn’t suitable in one way or another. For example, a fake database would usually not have fidelity to a real database in terms of hard drive storage because the fake would store everything in memory.

Primarily, however, a fake should maintain fidelity to the API contracts of the real implementation. For any given input to an API, a fake should return the same output and perform the same state changes of its corresponding real implementation. For example, for a real implementation of
database.save(itemId)
, if an item is successfully saved when its ID does not yet exist but an error is produced when the ID already exists, the fake must conform to this same behavior.

One way to think about this is that the fake must have perfect fidelity to the real implementation, but
only from the perspective of the test
. For example, a fake for a hashing API doesn’t need to guarantee that the hash value for a given input is exactly the same as the hash value that is generated by the real implementation—tests likely don’t care about the specific hash value, only that the hash value is unique for a given input. If the contract of the hashing API doesn’t make guarantees of what specific hash values will be returned, the fake is still conforming to the contract even if it doesn’t have perfect fidelity to the real implementation.

Other examples where perfect fidelity typically might not be useful for fakes include latency and resource consumption. However, a fake cannot be used if you need to explicitly test for these constraints (e.g., a performance test that verifies the latency of a function call), so you would need to resort to other mechanisms, such as by using a real implementation instead of a fake.

A fake might not need to have 100% of the functionality of its corresponding real implementation, especially if such behavior is not needed by most tests (e.g., error handling code for rare edge cases). It is best to have the fake fail fast in this case; for example, raise an error if an unsupported code path is executed. This failure communicates to the engineer that the fake is not appropriate in this situation.

Fakes Should Be Tested

A fake must have its
own
 tests to ensure that it conforms to the API of its corresponding real implementation.

A fake without tests might initially provide realistic behavior, but without tests, this behavior can diverge over time as the real implementation evolves.

One approach to writing tests for fakes involves writing tests against the API’s public

 interface and running those tests against both the real implementation and the fake (these are known as
contract tests
). The tests that run against the real implementation will likely be slower, but their downside is minimized because they need to be run only by the owners of the fake.
```

<a id="software-engineering-at-google-ch13-005"></a>
## software-engineering-at-google-ch13-005 — Stubbing, unclear tests, and paired commented examples

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 688–846.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Stubbing

As discussed earlier in this chapter, stubbing

 is a way

for a test to hardcode behavior for a function that otherwise has no behavior on its own. It is often a quick and easy way to replace a real implementation in a test. For example, the code in
Using stubbing to simulate responses
 uses stubbing to simulate the response from a credit card server.

Example 13-12.
Using stubbing to simulate responses

@Test public void getTransactionCount() {
  transactionCounter = new TransactionCounter(
mockCreditCardServer
);
  // Use stubbing to return three transactions.
  when(
mockCreditCardServer
.getTransactions()).thenReturn(
      newList(TRANSACTION_1, TRANSACTION_2, TRANSACTION_3));
  assertThat(transactionCounter.getTransactionCount()).isEqualTo(3);
}

The Dangers of Overusing Stubbing

Because stubbing is so easy to apply in tests, it can be tempting to use this technique anytime it’s not trivial to use a real implementation.

 However, overuse of stubbing can result in major losses in productivity for engineers who need to maintain these tests.

Tests become unclear

Stubbing involves writing extra code to define the behavior of the functions being stubbed.

 Having this extra code detracts from the intent of the test, and this code can be difficult to understand if you’re not familiar with the implementation of the system under test.

A key sign that stubbing isn’t appropriate for a test is if you find yourself mentally stepping through the system under test in order to understand why certain functions in the test are stubbed.

Tests become brittle

Stubbing leaks

 implementation details of your code into your test.

When implementation details in your production code change, you’ll need to update your tests to reflect these changes. Ideally, a good test should need to change only if user-facing behavior of an API changes; it should remain unaffected by changes to the API’s implementation.

Tests become less effective

With stubbing, there is no way to

 ensure the function being stubbed behaves like the real implementation, such as in a statement like that shown in the following snippet that hardcodes part of the contract of the
add()
 method (
“If 1 and 2 are passed in, 3 will be returned”
):

when(stubCalculator.add(1, 2)).thenReturn(3);

Stubbing is a poor choice if the system under test depends on the real implementation’s contract because you will be forced to duplicate the details of the contract, and there is no way to guarantee that the contract is correct (i.e., that the stubbed function has fidelity to the real implementation).

Additionally, with stubbing there is no way to store state, which can make it difficult to test certain aspects of your code. For example, if you call
database.save(item)
 on either a real implementation or a fake, you might be able to retrieve the item by calling
database.get(item.id())
 given that both of these calls are accessing internal state, but with stubbing, there is no way to do this.

An example of overusing stubbing

Overuse of stubbing
 illustrates a test that

 overuses stubbing.

Example 13-13.
Overuse of stubbing

@Test public void creditCardIsCharged() {
  // Pass in test doubles that were created by a mocking framework.

paymentProcessor
 =
      new PaymentProcessor(
mockCreditCardServer
,
mockTransactionProcessor
);
  // Set up stubbing for these test doubles.
  when(
mockCreditCardServer
.isServerAvailable()).thenReturn(true);
  when(
mockTransactionProcessor
.beginTransaction()).thenReturn(transaction);
  when(
mockCreditCardServer
.initTransaction(transaction)).thenReturn(true);
  when(
mockCreditCardServer
.pay(transaction, creditCard, 500))
      .thenReturn(false);
  when(
mockTransactionProcessor
.endTransaction()).thenReturn(true);
  // Call the system under test.

paymentProcessor
.processPayment(creditCard, Money.dollars(500));
  // There is no way to tell if the pay() method actually carried out the
  // transaction, so the only thing the test can do is verify that the
  // pay() method was called.
  verify(
mockCreditCardServer
).pay(transaction, creditCard, 500);
}

Refactoring a test to avoid stubbing
 rewrites the same test but avoids using stubbing. Notice how the test is shorter and that implementation details (such as how the transaction processor is used) are not exposed in the test.

No special setup is needed because the credit card server knows how to behave.

Example 13-14.
Refactoring a test to avoid stubbing

@Test public void creditCardIsCharged() {

paymentProcessor
 =
      new PaymentProcessor(
creditCardServer
,
transactionProcessor
);
  // Call the system under test.

paymentProcessor
.processPayment(creditCard, Money.dollars(500));
  // Query the credit card server state to see if the payment went through.
  assertThat(
creditCardServer
.getMostRecentCharge(creditCard))
      .isEqualTo(500);
}

We obviously don’t want such a test to talk to an external credit card server, so a fake credit card server would be more suitable. If a fake isn’t available, another option is to use a real implementation that talks to a hermetic credit card server, although this will increase the execution time of the tests. (We explore hermetic servers in the next chapter.)

When Is Stubbing Appropriate?

Rather than a catch-all replacement for a real implementation, stubbing is appropriate

when you need a function to return a specific value to get the system under test into a certain state, such as
Using stubbing to simulate responses
 that requires the system under test to return a non-empty list of transactions. Because a function’s behavior is defined inline in the test, stubbing can simulate a wide variety of return values or errors that might not be possible to trigger from a real implementation or a fake.

To ensure its purpose is clear, each stubbed function should have a direct relationship with the test’s assertions.

 As a result, a test typically should stub out a small number of functions because stubbing out many functions can lead to tests that are less clear. A test that requires many functions to be stubbed can be a sign that stubbing is being overused, or that the system under test is too complex and should be refactored.

Note that even when stubbing is appropriate, real implementations or fakes are still preferred because they don’t expose implementation details and they give you more guarantees about the correctness of the code compared to stubbing. But stubbing can be a reasonable technique to use, as long as its usage is constrained so that tests don’t become overly complex.
```

<a id="software-engineering-at-google-ch13-006"></a>
## software-engineering-at-google-ch13-006 — State and interaction testing with explanatory comments

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 848–955.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Interaction Testing

As discussed earlier in this chapter, interaction testing is a way to validate how a function

 is called without

actually calling the implementation of the function.

Mocking frameworks make it easy to perform interaction testing. However, to keep tests useful, readable, and resilient to change, it’s important to perform interaction testing only when necessary.

Prefer State Testing Over Interaction Testing

In contrast to interaction

 testing, it is preferred

 to test code through
state testing
.

With state testing, you call the system under test and validate that either the correct value was returned or that some other state in the system under test was properly changed.
State testing
 presents an example of state testing.

Example 13-15.
State testing

@Test public void sortNumbers() {
  NumberSorter
numberSorter
 = new NumberSorter(
quicksort
,
bubbleSort
);
  // Call the system under test.
  List
sortedList
 =
numberSorter
.sortNumbers(newList(3, 1, 2));
  // Validate that the returned list is sorted. It doesn’t matter which
  // sorting algorithm is used, as long as the right result was returned.
  assertThat(
sortedList
).isEqualTo(newList(1, 2, 3));
}

Interaction testing
 illustrates a similar test scenario but instead uses interaction testing. Note how it’s impossible for this test to determine that the numbers are actually sorted, because the test doubles don’t know how to sort the numbers—all it can tell you is that the system under test tried to sort the numbers.

Example 13-16.
Interaction testing

@Test public void sortNumbers_quicksortIsUsed() {
  // Pass in test doubles that were created by a mocking framework.
  NumberSorter
numberSorter
 =
      new NumberSorter(
mockQuicksort
,
mockBubbleSort
);

  // Call the system under test.

numberSorter
.sortNumbers(newList(3, 1, 2));

  // Validate that numberSorter.sortNumbers() used quicksort. The test
  // will fail if mockQuicksort.sort() is never called (e.g., if
  // mockBubbleSort is used) or if it’s called with the wrong arguments.
  verify(
mockQuicksort
).sort(newList(3, 1, 2));
}

At Google, we’ve found that emphasizing state testing is more scalable; it reduces test brittleness, making it easier to change and maintain code over time.

The primary

 issue with interaction testing is that it can’t tell you that the system under test is working properly; it can only validate that certain functions are called as expected. It requires you to make an assumption about the behavior of the code; for example, “
If
database.save(item)
 is called, we assume the item will be saved to the database.
” State testing is preferred because it actually validates this assumption (such as by saving an item to a database and then querying the database to validate that the item exists).

Another downside of interaction testing is that it utilizes implementation details of the system under test—to validate that a function was called, you are exposing to the test that the system under test calls this function. Similar to stubbing, this extra code makes tests brittle because it leaks implementation details of your production code into tests. Some people at Google jokingly refer to tests that overuse interaction
testing
 as
change-detector tests
 because they fail in response to any change to the production code, even if the behavior of the system under test remains unchanged.

When Is Interaction Testing Appropriate?

There are some

cases for which interaction testing is warranted:

You cannot perform state testing because you are unable to use a real implementation or a fake (e.g., if the real implementation is too slow and no fake exists). As a fallback, you can perform interaction testing to validate that certain functions are called. Although not ideal, this does provide some basic level of confidence that the system under test is working as expected.

Differences in the number or order of calls to a function would cause undesired behavior. Interaction testing is useful because it could be difficult to validate this behavior with state testing. For example, if you expect a caching feature to reduce the number of calls to a database, you can verify that the database object is not accessed more times than expected. Using Mockito, the code might look similar to this:

verify(databaseReader, atMostOnce()).selectRecords();

Interaction testing is not a complete replacement for state testing. If you are not able to perform state testing in a unit test, strongly consider supplementing your test suite with larger-scoped tests that do perform state testing. For instance, if you have a unit test that validates usage of a database through interaction testing, consider adding an integration test that can perform state testing against a real database. Larger-scope testing is an important strategy for risk mitigation, and we discuss it in the next
chapter.
```

<a id="software-engineering-at-google-ch13-007"></a>
## software-engineering-at-google-ch13-007 — Interaction-test readability and paired comment specimens

Source: [ch13.html](../../../../books/software-engineering-at-google/ch13.html); reading unit `ch13`, lines 957–1106.

Attribution: Andrew Trenk and Dillon Bly

Context: Test-double examples retain comments and the surrounding rationale and limits; executable annotation is labeled separately from comments.

Transcription/context notes: Examples retain the pinned extraction, including any original typos and syntax-highlighting line breaks; they are source specimens, not corrected runnable code.

```text
Best Practices for Interaction Testing

When performing

 interaction testing, following these practices can reduce some of the impact of the aforementioned downsides.

Prefer to perform interaction testing only for state-changing functions

When a system under

 test calls a function on a dependency, that

call falls into one of two categories:

State-changing

Functions that have side effects on the world outside the system under test. Examples:
sendEmail()
,
saveRecord()
,
logAccess()
.

Non-state-changing

Functions that don’t

have side effects; they return information about the world outside the system under test and don’t modify anything. Examples:
getUser()
,
findResults()
,
readFile()
.

In general, you should perform interaction testing only for functions that are state-changing. Performing interaction testing for non-state-changing functions is usually redundant given that the system under test will use the return value of the function to do other work that you can assert. The interaction itself is not an important detail for correctness, because it has no side effects.

Performing interaction testing for non-state-changing functions makes your test brittle because you’ll need to update the test anytime the pattern of interactions changes. It also makes the test less readable given that the additional assertions make it more difficult to determine which assertions are important for ensuring correctness of the code. By contrast, state-changing interactions represent something useful that your code is doing to change state somewhere else.

State-changing and non-state-changing interactions
 demonstrates interaction testing on both state-changing and non-state-changing functions.

Example 13-17.
State-changing and non-state-changing interactions

@Test public void grantUserPermission() {
  UserAuthorizer userAuthorizer =
      new UserAuthorizer(
mockUserService
,
mockPermissionDatabase
);
  when(
mockPermissionService
.
getPermission
(FAKE_USER)).thenReturn(EMPTY);

  // Call the system under test.
  userAuthorizer.grantPermission(USER_ACCESS);

  // addPermission() is state-changing, so it is reasonable to perform
  // interaction testing to validate that it was called.
  verify(
mockPermissionDatabase
).
addPermission
(FAKE_USER, USER_ACCESS);

  // getPermission() is non-state-changing, so this line of code isn’t
  // needed. One clue that interaction testing may not be needed:
  // getPermission() was already stubbed earlier in this test.
  verify(
mockPermissionDatabase
).
getPermission
(FAKE_USER);
}

Avoid overspecification

In
Unit Testing
, we discuss why it is useful to test behaviors rather than methods. This means that a test method should focus

 on verifying one behavior of a method or class rather than trying

 to verify multiple behaviors in a single test.

When performing interaction testing, we should aim to apply the same principle by avoiding overspecifying which functions and arguments are validated. This leads to tests that are clearer and more concise. It also leads to tests that are resilient to changes made to behaviors that are outside the scope of each test, so fewer tests will fail if a change is made to a way a function is called.

Overspecified interaction tests
 illustrates interaction testing with overspecification. The intention of the test is to validate that the user’s name is included in the greeting prompt, but the test will fail if unrelated behavior is changed.

Example 13-18.
Overspecified interaction tests

@Test public void displayGreeting_renderUserName() {
  when(mockUserService.getUserName()).thenReturn("Fake User");
  userGreeter.displayGreeting(); // Call the system under test.

  // The test will fail if any of the arguments to setText() are changed.
  verify(
userPrompt
).
setText
("Fake User", "Good morning!", "Version 2.1");

  // The test will fail if setIcon() is not called, even though this
  // behavior is incidental to the test since it is not related to
  // validating the user name.
  verify(
userPrompt
).
setIcon
(IMAGE_SUNSHINE);
}

Well-specified interaction tests
 illustrates interaction testing with more care in specifying relevant arguments and functions. The behaviors being tested are split into separate tests, and each test validates the minimum amount necessary for ensuring

 the behavior it is testing is correct.

Example 13-19.
Well-specified interaction tests

@Test public void displayGreeting_renderUserName() {
  when(mockUserService.getUserName()).thenReturn("Fake User");
  userGreeter.displayGreeting(); // Call the system under test.
  verify(
userPrompter
).
setText
(eq("Fake User"), any(), any());
}
@Test public void displayGreeting_timeIsMorning_useMorningSettings() {
  setTimeOfDay(TIME_MORNING);
  userGreeter.displayGreeting(); // Call the system under test.
  verify(
userPrompt
).
setText
(any(), eq("Good morning!"), any());
  verify(
userPrompt
).
setIcon
(IMAGE_SUNSHINE);
}
```

<a id="software-engineering-at-google-ch14-001"></a>
## software-engineering-at-google-ch14-001 — Unexpected behavior beyond specified contracts

Source: [ch14.html](../../../../books/software-engineering-at-google/ch14.html); reading unit `ch14`, lines 112–135.

Attribution: Joseph Graves

Context: Explains unanticipated inputs and behaviors when discussing limits of unit tests and fidelity.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Unanticipated behaviors, inputs, and side effects

Unit tests are limited by the imagination of the engineer writing them.

 That is, they can only test for anticipated behaviors and inputs.

However, issues that users find with a product are mostly unanticipated (otherwise it would be unlikely that they would make it to end users as issues). This fact suggests that different test techniques are needed to test for unanticipated behaviors.

Hyrum’s Law
 is an important consideration here: even if we could test 100% for conformance to a strict, specified contract, the effective user contract applies to all visible behaviors, not just a stated contract.

 It is unlikely that unit tests alone test for all visible behaviors that are not specified in the public API.

Emergent behaviors and the "vacuum effect"

Unit tests are limited to the scope that they cover (especially with the widespread use of test doubles), so if behavior changes

in areas outside of this scope, it cannot be detected. And because unit tests are designed to be fast and reliable, they deliberately eliminate the chaos of real dependencies, network, and data.

A unit test is like a problem in theoretical physics: ensconced in a vacuum, neatly hidden from the mess of the real world, which is great for speed and reliability but misses certain

 defect

categories.
```

<a id="software-engineering-at-google-ch14-002"></a>
## software-engineering-at-google-ch14-002 — Runnable specifications and language familiarity

Source: [ch14.html](../../../../books/software-engineering-at-google/ch14.html); reading unit `ch14`, lines 683–705.

Attribution: Joseph Graves

Context: Preserves user acceptance tests as runnable specifications, with the stated reason Google uses them infrequently.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
UAT

Tests of this type have the

 following

characteristics:

SUT: machine-hermetic or cloud-deployed isolated

Data: handcrafted

Verification: assertions

A key aspect of unit tests is that they are written by the developer writing the code under test. But that makes it quite likely that misunderstandings about the
intended
 behavior of a product are reflected not only in the code, but also the unit tests. Such unit tests verify that code is "Working as implemented" instead of "Working as intended."

For cases in which there is either a specific end customer or a customer proxy (a customer committee or even a product manager), UATs are automated tests that exercise the product through public APIs to ensure the overall behavior for specific
user journeys
 is as intended. Multiple public frameworks exist (e.g., Cucumber and RSpec) to make such tests writable/readable in a user-friendly language, often in the context of "runnable specifications."

Google does not actually do a lot of automated UAT and does not use specification languages very much. Many of Google’s products historically have been created by the software engineers themselves. There has been little need for runnable specification languages because those defining the intended product behavior are often fluent in the actual coding languages themselves.
```

<a id="software-engineering-at-google-ch14-003"></a>
## software-engineering-at-google-ch14-003 — Documenting how to run large tests

Source: [ch14.html](../../../../books/software-engineering-at-google/ch14.html); reading unit `ch14`, lines 823–850.

Attribution: Joseph Graves

Context: Clear libraries, documentation, and examples support test adoption; bespoke tests make running them difficult.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Authoring Large Tests

Although the

 structure of large tests is fairly standard, there

 is still a challenge with creating such a test, especially

if it is the first time someone on the team has done so.

The best way to make it possible to write such tests is to have clear libraries, documentation, and examples. Unit tests are easy to write because of native language support (JUnit was once esoteric but is now mainstream).

 We reuse these assertion libraries for functional integration tests, but we also have created over time libraries for interacting with SUTs, for running A/B diffs, for seeding test data, and for orchestrating test workflows.

Larger tests are more expensive to maintain, in both resources and human time, but not all large tests are created equal. One reason that A/B diff tests are popular is that they have less human cost in maintaining the verification step. Similarly, production SUTs have less maintenance cost than isolated hermetic SUTs.

 And because all of this authored infrastructure and code must be maintained, the cost savings can
compound.

However, this cost must be looked at holistically. If the cost of manually reconciling diffs or of supporting and safeguarding production testing outweighs the savings, it becomes ineffective.

Running Large Tests

We mentioned above how our larger tests don’t fit in TAP and so we have alternate continuous builds and presubmits for them.

 One of the initial challenges for our engineers is how to even run nonstandard tests and how to iterate on them.

As much as possible, we have tried to make our larger tests run in ways familiar for our engineers. Our presubmit infrastructure puts a common API in front of both running these tests and running TAP tests, and our code review infrastructure shows both sets of results. But many large tests are bespoke and thus need specific documentation for how to run them on demand. This can be a source of frustration for unfamiliar engineers.
```

<a id="software-engineering-at-google-ch14-004"></a>
## software-engineering-at-google-ch14-004 — Understandable tests, failures, and ownership

Source: [ch14.html](../../../../books/software-engineering-at-google/ch14.html); reading unit `ch14`, lines 896–952.

Attribution: Joseph Graves

Context: Retains meaningful error messages and names, readability of failure evidence, and explicit ownership documentation.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Making tests understandable

A specific case for

which it can be difficult

to integrate

tests into the developer workflow is when those tests produce results that are unintelligible to the engineer running the tests. Even unit tests can produce some confusion—if my change breaks your test, it can be difficult to understand why if I am generally unfamiliar with your code—but for larger tests, such confusion can be insurmountable. Tests that are assertive must provide a clear pass/fail signal and must provide meaningful error output to help triage the source of failure. Tests that require human investigation, like A/B diff tests, require special handling to be meaningful or else risk being skipped during presubmit.

How does this work in practice? A good

 large test that fails should do the following:

Have a message that clearly identifies what the failure is

The worst-case scenario is to have an error that just says "Assertion failed" and a stack trace. A good error anticipates the test runner’s unfamiliarity with the code and provides a message that gives context: "In test_ReturnsOneFullPageOfSearchResultsForAPopularQuery, expected 10 search results but got 1." For a performance or A/B diff test that fails, there should be a clear explanation in the output of what is being measured and why the behavior is considered suspect.

Minimize the effort necessary to identify the root cause of the discrepancy

A stack trace is not useful for larger tests because the call chain can span multiple process boundaries. Instead, it’s necessary to produce a trace across the call chain or to invest in automation that can narrow down the culprit. The test should produce some kind of artifact to this effect. For example,
Dapper
 is a framework used by Google to associate a single request ID with all the requests in an RPC call chain, and all of the associated logs for that request can be correlated by that ID to facilitate tracing.

Provide support and contact information.

It should be easy for the test runner to get help by making the owners and supporters of the test easy to contact.

Owning Large Tests

Larger tests must have

documented

owners—engineers who can adequately review changes to the test and who can be counted on to provide support in the case of test failures. Without proper ownership, a test can fall victim to the following:

It becomes more difficult for contributors to modify and update the test

It takes longer to resolve test failures

And the test rots.

Integration tests of components within a particular project should be owned by the project lead. Feature-focused tests (tests that cover a particular business feature across a set of services) should be owned by a "feature owner"; in some cases, this owner might be a software engineer responsible for the feature implementation end to end; in other cases it might be a product manager or a "test engineer" who owns the description of the business scenario. Whoever owns the test must be empowered to ensure its overall health and must have both the ability to support its maintenance and the incentives to do so.

It is possible to build automation around test owners if this information is recorded in a structured way. Some approaches that we use include the following:

Regular code ownership

In many cases, a larger test is a standalone code artifact that lives in a particular location in our codebase. In that case, we can use the OWNERS (
Code Review
) information already present in the monorepo to hint to automation that the owner(s) of a particular test are the owners of the test code.

Per-test annotations

In some cases, multiple test methods

can be added to a single test class or module, and each of these test methods can have a different feature owner. We use per-language structured annotations to document the test owner in each of these cases so that if a particular test method fails, we can identify the owner to contact.
```

<a id="software-engineering-at-google-ch15-001"></a>
## software-engineering-at-google-ch15-001 — Documentation and signposts during migration

Source: [ch15.html](../../../../books/software-engineering-at-google/ch15.html); reading unit `ch15`, lines 55–84.

Attribution: Hyrum Wright

Context: Deprecation discussion includes unknown uses, historical source access, and documentation that directs users toward replacements.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Why Is Deprecation So Hard?

We’ve mentioned Hyrum’s Law

elsewhere in this book, but it’s worth repeating its applicability here: the more users of a system, the higher

the probability that users are using it in unexpected and unforeseen ways, and the harder it will be to deprecate and remove such a system. Their usage just “happens to work” instead of being “guaranteed to work.” In this context, removing a system can be thought of as the ultimate change: we aren’t just changing behavior, we are removing that behavior completely! This kind of radical alteration will shake loose a number of unexpected dependents.

To further complicate matters, deprecation usually isn’t an option until a newer system is available that provides the same (or better!) functionality. The new system might be better, but it is also different: after all, if it were exactly the same as the obsolete system, it wouldn’t provide any benefit to users who migrate to it (though it might benefit the team operating it). This functional difference means a one-to-one match between the old system and the new system is rare, and every use of the old system must be evaluated in the context of the new one.

Another surprising reluctance to deprecate is emotional attachment to old systems, particularly those that the deprecator had a hand in helping to create. An example of this change aversion happens when systematically removing old code at Google: we’ve occasionally encountered resistance of the form “I like this code!” It can be difficult to convince engineers to tear down something they’ve spent years building. This is an understandable response, but ultimately self-defeating: if a system is obsolete, it has a net cost on the organization and should be removed. One of the ways we’ve addressed concerns about keeping old code within Google is by ensuring that the source code repository isn’t just searchable at trunk, but also historically. Even code that has been removed can be found again (see
Code Search
).

There’s an old joke within Google that there are two ways of doing things: the one that’s deprecated, and the one that’s not-yet-ready. This is usually the result of a new solution being “almost” done and is the unfortunate reality of working in a technological environment that is complex and fast-paced.

Google engineers have become used to working in this environment, but it can still be disconcerting. Good documentation, plenty of signposts, and teams of experts helping with the deprecation and migration process all make it easier to know whether you should be using the old thing, with all its warts, or the new one, with all its
uncertainties.

Finally, funding and executing deprecation efforts can be difficult politically; staffing a team and spending time removing obsolete systems costs real money, whereas the costs of doing nothing and letting the system lumber along unattended are not readily observable. It can be difficult to convince the relevant stakeholders that deprecation efforts are worthwhile, particularly if they negatively impact new feature development. Research techniques, such as those described in
Measuring Engineering Productivity
, can provide concrete evidence that a deprecation is worthwhile.

Given the difficulty in deprecating and removing obsolete software systems, it is often easier for users to evolve a system
in situ
, rather than completely replacing it. Incrementality doesn’t avoid the deprecation process altogether, but it does break it down into smaller, more manageable chunks that can yield incremental benefits. Within Google, we’ve observed that migrating to entirely new systems is
extremely
 expensive, and the costs are frequently underestimated. Incremental deprecation efforts
accomplished
 by in-place refactoring can keep existing systems running while making it easier to deliver value to users.
```

<a id="software-engineering-at-google-ch15-002"></a>
## software-engineering-at-google-ch15-002 — Advisory deprecation limits

Source: [ch15.html](../../../../books/software-engineering-at-google/ch15.html); reading unit `ch15`, lines 118–138.

Attribution: Hyrum Wright

Context: Context for why warnings and announcements alone do not necessarily migrate existing users.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Advisory Deprecation

Advisory
 deprecations are those that don’t

have a deadline

 and aren’t high priority for the organization (and for which the company isn’t willing to dedicate resources). These could also be labeled
aspirational
 deprecations: the team knows the system has been replaced, and although they hope clients will eventually migrate to the new system, they don’t have imminent plans to either provide support to help move clients or delete the old system. This kind of deprecation often lacks enforcement: we hope that clients move, but can’t force them to. As our friends in SRE will readily tell you: “Hope is not a strategy.”

Advisory deprecations are a good tool for advertising the existence of a new system and encouraging early adopting users to start trying it out. Such a new system should
not
 be considered in a beta period: it should be ready for production uses and loads and should be prepared to support new users indefinitely. Of course, any new system is going to experience growing pains, but after the old system has been deprecated in any way, the new system will become a critical piece of the organization’s
infrastructure.

One scenario we’ve seen at Google in which advisory deprecations have strong benefits is when the new system offers compelling benefits to its users. In these cases,
simply
 notifying users of this new system and providing them self-service tools to migrate to it often encourages adoption. However, the benefits cannot be simply incremental: they must be transformative. Users will be hesitant to migrate on their own for marginal benefits, and even new systems with vast improvements will not gain full adoption using only advisory deprecation efforts.

Advisory deprecation allows system authors to nudge users in the desired direction, but they should not be counted on to do the majority of migration work. It is often tempting to simply put a deprecation warning on an old system and walk away without any further effort. Our experience at Google has been that this can lead to (slightly) fewer new uses of an obsolete system, but it rarely leads to teams actively migrating away from it. Existing uses of the old system exert a sort of conceptual (or technical) pull toward it: comparatively many uses of the old system will tend to pick up a large share of new uses, no matter how much we say, “Please use the new system.” The old system will continue to require maintenance and other resources unless its users are more actively encouraged to migrate.
```

<a id="software-engineering-at-google-ch15-003"></a>
## software-engineering-at-google-ch15-003 — Actionable and relevant deprecation warnings

Source: [ch15.html](../../../../books/software-engineering-at-google/ch15.html); reading unit `ch15`, lines 166–191.

Attribution: Hyrum Wright

Context: Preserves alert fatigue, limits of marking everything deprecated, and targeted presentation of warnings.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Deprecation Warnings

For both advisory and compulsory deprecations, it is often useful to have a programmatic way

of marking systems as deprecated so that users are warned about their use and encouraged to move away. It’s often tempting to just mark something as deprecated and hope its uses eventually disappear, but remember: “hope is not a strategy.” Deprecation warnings can help prevent new uses, but rarely lead to migration of existing systems.

What usually happens in practice is that these warnings accumulate over time. If they are used in a transitive context (for example, library A depends on library B, which depends on library C, and C issues a warning, which shows up when A is built), these warnings can soon overwhelm users of a system to the point where they ignore them altogether.

 In health care, this phenomenon is known as “
alert fatigue
.”

Any deprecation warning issued to a user needs to have two properties: actionability and relevance. A warning is
actionable
 if the user can use the warning to actually perform some relevant action, not just in theory, but in practical terms, given the expertise in that problem area that we expect for an average engineer. For example, a tool might warn that a call to a given function should be replaced with a call to its updated counterpart, or an email might outline the steps required to move data from an old system to a new one. In each case, the warning provided the next steps that an engineer can perform to no longer depend on the deprecated system.
2

A warning can be actionable, but still be annoying. To be useful, a deprecation warning should also be
relevant
. A warning is relevant if it surfaces at a time when a user actually performs the indicated action. Warning about the use of a deprecated function is best done while the engineer is writing code that uses that function, not after it has been checked into the repository for several weeks. Likewise, an email for data migration is best sent several months before the old system is removed rather than as an afterthought a weekend before the removal occurs.

It’s important to resist the urge to put deprecation warnings on everything possible. Warnings themselves are not bad, but naive tooling often produces a quantity of warning messages that can overwhelm the unsuspecting engineer. Within Google, we are very liberal with marking old functions as deprecated but leverage tooling such as
ErrorProne
 or clang-tidy to ensure that warnings are surfaced in targeted ways. As discussed in
Static Analysis
, we limit these warnings to newly changed lines as a way to warn people about new uses of the deprecated symbol. Much more intrusive warnings, such as for deprecated targets in the dependency graph, are added only for compulsory deprecations, and the team is actively moving users away. In either case, tooling plays an important role in surfacing the appropriate information to the appropriate people at the proper time, allowing more warnings to be added without fatiguing the user.
```

<a id="software-engineering-at-google-ch15-004"></a>
## software-engineering-at-google-ch15-004 — Deprecation annotations carry owner messaging

Source: [ch15.html](../../../../books/software-engineering-at-google/ch15.html); reading unit `ch15`, lines 262–280.

Attribution: Hyrum Wright

Context: Compiler annotations communicate a deprecated API and its replacement; this is executable tooling metadata, not an ordinary prose comment.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
Preventing backsliding

Finally, an often overlooked piece of

 deprecation infrastructure is tooling for preventing the addition of new uses of the very thing being actively removed. Even for advisory deprecations, it is useful to warn users to shy away from a deprecated system in favor of a new one when they are writing new code. Without backsliding prevention, deprecation can become a game of whack-a-mole in which users constantly add new uses of a system with which they are familiar (or find examples of elsewhere in the codebase), and the deprecation team constantly migrates these new uses. This process is both counterproductive and demoralizing.

To prevent deprecation backsliding on a micro level, we use the Tricorder static analysis framework

to notify users that they are adding calls into a deprecated system and give them feedback on the appropriate replacement.

Owners of deprecated systems can add compiler annotations to deprecated symbols (such as the
@deprecated
 Java annotation), and Tricorder surfaces new uses of these symbols at review time. These annotations give control over messaging to the teams that own the deprecated system, while at the same time automatically alerting the change author. In limited cases, the tooling also suggests a push-button fix to migrate to the suggested replacement.

On a macro level,  we use visibility whitelists in our build system to ensure that new dependencies

are not introduced to the deprecated system. Automated tooling periodically examines these whitelists and prunes them as dependent systems are migrated away from

 the obsolete system.
```

<a id="software-engineering-at-google-ch16-001"></a>
## software-engineering-at-google-ch16-001 — Commit summaries and reflection

Source: [ch16.html](../../../../books/software-engineering-at-google/ch16.html); reading unit `ch16`, lines 103–109.

Attribution: Titus Winters

Context: Version-control discussion treats writing a summary as a moment to reflect and check a change; adjacent historical explanation context.

Transcription/context notes: Numbered derived text preserves original wording and extraction line breaks. Adjacent documentation and communication context is retained without converting it into a prescription about inline comments.

```text
A VCS removes the question of “which is more recent?” Use of modern version control automates error-prone operations like tracking which set of changes have been applied. Version control is how we coordinate between multiple developers and/or multiple points in time.

Because VCS has become so thoroughly embedded in the process of software engineering, even legal and regulatory practices have caught up. VCS allows a formal record of every change to every line of code, which is increasingly necessary for satisfying audit requirements. When mixing between in-house development and appropriate use of third-party sources, VCS helps track provenance and origination for every line of code.

In addition to the technical and regulatory aspects of tracking source over time and handling sync/branch/merge operations, version control triggers some nontechnical changes in behavior. The ritual of committing to version control and producing a commit log is a trigger for a moment of reflection: what have you accomplished since your last commit? Is the source in a state that you’re happy with? The moment of introspection associated with committing, writing up a summary, and marking a task complete might have value on its own for many people. The start of the commit process is a perfect time to run through a checklist, run static analyses (see
Static Analysis
), check test coverage, run tests and dynamic analysis, and so on.
```

<a id="software-engineering-at-google-ch17-001"></a>
## software-engineering-at-google-ch17-001 — Code understanding and linked bug identifiers

Source: [ch17.html](../../../../books/software-engineering-at-google/ch17.html); reading unit `ch17`, lines 7–51.

Attribution: Alexander Neubeck and Ben St. John

Context: Describes reading-oriented tooling, comment-aware search, and linking bug IDs in comments to reports.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Code Search is a tool for browsing and searching

code at Google that consists of a frontend UI and various backend elements. Like many of the development tools at Google, it arose directly out of a need to scale to the size of the codebase. Code Search began as a combination of a grep-type tool
1
 for internal code with the ranking and UI of external Code Search.
2
 Its place as a key tool for Google developers was cemented by the integration of Kythe/Grok,
3
 which added cross-references and the ability to jump to symbol definitions.

That integration changed its focus from searching to browsing code, and later development of Code Search was partly guided by a principle of "answering the next question about code in a single click." Now such questions as "Where is this symbol defined?", "Where is it used?", "How do I include it?", "When was it added to the codebase?", and even ones like "Fleet-wide, how many CPU cycles does it consume?" are all answerable with one or two clicks.

In contrast to integrated development environments (IDEs) or code editors, Code Search is optimized for the use case of reading, understanding, and exploring code at scale. To do so, it relies heavily on cloud-based backends for searching content and resolving cross-references.

In this chapter, we’ll look at Code Search in more detail, including how Googlers use it as part of their developer workflows, why we chose to develop a separate web tool for code searching, and examine how it addresses the challenges of searching and browsing code at Google repository scale.

The Code Search UI

The search box is a central

 element of the Code Search UI (see
Figure 17-1
), and like web search, it has "suggestions" that developers can use for quick navigation to files, symbols, or directories. For more complex use cases, a results page with code snippets is returned.

The search itself can be thought of as an instant “find in files” (like the Unix
grep
 command) with relevance ranking and some code-specific enhancements like proper syntax highlighting, scope awareness, and awareness of comments and string literals. Search is also available from the command line and can be incorporated into other tools via a Remote Procedure Call (RPC) API. This comes in handy when post-processing is required or if the result set is too large for manual
inspection.

Figure 17-1.
The Code Search UI

When viewing a single file, most tokens are clickable to let the user quickly navigate to related information. For example, a function call will link to its function definition, an imported filename to the actual source file, or a bug ID in a comment to the corresponding bug report. This is powered by compiler-based indexing tools like
Kythe
. Clicking the symbol name opens a panel with all the places the
symbol
 is used. Similarly, hovering over local variables in a function will highlight all occurrences of that variable in the implementation.

Code Search also shows the history of a file, via its integration

 with Piper (see
Version Control and Branch Management
). This means seeing older versions of the file, which changes have affected it, who wrote them, jumping to them in Critique (see
Critique: Google’s Code Review Tool
), diffing versions of files, and the classic "blame" view if desired. Even deleted files can be seen from a directory view.
```

<a id="software-engineering-at-google-ch17-002"></a>
## software-engineering-at-google-ch17-002 — Finding examples, explanations, and history

Source: [ch17.html](../../../../books/software-engineering-at-google/ch17.html); reading unit `ch17`, lines 53–105.

Attribution: Alexander Neubeck and Ben St. John

Context: Preserves the documented search intents and documentation links, including how, why, who and when questions.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
How Do Googlers Use Code Search?

Although similar functionality is available

 in other tools, Googlers still make heavy use of the Code Search UI for searching and file viewing and ultimately for understanding code.
4
 The tasks engineers try to complete with Code Search can be thought of answering questions about code, and recurring intents become visible.
5

Where?

About 16% of Code Searches try to answer the

question of where a specific piece of information exists in the codebase; for example, a function definition or configuration, all usages of an API, or just where a specific file is in the repository. These questions are very targeted and can be very precisely answered with either search queries or by following semantic links, like "jump to symbol definition." Such questions often arise during larger tasks like refactorings/cleanups or when collaborating with other engineers on a project. Therefore, it is essential that these small knowledge gaps are addressed efficiently.

Code Search provides two ways of helping: ranking the results, and a rich query language. Ranking addresses the common cases, and searches can be made very specific (e.g., restricting code paths, excluding languages, only considering functions) to deal with rarer cases.

The UI makes it easy to share a Code Search result with colleagues. So, for code reviews, you can simply include the link—for example, "Have you considered using this specialized hash map: cool_hash.h?" This is also very useful for documentation, in bug reports, and in postmortems and is the canonical way of referring to code within Google. Even older versions of the code can be referenced, so links can stay valid as the codebase evolves.

What?

Roughly one quarter of Code Searches are classic file browsing, to answer the question of what a specific part of the codebase is doing.

 These kinds of tasks are usually more exploratory, rather than locating a specific result. This is using Code Search to read the source, to better understand code before making a change, or to be able to understand someone else’s change.

To ease these kinds of tasks, Code Search introduced browsing via call hierarchies and quick navigation between related files (e.g., between header, implementation, test, and build files). This is about understanding code by easily answering each of the many questions a developer has when looking at it.

How?

The most frequent use case—about one third of Code Searches—are about seeing examples of how others have done something.

Typically, a developer has already found a specific API (e.g., how to read a file from remote storage) and wants to see how the API should be applied to a particular problem (e.g., how to set up the remote connection robustly and handle certain types of errors). Code Search is also used to find the proper library for specific problems in the first place (e.g., how to compute a fingerprint for integer values efficiently) and then pick the most appropriate implementation. For these kinds of tasks, a combination of searches and cross-reference browsing are typical.

Why?

Related to
what
 code is doing, there are more targeted queries around
why
 code is behaving differently than expected.

About 16% of Code Searches try to answer the question of why a certain piece of code was added, or why it behaves in a certain way. Such questions often arise during debugging; for example, why does an error occur under these particular circumstances?

An important capability here is being able to search and explore the exact state of the codebase at a particular point in time. When debugging a production issue, this can mean working with a state of the codebase that is weeks or months old, while debugging test failures for new code usually means working with changes that are only minutes old. Both are possible with Code Search.

Who and When?

About 8% of Code Searches try

to answer questions around who or when someone introduced a certain piece of code, interacting with the version control system. For example, it’s possible to see when a particular line was introduced (like Git’s "blame") and jump to the relevant code review.

 This history panel can also be very useful in finding the best person to ask about the code, or to review a change to it.
6
```

<a id="software-engineering-at-google-ch17-003"></a>
## software-engineering-at-google-ch17-003 — Live code embedded in documentation

Source: [ch17.html](../../../../books/software-engineering-at-google/ch17.html); reading unit `ch17`, lines 171–184.

Attribution: Alexander Neubeck and Ben St. John

Context: Documentation links survive file restructuring and embedded snippets avoid extra source documentation markers.

Transcription/context notes: Original Figure 17-4 visually inspected; its legible example is preserved in the related supplemental record, with clipped query text noted.

Related: [software-engineering-at-google-ch17-006](#software-engineering-at-google-ch17-006)

```text
Compilation errors and tests also typically refer back to a code location (e.g., test X in
file
 at
line
). These can be linkified even for unsubmitted code given that most development happens in specific cloud-visible workspaces that are accessible and searchable by Code Search.

Finally, codelabs and other documentation refer to APIs, examples, and implementations.

 Such links can be search queries referencing a specific class or function, which remain valid when the file structure changes. For code snippets, the most recent implementation at head can easily be embedded into a documentation page, as demonstrated in
Figure 17-4
, without the need to pollute the source file with additional documentation markers.

Figure 17-4.
Code Search integration in documentation
```

<a id="software-engineering-at-google-ch17-004"></a>
## software-engineering-at-google-ch17-004 — Investing in code understanding

Source: [ch17.html](../../../../books/software-engineering-at-google/ch17.html); reading unit `ch17`, lines 469–492.

Attribution: Alexander Neubeck and Ben St. John

Context: Conclusion relates working examples and semantic navigation to code understanding and productivity.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Conclusion

Code Search grew from an organic replacement for
grep
 into a central tool boosting developer productivity, leveraging Google’s web search technology along the way. What does this mean for you, though? If you are on a small project that easily fits in your IDE, probably not much. If you are responsible for the productivity of engineers on a larger codebase, there are probably some insights to be gained.

The most important one is perhaps obvious: understanding code is key to developing and maintaining it, and this means that investing in understanding code will yield dividends that might be difficult to measure, but are real. Every feature we added to Code Search was and is used by developers to help them in their daily work (admittedly some more than others). Two of the most important features, Kythe integration (i.e., adding semantic code understanding) and finding working examples, are also the most clearly tied to understanding code (versus, for example, finding it, or seeing how it’s changed). In terms of tool impact, no one uses a tool that they don’t know exists, so it is also important to make developers aware of the available tooling—at Google, it is part of "Noogler" training, the onboarding training for newly hired software engineers.

For you, this might mean setting up a standard indexing profile for IDEs, sharing knowledge about egrep, running ctags, or setting up some custom indexing tooling, like Code Search. Whatever you do, it will almost certainly be used, and used more, and in different ways than you expected—and your developers will benefit.

TL;DRs

Helping your developers understand code can be a big boost to engineering productivity. At Google, the key tool for this is Code Search.

Code Search has additional value as a basis for other tools and as a central, standard place that all documentation and developer tools link to.

The huge size of the Google codebase made a custom tool—as opposed to, for example,
grep
 or an IDE’s indexing—necessary.

As an interactive tool, Code Search must be fast, allowing a "question and answer" workflow. It is expected to have low latency in every respect: search, browsing, and indexing.

It will be widely used only if it is trusted, and will be trusted only if it indexes all code, gives all results, and gives the desired results first. However, earlier, less powerful, versions were both useful and used, as long as their limits were
understood.
```

<a id="software-engineering-at-google-ch17-005"></a>
## software-engineering-at-google-ch17-005 — Browsable code and limits of blame

Source: [ch17.html](../../../../books/software-engineering-at-google/ch17.html); reading unit `ch17`, lines 504–513.

Attribution: Alexander Neubeck and Ben St. John

Context: Footnotes preserve naming/types and shallow hierarchy advice, plus caveat about machine-generated changes diminishing naive blame.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
4
There is an interesting virtuous cycle that a ubiquitous code browser encourages: writing code that is easy to browse. This can mean things like not nesting hierarchies too deep, which requires many clicks to move from call sites to actual implementation, and using named types rather than generic things like strings or integers, because it’s then easy to find all usages.
5
Sadowski, Caitlin, Kathryn T. Stolee, and Sebastian Elbaum. “How Developers Search for Code: A Case Study” In
Proceedings of the 2015 10th Joint Meeting on Foundations of Software Engineering (ESEC/FSE 2015)
.
https://doi.org/10.1145/2786805.2786855
.
6
That said, given the rate of commits for machine-generated changes, naive “blame” tracking has less value than it does in more change-averse ecosystems.
```

<a id="software-engineering-at-google-ch17-006"></a>
## software-engineering-at-google-ch17-006 — Supplemental image transcription: live snippets in documentation

Source: [ch17.html](../../../../books/software-engineering-at-google/ch17.html); reading unit `ch17`, lines 548–563.

Attribution: Alexander Neubeck and Ben St. John

Context: Manual transcription of Figure 17-4 in ch17.html showing live-snippet syntax and embedded Fibonacci code; external documentation, not inline comments.

Transcription/context notes: Original PNG visually checked. Query is clipped after the visible f; indentation is approximate; UI icons, link styling and scrollbar omitted.

Related: [software-engineering-at-google-ch17-003](#software-engineering-at-google-ch17-003)

````text
Use a markdown code block and specify live-snippet as the language. Live snippets use
the Code Search cs/ query syntax to specify which code to include. For example:
```live-snippet
cs/file:google3/corp/g3doc/tests/regression/tests/testLiveSnippet/snippet_test.cc f
```
Which renders as:
static int Fibonacci(int n) {
  if (n <= 1) return n;
  int a = 0, b = 1;
  for (int i = 0; i < n; ++i) {
    int t = a;
    a = b;
    b += t;
  }
  return b;
}
````

<a id="software-engineering-at-google-ch18-001"></a>
## software-engineering-at-google-ch18-001 — Ant buildfile with explanatory XML comments

Source: [ch18.html](../../../../books/software-engineering-at-google/ch18.html); reading unit `ch18`, lines 147–216.

Attribution: Erik Kuefler; example attributed to the Ant manual

Context: Preserves the complete commented buildfile, its source attribution, and interpretation. The chapter does not separately evaluate these comments.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Task-Based Build Systems

The shell scripts we started developing in the

previous

section were an example of a primitive
task-based build system
. In a task-based build system, the fundamental unit of work is the task. Each task is a script of some sort that can execute any sort of logic, and tasks specify other tasks as dependencies that must run before them. Most major build systems in use today, such as Ant, Maven, Gradle, Grunt, and Rake, are task based.

Instead of shell scripts, most modern build systems require engineers to create
buildfiles
 that describe how to perform the build.

 Take this example from the
Ant manual
:

<project name="MyProject" default="dist" basedir=".">
  <description>
    simple example build file
  </description>
  <!-- set global properties for this build -->
  <property name="src" location="src"/>
  <property name="build" location="build"/>
  <property name="dist" location="dist"/>

  <target name="init">
    <!-- Create the time stamp -->
    <tstamp/>
    <!-- Create the build directory structure used by compile -->
    <mkdir dir="${build}"/>
  </target>

  <target name="compile" depends="init"
        description="compile the source">
    <!-- Compile the Java code from ${src} into ${build} -->
    <javac srcdir="${src}" destdir="${build}"/>
  </target>

  <target name="dist" depends="compile"
        description="generate the distribution">
    <!-- Create the distribution directory -->
    <mkdir dir="${dist}/lib"/>

    <!-- Put everything in ${build} into the MyProject-${DSTAMP}.jar file -->
    <jar jarfile="${dist}/lib/MyProject-${DSTAMP}.jar" basedir="${build}"/>
  </target>

  <target name="clean"
        description="clean up">
    <!-- Delete the ${build} and ${dist} directory trees -->
    <delete dir="${build}"/>
    <delete dir="${dist}"/>
  </target>
</project>

The buildfile is written in XML and defines some simple metadata about the build along with a list of tasks (the
<target>
 tags in the XML
3
). Each task executes a list of possible commands defined by Ant, which here include creating and deleting directories, running
javac
, and creating a JAR file.

This set of commands can be extended by user-provided plug-ins to cover any sort of logic. Each task can also define the tasks it depends on via the
depends
 attribute. These dependencies form an acyclic graph (see
Figure 18-1
).
```

<a id="software-engineering-at-google-ch18-002"></a>
## software-engineering-at-google-ch18-002 — Buildfile compared with stripped-down shell commands

Source: [ch18.html](../../../../books/software-engineering-at-google/ch18.html); reading unit `ch18`, lines 261–283.

Attribution: Erik Kuefler

Context: Connected comparison following the commented Ant example.

Transcription/context notes: Keep connected to ch18-001; this comparison concerns build systems, not a statement that removing comments improves code.

```text
In the end, the code executed by Ant when running the
dist
 task is equivalent to the following shell script:

./createTimestamp.sh
mkdir build/
javac src/* -d build/
mkdir -p dist/lib/
jar cf dist/lib/MyProject-$(date --iso-8601).jar build/*

When the syntax is stripped away, the buildfile and the build script actually aren’t too different.

 But we’ve already gained a lot by doing this. We can create new buildfiles in other directories and link them together. We can easily add new tasks that depend on existing tasks in arbitrary and complex ways. We need only pass the name of a single task to the
ant
 command-line tool, and it will take care of determining everything that needs to be run.

Ant is a very old piece of software, originally released in 2000—not what many people would consider a "modern" build system today!

Other tools like Maven and Gradle have improved on Ant in the intervening years and essentially

replaced it by adding features like automatic management of external dependencies and a cleaner syntax without any XML. But the nature of these newer systems remains the same: they

 allow engineers to write build scripts in a principled and modular way as tasks and provide tools for executing those tasks and managing dependencies among them.
```

<a id="software-engineering-at-google-ch19-001"></a>
## software-engineering-at-google-ch19-001 — Review history when inline explanations are absent

Source: [ch19.html](../../../../books/software-engineering-at-google/ch19.html); reading unit `ch19`, lines 7–35.

Attribution: Caitlin Sadowski, Ilham Kurnia, and Ben Rohlfs

Context: Review interactions can preserve technical decisions missing from inline comments; tooling supports communication but does not solve it.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
As you saw in
Code Review
, code review is a vital part of software development, particularly when working at scale.

 The main goal of code review is to improve the readability and maintainability of the code base, and this is supported fundamentally by the review process. However, having a well-defined code review process is only one part of the code review story. Tooling that supports that process also plays an important part in its success.

In this chapter, we’ll look at what makes successful code review tooling via Google’s well-loved in-house system,
Critique
. Critique has explicit support for the primary motivations of code review, providing reviewers and authors with a view of the review and ability to comment on the change. Critique also has support for gatekeeping what code is checked into the codebase, discussed in the section on "scoring" changes. Code review information from Critique also can be useful when doing code archaeology, following some technical decisions that are explained in code review interactions (e.g., when inline comments are lacking). Although Critique is not the only code review tool used at Google, it is the most popular one by a large margin.

Code Review Tooling Principles

We mentioned above that Critique provides functionality to support the goals of code review (we look at this functionality in more detail later in this chapter), but why is it so successful?

 Critique has been shaped by Google’s development culture, which includes code review as a core part of the workflow. This cultural influence translates into a set of guiding principles that Critique was designed to emphasize:

Simplicity

Critique’s user interface (UI) is based around making it easy to do code review without a lot of unnecessary choices, and with a smooth interface. The UI loads fast, navigation is easy and hotkey supported, and there are clear visual markers for the overall state of whether a change has been reviewed.

Foundation of trust

Code review is not for slowing others down; instead, it is for empowering others. Trusting colleagues as much as possible makes it work.

 This might mean, for example, trusting authors to make changes and not requiring an additional review phase to double check that minor comments are actually addressed. Trust also plays out by making changes openly accessible (for viewing and reviewing) across Google.

Generic communication

Communication problems are rarely solved through tooling. Critique prioritizes generic ways for users to comment on the code changes, instead of complicated protocols. Critique encourages users to spell out what they want in their comments or even suggests some edits instead of making the data model and process more complex. Communication can go wrong even with the best code review tool because the users are humans.
```

<a id="software-engineering-at-google-ch19-002"></a>
## software-engineering-at-google-ch19-002 — Providing change context to reviewers

Source: [ch19.html](../../../../books/software-engineering-at-google/ch19.html); reading unit `ch19`, lines 114–124.

Attribution: Caitlin Sadowski, Ilham Kurnia, and Ben Rohlfs

Context: Author review comments and bug links convey questions and context. These are review discussion comments, distinguished from source comments.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Stage 1: Create a Change

A code review tool should provide support at all stages of the review process and should not be the bottleneck for committing changes.

 In the prereview step, making it easier for change authors to polish a change before sending it out for review helps reduce the time taken by the reviewers to inspect the change. Critique displays change diffs with knobs to ignore whitespace changes and highlight move-only changes. Critique also surfaces the results from builds, tests, and static analyzers, including style checks (as discussed in
Code Review
).

Showing an author the diff of a change gives them the opportunity to wear a different hat: that of a code reviewer. Critique lets a change author see the diff of their changes as their reviewer will, and also see the automatic analysis results. Critique also supports making lightweight modifications to the change from within the review tool and suggests appropriate reviewers. When sending out the request, the author can also include preliminary comments on the change, providing the opportunity to ask reviewers directly about any open questions. Giving authors the chance to see a change just as their reviewers do prevents misunderstanding.

To provide further context for the reviewers, the author can also link the change to a specific bug. Critique uses an autocomplete service to show relevant bugs, prioritizing bugs that are assigned to the author.
```

<a id="software-engineering-at-google-ch19-003"></a>
## software-engineering-at-google-ch19-003 — Post-commit history and additional context

Source: [ch19.html](../../../../books/software-engineering-at-google/ch19.html); reading unit `ch19`, lines 375–384.

Attribution: Caitlin Sadowski, Ilham Kurnia, and Ben Rohlfs

Context: Review history and later comments explain why changes were made and how bugs arose.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
After Commit: Tracking History

In addition to the core use of Critique as a tool for reviewing source code changes before they are committed to the repository, Critique is also used as a tool for change archaeology.

For most files, developers can view a list of the past history of changes that modified a particular file in the Code Search system (see
Code Search
), or navigate directly to a change. Anyone at Google can browse the history of a change to generally viewable files, including the comments on and evolution of the change. This enables future auditing and is used to understand more details about why changes were made or how bugs were introduced. Developers can also use this feature to learn how changes were engineered, and code review data in aggregate is used to produce
trainings.

Critique also supports the ability to comment after a change is committed; for example, when a problem is discovered later or additional context might be useful for someone investigating the change at another time. Critique also supports the ability to roll back changes and see whether a particular change has already been rolled back.
```

<a id="software-engineering-at-google-ch20-001"></a>
## software-engineering-at-google-ch20-001 — Clearer method names and understood warnings

Source: [ch20.html](../../../../books/software-engineering-at-google/ch20.html); reading unit `ch20`, lines 85–95.

Attribution: Caitlin Sadowski

Context: containsValue versus contains clarifies intent even when the original behavior was correct; confusing messages can act like false positives.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

Related: [software-engineering-at-google-ch20-004](#software-engineering-at-google-ch20-004)

```text
Furthermore,
perception
 is a key aspect of the false-positive rate. If a static analysis tool is producing warnings that are technically correct but misinterpreted by users as false positives (e.g., due to confusing messages), users will react the same as if those warnings were in fact false positives. Similarly, warnings that are technically correct but unimportant in the grand scheme of things provoke the same reaction. We call the user-perceived false-positive rate the “effective false positive” rate. An issue is an “effective false positive” if developers did not take some positive action after seeing the issue. This means that if an analysis incorrectly reports an issue, yet the developer happily makes the fix anyway to improve code readability or maintainability, that is not an effective false positive. For example, we have a Java analysis that flags cases in which a developer calls the
contains
 method on a hash table (which is equivalent to
containsValue
) when they actually meant to call
containsKey
—even if the developer correctly meant to check for the value, calling
containsValue
 instead is clearer. Similarly, if an analysis reports an actual fault, yet the developer did not understand the fault and therefore took no action, that is an effective false positive.
```

<a id="software-engineering-at-google-ch20-002"></a>
## software-engineering-at-google-ch20-002 — Keeping code references and paired files current

Source: [ch20.html](../../../../books/software-engineering-at-google/ch20.html); reading unit `ch20`, lines 194–198.

Attribution: Caitlin Sadowski

Context: Analyzers warn on deleted source referenced by documentation and on paired regions that were not updated together.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Other analyzers showcase relationships between disparate files in a corpus. The Deleted Artifact Analyzer warns if a source file is deleted that is referenced by other non-code places in the codebase (such as inside checked-in documentation). IfThisThenThat allows developers to specify that portions of two different files must be changed in tandem (and warns if they are not). Chrome’s Finch analyzer runs on configuration files for A/B experiments in Chrome, highlighting common problems including not having the right approvals to launch an experiment or crosstalk with other currently running experiments that affect the same population. The Finch analyzer makes Remote Procedure Calls (RPCs) to other services in order to provide this information.

In addition to the source code itself, some analyzers run on other artifacts produced by that source code; many projects have enabled a binary size checker that warns when changes significantly affect a binary size.

Almost all analyzers are intraprocedural, meaning that the analysis results are based on code within a procedure (function). Compositional or incremental interprocedural analysis techniques are technically feasible but would require additional infrastructure investment (e.g., analyzing and storing method summaries as analyzers run).
```

<a id="software-engineering-at-google-ch20-003"></a>
## software-engineering-at-google-ch20-003 — Diagnostic explanation and fixes as documentation

Source: [ch20.html](../../../../books/software-engineering-at-google/ch20.html); reading unit `ch20`, lines 200–243.

Attribution: Caitlin Sadowski

Context: Preserves concrete confusing-message example, its correction, and automated fixes as an additional documentation source.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Integrated Feedback Channels

As mentioned earlier, establishing

a feedback

 loop between

analysis consumers and analysis writers is critical to track and maintain developer happiness. With Tricorder, we display the option to click a “Not useful” button on an analysis result; this click provides the option to file a bug
directly against the analyzer writer
 about why the result is not useful with information about analysis result prepopulated. Code reviewers can also ask change authors to address analysis results by clicking a “Please fix” button. The Tricorder team tracks analyzers with high “Not useful” click rates, particularly relative to how often reviewers ask to fix analysis results, and will disable analyzers if they don’t work to address problems and improve the “not useful” rate. Establishing and tuning this feedback loop took a lot of work, but has paid dividends many times over in improved analysis results and a better user experience (UX)—before we established clear feedback channels, many developers would just ignore analysis results they did not understand.

And sometimes the fix is pretty simple—such as updating the text of the message an analyzer outputs! For example, we once rolled out an Error Prone check that flagged when too many arguments were being passed to a
printf
-like function in Guava that accepted only
%s
 (and no other
printf
 specifiers). The Error Prone team received weekly "Not useful" bug reports claiming the analysis was incorrect because the number of format specifiers matched the number of arguments—all due to users trying to pass specifiers other than
%s
. After the team changed the diagnostic text to state directly that the function accepts only the
%s
 placeholder, the influx of bug reports stopped. Improving the message produced by an analysis provides an explanation of what is wrong, why, and how to fix it exactly at the point where that is most relevant and can make the difference for developers learning something when they read the message.

Suggested Fixes

Tricorder

 checks also,

when possible,
provide fixes
, as

 shown in
Figure 20-2
.

Figure 20-2.
View of an example static analysis fix in Critique

Automated fixes serve as an additional documentation source when the message is unclear and, as mentioned earlier, reduce the cost to addressing static analysis issues. Fixes can be applied directly from within Critique, or over an entire code change via a command-line tool. Although not all analyzers provide fixes, many do. We take the approach that
style
 issues in particular should be fixed automatically; for example, by formatters that automatically reformat source code files. Google has style guides for each language that specify formatting issues; pointing out formatting errors is not a good use of a human reviewer’s time. Reviewers click “Please Fix” thousands of times per day, and authors apply the automated fixes approximately 3,000 times per day. And Tricorder analyzers received “Not useful” clicks 250 times per day.
```

<a id="software-engineering-at-google-ch20-004"></a>
## software-engineering-at-google-ch20-004 — Supplemental image transcription: class and method comments in a diff

Source: [ch20.html](../../../../books/software-engineering-at-google/ch20.html); reading unit `ch20`, lines 369–391.

Attribution: Caitlin Sadowski

Context: Manual transcription of the paired source panes in Figure 20-1, including added class and method comments and a separately labeled human review comment. The figure illustrates static-analysis feedback.

Transcription/context notes: Original PNG visually checked. Approximate indentation/blank lines; gutters and UI controls omitted. The analyzer naming-warning regular expression is not transcribed. No comment-quality judgment is asserted by the surrounding prose.

Related: [software-engineering-at-google-ch20-001](#software-engineering-at-google-ch20-001)

```text
[Left code pane]
package path.to.file;

public class Test {
  public boolean foo() {

    return new String("foo") == "foo".toString();
  }
}
[Right code pane]
package path.to.file;

/**
 * Sample class
 */
public class Test {
  // Sample method
  public boolean Foo() {
    return new String("foo") == "foo".toString();
  }
}
[Human review comment, separate from both source-code panes]
Please add more test cases.
```

<a id="software-engineering-at-google-ch21-001"></a>
## software-engineering-at-google-ch21-001 — Expressing compatibility promises

Source: [ch21.html](../../../../books/software-engineering-at-google/ch21.html); reading unit `ch21`, lines 142–204.

Attribution: Titus Winters

Context: Preserves comparison of documented, implicit, and absent promises for C++, Go, Abseil, and Boost, including limits on extrapolating from code that happens to work.

Transcription/context notes: Boost quotation is attributed to the Boost project in the chapter; claims are historical source claims.

```text
Compatibility Promises

When we start

considering time, the situation gains some complicated trade-offs. Just because you get to avoid a
development
 cost doesn’t mean importing a dependency is the correct choice. In a software engineering organization that is aware of time and change, we need to also be mindful of its ongoing maintenance costs. Even if we import a dependency with no intent of upgrading it, discovered security vulnerabilities, changing platforms, and evolving dependency networks can conspire to force that upgrade, regardless of our intent. When that day comes, how expensive is it going to be? Some dependencies are more explicit than others about the expected maintenance cost for merely using that dependency: how much compatibility is assumed? How much evolution is assumed? How are changes handled? For how long are releases supported?

We suggest that a dependency provider should be clearer about the answers to these questions. Consider the example set by large infrastructure projects with millions of users and their compatibility promises.

C++

For the C++ standard library, the model is one of nearly indefinite backward compatibility.

Binaries built against an older version of the standard library are expected to build and link with the newer standard: the standard provides not only API compatibility, but ongoing backward compatibility

 for the binary artifacts, known as
ABI compatibility
. The extent to which this has been upheld varies from platform to platform. For users of gcc on Linux, it’s likely that most code works fine over a range of roughly a decade. The standard doesn’t explicitly call out its commitment to ABI compatibility—there are no public-facing policy documents on that point. However, the standard does publish
Standing Document 8
 (SD-8), which calls out a small set of types of change that the standard library can make between versions, defining implicitly what type of changes to be prepared for. Java is similar: source is compatible between language versions, and JAR files from older releases will readily work with newer versions.

Go

Not all languages prioritize the same amount of compatibility.

 The Go programming language explicitly promises source compatibility between most releases, but no binary compatibility. You cannot build a library in Go with one version of the language and link that library into a Go program built with a different version of the language.

Abseil

Google’s Abseil

project is much like Go, with an important caveat about time. We are unwilling to commit to compatibility
indefinitely
: Abseil lies at the foundation of most of our most computationally heavy services internally, which we believe are likely to be in use for many years to come. This means we’re careful to reserve the right to make changes, especially in implementation details and ABI, in order to allow better performance. We have experienced far too many instances of an API turning out to be confusing and error prone after the fact; publishing such known faults to tens of thousands of developers for the indefinite future feels wrong. Internally, we already have roughly 250 million lines of C++ code that depend on this library—we aren’t going to make API changes lightly, but it must be possible. To that end, Abseil explicitly does not promise ABI compatibility, but does promise a slightly limited form of API compatibility: we won’t make a breaking API change without also
providing
 an automated refactoring tool that will transform code from the old API to the new transparently. We feel that shifts the risk of unexpected costs significantly in favor of users: no matter what version a dependency was written against, a user of that dependency and Abseil should be able to use the most current version. The highest cost should be “run this tool,” and presumably send the resulting patch for review in the mid-level dependency (
liba
 or
libb
, continuing our example from earlier). In practice, the project is new enough that we haven’t had to make any significant API breaking changes. We can’t say how well this will work for the ecosystem as a whole, but in theory, it seems like a good balance for stability versus ease of upgrade.

Boost

By comparison, the Boost C++ library makes no

 promises

of
compatibility between versions
. Most code doesn’t change, of course, but “many of the Boost libraries are actively maintained and improved, so backward compatibility with prior version isn’t always possible.” Users are advised to upgrade only at a period in their project life cycle in which some change will not cause problems. The goal for Boost is fundamentally different than the standard library or Abseil: Boost is an experimental proving ground. A particular release from the Boost stream is probably perfectly stable and appropriate for use in many projects, but Boost’s project goals do not prioritize compatibility between versions—other long-lived projects might experience some friction keeping up to date. The Boost developers are every bit as expert as the developers for the standard library
4
—none of this is about technical expertise: this is purely a matter of what a project does or does not promise and prioritize.

Looking at the libraries in this discussion, it’s important to recognize that these compatibility issues are
software engineering
 issues, not
programming
 issues. You can download something like Boost with no compatibility promise and embed it deeply in the most critical, long-lived systems in your organization; it will
work
 just fine. All of the concerns here are about how those dependencies will change over time, keeping up with updates, and the difficulty of getting developers to worry about maintenance instead of just getting features working. Within Google, there is a constant stream of guidance directed to our engineers to help them consider this difference between “I got it to work” and “this is working in a supported fashion.” That’s unsurprising: it’s basic application of Hyrum’s Law, after all.

Put more broadly: it is important to realize that dependency management has a wholly different nature in a programming task versus a software engineering task. If you’re in a problem space for which maintenance over time is relevant, dependency management is difficult. If you’re purely developing a solution for today with no need to ever update anything, it is perfectly reasonable to grab as many readily available dependencies as you like with no thought of how to use them responsibly or plan for upgrades. Getting your program to work today by violating everything in SD-8 and also relying on binary compatibility from Boost and Abseil works fine…so long as you never upgrade the standard library, Boost, or Abseil, and neither does anything that depends on you.
```

<a id="software-engineering-at-google-ch21-002"></a>
## software-engineering-at-google-ch21-002 — Documentation and prohibitive names do not ensure safe changes

Source: [ch21.html](../../../../books/software-engineering-at-google/ch21.html); reading unit `ch21`, lines 472–490.

Attribution: Titus Winters; Hyrum Law quotation attributed to Hyrum Wright

Context: Explicit warnings in documentation or an internal-use name do not eliminate real dependencies on observable behavior.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
SemVer Might Overpromise

On the flip side, the application of SemVer makes the

explicit assumption

 that an API provider’s estimate of compatibility can be fully predictive and that changes fall into three buckets: breaking (by modification or removal), strictly additive, or non-API-impacting. If SemVer is a perfectly faithful representation of the risk of a change by classifying syntactic and semantic changes, how do we characterize a change that adds a one-millisecond delay to a time-sensitive API? Or, more plausibly: how do we characterize a change that alters the format of our logging output? Or that alters the order that we import external dependencies? Or that alters the order that results are returned in an “unordered” stream? Is it reasonable to assume that those changes are “safe” merely because those aren’t part of the syntax or contract of the API in question? What if the documentation said “This may change in the future”? Or the API was named “ForInternalUseByLibBaseOnlyDoNotTouchThisIReallyMeanIt?”
11

The idea that SemVer patch versions, which in theory are only changing implementation details, are “safe” changes absolutely runs afoul of Google’s experience with Hyrum’s Law—“With a sufficient number of users, every observable behavior of your system will be depended upon by someone.” Changing the order that dependencies are imported, or changing the output order for an “unordered” producer will, at scale, invariably break assumptions that some consumer was (perhaps incorrectly) relying upon. The very term “breaking change” is misleading: there are changes that are theoretically breaking but safe in practice (removing an unused API). There are also changes that are theoretically safe but break client code in practice (any of our earlier Hyrum’s Law examples). We can see this in any SemVer/dependency-management system for which the version-number requirement system allows for restrictions on the patch number: if you can say
liba requires libbase >1.1.14
 rather than
liba requires libbase 1.1
, that’s clearly an admission that there are observable differences in patch versions.

A change in isolation isn’t breaking or nonbreaking—
that statement can be evaluated only in the context of how it is being used. There is no absolute truth in the notion of “This is a breaking change”; a change can been seen to be breaking for only a (known or unknown) set of existing users and use cases. The reality of how we evaluate a change inherently relies upon information that isn’t present in the SemVer formulation of dependency management: how are downstream users consuming this dependency?

Because of this, a SemVer constraint solver might report that your dependencies work together when they don’t, either because a bump was applied incorrectly or because something in your dependency network had a Hyrum’s Law dependence on something that wasn’t considered part of the observable API surface. In these cases, you might have either build errors or runtime bugs, with no theoretical upper bound on their severity.
```

<a id="software-engineering-at-google-ch21-003"></a>
## software-engineering-at-google-ch21-003 — Publishing intent despite its limits

Source: [ch21.html](../../../../books/software-engineering-at-google/ch21.html); reading unit `ch21`, lines 492–519.

Attribution: Titus Winters

Context: Clear statements of compatibility intent provide a starting point even if nonbinding or ignored; preserves surrounding incentives and human-error caveats.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Motivations

There is a further argument that SemVer doesn’t always incentivize the creation of stable code.

 For a maintainer of an arbitrary dependency, there is variable systemic incentive to
not
 make breaking changes and bump major versions. Some projects care deeply about compatibility and will go to great lengths to avoid a major-version bump. Others are more aggressive, even intentionally bumping major versions on a fixed schedule. The trouble is that most users of any given dependency are indirect users—they wouldn’t have any significant reasons to be aware of an upcoming change. Even most direct users don’t subscribe to mailing lists or other release
notifications.

All of which combines to suggest that no matter how many users will be inconvenienced by adoption of an incompatible change to a popular API, the maintainers bear a tiny fraction of the cost of the resulting version bump. For maintainers who are also users, there can also be an incentive
toward
 breaking: it’s always easier to design a better interface in the absence of legacy constraints. This is part of why we think projects should publish clear statements of intent with respect to compatibility, usage, and breaking changes. Even if those are best-effort, nonbinding, or ignored by many users, it still gives us a starting point to reason about whether a breaking change/major version bump is “worth it,” without bringing in these conflicting incentive structures.

Go
 and
Clojure
 both handle this nicely: in their standard package management ecosystems, the equivalent of a major-version bump is expected to be a fully new package.

This has a certain sense of justice to it: if you’re willing to break backward compatibility for your package, why do we pretend this is the same set of APIs? Repackaging and renaming everything seems like a reasonable amount of work to expect from a provider in exchange for them taking the nuclear option and throwing away backward
compatibility.

Finally, there’s the human fallibility of the process. In general, SemVer version bumps should be applied to
semantic
 changes just as much as syntactic ones; changing the behavior of an API matters just as much as changing its structure. Although it’s plausible that tooling could be developed to evaluate whether any particular release involves syntactic changes to a set of public APIs, discerning whether there are meaningful and intentional semantic changes is computationally infeasible.
12
 Practically speaking, even the potential tools for identifying syntactic changes are limited. In almost all cases, it is up to the human judgement of the API provider whether to bump major, minor, or patch versions for any given change. If you’re relying on only a handful of professionally maintained dependencies, your expected exposure to this form of SemVer clerical error is probably low.
13
 If you have a network of thousands of dependencies underneath your product, you should be prepared for some amount of chaos simply from human error.
```

<a id="software-engineering-at-google-ch21-005"></a>
## software-engineering-at-google-ch21-005 — Undocumented behavior in the gflags forks

Source: [ch21.html](../../../../books/software-engineering-at-google/ch21.html); reading unit `ch21`, lines 665–704.

Attribution: Titus Winters

Context: The complete gflags case provides context for a downstream dependency on observable but undocumented behavior.

Related: [software-engineering-at-google-ch21-002](#software-engineering-at-google-ch21-002), [software-engineering-at-google-ch21-003](#software-engineering-at-google-ch21-003)

```text
Example: open sourcing gflags

For reputation loss, consider the case of something like Google’s experience circa 2006 open sourcing our C++ command-line flag libraries.

 Surely giving back to the open source community is a purely good act that won’t come back to haunt us, right? Sadly, no. A host of reasons conspired to make this good act into something that certainly hurt our reputation and possibly damaged the OSS community as well:

At the time, we didn’t have the ability to execute large-scale refactorings, so everything that used that library internally had to remain exactly the same—we couldn’t move the code to a new location in the codebase.

We segregated our repository into “code developed in-house” (which can be copied freely if it needs to be forked, so long as it is renamed properly) and “code that may have legal/licensing concerns” (which can have more nuanced usage requirements).

If an OSS project accepts code from outside developers, that’s generally a legal issue—the project originator doesn’t
own
 that contribution, they only have rights to it.

As a result, the gflags project was doomed to be either a “throw over the wall” release or a disconnected fork. Patches contributed to the project couldn’t be reincorporated into the original source inside of Google, and we couldn’t move the project within our monorepo because we hadn’t yet mastered that form of refactoring, nor could we make everything internally depend on the OSS version.

Further, like most organizations, our priorities have shifted and changed over time. Around the time of the original release of that flags library, we were interested in products outside of our traditional space (web applications, search), including things like Google Earth, which had a much more traditional distribution mechanism: precompiled binaries for a variety of platforms. In the late 2000s, it was unusual but not unheard of for a library in our monorepo, especially something low-level like flags, to be used on a variety of platforms. As time went on and Google grew, our focus narrowed to the point that it was extremely rare for any libraries to be built with anything other than our in-house configured toolchain, then deployed to our production fleet. The “portability” concerns for properly supporting an OSS project like
flags
 were nearly impossible to maintain: our internal tools simply didn’t have support for those platforms, and our average developer didn’t have to interact with external tools. It was a constant battle to try to maintain portability.

As the original authors and OSS supporters moved on to new companies or new teams, it eventually became clear that nobody internally was really supporting our OSS
flags
 project—nobody could tie that support back to the priorities for any particular team. Given that it was no specific team’s job, and nobody could say why it was important, it isn’t surprising that we basically let that project rot externally.
18
 The internal and external versions diverged slowly over time, and eventually some external developers took the external version and forked it, giving it some proper
attention.

Other than the initial “Oh look, Google contributed something to the open source world,” no part of that made us look good, and yet every little piece of it made sense given the priorities of our engineering organization. Those of us who have been close to it have learned, “Don’t release things without a plan (and a mandate) to support it for the long term.” Whether the whole of Google engineering has learned that or not remains to be seen. It’s a big organization.

Above and beyond the nebulous “We look bad,” there are also parts of this story that illustrate how we can be subject to technical problems stemming from poorly released/poorly maintained external dependencies. Although the
flags
 library was shared but ignored, there were still some Google-backed open source projects, or projects that needed to be shareable outside of our monorepo ecosystem. Unsurprisingly, the authors of those other projects were able to identify
19
 the common API subset between the internal and external forks of that library. Because that common subset stayed fairly stable between the two versions for a long period, it silently became “the way to do this” for the rare teams that had unusual portability requirements between roughly 2008 and 2017. Their code could build in both internal and external ecosystems, switching out forked versions of the
flags
 library depending on environment.

Then, for unrelated reasons, C++ library teams began tweaking observable-but-not-documented pieces of the internal
flag
 implementation. At that point, everyone who was depending on the stability and equivalence of an unsupported external fork started screaming that their builds and releases were suddenly broken. An optimization opportunity worth some thousands of aggregate CPUs across Google’s fleet was significantly delayed, not because it was difficult to update the API that 250 million lines of code depended upon, but because a tiny handful of projects were relying on unpromised and unexpected things. Once again, Hyrum’s Law affects software changes, in this case even for forked APIs maintained by separate organizations.
```

<a id="software-engineering-at-google-ch21-004"></a>
## software-engineering-at-google-ch21-004 — Private access and behavioral intention footnotes

Source: [ch21.html](../../../../books/software-engineering-at-google/ch21.html); reading unit `ch21`, lines 776–779.

Attribution: Titus Winters

Context: Footnote qualifies long prohibitive names and recommends language access controls; next footnote distinguishes intentional behavior changes from fixes.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
11
It’s worth noting: in our experience, naming like this doesn’t fully solve the problem of users reaching in to access private APIs. Prefer languages that have good control over public/private access to APIs of all forms.
12
In a world of ubiquitous unit tests, we could identify changes that required a change in test behavior, but it would still be difficult to algorithmically separate “This is a behavioral change” from “This is a bug fix to a behavior that wasn’t intended/promised.”
```

<a id="software-engineering-at-google-ch22-005"></a>
## software-engineering-at-google-ch22-005 — Inconsistent file naming and migration

Source: [ch22.html](../../../../books/software-engineering-at-google/ch22.html); reading unit `ch22`, lines 67–81.

Attribution: Hyrum Wright

Context: Case study of the stl_util.h and map-util.h separator inconsistency and the reported effect of changing it.

```text
Case Study: Filling Potholes

Although the LSC systems at Google are used for high-priority migrations, we’ve also discovered that just having them available opens up opportunities for various small fixes across our codebase, which just wouldn’t have been possible without them.

 Much like transportation infrastructure tasks consist of building new roads as well as repairing old ones, infrastructure groups at Google spend a lot of time fixing existing code, in addition to developing new systems and moving users to them.

For example, early in our history, a template library emerged to supplement the C++ Standard Template Library. Aptly named the Google Template Library, this library consisted of several header files’ worth of implementation. For reasons lost in the mists of time, one of these header files was named
stl_util.h
 and another was named
map-util.h
 (note the different separators in the file names). In addition to driving the consistency purists nuts, this difference also led to reduced productivity, and engineers had to remember which file used which separator, and only discovered when they got it wrong after a potentially lengthy compile cycle.

Although fixing this single-character change might seem pointless, particularly across a codebase the size of Google’s, the maturity of our LSC tooling and process enabled us to do it with just a couple weeks’ worth of background-task effort. Library authors could find and apply this change en masse without having to bother end users of these files, and we were able to quantitatively reduce the number of build failures caused by this specific issue. The resulting increases in productivity (and happiness) more than paid for the time to make the change.

As the ability to make changes across our entire codebase has improved, the diversity of changes has also expanded, and we can make some engineering decisions knowing that they aren’t immutable in the future. Sometimes, it’s worth the effort to fill a few potholes.
```

<a id="software-engineering-at-google-ch22-001"></a>
## software-engineering-at-google-ch22-001 — Change rationale and low-value text churn

Source: [ch22.html](../../../../books/software-engineering-at-google/ch22.html); reading unit `ch22`, lines 270–289.

Attribution: Hyrum Wright

Context: Oversight for broad edits includes typo cleanup without recurrence prevention and explaining large changes to local owners.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Policies and Culture

As we’ve described in
Version Control and Branch Management
, Google stores the bulk

 of its source code in a single monolithic repository (monorepo), and every engineer has visibility into almost all of this code. This high degree of openness means that any engineer can edit any file and send those edits for review to those who can approve them. However, each of those edits has costs, both to generate as well as review.

10

Historically, these costs have been somewhat symmetric, which limited the scope of changes a single engineer or team could generate. As Google’s LSC tooling improved, it became easier to generate a large number of changes very cheaply, and it became equally easy for a single engineer to impose a burden on a large number of reviewers across the company. Even though we want to encourage widespread improvements to our codebase, we want to make sure there is some oversight and thoughtfulness behind them, rather than indiscriminate tweaking.
11

The end result is a lightweight approval process for teams and individuals seeking to make LSCs across Google. This process is overseen by a group of experienced engineers who are familiar with the nuances of various languages, as well as invited domain experts for the particular change in question. The goal of this process is not to prohibit LSCs, but to help change authors produce the best possible changes, which make the best use of Google’s technical and human capital. Occasionally, this group might suggest that a cleanup just isn’t worth it: for example, cleaning up a common typo without any way of preventing recurrence.

Related to these policies was a shift in cultural norms surrounding LSCs.

 Although it is important for code owners to have a sense of responsibility for their software, they also needed to learn that LSCs were an important part of Google’s effort to scale our software engineering practices. Just as product teams are the most familiar with their own software, library infrastructure teams know the nuances of the infrastructure, and getting product teams to trust that domain expertise is an important step toward social acceptance of LSCs. As a result of this culture shift, local product teams have grown to trust LSC authors to make changes relevant to those authors’ domains.

Occasionally, local owners question the purpose of a specific commit being made as part of a broader LSC, and change authors respond to these comments just as they would other review comments. Socially, it’s important that code owners understand the changes happening to their software, but they also have come to realize that they don’t hold a veto over the broader LSC. Over time, we’ve found that a good FAQ and a solid historic track record of improvements have generated widespread endorsement of LSCs throughout Google.
```

<a id="software-engineering-at-google-ch22-002"></a>
## software-engineering-at-google-ch22-002 — Automated changes remain readable

Source: [ch22.html](../../../../books/software-engineering-at-google/ch22.html); reading unit `ch22`, lines 343–358.

Attribution: Hyrum Wright

Context: Formatting should make automated changes intelligible to reviewers and future readers.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Language Support

LSCs at Google are typically done on a per-language basis, and some languages support them much more easily than others.

 We’ve found that language features such as type aliasing and forwarding functions are invaluable for allowing existing users to continue to function while we introduce new systems and migrate users to them non-atomically. For languages that lack these features, it is often difficult to migrate systems incrementally.
12

We’ve also found that statically typed languages are much easier to perform large automated changes in than dynamically typed languages. Compiler-based tools along with strong static analysis provide a significant amount of information that we can use to build tools to affect LSCs and reject invalid transformations before they even get to the testing phase. The unfortunate result of this is that languages like Python, Ruby, and JavaScript that are dynamically typed are extra difficult for maintainers. Language choice is, in many respects, intimately tied to the question of code lifespan: languages that tend to be viewed as more focused on developer productivity tend to be more difficult to maintain. Although this isn’t an intrinsic design requirement, it is where the current state of the art happens to be.

Finally, it’s worth pointing out that automatic language formatters are a crucial part of the LSC infrastructure. Because we work toward optimizing our code for readability, we want to make sure that any changes produced by automated tooling are intelligible to both immediate reviewers and future readers of the code. All of the LSC-generation tools run the automated formatter appropriate to the language being changed as a separate pass so that the change-specific tooling does not need to
concern
 itself with formatting specifics. Applying automated formatting, such as
google-java-format
 or
clang-format
, to our codebase means that automatically produced changes will “fit in” with code written by a human, reducing future development friction. Without automated formatting, large-scale automated changes would never have become the accepted status quo at Google.
```

<a id="software-engineering-at-google-ch22-003"></a>
## software-engineering-at-google-ch22-003 — Explaining a migration to unfamiliar engineers

Source: [ch22.html](../../../../books/software-engineering-at-google/ch22.html); reading unit `ch22`, lines 393–405.

Attribution: Hyrum Wright

Context: Proposal, FAQ, and change descriptions make reasoning explicit for readers outside the domain.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Authorization

We ask potential authors to fill out a brief document explaining the reason for a proposed change, its estimated impact across

 the codebase (i.e., how many smaller shards the large change would generate), and answers to any questions potential reviewers might have.

 This process also forces authors to think about how they will describe the change to an engineer unfamiliar with it in the form of an FAQ and proposed change description. Authors also get “domain review” from the owners of the API being refactored.

This proposal is then forwarded to an email list with about a dozen people who have oversight over the entire process. After discussion, the committee gives feedback on how to move forward. For example, one of the most common changes made by the committee is to direct all of the code reviews for an LSC to go to a single "global approver." Many first-time LSC authors tend to assume that local project owners should review everything, but for most mechanical LSCs, it’s cheaper to have a single expert understand the nature of the change and build automation around reviewing it properly.

After the change is approved, the author can move forward in getting their change submitted. Historically, the committee has been very liberal with their approval,
13
 and often gives approval not just for a specific change, but also for a broad set of related changes. Committee members can, at their discretion, fast-track obvious changes without the need for full deliberation.
```

<a id="software-engineering-at-google-ch22-006"></a>
## software-engineering-at-google-ch22-006 — Generating changes readable by people

Source: [ch22.html](../../../../books/software-engineering-at-google/ch22.html); reading unit `ch22`, lines 409–424.

Attribution: Hyrum Wright

Context: Automated migration output is discussed in relation to readable source, style guides, and formatting.

Related: [software-engineering-at-google-ch22-002](#software-engineering-at-google-ch22-002), [software-engineering-at-google-ch22-004](#software-engineering-at-google-ch22-004)

```text
Change Creation

After getting the required approval, an LSC author will begin to produce the actual code edits.

Sometimes, these can be generated comprehensively into a single large global change that will be subsequently sharded into many smaller independent pieces. Usually, the size of the change is too large to fit in a single global change, due to technical limitations of the underlying version control system.

The change generation process should be as automated as possible so that the parent change can be updated as users backslide into old uses
14
 or textual merge conflicts occur in the changed code. Occasionally, for the rare case in which technical tools aren’t able to generate the global change, we have sharded change generation across humans (see
Case Study: Operation RoseHub
). Although much more labor intensive than automatically generating changes, this allows global changes to happen much more quickly for time-sensitive applications.

Keep in mind that we optimize for human readability of our codebase, so whatever tool generates changes, we want the resulting changes to look as much like human-generated changes as possible. This requirement leads to the necessity of style guides and automatic formatting tools (see
Style Guides and Rules
).
15
```

<a id="software-engineering-at-google-ch22-004"></a>
## software-engineering-at-google-ch22-004 — Comment-spelling disputes and rejected changes

Source: [ch22.html](../../../../books/software-engineering-at-google/ch22.html); reading unit `ch22`, lines 555–572.

Attribution: Hyrum Wright

Context: Footnotes explicitly mention gray versus grey in comments, British/American spelling edits, and changing approval thresholds.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
10
There are obvious technical costs here in terms of compute and storage, but the human costs in time to review a change far outweigh the technical ones.
11
For example, we do not want the resulting tools to be used as a mechanism to fight over the proper spelling of “gray” or “grey” in comments.
12
In fact, Go recently introduced these kinds of language features specifically to support large-scale refactorings (see
https://talks.golang.org/2016/refactor.article
).
13
The only kinds of changes that the committee has outright rejected have been those that are deemed dangerous, such as converting all
NULL
 instances to
nullptr
, or extremely low-value, such as changing spelling from British English to American English, or vice versa. As our experience with such changes has increased and the cost of LSCs has dropped, the threshold for approval has as well.
14
This happens for many reasons: copy-and-paste from existing examples, committing changes that have been in development for some time, or simply reliance on old habits.
15
In actuality, this is the reasoning behind the original work on clang-format for C++.
```

<a id="software-engineering-at-google-ch23-001"></a>
## software-engineering-at-google-ch23-001 — Accessible history and readable feedback

Source: [ch23.html](../../../../books/software-engineering-at-google/ch23.html); reading unit `ch23`, lines 114–122.

Attribution: Rachel Tannenbaum

Context: Test and bug history supports learning and diagnosis; test output should make feedback understandable.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Accessible and actionable feedback

It’s also important that feedback from CI be widely accessible. In addition to our open culture around code visibility, we feel similarly about our test reporting. We have a unified test reporting system in which anyone can easily look up a build or test run, including all logs (excluding user Personally Identifiable Information [PII]), whether for an individual engineer’s local run or on an automated development or staging build.

Along with logs, our test reporting system provides a detailed history of when build or test targets began to fail, including audits of where the build was cut at each run, where it was run, and by whom. We also have a system for flake classification, which uses statistics to classify flakes at a Google-wide level, so engineers don’t need to figure this out for themselves to determine whether their change broke another project’s test (if the test is flaky: probably not).

Visibility into test history empowers engineers to share and collaborate on feedback, an essential requirement for disparate teams to diagnose and learn from integration failures between their systems. Similarly, bugs (e.g., tickets or issues) at Google are open with full comment history for all to see and learn from (with the exception, again, of customer PII).

Finally, any feedback from CI tests should not just be accessible but actionable—easy to use to find and fix problems. We’ll look at an example of improving user-unfriendly feedback in our case study later in this chapter. By improving test output readability, you automate the understanding of feedback.
```

<a id="software-engineering-at-google-ch23-002"></a>
## software-engineering-at-google-ch23-002 — Indecipherable logs and improved explanation

Source: [ch23.html](../../../../books/software-engineering-at-google/ch23.html); reading unit `ch23`, lines 565–587.

Attribution: Rachel Tannenbaum

Context: Takeout case study retains the diagnostic cost and links in failure messages that reduced manual assistance.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Scenario #2: Indecipherable test logs

Problem:
 As Takeout incorporated more Google products, it grew into a mature platform that allowed product teams to insert plug-ins, with product-specific data-fetching code, directly into Takeout's binary. For example, the Google Photos plug-in knows how to fetch photos, album metadata, and the like. Takeout expanded from its original “handful” of products to now integrate with more than
90
.

Takeout’s end-to-end tests dumped its failures to a log, and this approach didn’t scale to 90 product plug-ins. As more products integrated, more failures were introduced. Even though the team was running the tests earlier and more often with the addition of the post-submit CI, multiple failures would still pile up inside and were easy to miss. Going through these logs became a frustrating time sink, and the tests were almost always failing.

What the team did

The team refactored the tests into a dynamic, configuration-based suite (using a
parameterized test runner
) that reported results in a friendlier UI, clearly showing individual test results as green or red: no more digging through logs. They also made failures much easier to debug, most notably, by displaying failure information, with links to logs, directly in the error message. For example, if Takeout failed to fetch a file from Gmail, the test would dynamically construct a link that searched for that file’s ID in the Takeout logs and include it in the test failure message. This automated much of the debugging process for product plug-in engineers and required less of the Takeout team’s assistance in sending them logs, as demonstrated in
Figure 23-3
.

Figure 23-3.
The team’s involvement in debugging client failures

Lesson learned

Accessible, actionable feedback from CI reduces test failures and improves productivity. These initiatives reduced the Takeout team’s involvement in debugging client (product plug-in) test failures by 35%.
```

<a id="software-engineering-at-google-ch23-003"></a>
## software-engineering-at-google-ch23-003 — Commenting out tests versus tracked disablement

Source: [ch23.html](../../../../books/software-engineering-at-google/ch23.html); reading unit `ch23`, lines 610–645.

Attribution: Rachel Tannenbaum

Context: Commented-out failures are easy to forget. Preserves bug-tag alternative, automatic cleanup, flaky-test exception, and remaining manual burden.

Transcription/context notes: Original Figures 23-4 and 23-5 visually inspected: the former plots % Disabled, % Passed, and % Green over dates; the latter plots mean days to close bugs over dates. Curves remain graphical in the original PNGs; no numerical values inferred from pixels.

```text
Scenario #4: Keeping it green

Problem:
 As the platform supported more product plug-ins, which each included end-to-end tests, these tests would fail and the end-to-end test suites were nearly always broken. The failures could not all be immediately fixed. Many were due to bugs in product plug-in binaries, which the Takeout team had no control over. And some failures mattered more than others—low-priority bugs and bugs in the test code did not need to block a release, whereas higher-priority bugs did. The team could easily disable tests by commenting them out, but that would make the failures too easy to forget about.

One common source of failures: tests would break when product plug-ins were rolling out a feature. For example, a playlist-fetching feature for the YouTube plug-in might be enabled for testing in dev for a few months before being enabled in prod. The Takeout tests only knew about one result to check, so that often resulted in the test needing to be disabled in particular environments and manually curated as the feature rolled out.

What the team did

The team came up with a strategic way to disable failing tests by tagging them with an associated bug and filing that off to the responsible team (usually a product plug-in team). When a failing test was tagged with a bug, the team’s testing framework would suppress its failure. This allowed the test suite to stay green and still provide confidence that everything else, besides the known issues, was passing, as illustrated in
Figure 23-4
.

Figure 23-4.
Achieving greenness through (responsible) test disablement

For the rollout problem, the team added capability for plug-in engineers to specify the name of a feature flag, or ID of a code change, that enabled a particular feature along with the output to expect both with and without the feature. The tests were equipped to query the test environment to determine whether the given feature was enabled there and verified the expected output accordingly.

When bug tags from disabled tests began to accumulate and were not updated, the team automated their cleanup. The tests would now check whether a bug was closed by querying our bug system’s API. If a tagged-failing test actually passed and was passing for longer than a configured time limit, the test would prompt to clean up the tag (and mark the bug fixed, if it wasn’t already). There was one exception for this strategy: flaky tests. For these, the team would allow a test to be tagged as flaky, and the system wouldn’t prompt a tagged “flaky” failure for cleanup if it passed.

These changes made a mostly self-maintaining test suite, as illustrated in
Figure 23-5
.

Figure 23-5.
Mean time to close bug, after fix submitted

Lessons learned

Disabling failing tests that can’t be immediately fixed is a practical approach to keeping your suite green, which gives confidence that you’re aware of all test failures. Also, automating the test suite’s maintenance, including rollout management and updating tracking bugs for fixed tests, keeps the suite clean and prevents technical debt. In DevOps parlance, we could call the metric in
Figure 23-5
 MTTCU: mean time to clean up.

Future improvement

Automating the filing and tagging of bugs would be a helpful next step. This is still a manual and burdensome process. As mentioned earlier, some of our larger teams already do this.
```

<a id="software-engineering-at-google-ch25-001"></a>
## software-engineering-at-google-ch25-001 — Configuration documentation deteriorates

Source: [ch25.html](../../../../books/software-engineering-at-google/ch25.html); reading unit `ch25`, lines 385–407.

Attribution: Onufry Wojtaszczyk

Context: Contrasts documentation and tribal knowledge of CLI parameters with checked-in declarative configuration, retaining scale and automation context.

Transcription/context notes: Numbered derived text retains source wording and extraction line breaks.

```text
Submitted Configuration

The Borg scheduler receives the configuration of

 a replicated service or batch job to run in the cell as the contents of a Remote Procedure Call (RPC). It’s possible for the operator of the service to manage it by using a command-line interface (CLI) that sends those RPCs, and have the parameters to the CLI stored in shared documentation, or in their head.

Depending on documentation and tribal knowledge over code submitted to a repository is rarely a good idea in general because both documentation and tribal knowledge have a tendency to deteriorate over time (see
Knowledge Sharing
). However, the next natural step in the evolution—wrapping the execution of the CLI in a locally developed script—is still inferior to using a dedicated configuration language to specify the configuration of your service.

Over time, the runtime presence of a logical service will typically grow beyond a single set of replicated containers in one datacenter across many axes:

It will spread its presence across multiple datacenters (both for user affinity and failure resistance).

It will fork into having staging and development environments in addition to the production environment/configuration.

It will accrue additional replicated containers of different types in the form of attached services, like a memcached accompanying the service.

Management of the service is much simplified if this complex setup can be expressed in a standardized configuration language that allows easy expression of standard operations (like “update my service to the new version of the binary, but taking down no more than 5% of capacity at any given time”).

A standardized configuration language provides standard configuration that other teams can easily include in their service definition. As usual, we emphasize the value of such standard configuration over time and scale. If every team writes a different snippet of custom code to stand up their memcached service, it becomes very difficult to perform organization-wide tasks like swapping out to a new memcache implementation (e.g., for performance or licencing reasons) or to push a security update to all the memcache deployments. Also note that such a standardized configuration language is a requirement for automation in deployment (see
Continuous Delivery
).
```
